import django
import os


def pytest_configure():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    os.environ.setdefault("STATIC_MANIFEST", "0")  # tests skip collectstatic
    django.setup()
