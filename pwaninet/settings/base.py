"""
Base settings for pwaninet project.
"""
from pathlib import Path
import os
from datetime import timedelta

from dotenv import load_dotenv
import os

# Import version information (single source of truth)
from pwaninet import version

# Expose version metadata to settings
APP_VERSION = version.__version__
APP_BUILD_NUMBER = version.__build_number__
APP_ENVIRONMENT = version.__environment__
APP_RELEASE_DATE = version.__release_date__

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

load_dotenv(os.path.join(BASE_DIR, ".env"))

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-change-this-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,10.20.152.125').split(',')
ALLOWED_HOSTS = [
    host.split(':')[0].strip()
    for host in os.environ.get(
        'ALLOWED_HOSTS',
        'localhost,127.0.0.1,10.20.152.125,pwaninet.app,192.168.114.221,192.168.43.170,192.168.127.221'
    ).split(',')
    if host.strip()
]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'channels',
    'rest_framework',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    'rest_framework.authtoken',
    'axes',
    'courses',
    'users',
    'posts',
    'groups',
    'notifications',
    'documents',
    'releases',
    'messaging',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',
    'pwaninet.middleware.language_preference.LanguagePreferenceMiddleware',
    'pwaninet.middleware.cache_headers.CacheHeadersMiddleware',
]

ROOT_URLCONF = 'pwaninet.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'notifications.context_processors.notification_count',
                'pwaninet.context_processors.release_metadata',
            ],
        },
    }
]

WSGI_APPLICATION = 'pwaninet.wsgi.application'
ASGI_APPLICATION = 'pwaninet.asgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'pwaninet_db'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'postgres'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'CONN_MAX_AGE': 60,
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Static file caching - Cache fonts for 1 year (fonts rarely change)
# This improves performance by avoiding repeated font downloads
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# File upload settings
FILE_UPLOAD_TEMP_DIR = BASE_DIR / 'media' / 'temp'
# Must match the client-side validator in upload_validator.js (150MB)
FILE_UPLOAD_MAX_MEMORY_SIZE = 150 * 1024 * 1024  # 150MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 150 * 1024 * 1024  # 150MB

# Auth settings
LOGIN_REDIRECT_URL = 'posts:home'
LOGOUT_REDIRECT_URL = 'users:logout'
AUTH_USER_MODEL = 'users.User'

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Session settings
SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = False  # Set to True in production with HTTPS
CSRF_COOKIE_HTTPONLY = True

# Caching configuration
CACHES = {
    'default': {
        'BACKEND': 'pwaninet.cache_backends.FallbackRedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'TIMEOUT': 300,
        'KEY_PREFIX': 'pwaninet',
    },
    'fallback': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'pwaninet-fallback-cache',
    }
}

# REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
        # 'rest_framework_simplejwt.authentication.JWTAuthentication',  # Temporarily disabled due to pkg_resources issue
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
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
        'user': '1000/hour',
        # Messaging throttling - FROZEN FOR MVP
        # 'message_send': '60/minute',
        # 'message_reaction': '30/minute',
        # 'conversation_create': '10/minute',
        # 'ws_message': '100/minute',
    },
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ['v1'],
    'VERSION_PARAM': 'version',
}

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# drf-spectacular settings
SPECTACULAR_SETTINGS = {
    'TITLE': 'Pwaninet API',
    'DESCRIPTION': 'Social networking platform for students and academic communities',
    'VERSION': version.__version__,
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'COMPONENT_NO_READ_ONLY_REQUIRED': True,
    'ENUM_ADD_EXPLICIT_BLANK_NULL_CHOICE': True,
}

# django-axes configuration for rate limiting
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=5)
AXES_LOCKOUT_TEMPLATE = 'axes/lockout.html'
AXES_RESET_ON_SUCCESS = True
# AXES_LOCK_OUT_BY_COMBINATION_USER_AND_IP = True  # Deprecated in django-axes 6.0

# Channels configuration
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [(os.environ.get('REDIS_HOST', '127.0.0.1'), int(os.environ.get('REDIS_PORT', 6379)))],
        },
    },
}

# Celery configuration
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://127.0.0.1:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = os.environ.get('TIME_ZONE', 'UTC')
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000

# CORS settings (includes Capacitor origins and CDN)
_default_cors = [
    'http://localhost',
    'https://localhost',
    'http://localhost:3000',
    'http://localhost:8000',
    'capacitor://localhost',
    'http://10.0.2.2:8000',
    'https://pwaninet.app',
    'https://cdn.pwaninet.app',
]
_env_cors = [c.strip() for c in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',') if c.strip()]
CORS_ALLOWED_ORIGINS = list(set(_default_cors + _env_cors))
CORS_ALLOW_CREDENTIALS = True

# CSRF settings (supports both http:// and https:// for web and Capacitor)
_csrf_hosts = [h.split(':')[0].strip() for h in os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,pwaninet.app').split(',') if h.strip()]
CSRF_TRUSTED_ORIGINS = list(set([
    'https://pwaninet.app',
    'https://cdn.pwaninet.app',
    'capacitor://localhost',
    'http://localhost',
    'https://localhost',
    *[f"http://{h}" for h in _csrf_hosts],
    *[f"https://{h}" for h in _csrf_hosts],
]))

# VAPID keys for Web Push notifications
VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY', '')
VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', '')
VAPID_SUBJECT = os.environ.get('VAPID_SUBJECT', 'mailto:admin@pwaninet.app')

# Email configuration
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@pwaninet.app')
SERVER_EMAIL = os.environ.get('SERVER_EMAIL', DEFAULT_FROM_EMAIL)

# Notification processing configuration
ENABLE_NOTIFICATION_PROCESSING = True

# ---------------------------------------------------------------------------
# Cloud Storage & CDN (django-storages + boto3 → Cloudflare R2)
# ---------------------------------------------------------------------------
# Set USE_S3=1 in .env to activate.  Locally the app stays on local disk.
# All values come from .env — no secrets are hardcoded here.
# ---------------------------------------------------------------------------
USE_S3 = os.environ.get('USE_S3', '0') == '1'

# Expose CDN domain at module level so Post.get_hls_url can use it
CDN_DOMAIN = os.environ.get('CDN_DOMAIN', '')

if USE_S3:
    from botocore.config import Config

    # --- Credentials & bucket ------------------------------------------------
    AWS_ACCESS_KEY_ID       = os.environ.get('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY   = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
    AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME', '')

    # Cloudflare R2 endpoint:  https://<accountid>.r2.cloudflarestorage.com
    AWS_S3_ENDPOINT_URL     = os.environ.get('AWS_S3_ENDPOINT_URL', '')
    AWS_S3_REGION_NAME      = os.environ.get('AWS_S3_REGION_NAME', 'auto')
    AWS_S3_ADDRESSING_STYLE = 'path'
    AWS_S3_SIGNATURE_VERSION = 's3v4'

    # --- R2-specific: ACLs are NOT supported ---------------------------------
    # Empty string from .env must become None so boto3 never sends an ACL header
    _acl_raw        = os.environ.get('AWS_DEFAULT_ACL', '')
    AWS_DEFAULT_ACL = _acl_raw if _acl_raw else None

    # Boto3 client config for Cloudflare R2 compatibility:
    AWS_S3_CLIENT_CONFIG = Config(
        signature_version='s3v4',
        s3={'addressing_style': 'path'},
    )

    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400, public',
    }
    AWS_S3_FILE_OVERWRITE = False
    AWS_QUERYSTRING_AUTH  = False   # public bucket — no signed URLs for reads

    # Expose boto3 config so Celery tasks can upload HLS segments directly
    R2_BOTO3_CONFIG = {
        'endpoint_url':          AWS_S3_ENDPOINT_URL,
        'aws_access_key_id':     AWS_ACCESS_KEY_ID,
        'aws_secret_access_key': AWS_SECRET_ACCESS_KEY,
        'region_name':           AWS_S3_REGION_NAME,
        'config':                AWS_S3_CLIENT_CONFIG,
    }

    # --- CDN edge domain (cdn.pwaninet.app) ----------------------------------
    AWS_S3_CUSTOM_DOMAIN = CDN_DOMAIN

    # Allow opting into S3 for staticfiles if explicitly set (default: keep static local for WhiteNoise)
    USE_S3_STATIC = os.environ.get('USE_S3_STATIC', '0') == '1'

    # --- Storage backend routing (django-storages) ---------------------------
    STORAGES = {
        'default': {
            # All media uploads (video, images, HLS segments, docs, audio)
            'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
            'OPTIONS': {
                'bucket_name':       AWS_STORAGE_BUCKET_NAME,
                'endpoint_url':      AWS_S3_ENDPOINT_URL,
                'region_name':       AWS_S3_REGION_NAME,
                'access_key':        AWS_ACCESS_KEY_ID,
                'secret_key':        AWS_SECRET_ACCESS_KEY,
                'location':          'media',
                'default_acl':       None,          # R2: no ACLs
                'file_overwrite':    False,
                'custom_domain':     CDN_DOMAIN or None,
                'object_parameters': {'CacheControl': 'max-age=604800, public'},  # 7 days
                'signature_version': 's3v4',
                'addressing_style':  'path',
                'client_config':     AWS_S3_CLIENT_CONFIG,
            },
        },
        'staticfiles': {
            # Static files stay local for WhiteNoise / Nginx unless USE_S3_STATIC=1
            'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage' if USE_S3_STATIC else 'django.contrib.staticfiles.storage.StaticFilesStorage',
            **({
                'OPTIONS': {
                    'bucket_name':       AWS_STORAGE_BUCKET_NAME,
                    'endpoint_url':      AWS_S3_ENDPOINT_URL,
                    'region_name':       AWS_S3_REGION_NAME,
                    'access_key':        AWS_ACCESS_KEY_ID,
                    'secret_key':        AWS_SECRET_ACCESS_KEY,
                    'location':          'static',
                    'default_acl':       None,
                    'file_overwrite':    True,
                    'custom_domain':     CDN_DOMAIN or None,
                    'object_parameters': {'CacheControl': 'max-age=31536000, public'},
                    'signature_version': 's3v4',
                    'addressing_style':  'path',
                    'client_config':     AWS_S3_CLIENT_CONFIG,
                }
            } if USE_S3_STATIC else {})
        },
    }

    # Rewrite Django's MEDIA_URL to the CDN edge
    MEDIA_URL  = f'https://{CDN_DOMAIN}/media/'
    if USE_S3_STATIC:
        STATIC_URL = f'https://{CDN_DOMAIN}/static/'

