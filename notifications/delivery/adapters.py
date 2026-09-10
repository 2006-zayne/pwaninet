"""
Delivery Adapters for PwaniNet Notification Engine v2

This module provides delivery adapters for different communication channels.
Following Chapter 9 of the specification.
"""
import logging
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
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

                # Resolve actor avatar and thumbnail for rich in-app toast
                actor_avatar = None
                if notification.metadata and isinstance(notification.metadata, dict):
                    actor_avatar = notification.metadata.get('actor_avatar')
                if not actor_avatar and hasattr(notification, 'actor') and notification.actor:
                    if hasattr(notification.actor, 'profile_pic') and notification.actor.profile_pic:
                        try:
                            actor_avatar = notification.actor.profile_pic.url
                        except Exception:
                            pass
                if not actor_avatar:
                    actor_avatar = '/static/images/web-app-manifest-192x192-rounded.png'

                thumb_img = None
                if notification.metadata and isinstance(notification.metadata, dict):
                    thumb_img = notification.metadata.get('thumbnail_url') or notification.metadata.get('image_url')

                try:
                    from notifications.delivery.image_utils import get_rounded_avatar_url, get_rounded_thumbnail_url
                    if actor_avatar:
                        rounded_av = get_rounded_avatar_url(actor_avatar)
                        if rounded_av:
                            actor_avatar = rounded_av
                    if thumb_img:
                        rounded_th = get_rounded_thumbnail_url(thumb_img)
                        if rounded_th:
                            thumb_img = rounded_th
                except Exception:
                    pass

                # Serialize notification data
                notification_data = {
                    'notification_id': str(notification.notification_id),
                    'type': notification.notification_type,
                    'category': notification.category,
                    'priority': notification.priority,
                    'title': notification.title,
                    'summary': notification.summary,
                    'actor_avatar': actor_avatar,
                    'thumbnail_url': thumb_img,
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

    @staticmethod
    def _make_absolute_url(url: Optional[str]) -> Optional[str]:
        """Convert relative paths or CDN links into fully qualified HTTPS URLs."""
        if not url:
            return None
        url = str(url).strip()
        if not url:
            return None
        if url.startswith('http://') or url.startswith('https://'):
            return url
        base_url = getattr(settings, 'SITE_URL', '') or getattr(settings, 'BASE_URL', '') or 'https://pwaninet.app'
        base_url = base_url.rstrip('/')
        if not url.startswith('/'):
            url = '/' + url
        return f"{base_url}{url}"

    def _resolve_push_content(self, notification: NotificationObject) -> dict:
        """
        Resolve rich push notification content matching in-app notification cards.
        Uses NotificationMessageEngine to construct human-friendly message text.
        Extracts resource previews (images, thumbnails, titles) for posts and docs.
        Consolidates to a single unified notification channel for mobile clients.
        """
        rich_body = None
        payload = None
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

        title = "PwaniNet"

        # 2. Resolve Actor Avatar / Icon
        actor_avatar = None
        if payload and payload.actors and payload.actors[0].avatar:
            actor_avatar = payload.actors[0].avatar
        if not actor_avatar and notification.metadata and isinstance(notification.metadata, dict):
            actor_avatar = notification.metadata.get('actor_avatar')
        if not actor_avatar and hasattr(notification, 'actor') and notification.actor:
            try:
                if hasattr(notification.actor, 'profile_pic') and notification.actor.profile_pic:
                    actor_avatar = notification.actor.profile_pic.url
            except Exception:
                pass
        if not actor_avatar:
            actor_avatar = '/static/images/web-app-manifest-192x192-rounded.png'

        actor_avatar = self._make_absolute_url(actor_avatar)
        try:
            from notifications.delivery.image_utils import get_rounded_avatar_url, get_rounded_thumbnail_url
            rounded_avatar = get_rounded_avatar_url(actor_avatar)
            if rounded_avatar:
                actor_avatar = self._make_absolute_url(rounded_avatar)
        except Exception as e:
            logger.debug(f"Could not generate rounded avatar: {e}")

        # 3. Resolve Resource Preview (Post / Document updates)
        preview_image = None
        resource_type = None
        resource_title = None
        resource_url = None

        if payload and payload.resource:
            res = payload.resource
            resource_type = res.type.value if hasattr(res.type, 'value') else str(res.type or '')
            resource_title = res.title
            resource_url = res.url
            if res.image_url:
                preview_image = self._make_absolute_url(res.image_url)

        # Fallback 1: check metadata directly if payload.resource image was missing
        if not preview_image and notification.metadata and isinstance(notification.metadata, dict):
            raw_thumb = notification.metadata.get('thumbnail_url') or notification.metadata.get('image_url')
            if raw_thumb:
                preview_image = self._make_absolute_url(raw_thumb)

        # Fallback 2: If still no preview_image and notification relates to a post, lookup post directly
        if not preview_image:
            post_id = None
            if str(notification.target_type).upper() in ['POST', 'POSTS'] and notification.target_id:
                post_id = notification.target_id
            elif str(notification.context_type).upper() in ['POST', 'POSTS'] and notification.context_id:
                post_id = notification.context_id
            elif notification.metadata and isinstance(notification.metadata, dict):
                post_id = notification.metadata.get('post_id') or notification.metadata.get('target_id')

            if post_id:
                try:
                    from posts.models import Post
                    post_obj = Post.objects.filter(id=int(post_id)).first() if str(post_id).isdigit() else Post.objects.filter(share_id=str(post_id)).first()
                    if post_obj:
                        if post_obj.images.exists():
                            first_img = post_obj.images.first()
                            thumb = getattr(first_img, 'get_thumbnail_url', lambda s: None)('400') or (first_img.image.url if getattr(first_img, 'image', None) else None)
                            if thumb:
                                preview_image = self._make_absolute_url(thumb)
                        if not preview_image and post_obj.video_poster:
                            preview_image = self._make_absolute_url(post_obj.video_poster.url)
                        if not preview_image and post_obj.shared_document:
                            doc = post_obj.shared_document
                            if hasattr(doc, 'latest_version') and doc.latest_version:
                                f_file = doc.latest_version.files.first()
                                if f_file and (f_file.thumbnail_path or f_file.preview_path):
                                    preview_image = self._make_absolute_url(f"/media/{f_file.thumbnail_path or f_file.preview_path}")
                        if not preview_image and post_obj.thumbnail:
                            preview_image = self._make_absolute_url(post_obj.thumbnail.url)
                except Exception as e:
                    logger.debug(f"Failed direct post thumbnail lookup for notification {notification.notification_id}: {e}")

        if preview_image:
            try:
                rounded_thumb = get_rounded_thumbnail_url(preview_image)
                if rounded_thumb:
                    preview_image = self._make_absolute_url(rounded_thumb)
            except Exception as e:
                logger.debug(f"Could not generate rounded thumbnail: {e}")

        # 4. Resolve Target URL
        try:
            from notifications.services.notification_service import resolve_notification_target_url
            destination_url = resolve_notification_target_url(notification)
        except Exception:
            destination_url = resource_url or '/notifications/'

        target_url = getattr(notification, 'target_url', None)
        if not target_url and notification.metadata and isinstance(notification.metadata, dict):
            target_url = notification.metadata.get('url')
        if not target_url:
            target_url = f'/notifications/{notification.notification_id}/'

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

        # 6. Android Notification Channel (unified channel matching native-app.js)
        channel_id = 'pwaninet_notifications'

        return {
            'title': title,
            'body': rich_body,
            'icon': actor_avatar,
            'image': preview_image,
            'resource_type': resource_type,
            'resource_title': resource_title,
            'tag': tag,
            'channel_id': channel_id,
            'target_url': target_url,
            'destination_url': destination_url,
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
            'image': content.get('image'),
            'badge': self._make_absolute_url('/static/images/pwaninetmonochrome.png'),
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
                'destination_url': content.get('destination_url') or content['target_url'],
                'notification_type': notification.notification_type,
                'category': notification.category,
                'image': content.get('image'),
                'resource_type': content.get('resource_type'),
                'resource_title': content.get('resource_title'),
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

            fcm_data = {
                "title": str(content.get('title') or 'PwaniNet'),
                "body": str(content.get('body') or ''),
                "url": str(content.get('target_url') or '/'),
                "destination_url": str(content.get('destination_url') or content.get('target_url') or '/'),
                "notification_id": str(notification.notification_id),
                "notification_type": str(notification.notification_type),
                "category": str(notification.category or ''),
                "icon": "ic_stat_pwaninet",
                "avatar_url": str(content.get('icon') or ''),
                "image": str(content.get('image') or ''),
                "resource_type": str(content.get('resource_type') or ''),
                "resource_title": str(content.get('resource_title') or ''),
                "channel_id": str(content.get('channel_id') or 'pwaninet_notifications'),
                "tag": str(content.get('tag') or f"pwaninet-{notification.notification_id}"),
                "color": "#2563eb",
            }

            is_android = str(getattr(sub, 'platform', '')).upper() in ('ANDROID_NATIVE', 'ANDROID')

            if is_android:
                # For Android Native, dispatch high-priority data message.
                # This guarantees PwaninetFirebaseMessagingService runs across all lifecycle states
                # (Foreground, Background, and Terminated), downloading the actor avatar as largeIcon (circular)
                # and media thumbnail as BigPictureStyle, while preventing Google Play Services from double-posting.
                message = messaging.Message(
                    android=messaging.AndroidConfig(
                        priority='high',
                        data=fcm_data
                    ),
                    data=fcm_data,
                    token=sub.fcm_token,
                )
            else:
                notification_kwargs = {
                    'title': content['title'],
                    'body': content['body'],
                }

                android_notif_kwargs = {
                    'icon': 'ic_stat_pwaninet',
                    'channel_id': content.get('channel_id') or 'pwaninet_notifications',
                    'tag': content.get('tag') or f"pwaninet-{notification.notification_id}",
                    'color': '#2563eb',
                    'default_sound': True,
                    'default_vibrate_timings': True,
                    'priority': 'high',
                    'visibility': 'public',
                }

                # Display image: Post thumbnail preview, or actor avatar as primary image
                display_image = content.get('image') or content.get('icon')
                if display_image:
                    notification_kwargs['image'] = display_image
                    android_notif_kwargs['image'] = display_image

                message = messaging.Message(
                    notification=messaging.Notification(**notification_kwargs),
                    android=messaging.AndroidConfig(
                        priority='high',
                        notification=messaging.AndroidNotification(**android_notif_kwargs),
                        data=fcm_data
                    ),
                    data=fcm_data,
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
                or "Unregistered" in err_msg
                or "registration-token-not-registered" in err_msg
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
