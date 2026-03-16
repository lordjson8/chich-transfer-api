from .base import *

DEBUG = False

# Wildcard for all subdomains of awdpay.net
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*.awdpay.com').split(',')

# 1. REMOVED DebugToolbar (Never in production)
# 2. WhiteNoise MUST be at the top of the list if possible, 
#    but we'll insert it safely here.
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'



USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


# CSRF — autoriser le domaine frontend qui appelle l'admin
CSRF_TRUSTED_ORIGINS = ['https://sandboxapi.awdpay.com']



# --- Safety Headers ---
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# --- Path Fixes ---
STATIC_ROOT = BASE_DIR / 'staticfiles'

# EMERGENCY LOG FIX: Use a path we KNOW exists inside the container
# LOGGING['handlers']['file']['filename'] = BASE_DIR / 'logs' / 'app.log'