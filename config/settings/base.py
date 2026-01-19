"""
Base Django settings for money_transfer_api project.
"""
import os
from pathlib import Path
from datetime import timedelta
from decouple import config, Csv

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-this-in-production')

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_extensions',
    # 'drf_yasg',
    'drf_spectacular',
    'phonenumber_field',
]

LOCAL_APPS = [
    'apps.core',
    'apps.authentication',
    'apps.integrations',
    'apps.kyc',
    'apps.transfers',
    'apps.routes',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# Middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # CORS - must be before CommonMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.core.middleware.RequestLoggingMiddleware',  # Custom logging
    'apps.core.middleware.TimezoneMiddleware',
]

ROOT_URLCONF = 'config.urls'

# Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


DB_ENGINE = config("DB_ENGINE", "django.db.backends.sqlite3")
# print(f"Engine {DB_ENGINE}")

if DB_ENGINE == "django.db.backends.mysql":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "HOST": config("DB_HOST", "127.0.0.1"),
            "PORT": config("DB_PORT", "3306"),
            "NAME": config("DB_NAME", "chic_transfer_dev"),
            "USER": config("DB_USER", "chic_user"),
            "PASSWORD": config("DB_PASSWORD", "chic_password"),
            "OPTIONS": {
                "charset": "utf8mb4",
            },
        }
    }
elif DB_ENGINE == "django.db.backends.postgresql":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "HOST": config("DB_HOST", "127.0.0.1"),
            "PORT": config("DB_PORT", "5432"),
            "NAME": config("DB_NAME", "chic_transfer"),
            "USER": config("DB_USER", "chic_user"),
            "PASSWORD": config("DB_PASSWORD", "chic_password"),
        }
    }
else:
    # fallback (e.g., tests)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
# Custom User Model (we'll create this)
AUTH_USER_MODEL = 'authentication.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8}
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
    {
        'NAME': 'apps.authentication.validators.CustomPasswordValidator',  # Our custom validator
    }
]

# Password Hashers (Use Argon2 - most secure)
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',  # Primary
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================================================
# DJANGO REST FRAMEWORK
# ============================================================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
    'DEFAULT_PAGINATION_CLASS': 'apps.core.pagination.CustomPageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
   'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/minute',
        'login': '5/minute',
        'otp': '3/minute',
        "kyc": '1000/minute',
        # "transaction": '1000/minute',
        # 'password_reset': '5/hour',      # Request reset 5 times/hour
        'password_change': '10/day',     # Change password 10 times/day
    },
    'EXCEPTION_HANDLER': 'apps.core.exceptions.custom_exception_handler',
    'DATETIME_FORMAT': '%Y-%m-%dT%H:%M:%SZ',
    'DATE_FORMAT': '%Y-%m-%d',
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    "NON_FIELD_ERRORS_KEY": "errors",
}

# ============================================================================
# JWT SETTINGS
# ============================================================================
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    
    'JTI_CLAIM': 'jti',
    
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

# ============================================================================
# REDIS & CACHING
# ============================================================================
REDIS_HOST = config('REDIS_HOST', default='localhost')
REDIS_PORT = config('REDIS_PORT', default=6379, cast=int)
REDIS_DB = config('REDIS_DB', default=0, cast=int)
REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PASSWORD': config('REDIS_PASSWORD', default=''),
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
        },
        'KEY_PREFIX': 'moneytransfer',
        'TIMEOUT': 300,  # 5 minutes default
    }
}

# Session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# ============================================================================
# CELERY CONFIGURATION
# ============================================================================
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes
CELERY_WORKER_PREFETCH_MULTIPLIER = 4
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000

# ============================================================================
# CORS SETTINGS
# ============================================================================
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000,http://localhost:19006',
    cast=Csv()
)
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'idempotency-key',
]

# ============================================================================
# SECURITY SETTINGS
# ============================================================================
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# ============================================================================
# EMAIL CONFIGURATION
# ============================================================================
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@moneytransfer.com')

# print(EMAIL_BACKEND,EMAIL_HOST,EMAIL_HOST_PASSWORD,EMAIL_HOST_USER,EMAIL_USE_TLS)

# ============================================================================
# PHONE NUMBER FIELD
# ============================================================================
PHONENUMBER_DEFAULT_REGION = 'CI'  # Côte d'Ivoire
PHONENUMBER_DB_FORMAT = 'E164'

# ============================================================================
# CUSTOM APP SETTINGS
# ============================================================================

# OTP Settings
OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 10
OTP_MAX_ATTEMPTS = 3
OTP_RESEND_COOLDOWN_SECONDS = 60

# KYC Settings
KYC_DOCUMENT_MAX_SIZE_MB = 5
KYC_FACE_MATCH_THRESHOLD = 70  # 70% confidence
KYC_ALLOWED_FORMATS = ['image/jpeg', 'image/png']

# Transfer Limits
TRANSFER_MAX_AMOUNT_EUR = 1000
TRANSFER_DAILY_LIMIT_EUR = 5000
TRANSFER_QUOTE_VALIDITY_MINUTES = 5

# AwdPay Integration
AWDPAY_API_KEY = config('AWDPAY_API_KEY', default='')
AWDPAY_API_SECRET = config('AWDPAY_API_SECRET', default='')
AWDPAY_API_URL = config('AWDPAY_BASE_URL', default='https://api.awdpay.com/v1')
AWDPAY_WEBHOOK_SECRET = config('AWDPAY_WEBHOOK_SECRET', default='')

# SMS Provider (example: Africa's Talking)
SMS_PROVIDER = config('SMS_PROVIDER', default='africastalking')
SMS_API_KEY = config('SMS_API_KEY', default='')
SMS_USERNAME = config('SMS_USERNAME', default='')

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'app.log',
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}


SPECTACULAR_SETTINGS = {
    'TITLE': 'Money Transfer API',
    'DESCRIPTION': 'Cross-border money transfer API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'CONTACT': {
        "name": "Developer Support",
        "email": "lordjson8@gmail.com"
    },
    # 'SWAGGER_UI_DIST': 'SIDECAR',  # shorthand to use the sidecar instead
    # 'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    # 'REDOC_DIST': 'SIDECAR',
}

PASSWORD_RESET_TOKEN_EXPIRY_HOURS = config('PASSWORD_RESET_TOKEN_EXPIRY_HOURS', default=1, cast=int)

