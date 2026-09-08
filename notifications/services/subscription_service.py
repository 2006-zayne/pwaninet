"""
Service layer for push subscription management.

This module handles all business logic for push notification subscriptions,
including creation, updates, and deactivation. Views should delegate to this
service layer rather than containing business logic directly.
"""
from django.db import transaction
from notifications.models import PushSubscription


class SubscriptionService:
    """Service for managing push notification subscriptions."""

    @staticmethod
    @transaction.atomic
    def subscribe(user, validated_data):
        """
        Create or update a push subscription for a user (VAPID or FCM).
        """
        token_type = validated_data.get('token_type', PushSubscription.TokenType.VAPID)
        platform = validated_data.get('platform', PushSubscription.Platform.WEB)
        device_id = validated_data.get('device_id')
        user_agent = validated_data.get('user_agent', '')

        if token_type == PushSubscription.TokenType.VAPID:
            endpoint = validated_data.get('endpoint')
            keys = validated_data.get('keys', {})
            p256dh = keys.get('p256dh') or validated_data.get('p256dh')
            auth = keys.get('auth') or validated_data.get('auth')

            if not endpoint or not p256dh or not auth:
                raise ValueError("Missing required WebPush keys (endpoint, p256dh, auth)")

            subscription, _ = PushSubscription.objects.update_or_create(
                user=user,
                endpoint=endpoint,
                defaults={
                    'platform': platform,
                    'token_type': PushSubscription.TokenType.VAPID,
                    'p256dh': p256dh,
                    'auth': auth,
                    'user_agent': user_agent,
                    'device_id': device_id,
                    'is_active': True,
                }
            )
            return subscription

        elif token_type == PushSubscription.TokenType.FCM:
            fcm_token = validated_data.get('fcm_token')
            if not fcm_token:
                raise ValueError("Missing required fcm_token")

            subscription, _ = PushSubscription.objects.update_or_create(
                user=user,
                fcm_token=fcm_token,
                defaults={
                    'platform': platform or PushSubscription.Platform.ANDROID_NATIVE,
                    'token_type': PushSubscription.TokenType.FCM,
                    'device_id': device_id,
                    'user_agent': user_agent,
                    'is_active': True,
                }
            )
            return subscription
        else:
            raise ValueError(f"Unsupported token_type: {token_type}")

    @staticmethod
    @transaction.atomic
    def unsubscribe(user, endpoint):
        """
        Deactivate a push subscription for a user.

        This method performs a soft delete by setting is_active to False.
        The record is preserved in the database for audit purposes and to
        prevent duplicate subscriptions if the user re-subscribes.

        Args:
            user: The user instance unsubscribing
            endpoint: The endpoint URL to unsubscribe

        Returns:
            PushSubscription: The deactivated subscription instance

        Raises:
            PushSubscription.DoesNotExist: If no subscription exists for the user/endpoint
        """
        subscription = PushSubscription.objects.get(
            user=user,
            endpoint=endpoint
        )
        subscription.is_active = False
        subscription.save()
        return subscription
