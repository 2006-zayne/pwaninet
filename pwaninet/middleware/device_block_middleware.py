"""
Blocked-device enforcement middleware (Phase 1).

Refuses session-authenticated requests whose bound device fingerprint has
been blocked by the user ("No, it wasn't me"). Fresh login attempts are
refused by users.services.device_alert_service.evaluate_device_login; this
middleware covers sessions created *before* the block.
"""
import logging

from django.contrib.auth import logout
from django.core.cache import cache

from users.services.device_service import hash_device_id

logger = logging.getLogger(__name__)


def _blocked_hashes_for_user(user_id):
    """Per-user set of blocked device hashes, cached briefly."""
    cache_key = f"devalert:blocked:{user_id}"
    hashes = cache.get(cache_key)
    if hashes is None:
        from users.models import BlockedDevice
        hashes = set(
            BlockedDevice.objects.filter(user_id=user_id).values_list('device_hash', flat=True)
        )
        cache.set(cache_key, hashes, 60)
    return hashes


def invalidate_blocked_device_cache(user_id):
    cache.delete(f"devalert:blocked:{user_id}")


class BlockedDeviceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated:
            session_key = request.session.session_key
            if session_key:
                try:
                    from users.models import DeviceAccount
                    device_hash = (
                        DeviceAccount.objects.filter(
                            user_id=user.pk, session_key=session_key
                        ).values_list('device_id', flat=True).first()
                    )
                except Exception:
                    device_hash = None
                if device_hash and device_hash in _blocked_hashes_for_user(user.pk):
                    logger.warning(
                        f"[DEVICE-ALERT] Terminating session of user '{user.username}' "
                        f"on blocked device (hash={device_hash[:10]})"
                    )
                    logout(request)
                    from django.contrib import messages
                    from django.utils.translation import gettext_lazy as _
                    messages.error(
                        request,
                        _("This device has been blocked from your account. "
                          "If you believe this is a mistake, contact support.")
                    )
        return self.get_response(request)
