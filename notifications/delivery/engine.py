"""
Delivery Engine for PwaniNet Notification Engine v2

This module implements the Delivery Engine that delivers approved notifications
through supported communication channels. Following Chapter 9 of the specification.
"""
import logging
from typing import List, Optional, Dict
from datetime import timedelta
from django.utils import timezone
from notifications.models import NotificationObject, DeliveryAttempt
from .adapters import get_adapter

logger = logging.getLogger(__name__)


class DeliveryEngine:
    """
    The Delivery Engine delivers approved Notification Objects through
    one or more supported communication channels.
    
    Responsibilities:
    - Receive approved notifications
    - Select delivery channels
    - Queue deliveries
    - Invoke delivery adapters
    - Record delivery status
    - Retry failed deliveries
    - Handle temporary failures
    
    It does NOT:
    - Evaluate notification rules
    - Aggregate notifications
    - Manage preferences
    - Render user interfaces
    """
    
    # Retry schedule (exponential backoff)
    RETRY_DELAYS = [30, 120, 600, 1800]  # 30s, 2m, 10m, 30m
    MAX_RETRIES = 4
    
    @staticmethod
    def deliver_notification(notification: NotificationObject, channels: List[str]) -> List[DeliveryAttempt]:
        """
        Deliver a notification through specified channels.
        
        Args:
            notification: The NotificationObject to deliver
            channels: List of delivery channels (e.g., ['IN_APP', 'EMAIL'])
            
        Returns:
            List of DeliveryAttempt objects
        """
        logger.info(f"Delivering notification {notification.notification_id} through channels: {channels}")
        
        # Check if notification has expired
        if notification.expires_at and notification.expires_at < timezone.now():
            logger.info(f"Notification {notification.notification_id} has expired, skipping delivery")
            return []
        
        attempts = []
        
        for channel in channels:
            try:
                attempt = DeliveryEngine._deliver_through_channel(notification, channel)
                if attempt:
                    attempts.append(attempt)
            except Exception as e:
                logger.error(f"Failed to deliver notification {notification.notification_id} through {channel}: {e}")
        
        return attempts
    
    @staticmethod
    def _deliver_through_channel(notification: NotificationObject, channel: str) -> Optional[DeliveryAttempt]:
        """
        Deliver a notification through a specific channel.
        
        Args:
            notification: The NotificationObject to deliver
            channel: The delivery channel
            
        Returns:
            DeliveryAttempt object or None if delivery not possible
        """
        # Get adapter for this channel
        adapter = get_adapter(channel)
        if not adapter:
            logger.warning(f"No adapter found for channel {channel}")
            return None
        
        # Validate delivery is possible
        if not adapter.validate(notification):
            logger.warning(f"Delivery validation failed for notification {notification.notification_id} through {channel}")
            return None
        
        # Create delivery attempt
        attempt = DeliveryAttempt.objects.create(
            notification=notification,
            channel=channel,
            status='PENDING'
        )
        
        # Mark as queued
        attempt.mark_as_queued()
        
        # Attempt delivery
        attempt.mark_as_sending()
        
        try:
            success = adapter.deliver(notification, attempt)
            
            if success:
                attempt.mark_as_delivered()
                logger.info(f"Delivery successful for notification {notification.notification_id} through {channel}")
            else:
                attempt.mark_as_failed(error_message="Adapter returned False")
                # Schedule retry if applicable
                if attempt.attempt_count < DeliveryEngine.MAX_RETRIES:
                    delay = DeliveryEngine.RETRY_DELAYS[min(attempt.attempt_count, len(DeliveryEngine.RETRY_DELAYS) - 1)]
                    attempt.schedule_retry(delay)
                    logger.info(f"Scheduling retry for notification {notification.notification_id} through {channel} in {delay}s")
                else:
                    logger.error(f"Max retries exceeded for notification {notification.notification_id} through {channel}")
            
        except Exception as e:
            attempt.mark_as_failed(error_message=str(e), error_code="DELIVERY_ERROR")
            logger.error(f"Delivery error for notification {notification.notification_id} through {channel}: {e}")
        
        return attempt
    
    @staticmethod
    def process_retry_queue():
        """
        Process the retry queue for failed deliveries.
        
        This method should be called periodically by a background worker.
        """
        logger.info("Processing retry queue")
        
        # Find deliveries scheduled for retry
        retry_attempts = DeliveryAttempt.objects.filter(
            status='RETRY_SCHEDULED',
            next_retry_at__lte=timezone.now()
        )
        
        for attempt in retry_attempts:
            try:
                notification = attempt.notification
                channel = attempt.channel
                
                logger.info(f"Retrying delivery for notification {notification.notification_id} through {channel}")
                
                # Reset status to sending
                attempt.status = 'SENDING'
                attempt.save(update_fields=['status', 'updated_at'])
                
                # Get adapter and retry
                adapter = get_adapter(channel)
                if adapter:
                    success = adapter.deliver(notification, attempt)
                    
                    if success:
                        attempt.mark_as_delivered()
                    else:
                        attempt.mark_as_failed(error_message="Adapter returned False on retry")
                        # Schedule another retry if applicable
                        if attempt.attempt_count < DeliveryEngine.MAX_RETRIES:
                            delay = DeliveryEngine.RETRY_DELAYS[min(attempt.attempt_count, len(DeliveryEngine.RETRY_DELAYS) - 1)]
                            attempt.schedule_retry(delay)
                        else:
                            logger.error(f"Max retries exceeded for notification {notification.notification_id} through {channel}")
                
            except Exception as e:
                logger.error(f"Retry failed for delivery attempt {attempt.id}: {e}")
                attempt.mark_as_failed(error_message=str(e))
    
    @staticmethod
    def get_delivery_status(notification: NotificationObject) -> Dict[str, str]:
        """
        Get the delivery status for a notification across all channels.
        
        Args:
            notification: The NotificationObject to check
            
        Returns:
            Dictionary mapping channel to status
        """
        attempts = DeliveryAttempt.objects.filter(notification=notification)
        
        status = {}
        for attempt in attempts:
            status[attempt.channel] = attempt.status
        
        return status
    
    @staticmethod
    def mark_notification_as_delivered(notification: NotificationObject):
        """
        Mark a notification as delivered (convenience method).
        
        This marks the notification itself as delivered, not individual channel attempts.
        
        Args:
            notification: The NotificationObject to mark as delivered
        """
        notification.status = 'DELIVERED'
        notification.save(update_fields=['status', 'updated_at'])
        
        logger.info(f"Notification {notification.notification_id} marked as delivered")


def deliver_notification(notification: NotificationObject, channels: List[str]) -> List[DeliveryAttempt]:
    """
    Convenience function to deliver a notification through the Delivery Engine.
    
    Args:
        notification: The NotificationObject to deliver
        channels: List of delivery channels
        
    Returns:
        List of DeliveryAttempt objects
    """
    return DeliveryEngine.deliver_notification(notification, channels)
