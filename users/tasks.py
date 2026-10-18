"""
Celery tasks for device login alerts (Phase 1).
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=20)
def link_device_verification_notification(self, verification_id):
    """
    Link the NotificationObject produced by the security device pipeline back
    onto its DeviceVerificationEvent (may trail the event by a few seconds
    when delivery runs on a celery worker instead of in-request).
    """
    from users.services.device_alert_service import _link_notification

    try:
        notification = _link_notification(verification_id)
        if notification:
            logger.info(
                f"[DEVICE-ALERT] Linked challenge {verification_id} to "
                f"notification {notification.notification_id}"
            )
    except Exception as exc:
        logger.error(f"[DEVICE-ALERT] link task failed for {verification_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True)
def expire_device_verifications(self):
    """
    Expire pending challenges past their window (default 24h): marks events
    EXPIRED and archives their notification cards. Non-blocking design means
    expiry is purely cosmetic housekeeping — no lockout, no auto-kill.
    """
    from django.utils import timezone
    from notifications.models import NotificationObject
    from users.models import DeviceVerificationEvent, DeviceVerificationStatus

    now = timezone.now()
    expired_count = 0
    qs = DeviceVerificationEvent.objects.filter(
        status=DeviceVerificationStatus.PENDING,
        expires_at__lte=now,
    ).select_related('notification')[:500]

    for event in qs.iterator():
        event.status = DeviceVerificationStatus.EXPIRED
        event.save(update_fields=['status'])
        expired_count += 1
        if event.notification and event.notification.status not in ('ARCHIVED', 'EXPIRED'):
            event.notification.status = 'ARCHIVED'
            event.notification.save(update_fields=['status'])
        from users.services.device_alert_service import invalidate_and_broadcast
        invalidate_and_broadcast(event.user_id)

    if expired_count:
        logger.info(f"[DEVICE-ALERT] Expired {expired_count} pending device challenges")
    return expired_count
