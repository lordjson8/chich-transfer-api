from .base import *

DEBUG = True

ALLOWED_HOSTS = ['*']

# DB_ENGINE = "django.db.backends.mysql"

# Development-specific apps
INSTALLED_APPS += [
    'debug_toolbar',
]

MIDDLEWARE += [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

# Debug toolbar
INTERNAL_IPS = ['127.0.0.1','192.168.100.223']

# Email backend for development
EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST_USER="wouriwise@gmail.com"
EMAIL_HOST_PASSWORD="iduxsyirrnolrvti"
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Less strict CORS for development
CORS_ALLOW_ALL_ORIGINS = True

# Disable SSL redirect in development
SECURE_SSL_REDIRECT = False
