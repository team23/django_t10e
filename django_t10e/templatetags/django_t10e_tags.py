# -*- coding: utf-8 -*-
from django import template

register = template.Library()


@register.filter
def safe_translate(translatable, language=None):
    return translatable.safe_translate(language)
