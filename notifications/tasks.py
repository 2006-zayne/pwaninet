"""
Celery tasks for notification processing.
"""
import logging
from celery import shared_task
from .event_processor import run_event_pipeline


logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def process_platform_event_task(self, event_id):
    """
    Asynchronously process a PlatformEvent through the notification pipeline.
    """
    try:
        from notifications.models import PlatformEvent
        event = PlatformEvent.objects.get(event_id=event_id)
        run_event_pipeline(event)
    except PlatformEvent.DoesNotExist:
        logger.warning(f"PlatformEvent {event_id} not found for processing")
    except Exception as exc:
        logger.error(f"Error processing event {event_id}: {exc}", exc_info=True)
        raise self.retry(exc=exc)

