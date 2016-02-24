from django.db import models
from . import settings
from django.db.models.fields.related import ReverseSingleRelatedObjectDescriptor
from django.db import connections, router
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from jsonfield import JSONField


class LanguageField(models.CharField):
    LANGUAGE_CHOICES = [
        (lang_code, _(lang_name))
        for lang_code, lang_name
        in settings.T10E_LANGUAGE_CHOICES
    ]

    def __init__(self, *args, **kwargs):
        # 10 chars should be enough, see http://www.i18nguy.com/unicode/language-identifiers.html
        # (note: 2 or 5 chars are definately NOT enough)
        kwargs.setdefault('max_length', 10)
        # Set default language choices
        # TODO: Currently selected language should always stay in choices, even if this value is not
        #       in settings.LANGUAGES any more
        kwargs.setdefault('choices', self.LANGUAGE_CHOICES)
        super(LanguageField, self).__init__(*args, **kwargs)


class TranslatableReverseSingleRelatedObjectDescriptor(ReverseSingleRelatedObjectDescriptor):
    def __set__(self, instance, value):
        # This method just replaces any objects passed in with the primary translation / translation set object.
        if (hasattr(value, 'translation_set_id')):
            if value.translation_set_id != value.pk:
                assert value.translation_set_id, (
                    "{value}: translation_set is required".format(value=value))
                value = value.translation_set
        return super(TranslatableReverseSingleRelatedObjectDescriptor, self).__set__(instance, value)


# TODO: This may extend existing Django classes later (although the core really is hard to understand)
class TranslatableForeignRelatedObjectsDescriptor(object):
    def __init__(self, field):
        self.field = field

    def __get__(self, instance, instance_type=None):
        if instance is None:
            return self
        return self.translatable_related_manager_cls(instance)

    @cached_property
    def translatable_related_manager_cls(self):
        superclass = self.field.rel.to._default_manager.__class__
        rel_field = self.field.rel.to._meta.get_field('translation_set')
        rel_model = self.field.rel.to
        obj_field = self.field

        # Based on ForeignRelatedObjectsDescriptor.related_manager_cls's RelatedManager
        class TranslatableRelatedManager(superclass):
            def __init__(self, instance):
                super(TranslatableRelatedManager, self).__init__()
                self.instance = instance
                self.core_filters = {'%s__exact' % rel_field.name: getattr(instance, obj_field.attname)}
                self.model = rel_model

            def get_queryset(self):
                try:
                    return self.instance._prefetched_objects_cache[rel_field.related_query_name()]
                except (AttributeError, KeyError):
                    db = self._db or router.db_for_read(self.model, instance=self.instance)
                    qs = super(TranslatableRelatedManager, self).get_queryset().using(db).filter(**self.core_filters)
                    empty_strings_as_null = connections[db].features.interprets_empty_strings_as_nulls
                    for field in rel_field.foreign_related_fields:
                        val = getattr(self.instance, field.attname)
                        if val is None or (val == '' and empty_strings_as_null):
                            return qs.none()
                    #qs._known_related_objects = {rel_field: {self.instance.pk: self.instance}}
                    return qs

        return TranslatableRelatedManager


# TODO: Handle deletion of primary translation
class TranslatableForeignKey(models.ForeignKey):
    def __init__(self, *args, **kwargs):
        self.translations_name = kwargs.pop('translations_name', '%s_translations')
        super(TranslatableForeignKey, self).__init__(*args, **kwargs)

    def _get_translations_name(self):
        if '%s' in self.translations_name:
            return self.translations_name % self.name
        else:
            return self.translations_name

    def contribute_to_class(self, cls, name, virtual_only=False):
        super(TranslatableForeignKey, self).contribute_to_class(cls, name, virtual_only)
        # we overwrite the descriptor, so we can always use the translation_set_id for foreign keys
        setattr(cls, self.name, TranslatableReverseSingleRelatedObjectDescriptor(self))
        # in addition we add an new attribute to access all translations
        setattr(cls, self._get_translations_name(), TranslatableForeignRelatedObjectsDescriptor(self))


class UnsyncedI18nFieldsField(JSONField):
    """Field contains a set of fields that should explicitly be not synced
    between translations.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('blank', True)
        kwargs.setdefault('null', True)
        super(UnsyncedI18nFieldsField, self).__init__(*args, **kwargs)

    def pre_init(self, value, obj):
        value = super(UnsyncedI18nFieldsField, self).pre_init(value, obj)
        if value in (None, ''):
            value = []
        assert isinstance(value, (tuple, list, set, frozenset)), \
            'Expected list, tuple or set, got: %r' % type(value)
        value = list(set(value))
        return value

    def pre_save(self, model_instance, add):
        """Convert JSON object to a string"""
        value = getattr(model_instance, self.attname)
        assert isinstance(value, list)
        if len(value) == 0:
            return None
        return list(set(value))

    def value_from_object(self, model_instance):
        value = getattr(model_instance, self.attname)
        assert isinstance(value, list)
        return list(set(value))


try:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], ["^django_t10e\.fields\.LanguageField"])
    add_introspection_rules([], ["^django_t10e\.fields\.TranslatableForeignKey"])
    add_introspection_rules([], ["^django_t10e\.fields\.UnsyncedI18nFieldsField"])
except ImportError:
    pass
