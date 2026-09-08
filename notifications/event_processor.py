"""
Event Processor for PwaniNet Notification Engine v2

This module processes PlatformEvents through the notification pipeline.
It connects PlatformEvent creation to the Rules Engine to create NotificationObjects.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from notifications.models import PlatformEvent
from notifications.rules.engine import RulesEngine
from notifications.preferences.engine import PreferenceEngine
from notifications.aggregation.engine import AggregationEngine
from notifications.delivery.engine import DeliveryEngine
from notifications.services.notification_service import invalidate_unread_count_cache
from notifications.queries.notification_queries import get_unread_count_by_user_id
from channels.layers import get_channel_layer
from django.db import transaction
from asgiref.sync import async_to_sync

User = get_user_model()

logger = logging.getLogger(__name__)


def run_event_pipeline(instance):
    """
    Run PlatformEvent through Rules, Preferences, Aggregation, and Delivery engines.
    """
    logger.info(f"Processing PlatformEvent: {instance.event_type} (ID: {instance.event_id})")

    try:
        # Step 1: Rules Engine - Create NotificationObjects
        notifications = RulesEngine.process_event(instance)

        if not notifications:
            logger.info(f"No notifications created for event {instance.event_id}")
            return

        logger.info(f"Created {len(notifications)} NotificationObjects for event {instance.event_id}")

        # Invalidate unread count cache for all recipients and broadcast updates
        channel_layer = get_channel_layer()
        for notification in notifications:
            recipient_id = notification.recipient_id
            invalidate_unread_count_cache(recipient_id)

            # Get the actual count
            count = get_unread_count_by_user_id(recipient_id)
            logger.info(f"Broadcasting unread count update to user {recipient_id}: count={count}")

            # Broadcast unread count update via WebSocket
            if channel_layer:
                try:
                    async_to_sync(channel_layer.group_send)(
                        f"notifications_{recipient_id}",
                        {
                            'type': 'unread_count_update',
                            'count': count
                        }
                    )
                    logger.info(f"Successfully sent WebSocket broadcast to notifications_{recipient_id}")
                except Exception as ws_err:
                    logger.warning(f"Failed to send WebSocket broadcast: {ws_err}")

        # Step 2-4: Process each notification through the pipeline
        for notification in notifications:
            try:
                # Step 2: Preference Engine - Check if notification should be delivered
                allowed, allowed_channels = PreferenceEngine.evaluate_notification(
                    notification, channel='IN_APP'
                )

                if not allowed:
                    logger.info(f"Notification {notification.notification_id} filtered by preferences")
                    notification.status = 'ARCHIVED'
                    notification.save()
                    continue

                # Step 4: Delivery Engine - Deliver through allowed channels
                if allowed_channels:
                    DeliveryEngine.deliver_notification(notification, allowed_channels)
                    logger.info(f"Notification {notification.notification_id} delivered via {allowed_channels}")

            except Exception as e:
                logger.error(f"Failed to process notification {notification.notification_id}: {e}", exc_info=True)
                continue

    except Exception as e:
        logger.error(f"Failed to process event {instance.event_id}: {e}", exc_info=True)


@receiver(post_save, sender=PlatformEvent)
def process_platform_event(sender, instance, created, **kwargs):
    """
    Handle post-save of PlatformEvent by deferring pipeline execution to transaction commit.
    Dispatches to Celery task if available, with synchronous fallback.
    """
    if not created:
        return

    import sys
    from django.conf import settings
    if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False) or getattr(settings, 'TESTING', False) or 'test' in sys.argv:
        run_event_pipeline(instance)
        return

    def _dispatch():
        try:
            # Check if Celery worker is active; if not, execute synchronously
            from pwaninet.celery import app as celery_app
            inspector = celery_app.control.inspect(timeout=0.15)
            ping = inspector.ping() if inspector else None
            if not ping:
                run_event_pipeline(instance)
                return

            from notifications.tasks import process_platform_event_task
            process_platform_event_task.delay(str(instance.event_id))
        except Exception:
            run_event_pipeline(instance)

    transaction.on_commit(_dispatch)

