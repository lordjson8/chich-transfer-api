from .base import *

DEBUG = False

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*.awdpay.com').split(',')

MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Proxy SSL (Nginx termine TLS, Gunicorn reçoit HTTP)
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Cookies sécurisés
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# CSRF origins
CSRF_TRUSTED_ORIGINS = ['https://sandboxapi.awdpay.com']

# NE PAS mettre SECURE_SSL_REDIRECT = True
# Nginx s'en charge déjà dans nginx.conf

STATIC_ROOT = BASE_DIR / 'staticfiles'