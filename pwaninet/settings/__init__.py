import os
import logging
from .base import *

# Strict environment isolation: NEVER import local settings in production
_env = os.environ.get('DJANGO_ENV', '').strip().lower()
_settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', '').strip()

if _env != 'production' and _settings_module != 'pwaninet.settings.production':
    try:
        from .local import *
    except ImportError:
        pass

