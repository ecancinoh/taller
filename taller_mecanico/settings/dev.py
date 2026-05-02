from .base import *  # noqa

DEBUG = True

INSTALLED_APPS += ['django.contrib.admindocs']

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
