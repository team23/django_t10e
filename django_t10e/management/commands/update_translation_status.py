from django.core.management.base import BaseCommand
from django.utils.encoding import force_text
from django.db import models


class Command(BaseCommand):
    help = (
        "Update translation status for all relevant models. Give <app.model> "
        "as argument to only update a particular model.")

    def handle(self, *args, **options):
        limited_models = [name.lower() for name in args]
        for Model in models.get_models():
            if limited_models:
                model_name = '{0}.{1}'.format(
                    Model._meta.app_label.lower(),
                    Model._meta.object_name.lower())
                if model_name not in limited_models:
                    continue
            if hasattr(Model, 'update_translation_status'):
                print("Updating {0} ...".format(
                    force_text(Model._meta.verbose_name)))
                for instance in Model.objects.all():
                    instance.update_translation_status()
                    instance.save()
