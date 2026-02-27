# ===========================================================================
# Production Settings — config/settings/production.py
# ===========================================================================
# These settings OVERRIDE the base settings (base.py) for production.
# They enable security features, configure external services, and
# optimize Django for a live environment behind Nginx.
# ===========================================================================

from .base import *

# Never show debug pages with stack traces in production.
# Debug=True exposes source code, settings, and database info to attackers.
DEBUG = False

# Only accept requests for these hostnames.
# Prevents HTTP Host header attacks. Set in .env.prod as comma-separated values.
# Example: ALLOWED_HOSTS=api.yourdomain.com,yourdomain.com
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())

# --- Security Settings ---
# These headers protect against common web vulnerabilities.

# Redirect all HTTP requests to HTTPS at the Django level.
# (Nginx also does this, but this is a safety net.)
SECURE_SSL_REDIRECT = True

# Only send session and CSRF cookies over HTTPS connections.
# Prevents cookies from being intercepted on plain HTTP.
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HTTP Strict Transport Security — tell browsers to ONLY use HTTPS for 1 year.
# After visiting once, the browser will refuse plain HTTP connections.
SECURE_HSTS_SECONDS = 31536000  # 1 year in seconds
SECURE_HSTS_INCLUDE_SUBDOMAINS = True  # Apply to all subdomains too
SECURE_HSTS_PRELOAD = True             # Allow inclusion in browser preload lists

# Tell Django it's behind a reverse proxy (Nginx).
# Nginx sets the X-Forwarded-Proto header to "https", and Django reads it
# to know the original request was HTTPS (even though Nginx→Django is HTTP).
# Without this, Django thinks all requests are HTTP and redirect-loops.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# --- Static Files ---
# Override STATIC_ROOT to use an absolute path inside the container.
# This is where "collectstatic" gathers all static files.
# Nginx serves this directory directly (see nginx.conf location /static/).
STATIC_ROOT = '/app/staticfiles'

# --- Sentry Error Tracking (Optional) ---
# Sentry captures unhandled exceptions and sends them to a dashboard.
# Leave SENTRY_DSN empty in .env.prod to disable.
_sentry_dsn = config('SENTRY_DSN', default='')
if _sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    sentry_sdk.init(
        dsn=_sentry_dsn,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,         # Sample 10% of requests for performance monitoring
        send_default_pii=False,         # Don't send personally identifiable information
        environment='production',
    )

# --- AWS S3 Media Storage (Optional) ---
# If AWS credentials are provided, store user uploads on S3 (scalable, durable).
# If not, Django uses local filesystem (MEDIA_ROOT from base.py).
_aws_key = config('AWS_ACCESS_KEY_ID', default='')
if _aws_key:
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    AWS_ACCESS_KEY_ID = _aws_key
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='eu-west-1')
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    AWS_DEFAULT_ACL = 'private'         # Files are private by default (require signed URLs)
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',  # Browser caches S3 files for 1 day
    }

# --- Production Logging ---
# Override the log file path to write to /var/log/moneytransfer/.
# This directory is created by entrypoint.prod.sh before Gunicorn starts.
LOGGING['handlers']['file']['filename'] = '/var/log/moneytransfer/app.log'
