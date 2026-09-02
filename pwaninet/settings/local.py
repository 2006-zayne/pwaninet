"""
Local development settings.
"""
from .base import *

DEBUG = True

ALLOWED_HOSTS = [
    host.split(':')[0].strip()
    for host in os.environ.get(
        'ALLOWED_HOSTS',
        'localhost,127.0.0.1,0.0.0.0,pwaninet.app,192.168.58.221,192.168.43.170,10.0.2.2'
    ).split(',')
    if host.strip()
]

# Ensure the specific IP is in ALLOWED_HOSTS
if 'pwaninet.app' not in ALLOWED_HOSTS:

        ALLOWED_HOSTS.append('192.168.58.221')



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
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Allow all origins for CSRF in local development (both HTTP and HTTPS)
CSRF_TRUSTED_ORIGINS = [
    'http://localhost',
    'http://localhost:8000',
    'https://localhost',
    'https://localhost:8000',
    'http://127.0.0.1',
    'http://127.0.0.1:8000',
    'https://127.0.0.1',
    'https://127.0.0.1:8000',
    'http://0.0.0.0',
    'http://0.0.0.0:8000',
    'https://0.0.0.0',
    'https://0.0.0.0:8000',
    'http://10.20.152.125',
    'http://10.20.152.125:8000',
    'https://10.20.152.125',
    'https://10.20.152.125:8000',
    'http://10.0.2.2',
    'http://10.0.2.2:8000',
    'http://192.168.213.221',
    'http://192.168.213.221:8000',
    'https://192.168.213.221',
    'https://192.168.213.221:8000',
    'http://192.168.180.221',
    'http://192.168.180.221:8000',
    'https://192.168.180.221',
    'https://192.168.180.221:8000',
    'http://192.168.72.88',
    'http://192.168.72.88:8000',
    'https://192.168.72.88',
    'https://192.168.72.88:8000',
    'http://192.168.85.117',
    'http://192.168.85.117:8000',
    'https://192.168.85.117',
    'https://192.168.85.117:8000',
    'http://192.168.183.245',
    'http://192.168.183.245:8000',
    'https://192.168.183.245',
    'https://192.168.183.245:8000',
    'http://172.18.0.1',
    'http://172.18.0.1:8000',
    'https://172.18.0.1',
    'https://172.18.0.1:8000',
    'capacitor://localhost',
    'http://localhost',
    'http://192.168.127.221',
    'http://192.168.127.221:8000',
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
