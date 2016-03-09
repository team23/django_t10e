from django.db.models import F
from django.db.models.query import QuerySet
from django.utils.translation import get_language
from .compat import Manager


class TranslatableFilterMixin(object):
    def translate(self, language=None):
        if language is None:
            language = get_language()
        return self.filter(language=language)

    def translations(self, translation_set):
        if isinstance(translation_set, self.model):
            translation_set = translation_set.translation_set_id
        return self.filter(translation_set=translation_set)

    def translation_set_parents(self):
        """
        Only return objects which are translation set parents, i.e. where
        ``self.translation_set == self``.
        """
        return self.filter(translation_set__pk=F('pk'))


class TranslatableQuerySet(TranslatableFilterMixin, QuerySet):
    pass


TranslatableManager = Manager.from_queryset(TranslatableQuerySet)
