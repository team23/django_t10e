from django.conf import settings

T10E_LANGUAGE_CHOICES = getattr(settings, 'T10E_LANGUAGE_CHOICES', settings.LANGUAGES)
