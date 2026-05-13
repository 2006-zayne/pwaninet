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
        Create or update a push subscription for a user.

        This method implements deduplication logic:
        - If a subscription with the same endpoint exists for the user, update it
        - Otherwise, create a new subscription

        Args:
            user: The user instance subscribing
            validated_data: Dictionary containing validated subscription data with keys:
                - endpoint: str (required)
                - p256dh: str (required)
                - auth: str (required)
                - user_agent: str (optional)

        Returns:
            PushSubscription: The created or updated subscription instance
        """
        endpoint = validated_data['endpoint']
        p256dh = validated_data['p256dh']
        auth = validated_data['auth']
        user_agent = validated_data.get('user_agent', '')

        # Try to find existing subscription by endpoint for this user
        try:
            subscription = PushSubscription.objects.get(
                user=user,
                endpoint=endpoint
            )
            # Update existing subscription
            subscription.p256dh = p256dh
            subscription.auth = auth
            subscription.user_agent = user_agent
            subscription.is_active = True
            subscription.save()
            return subscription
        except PushSubscription.DoesNotExist:
            # Create new subscription
            subscription = PushSubscription.objects.create(
                user=user,
                endpoint=endpoint,
                p256dh=p256dh,
                auth=auth,
                user_agent=user_agent,
                is_active=True
            )
            return subscription

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
