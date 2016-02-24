from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils.translation import get_language
from django_cloneable.models import CloneableMixin

from .managers import TranslatableManager
from .fields import LanguageField
from .updatetranslations import UpdateTranslationsMixin  # noqa
from .translationstatus import TranslationStatusMixin  # noqa


LANGUAGES = settings.LANGUAGES


class TranslatableBaseMixin(CloneableMixin):
    class Meta:
        abstract = True
        unique_together = (
            ('translation_set', 'language',),
        )

    translation_set = models.ForeignKey('self', null=True, blank=True, related_name='base_translation_for')
    language = LanguageField(db_index=True)

    objects = TranslatableManager()

    def save(self, *args, **kwargs):
        result = super(TranslatableBaseMixin, self).save(*args, **kwargs)
        if not self.translation_set_id:
            self.translation_set_id = self.pk
            self.__class__.objects.filter(pk=self.pk).update(translation_set=self.pk)
        return result

    def translations(self):
        return self.__class__.objects.translations(self)

    def prepare_translation(self, language, exclude_fields=None):
        attrs = {
            'translation_set': self.translation_set,
            'language': language,
        }
        # Set contents fields to None.
        for contents_field in self.get_contents_fields():
            attrs[contents_field] = None
        return self.clone(commit=False, attrs=attrs, exclude=exclude_fields)

    def create_translation(self, language):
        translation = self.prepare_translation(language)
        translation.save()
        translation.clone_m2m()
        return translation

    def get_required_languages(self):
        """No languages are required in this base implementation."""
        return []

    def create_required_translations(self):
        """
        Ensure that all languages have a corresponding translation. You can
        limit the creation to a specific languages by providing the languages
        argument.
        """
        untranslated_languages = set(code for code, name in self.untranslated_languages())
        required_languages = set(self.get_required_languages())
        for language in untranslated_languages.intersection(required_languages):
            self.create_translation(language)


class TranslatableUtilsMixin(object):
    """
    Can be used by classes that proxy/delegate the TranslatableMixin to other
    classes. The delegator only needs to implement the following methods:

    - ``language`` (property)
    - ``translations()``
    """

    def translate(self, language=None):
        if language is None:
            language = get_language()
        if language == self.language:
            return self
        return self.translations().translate(language).get()

    def safe_translate(self, language=None):
        # Cache result for faster access when called multiple times.
        if not hasattr(self, '_safe_translate_cache'):
            self._safe_translate_cache = {}
        if language is None:
            language = get_language()
        if language not in self._safe_translate_cache:
            try:
                self._safe_translate_cache[language] = self.translate(language)
            # With multiple inheritance, the raised exception can be different to
            # self.DoesNotExist.
            except ObjectDoesNotExist:
                self._safe_translate_cache[language] = self
        return self._safe_translate_cache[language]

    def untranslated_languages(self):
        untranslated_languages = []
        translated_languages = set(self.translations().values_list('language', flat=True))
        for language in LANGUAGES:
            if language[0] not in translated_languages:
                untranslated_languages.append(language)
        return untranslated_languages

    # TODO: Move this somewhere else (template filter?), not generally needed
    def languages(self):
        languages = []
        translations = dict([(t.language, t) for t in self.translations()])
        for language in LANGUAGES:
            languages.append((language, translations.get(language[0])))
        return languages

    def get_contents_fields(self):
        """
        Return the names of fields that should not be copied over during initial
        translation.
        """
        return tuple(getattr(self, '_contents_fields', []))


class TranslatableMixin(TranslatableBaseMixin, TranslatableUtilsMixin):
    class Meta(TranslatableBaseMixin.Meta):
        abstract = True
