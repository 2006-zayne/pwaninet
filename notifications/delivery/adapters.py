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
                
                from notifications.queries.notification_queries import get_unread_count
                unread_count = get_unread_count(notification.recipient)

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
                    'unread_count': unread_count,
                    'metadata': notification.metadata
                }
                
                async_to_sync(channel_layer.group_send)(
                    group_name,
                    {
                        'type': 'notification',
                        'notification': notification_data,
                        'unread_count': unread_count
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


# Firebase Admin Initialization Guard
_firebase_app = None


def get_firebase_app():
    global _firebase_app
    if _firebase_app is None:
        try:
            import os
            import firebase_admin
            from firebase_admin import credentials
            if not firebase_admin._apps:
                cred_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', None)
                if cred_path and os.path.exists(cred_path):
                    cred = credentials.Certificate(cred_path)
                    _firebase_app = firebase_admin.initialize_app(cred)
                    logger.info("Firebase Admin SDK initialized successfully with credentials at: %s", cred_path)
                else:
                    logger.warning("FIREBASE_CREDENTIALS_PATH not found or invalid (%s). Native push notifications disabled.", cred_path)
            else:
                _firebase_app = firebase_admin.get_app()
        except Exception as err:
            logger.error("Failed to initialize Firebase Admin SDK: %s", err)
    return _firebase_app


class PushAdapter(DeliveryAdapter):
    """
    Push notification adapter.
    
    Delivers notifications via Web Push (VAPID via pywebpush) and Native Push (FCM via Firebase Admin SDK).
    """

    def deliver(self, notification: NotificationObject, attempt: Any = None) -> bool:
        """
        Deliver notification via Web Push or Native FCM push.
        """
        try:
            subscriptions = PushSubscription.objects.filter(
                user=notification.recipient,
                is_active=True
            )

            if not subscriptions.exists():
                logger.info(f"No active push subscriptions for user {notification.recipient.id}, skipping push delivery")
                return True  # Not an error, just no subscriptions

            delivered_count = 0
            for sub in subscriptions:
                if sub.token_type == PushSubscription.TokenType.VAPID:
                    if self._deliver_webpush(sub, notification):
                        delivered_count += 1
                elif sub.token_type == PushSubscription.TokenType.FCM:
                    if self._deliver_fcm(sub, notification):
                        delivered_count += 1

            if delivered_count > 0:
                logger.info(f"Push delivery successful for notification {notification.notification_id} (delivered to {delivered_count}/{subscriptions.count()} subscriptions)")
                if attempt:
                    attempt.status = 'DELIVERED'
                    attempt.delivered_at = timezone.now()
                    attempt.save(update_fields=['status', 'delivered_at'])
                return True
            else:
                logger.warning(f"Push delivery failed for notification {notification.notification_id} across all active subscriptions")
                if attempt:
                    attempt.status = 'FAILED'
                    attempt.error_message = 'Failed to deliver push across all active subscriptions.'
                    attempt.save(update_fields=['status', 'error_message'])
                return False

        except Exception as e:
            logger.error(f"Push delivery failed for notification {notification.notification_id}: {e}", exc_info=True)
            if attempt:
                attempt.status = 'FAILED'
                attempt.error_message = str(e)
                attempt.save(update_fields=['status', 'error_message'])
            return False

    def _resolve_push_content(self, notification: NotificationObject) -> dict:
        """
        Resolve rich push notification content matching in-app notification cards.
        Uses NotificationMessageEngine to construct human-friendly message text
        (e.g., 'Grace Student pinched you.' or 'Zayne Dev liked your post.').
        Also computes smart aggregation / collapse tags and Android channels.
        """
        # 1. Resolve human-friendly conversational message body
        rich_body = None
        try:
            from notifications.rendering.adapters import get_payload_adapter
            from notifications.rendering.message_engine import message_engine

            adapter = get_payload_adapter(notification)
            payload = adapter.to_standard_payload(notification)
            rich_body = message_engine.generate_message(payload)
        except Exception as e:
            logger.debug(f"Failed to generate rich message for notification {notification.notification_id}: {e}")

        if not rich_body:
            rich_body = notification.summary or notification.title or "You have a new notification"

        # 2. Resolve Title
        title = "PwaniNet"

        # 3. Resolve Actor Avatar / Icon
        actor_avatar = None
        if notification.metadata and isinstance(notification.metadata, dict):
            actor_avatar = notification.metadata.get('actor_avatar')
        if not actor_avatar:
            actor_avatar = '/static/images/web-app-manifest-192x192-rounded.png'

        # 4. Resolve Target URL
        target_url = getattr(notification, 'target_url', None)
        if not target_url and notification.metadata and isinstance(notification.metadata, dict):
            target_url = notification.metadata.get('url')
        if not target_url:
            target_url = f'/notifications/{notification.notification_id}'

        # 5. Smart Tagging & Grouping
        # Collapse related notifications together to avoid notification flooding
        if notification.aggregation_key:
            tag = f"pwaninet-{notification.aggregation_key}"
        elif notification.context_type and notification.context_id:
            tag = f"pwaninet-{str(notification.context_type).lower()}-{notification.context_id}"
        else:
            cat_str = str(notification.category).lower() if notification.category else "general"
            type_str = str(notification.notification_type).lower() if notification.notification_type else "alert"
            tag = f"pwaninet-{cat_str}-{type_str}"

        # 6. Android Notification Channel
        category = str(notification.category or '').upper()
        ntype = str(notification.notification_type or '').upper()
        if category == 'MESSAGING' or 'MESSAGE' in ntype:
            channel_id = 'pwaninet_messages'
        else:
            channel_id = 'pwaninet_social'

        return {
            'title': title,
            'body': rich_body,
            'icon': actor_avatar,
            'tag': tag,
            'channel_id': channel_id,
            'target_url': target_url,
        }

    def _deliver_webpush(self, sub: PushSubscription, notification: NotificationObject) -> bool:
        """Deliver via W3C WebPush using pywebpush."""
        from pywebpush import webpush, WebPushException

        vapid_private_key = getattr(settings, 'VAPID_PRIVATE_KEY', '')
        vapid_subject = getattr(settings, 'VAPID_SUBJECT', 'mailto:admin@pwaninet.app')

        if not vapid_private_key:
            logger.warning(f"VAPID private key not configured, skipping web push for subscription {sub.id}")
            return False

        if not sub.endpoint or not sub.p256dh or not sub.auth:
            logger.warning(f"Subscription {sub.id} missing endpoint/keys, deactivating")
            sub.is_active = False
            sub.save(update_fields=['is_active'])
            return False

        content = self._resolve_push_content(notification)

        push_data = {
            'title': content['title'],
            'body': content['body'],
            'icon': content['icon'],
            'badge': '/static/images/favicon-96x96.png',
            'vibrate': [200, 100, 200],
            'requireInteraction': False,
            'tag': content['tag'],
            'renotify': True,
            'actions': [
                {'action': 'view', 'title': 'View', 'icon': '/static/images/favicon-96x96.png'},
                {'action': 'dismiss', 'title': 'Dismiss', 'icon': '/static/images/favicon-96x96.png'}
            ],
            'data': {
                'notification_id': str(notification.notification_id),
                'url': content['target_url'],
                'notification_type': notification.notification_type,
                'category': notification.category,
                'tag': content['tag'],
            },
            'timestamp': notification.created_at.isoformat() if notification.created_at else timezone.now().isoformat()
        }

        try:
            subscription_info = {
                'endpoint': sub.endpoint,
                'keys': {
                    'p256dh': sub.p256dh,
                    'auth': sub.auth
                }
            }

            webpush(
                subscription_info=subscription_info,
                data=json.dumps(push_data),
                vapid_private_key=vapid_private_key,
                vapid_claims={'sub': vapid_subject},
                timeout=10
            )
            logger.info(f"WebPush sent successfully to subscription {sub.id} for notification {notification.notification_id}")
            return True

        except WebPushException as ex:
            logger.warning(f"WebPush failed for subscription {sub.id}: {ex}")
            # Invalidate expired / unsubscribed endpoints
            if ex.response and getattr(ex.response, 'status_code', None) in [404, 410]:
                sub.is_active = False
                sub.save(update_fields=['is_active'])
                logger.info(f"Deactivated expired web push subscription {sub.id}")
            return False
        except Exception as ex:
            logger.error(f"Unexpected WebPush error for subscription {sub.id}: {ex}")
            return False

    def _deliver_fcm(self, sub: PushSubscription, notification: NotificationObject) -> bool:
        """Deliver via Firebase Cloud Messaging for native devices."""
        app = get_firebase_app()
        if not app:
            logger.warning("Firebase app unavailable; skipping FCM delivery.")
            return False

        if not sub.fcm_token:
            logger.warning(f"Subscription {sub.id} missing fcm_token, deactivating")
            sub.is_active = False
            sub.save(update_fields=['is_active'])
            return False

        content = self._resolve_push_content(notification)

        try:
            from firebase_admin import messaging
            message = messaging.Message(
                notification=messaging.Notification(
                    title=content['title'],
                    body=content['body'],
                ),
                android=messaging.AndroidConfig(
                    priority='high',
                    collapse_key=content['tag'],
                    notification=messaging.AndroidNotification(
                        channel_id=content['channel_id'],
                        tag=content['tag'],
                        color='#2563eb',
                        sound='default',
                        click_action='OPEN_NOTIFICATION',
                    ),
                    data={
                        "url": content['target_url'] or '/',
                        "notification_id": str(notification.notification_id),
                        "notification_type": str(notification.notification_type),
                        "category": str(notification.category),
                        "icon": content['icon'],
                        "tag": content['tag'],
                    }
                ),
                data={
                    "url": content['target_url'] or '/',
                    "notification_id": str(notification.notification_id),
                    "notification_type": str(notification.notification_type),
                    "category": str(notification.category),
                    "tag": content['tag'],
                },
                token=sub.fcm_token,
            )
            messaging.send(message, app=app)
            logger.info(f"FCM sent successfully to subscription {sub.id} for notification {notification.notification_id}")
            return True
        except Exception as ex:
            err_msg = str(ex)
            ex_name = type(ex).__name__
            logger.warning(f"FCM delivery failed for user {sub.user_id} (sub {sub.id}): [{ex_name}] {err_msg}")
            if (
                "Unregistered" in ex_name
                or "NotFound" in ex_name
                or "InvalidArgument" in ex_name
                or "Unregistered" in err_msg
                or "InvalidArgument" in err_msg
                or "not a valid FCM registration token" in err_msg
            ):
                sub.is_active = False
                sub.save(update_fields=['is_active'])
                logger.info(f"Deactivated invalid FCM subscription {sub.id}")
            return False

    def validate(self, notification: NotificationObject) -> bool:
        """
        Validate that notification can be delivered via push.
        Recipient must have an active push subscription (VAPID or FCM).
        """
        subscriptions = PushSubscription.objects.filter(
            user=notification.recipient,
            is_active=True
        )
        if not subscriptions.exists():
            logger.info(f"Cannot deliver notification {notification.notification_id} via push: no active subscription for user {notification.recipient.id}")
            return False

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
