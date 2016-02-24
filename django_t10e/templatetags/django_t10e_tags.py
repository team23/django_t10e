# -*- coding: utf-8 -*-
from django import template

register = template.Library()


@register.filter
def safe_translate(translatable, language=None):
    if hasattr(translatable, 'safe_translate'):
        return translatable.safe_translate(language)
    return translatable
