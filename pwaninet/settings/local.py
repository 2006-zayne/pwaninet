"""
Local development settings.
"""
from .base import *

DEBUG = True           

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', '[::1]']



# Database - PostgreSQL for local development
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

# Disable security features for local development
SECURE_BROWSER_XSS_FILTER = False
SECURE_CONTENT_TYPE_NOSNIFF = False
# Cookie isolation to prevent collisions with production in the same browser
SESSION_COOKIE_NAME = 'pwaninet_local_sessionid'
CSRF_COOKIE_NAME = 'pwaninet_local_csrftoken'
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Proxy SSL header for reverse proxies and tunnels (Cloudflare Tunnel, Nginx)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# CSRF Trusted Origins for local development
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

# Disable CSRF for API endpoints in local development
CSRF_COOKIE_HTTPONLY = False

# Disable Django cache in local dev
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache"
    }
}

# Add CSRF exemption middleware for API endpoints in local dev
MIDDLEWARE = [
    'pwaninet.middleware.csrf_exempt.CSRFExemptMiddleware',
] + MIDDLEWARE

# WhiteNoise dev behavior
WHITENOISE_AUTOREFRESH = True
WHITENOISE_USE_FINDERS = True
WHITENOISE_MAX_AGE = 0

# Browser/static cache headers
SEND_FILE_MAX_AGE_DEFAULT = 0

AXES_ENABLED = False

# Celery configuration for local development
CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/0'
