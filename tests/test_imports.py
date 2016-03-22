def test_imports():
    import django_t10e  # noqa


def test_has_version():
    import django_t10e

    assert django_t10e.__version__.count('.') >= 2
