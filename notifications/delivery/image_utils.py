"""
Image utility for generating rounded avatars and thumbnails for notifications.
Provides cached circular masks for user avatars and rounded-corner masks for
post thumbnail previews, ensuring proper presentation across Android FCM and Web Push.
"""
import os
import hashlib
import logging
from urllib.parse import urlparse
from django.conf import settings
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

CACHE_DIR_NAME = 'notification_rounded_cache'


def _get_cache_dir() -> str:
    """Ensure and return the disk path for cached rounded images."""
    cache_dir = os.path.join(settings.MEDIA_ROOT, CACHE_DIR_NAME)
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def _url_to_local_path(url_or_path: str) -> str | None:
    """Resolve a media or static URL to a local filesystem path if possible."""
    if not url_or_path:
        return None

    parsed = urlparse(url_or_path)
    path = parsed.path if parsed.path else url_or_path

    # Handle /media/ URLs
    media_url = settings.MEDIA_URL
    if path.startswith(media_url):
        rel_path = path[len(media_url):]
        local_file = os.path.join(settings.MEDIA_ROOT, rel_path)
        if os.path.exists(local_file):
            return local_file

    # Handle /static/ URLs
    static_url = settings.STATIC_URL
    if path.startswith(static_url):
        rel_path = path[len(static_url):]
        # Check staticfiles directories
        if hasattr(settings, 'STATICFILES_DIRS') and settings.STATICFILES_DIRS:
            for sdir in settings.STATICFILES_DIRS:
                cand = os.path.join(sdir, rel_path)
                if os.path.exists(cand):
                    return cand
        if hasattr(settings, 'STATIC_ROOT') and settings.STATIC_ROOT:
            cand = os.path.join(settings.STATIC_ROOT, rel_path)
            if os.path.exists(cand):
                return cand

    # Direct local path
    if os.path.exists(path):
        return path

    return None


def get_rounded_avatar_url(avatar_url: str) -> str:
    """
    Generate or retrieve a circular-masked version of the given avatar image.
    Returns the media URL of the circular image with transparent background.
    Falls back to original URL on error.
    """
    if not avatar_url:
        return avatar_url

    # Skip if already a cached rounded image
    if CACHE_DIR_NAME in avatar_url:
        return avatar_url

    local_path = _url_to_local_path(avatar_url)
    if not local_path:
        return avatar_url

    try:
        file_hash = hashlib.md5(f"avatar_circle_{local_path}_{os.path.getmtime(local_path)}".encode()).hexdigest()
        filename = f"avatar_circle_{file_hash}.png"
        out_path = os.path.join(_get_cache_dir(), filename)
        out_url = f"{settings.MEDIA_URL}{CACHE_DIR_NAME}/{filename}"

        if os.path.exists(out_path):
            return out_url

        with Image.open(local_path) as img:
            img = img.convert('RGBA')
            size = min(img.size)
            # Center crop to square if not square
            left = (img.width - size) // 2
            top = (img.height - size) // 2
            img = img.crop((left, top, left + size, top + size))

            # Resize if too large for notification icon (max 256x256 is ideal)
            if size > 256:
                img = img.resize((256, 256), Image.Resampling.LANCZOS)
                size = 256

            # Apply circular mask
            mask = Image.new('L', (size, size), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, size, size), fill=255)

            # Combine existing alpha with circular mask
            orig_r, orig_g, orig_b, orig_a = img.split()
            final_a = Image.new('L', (size, size), 0)
            final_a.paste(mask)
            # Blend with existing alpha if any
            final_a = Image.composite(orig_a, final_a, mask)

            result = Image.merge('RGBA', (orig_r, orig_g, orig_b, final_a))
            result.save(out_path, 'PNG', optimize=True)

        return out_url
    except Exception as e:
        logger.warning(f"Failed to generate rounded avatar for {avatar_url}: {e}")
        return avatar_url


def get_rounded_thumbnail_url(thumbnail_url: str, radius: int = 24) -> str:
    """
    Generate or retrieve a rounded-rectangle version of the given thumbnail image.
    Returns the media URL of the rounded-corner image with transparent background.
    Falls back to original URL on error.
    """
    if not thumbnail_url:
        return thumbnail_url

    if CACHE_DIR_NAME in thumbnail_url:
        return thumbnail_url

    local_path = _url_to_local_path(thumbnail_url)
    if not local_path:
        return thumbnail_url

    try:
        file_hash = hashlib.md5(f"thumb_round_{local_path}_{radius}_{os.path.getmtime(local_path)}".encode()).hexdigest()
        filename = f"thumb_round_{file_hash}.png"
        out_path = os.path.join(_get_cache_dir(), filename)
        out_url = f"{settings.MEDIA_URL}{CACHE_DIR_NAME}/{filename}"

        if os.path.exists(out_path):
            return out_url

        with Image.open(local_path) as img:
            img = img.convert('RGBA')
            w, h = img.size

            # Resize down to reasonable thumbnail dimension for notifications
            max_dim = 600
            if max(w, h) > max_dim:
                scale = max_dim / max(w, h)
                w, h = int(w * scale), int(h * scale)
                img = img.resize((w, h), Image.Resampling.LANCZOS)

            # Scale corner radius proportionally
            eff_radius = min(radius, min(w, h) // 4)

            # Create rounded rectangle mask
            mask = Image.new('L', (w, h), 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle((0, 0, w, h), radius=eff_radius, fill=255)

            orig_r, orig_g, orig_b, orig_a = img.split()
            final_a = Image.composite(orig_a, mask, mask)

            result = Image.merge('RGBA', (orig_r, orig_g, orig_b, final_a))
            result.save(out_path, 'PNG', optimize=True)

        return out_url
    except Exception as e:
        logger.warning(f"Failed to generate rounded thumbnail for {thumbnail_url}: {e}")
        return thumbnail_url
