django-t10e
===========

|pypi-badge| |build-status|

.. |build-status| image:: https://travis-ci.org/team23/django_t10e.svg
    :target: https://travis-ci.org/team23/django_t10e

.. |pypi-badge| image:: https://img.shields.io/pypi/v/django-t10e.svg
    :target: https://pypi.python.org/pypi/django-t10e

**django-t10e** is an approach that allows you to translate the contents of
your models. **django-t10e** stands for *django-translatable*.

The concept behind django-t10e is that we have one model instance per
language. This means one object that is translated into two different languages
will be represented by two rows in the model's database table. Every translatable
model has a ``language`` field and a ``translation_set`` field.

``language`` obviously defines the language of each translation and
``translation_set`` groups the translations of one entity together. All
instances with the same ``translation_set`` are considered to be different
translations of the same entity. An entity might be a news article that is
translated into multiple languages..

The ``translation_set`` field is a ``models.ForeignKey('self')`` field, so it
always points to instances of the same model. The first saved instance of one
translation will set this foreign key to its own primary key. The instance to
which all translations of one entity point to (the first translation) is called
the base translation.

An example. Let's assume the following page instances:

- ``Article(id=13, title='I18N is hard', language='en', translation_set=13)``
- ``Article(id=14, title='Internationalisierung ist schwer', language='de', translation_set=13)``
- ``Article(id=15, title='La internacionalización es dura', language='es', translation_set=13)``

The article with ``id=13`` is considered the base translation. ``id=14`` is the
german translation of ``id=13``. ``id=15`` is the spanish translation of
``id=13``. All three make up one translation set for the "I18N is hard"
article.

There might also be fields that don't need translation, like date fields etc.
These are synced in the translation set. For example: an article model might
have a ``pub_date`` field. So all translations in one translation set have the
same ``pub_date`` value assigned. When one translation is changed you need to
call the ``update_translations()`` method. That will update all other instances
in the translation set accordingly.

Development
-----------

Install the dependencies (including the test dependencies) with::

    pip install -r requirements.txt

Then you can run all tests with::

    tox
