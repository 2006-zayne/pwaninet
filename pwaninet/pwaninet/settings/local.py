"""
Local development settings.
"""
from .base import *

DEBUG = True

ALLOWED_HOSTS = [
    host.split(':')[0].strip()
    for host in os.environ.get(
        'ALLOWED_HOSTS',
        'localhost,127.0.0.1,0.0.0.0,10.20.152.125,192.168.213.221,192.168.180.221,192.168.72.88,192.168.85.117,192.168.72.88'
    ).split(',')
    if host.strip()
]

# Database - SQLite for local development
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Disable security features for local development
SECURE_BROWSER_XSS_FILTER = False
SECURE_CONTENT_TYPE_NOSNIFF = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Allow all origins for CSRF in local development
CSRF_TRUSTED_ORIGINS = ['http://*', 'https://*']
