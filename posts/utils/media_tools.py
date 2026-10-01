"""Resolve media tool executables consistently across web and worker processes."""

import logging
import os
import shutil

from django.conf import settings

logger = logging.getLogger(__name__)


def resolve_ffprobe():
    """Return the configured ffprobe executable or a PATH-discovered fallback."""
    configured = getattr(settings, 'FFPROBE_PATH', None)
    if configured:
        if os.path.isfile(configured) and os.access(configured, os.X_OK):
            logger.debug('Using configured ffprobe executable: %s', configured)
            return configured
        logger.warning('Configured FFPROBE_PATH is not executable (%s); searching PATH', configured)

    discovered = shutil.which('ffprobe')
    if discovered:
        logger.debug('Using ffprobe discovered on PATH: %s', discovered)
        return discovered

    # Preserve a useful subprocess error with the executable name when missing.
    logger.error('ffprobe was not found: configure FFPROBE_PATH or install it on PATH')
    return 'ffprobe'
