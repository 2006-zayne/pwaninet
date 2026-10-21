"""
Static file storage with automatic, content-derived cache busting.

Why this module exists
----------------------
Production serves static assets through Cloudflare, which caches them for a
very long time (``Cache-Control: public, max-age=315360000, immutable``).
The only thing that ever changed the cache key was the manual
``?v={{ app_version }}-{{ app_build }}`` suffix in the templates, and that
value comes from the database release record.

That release record was frozen at ``1.14.3-154`` (created 2026-10-17) while
CSS and JS kept changing every day. The URLs therefore stayed identical
across deploys, so Cloudflare kept serving the 2026-10-13 copy of every
stylesheet and script -- the deployed code was correct, the *assets* were
years old.

``whitenoise.storage.CompressedManifestStaticFilesStorage`` was supposed to
prevent this by hashing file names, but Django 4.2+ ignores the legacy
``STATICFILES_STORAGE`` setting whenever ``STORAGES`` is defined, and this
project defines ``STORAGES``. The hashing backend was therefore dead code
that never ran.

What this module does
---------------------
It keeps file names stable -- so the hard-coded ``/static/...`` references
(PWA icons, the web manifest) keep working -- and appends a fingerprint of
the static tree to every URL produced by ``{% static %}``. Change any
stylesheet or script and the URL changes with it, so the browser, the
service worker and Cloudflare all fetch the new file.

The fingerprint is derived from ``(path, size, mtime)`` of every collected
and source static file. ``collectstatic`` only rewrites a file when the
source is newer, so unchanged assets keep their fingerprint and their cache
entry across deploys.
"""

import hashlib
import os
from functools import lru_cache

from django.contrib.staticfiles.storage import StaticFilesStorage


def _walk(root):
    """Yield ``(relative_path, size, mtime_ns)`` for every file under root."""
    if not root or not os.path.isdir(root):
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            path = os.path.join(dirpath, name)
            try:
                stat = os.stat(path)
            except OSError:
                # File vanished mid-walk; skip it rather than failing the
                # whole request.
                continue
            yield os.path.relpath(path, root), stat.st_size, stat.st_mtime_ns


@lru_cache(maxsize=8)
def _fingerprint(roots):
    digest = hashlib.sha256()
    for root in roots:
        digest.update(root.encode("utf-8", "replace"))
        digest.update(b"\x00")
        for relpath, size, mtime_ns in _walk(root):
            digest.update(f"{relpath}:{size}:{mtime_ns}\n".encode("utf-8", "replace"))
    return digest.hexdigest()[:12]


def static_fingerprint():
    """
    Short digest of the deployed static tree.

    Returns an empty string when settings are not ready yet, so callers can
    fall back to an un-suffixed URL rather than raising during startup.
    """
    try:
        from django.conf import settings

        static_root = getattr(settings, "STATIC_ROOT", None)
        source_dirs = getattr(settings, "STATICFILES_DIRS", []) or []
    except Exception:
        return ""

    roots = []
    if static_root:
        roots.append(str(static_root))
    roots.extend(str(path) for path in source_dirs)

    if not roots:
        return ""

    try:
        return _fingerprint(tuple(sorted(set(roots))))
    except Exception:
        return ""


class StaticFingerprintMixin:
    """
    Append the static-tree fingerprint to every generated static URL.

    Mixed in front of a ``StaticFilesStorage`` (or S3) backend so the URL
    keeps the backend's own base URL and only gains a cache-busting query
    string.
    """

    def url(self, name):
        url = super().url(name)
        if not url:
            return url

        fingerprint = static_fingerprint()
        if not fingerprint:
            return url

        separator = "&" if "?" in url else "?"
        return f"{url}{separator}v={fingerprint}"


class FingerprintedStaticFilesStorage(StaticFingerprintMixin, StaticFilesStorage):
    """Local static storage (WhiteNoise) with automatic cache busting."""


try:
    from storages.backends.s3boto3 import S3Boto3Storage
except ImportError:  # pragma: no cover - django-storages is a hard dependency
    S3Boto3Storage = None


if S3Boto3Storage is not None:

    class FingerprintedS3StaticFilesStorage(StaticFingerprintMixin, S3Boto3Storage):
        """S3/R2 static storage with automatic cache busting."""

    __all__ = [
        "FingerprintedStaticFilesStorage",
        "FingerprintedS3StaticFilesStorage",
        "static_fingerprint",
    ]
else:  # pragma: no cover
    __all__ = ["FingerprintedStaticFilesStorage", "static_fingerprint"]
