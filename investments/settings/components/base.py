"""
Django settings for investments project.

Generated by 'django-admin startproject' using Django 3.2.6.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
PROJECT_PATH = Path(__file__).resolve().parent.parent
BASE_DIR = PROJECT_PATH.parent

# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# Application definition

INSTALLED_APPS = [
    # Third party apps
    "django_extensions",
    "debug_toolbar",
    "django_object_actions",
    # Django Apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Project apps
    "investments",
    "investments.contrib.users.apps.UsersConfig",
    "investments.contrib.brokers.apps.BrokersConfig",
    "investments.contrib.tags.apps.TagsConfig",
    "investments.contrib.securities.apps.SecuritiesConfig",
    "investments.contrib.positions.apps.PositionsConfig",
]

ROOT_URLCONF = "investments.urls"

WSGI_APPLICATION = "investments.wsgi.application"

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = "/static/"

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "users.User"
