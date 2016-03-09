from django.db import models
from django.db import transaction
from django.db.models.fields import FieldDoesNotExist
from django_cloneable.models import ModelCloneHelper
from .fields import UnsyncedI18nFieldsField
from .translationstatus import TranslationStatusMixin


class UpdateTranslationsMixin(TranslationStatusMixin, models.Model):
    """
    Helper to syncronize fields that do not contain translatable content.

    Subclasses usually only call ``update_translations``.
    """

    unsynced_i18n_fields = UnsyncedI18nFieldsField()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """
        Always try to keep the translation status up to date.
        """
        self.update_translation_status()
        return super(UpdateTranslationsMixin, self).save(*args, **kwargs)

    def get_synced_i18n_fields(self):
        """
        Override this method in subclasses to define which fields should be
        syncronized between translations.
        """
        return ['unsynced_i18n_fields']

    def get_to_be_synced_i18n_fields(self):
        return list(
            set(self.get_synced_i18n_fields()) -
            set(self.get_unsynced_i18n_fields()))

    def get_unsynced_i18n_fields(self):
        """
        This method defines an exclude list of fields that should NOT be synced.
        It takes precendence over values from ``get_synced_i18n_fields()``.
        """
        return list(self.unsynced_i18n_fields)

    @transaction.atomic
    def update_translations(self):
        """
        Entry point for the feature of this mixin.
        """
        self.create_required_translations()
        for translation in self.translations().exclude(pk=self.pk):
            if translation.shall_update_from_translation(self):
                translation.update_from_translation(self)
            if self._has_translation_status_field():
                translation.update_translation_status()
                translation.save()

    def shall_update_from_translation(self, translation):
        """
        Returns ``True`` if any of the synced fields differs between `self` and
        `translation`.
        """
        return any(
            self.shall_update_field_from_translation(translation, field_name)
            for field_name in translation.get_to_be_synced_i18n_fields())

    def shall_update_field_from_translation(self, translation, field_name):
        try:
            field = self._meta.get_field(field_name)
        except FieldDoesNotExist:
            field = None
        local = getattr(self, field_name)
        new_value = getattr(translation, field_name)
        if field:
            is_reverse_relation = (field.one_to_many and field.auto_created)
            if isinstance(field, models.ManyToManyField):
                local = list(local.values_list('pk', flat=True))
                new_value = list(new_value.values_list('pk', flat=True))
                return local != new_value
            elif is_reverse_relation:
                # Comparing relations can be a bit tricky. What fields should
                # we take into account? We just do all fields except the
                # primary key and m2ms.
                relation = field
                rel_fields = [
                    rel_field
                    for rel_field in relation.field.model._meta.get_fields()
                    if (
                        not rel_field.is_relation or
                        rel_field.one_to_one or
                        (rel_field.many_to_one and rel_field.related_model))]
                compare_field_names = [
                    rel_field.name for rel_field in rel_fields
                    if (
                        # Skip the field that is the ForeignKey to the to be
                        # translated model.
                        rel_field.name != relation.field.name and
                        # Skip primary key fields, those will always differ by
                        # definition.
                        not getattr(rel_field, 'primary_key', False) and
                        # Skip many to many fields.
                        not isinstance(rel_field, models.ManyToManyField))]
                local = list(local.values(*compare_field_names).order_by(*compare_field_names))
                new_value = list(new_value.values(*compare_field_names).order_by(*compare_field_names))
        return local != new_value

    def update_from_translation(self, translation):
        """
        This should be called on the to-be-updated translation.
        So ``de.update_from_translation(en)`` will update ``de``.

        It is this way around since the method should belong to the object it
        modifies.
        """
        self.update_translation_fields(translation)
        self.save()

    def update_translation_fields(self, translation):
        """
        Copy all synced fields from `translation` to `save`.
        """
        for field_name in translation.get_to_be_synced_i18n_fields():
            self.update_translation_field(translation, field_name)

    def update_translation_field(self, translation, field_name):
        """
        Copy the data from the origin translation to the current object on the
        give field. It special cases ManyToManyField as it needs to copy the
        relation objects (the through model data).
        """
        try:
            field = self._meta.get_field(field_name)
        except FieldDoesNotExist:
            field = None
        reverse_relations = dict(
            (relation.get_accessor_name(), relation)
            for relation in self._meta.get_all_related_objects())
        if isinstance(field, models.ManyToManyField):
            if field.rel.through and not field.rel.through._meta.auto_created:
                rel_name = field.m2m_field_name()

                # Clear the relation ...
                self_m2m_objs = field.rel.through._default_manager.filter(**{
                    rel_name: self,
                })
                self_m2m_objs.delete()

                # Copy it back from the translation ...
                m2m_objs = field.rel.through._default_manager.filter(**{
                    rel_name: translation,
                })

                # through-model could be cloneable
                if hasattr(field.rel.through, 'clone'):
                    for m2m_obj in m2m_objs:
                        m2m_obj.clone(attrs={rel_name: self})
                else:
                    for m2m_obj in m2m_objs:
                        ModelCloneHelper(m2m_obj).clone(attrs={rel_name: self})
            # normal m2m, this is easy
            else:
                new_value = getattr(translation, field_name).all()
                setattr(self, field_name, new_value)
        elif field_name in reverse_relations:
            relation = reverse_relations[field_name]
            reverse_queryset = getattr(self, field_name).all()
            reverse_translation_queryset = getattr(translation, field_name).all()
            reverse_queryset.delete()
            for related in reverse_translation_queryset:
                # Clone related object, but point it to the new translation
                # (self in this case).
                related.clone(attrs={
                    relation.field.name: self,
                })
        else:
            new_value = getattr(translation, field_name)
            setattr(self, field_name, new_value)

    def prepare_translation(self, language, exclude_fields=None):
        if exclude_fields is None:
            exclude_fields = []
        exclude_fields.extend(self.get_unsynced_i18n_fields())
        return super(UpdateTranslationsMixin, self).prepare_translation(
            language, exclude_fields=exclude_fields)
