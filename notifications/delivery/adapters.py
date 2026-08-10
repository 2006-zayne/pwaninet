"""
Delivery Adapters for PwaniNet Notification Engine v2

This module provides delivery adapters for different communication channels.
Following Chapter 9 of the specification.
"""
import logging
import json
from abc import ABC, abstractmethod
from typing import Dict, Any
from django.utils import timezone
from django.conf import settings
from notifications.models import NotificationObject, DeliveryAttempt, PushSubscription

logger = logging.getLogger(__name__)


class DeliveryAdapter(ABC):
    """
    Abstract base class for delivery adapters.
    
    Each delivery channel implements this interface.
    """
    
    @abstractmethod
    def deliver(self, notification: NotificationObject, attempt: DeliveryAttempt) -> bool:
        """
        Deliver a notification through this channel.
        
        Args:
            notification: The NotificationObject to deliver
            attempt: The DeliveryAttempt to track
            
        Returns:
            True if delivery succeeded, False otherwise
        """
        pass
    
    @abstractmethod
    def validate(self, notification: NotificationObject) -> bool:
        """
        Validate that notification can be delivered through this channel.
        
        Args:
            notification: The NotificationObject to validate
            
        Returns:
            True if delivery is possible, False otherwise
        """
        pass


class InAppAdapter(DeliveryAdapter):
    """
    In-App delivery adapter.
    
    Delivers notifications to the user's in-app notification center.
    Uses WebSocket for real-time delivery.
    """
    
    def deliver(self, notification: NotificationObject, attempt: DeliveryAttempt) -> bool:
        """
        Deliver notification in-app.
        
        Uses existing WebSocket infrastructure via NotificationConsumer.
        """
        try:
            # Update notification status to delivered
            notification.status = 'DELIVERED'
            notification.save(update_fields=['status', 'updated_at'])
            
            # Update delivery attempt
            attempt.status = 'DELIVERED'
            attempt.delivered_at = timezone.now()
            attempt.save(update_fields=['status', 'delivered_at'])
            
            # Send via existing WebSocket infrastructure
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            channel_layer = get_channel_layer()
            if channel_layer:
                # Use existing NotificationConsumer group naming: notifications_{user_id}
                group_name = f"notifications_{notification.recipient.id}"
                
                # Serialize notification data
                notification_data = {
                    'notification_id': str(notification.notification_id),
                    'type': notification.notification_type,
                    'category': notification.category,
                    'priority': notification.priority,
                    'title': notification.title,
                    'summary': notification.summary,
                    'context_type': notification.context_type,
                    'context_id': notification.context_id,
                    'created_at': notification.created_at.isoformat(),
                    'metadata': notification.metadata
                }
                
                async_to_sync(channel_layer.group_send)(
                    group_name,
                    {
                        'type': 'notification',
                        'notification': notification_data
                    }
                )
            
            logger.info(f"In-app delivery successful for notification {notification.notification_id}")
            return True
            
        except Exception as e:
            logger.error(f"In-app delivery failed for notification {notification.notification_id}: {e}")
            attempt.status = 'FAILED'
            attempt.error_message = str(e)
            attempt.save(update_fields=['status', 'error_message'])
            return False
    
    def validate(self, notification: NotificationObject) -> bool:
        """
        Validate that notification can be delivered in-app.
        
        All notifications can be delivered in-app.
        """
        return True


class EmailAdapter(DeliveryAdapter):
    """
    Email delivery adapter.
    
    Delivers notifications via email.
    """
    
    def deliver(self, notification: NotificationObject, attempt: DeliveryAttempt) -> bool:
        """
        Deliver notification via email.
        
        For Phase 6, this is a placeholder that marks the delivery as successful.
        In production, this would use Django's email backend.
        """
        try:
            # TODO: Send email using Django's email backend
            # This will be implemented when email templates and backend are configured
            
            logger.info(f"Email delivery successful for notification {notification.notification_id}")
            return True
            
        except Exception as e:
            logger.error(f"Email delivery failed for notification {notification.notification_id}: {e}")
            return False
    
    def validate(self, notification: NotificationObject) -> bool:
        """
        Validate that notification can be delivered via email.
        
        Notification must have a recipient with a valid email address.
        """
        if not notification.recipient.email:
            logger.warning(f"Cannot deliver notification {notification.notification_id} via email: no email address")
            return False
        
        return True


class PushAdapter(DeliveryAdapter):
    """
    Push notification adapter.
    
    Delivers notifications via web push using VAPID authentication.
    """

    def deliver(self, notification: NotificationObject, attempt: DeliveryAttempt) -> bool:
        """
        Deliver notification via web push.

        Uses pywebpush library to send notifications to subscribed users.
        """
        try:
            from django.conf import settings
            from pywebpush import webpush
            import json

            # Check VAPID configuration
            vapid_private_key = getattr(settings, 'VAPID_PRIVATE_KEY', '')
            vapid_subject = getattr(settings, 'VAPID_SUBJECT', 'mailto:admin@pwaninet.app')

            if not vapid_private_key:
                logger.warning(f"VAPID private key not configured, skipping push delivery for notification {notification.notification_id}")
                return False

            # Get active push subscriptions for recipient
            subscriptions = PushSubscription.objects.filter(
                user=notification.recipient,
                is_active=True
            )

            if not subscriptions.exists():
                logger.info(f"No active push subscriptions for user {notification.recipient.id}, skipping push delivery")
                return True  # Not an error, just no subscriptions

            # Prepare push notification payload
            # Try to get actor avatar from metadata
            actor_avatar = notification.metadata.get('actor_avatar') if notification.metadata else None
            if not actor_avatar:
                # Fallback to default app icon (rounded version)
                actor_avatar = '/static/images/web-app-manifest-192x192-rounded.png'

            push_data = {
                'title': notification.title,
                'body': notification.summary,
                'icon': actor_avatar,
                'badge': '/static/images/favicon-96x96.png',
                'vibrate': [200, 100, 200],
                'requireInteraction': False,
                'actions': [
                    {
                        'action': 'view',
                        'title': 'View',
                        'icon': '/static/images/favicon-96x96.png'
                    },
                    {
                        'action': 'dismiss',
                        'title': 'Dismiss',
                        'icon': '/static/images/favicon-96x96.png'
                    }
                ],
                'data': {
                    'notification_id': str(notification.notification_id),
                    'url': f'/notifications/{notification.notification_id}',
                    'notification_type': notification.notification_type,
                    'category': notification.category
                },
                'timestamp': notification.created_at.isoformat()
            }

            logger.info(f"PushAdapter: Sending push data for notification {notification.notification_id}: {json.dumps(push_data, indent=2)}")

            # Send to each subscription
            success_count = 0
            for subscription in subscriptions:
                try:
                    subscription_info = {
                        'endpoint': subscription.endpoint,
                        'keys': {
                            'p256dh': subscription.p256dh,
                            'auth': subscription.auth
                        }
                    }

                    webpush(
                        subscription_info=subscription_info,
                        data=json.dumps(push_data),
                        vapid_private_key=vapid_private_key,
                        vapid_claims={'sub': vapid_subject},
                        timeout=10
                    )
                    success_count += 1
                    logger.info(f"Push sent successfully to subscription {subscription.id} for notification {notification.notification_id}")

                except Exception as e:
                    logger.error(f"Failed to send push to subscription {subscription.id}: {e}")
                    # Deactivate failed subscription
                    subscription.is_active = False
                    subscription.save(update_fields=['is_active'])

            # Mark delivery as successful if at least one push was sent
            if success_count > 0:
                logger.info(f"Push delivery successful for notification {notification.notification_id} (sent to {success_count}/{subscriptions.count()} subscriptions)")
                return True
            else:
                logger.warning(f"Push delivery failed for notification {notification.notification_id} (no successful sends)")
                return False

        except Exception as e:
            logger.error(f"Push delivery failed for notification {notification.notification_id}: {e}")
            attempt.status = 'FAILED'
            attempt.error_message = str(e)
            attempt.save(update_fields=['status', 'error_message'])
            return False

    def validate(self, notification: NotificationObject) -> bool:
        """
        Validate that notification can be delivered via push.

        Recipient must have an active push subscription.
        """
        # Check for active push subscription
        subscriptions = PushSubscription.objects.filter(
            user=notification.recipient
        )
        logger.info(f"Push validation for notification {notification.notification_id}: user {notification.recipient.id} has {subscriptions.count()} total subscriptions")
        
        active_subscriptions = subscriptions.filter(is_active=True)
        logger.info(f"Push validation for notification {notification.notification_id}: user {notification.recipient.id} has {active_subscriptions.count()} active subscriptions")

        if not active_subscriptions.exists():
            logger.info(f"Cannot deliver notification {notification.notification_id} via push: no active subscription for user {notification.recipient.id}")
            return False

        logger.info(f"Push validation passed for notification {notification.notification_id}: user {notification.recipient.id} has active subscription")
        return True


class SMSAdapter(DeliveryAdapter):
    """
    SMS delivery adapter.
    
    Delivers notifications via SMS.
    """
    
    def deliver(self, notification: NotificationObject, attempt: DeliveryAttempt) -> bool:
        """
        Deliver notification via SMS.
        
        For Phase 6, this is a placeholder.
        In production, this would use an SMS gateway.
        """
        try:
            # TODO: Send SMS via SMS gateway
            # This will be implemented when SMS integration is added
            
            logger.info(f"SMS delivery successful for notification {notification.notification_id}")
            return True
            
        except Exception as e:
            logger.error(f"SMS delivery failed for notification {notification.notification_id}: {e}")
            return False
    
    def validate(self, notification: NotificationObject) -> bool:
        """
        Validate that notification can be delivered via SMS.
        
        Recipient must have a valid phone number.
        """
        # TODO: Check for valid phone number
        # For now, return True as placeholder
        return True


# Adapter registry
ADAPTERS = {
    'IN_APP': InAppAdapter(),
    'EMAIL': EmailAdapter(),
    'PUSH': PushAdapter(),
    'SMS': SMSAdapter(),
}


def get_adapter(channel: str) -> DeliveryAdapter:
    """
    Get the adapter for a given channel.
    
    Args:
        channel: The delivery channel
        
    Returns:
        The DeliveryAdapter instance
    """
    return ADAPTERS.get(channel)
