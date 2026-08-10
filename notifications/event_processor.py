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

User = get_user_model()

logger = logging.getLogger(__name__)


@receiver(post_save, sender=PlatformEvent)
def process_platform_event(sender, instance, created, **kwargs):
    """
    Process a PlatformEvent through the notification pipeline.
    
    Pipeline:
    1. Rules Engine: Create NotificationObjects from events
    2. Preference Engine: Filter based on user preferences
    3. Aggregation Engine: Combine related notifications
    4. Delivery Engine: Deliver through appropriate channels
    
    Args:
        sender: PlatformEvent model
        instance: The PlatformEvent instance
        created: Whether this is a new instance
    """
    if not created:
        # Only process new events
        return
    
    logger.info(f"Processing PlatformEvent: {instance.event_type} (ID: {instance.event_id})")
    
    try:
        # Step 1: Rules Engine - Create NotificationObjects
        notifications = RulesEngine.process_event(instance)
        
        if not notifications:
            logger.info(f"No notifications created for event {instance.event_id}")
            return
        
        logger.info(f"Created {len(notifications)} NotificationObjects for event {instance.event_id}")
        
        # Invalidate unread count cache for all recipients
        for notification in notifications:
            invalidate_unread_count_cache(notification.recipient_id)
        
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
                
                # Step 3: Aggregation Engine - Combine with related notifications
                # Note: Aggregation is now handled at creation time in the Rules Engine
                # to prevent duplicate notifications. The AggregationEngine is still
                # available for manual aggregation operations if needed.
                
                # Step 4: Delivery Engine - Deliver through allowed channels
                if allowed_channels:
                    DeliveryEngine.deliver_notification(notification, allowed_channels)
                    logger.info(f"Notification {notification.notification_id} delivered via {allowed_channels}")
                
            except Exception as e:
                logger.error(f"Failed to process notification {notification.notification_id}: {e}", exc_info=True)
                continue
    
    except Exception as e:
        logger.error(f"Failed to process event {instance.event_id}: {e}", exc_info=True)
