from django.db.models.fields import FieldDoesNotExist
from django.db import models


class TranslationStatusMixin(models.Model):
    """Defines the interface that all models that support translation statuses
    should have. Subclasses should define a ``translation_status`` field."""

    class Meta:
        abstract = True

    @classmethod
    def _has_translation_status_field(cls):
        try:
            cls._meta.get_field('translation_status')
            return True
        except FieldDoesNotExist:
            return False

    def determine_translation_status(self):
        """Subclasses should overwrite this method to define their own logic.

        This method should take no parameters and return the determined
        translation status without setting any values on the model itself. That
        should be part of ``update_translation_status``.
        """
        raise NotImplementedError(
            'Subclasses that define a ``translation_status`` field should '
            'also implement the ``determine_translation_status`` method.')

    def update_translation_status(self):
        """Default implementation for the translation status. Assumes that there
        is a translation_status field on the model. Subclasses might want to
        overwrite the method to change the behaviour.
        """
        self.translation_status = self.determine_translation_status()
