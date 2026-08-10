from rest_framework import serializers
from .models import NotificationObject
from notifications.notifications.registry import NotificationStatuses
from users.serializers import UserPublicSerializer


class NotificationSerializer(serializers.ModelSerializer):
    recipient = UserPublicSerializer(read_only=True)
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = NotificationObject
        fields = [
            'notification_id', 'recipient', 'source_events',
            'notification_type', 'notification_type_display',
            'category', 'category_display',
            'priority', 'priority_display',
            'title', 'summary',
            'context_type', 'context_id',
            'status', 'status_display',
            'delivery_policy', 'aggregation_key',
            'event_count', 'first_event_time', 'latest_event_time',
            'metadata', 'created_at', 'updated_at', 'expires_at'
        ]
        read_only_fields = ['notification_id', 'created_at', 'updated_at']


class NotificationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationObject
        fields = [
            'recipient', 'notification_type', 'category', 'priority',
            'title', 'summary', 'context_type', 'context_id',
            'delivery_policy', 'metadata'
        ]

    def validate(self, data):
        # Ensure notification_type is valid
        notification_type = data.get('notification_type')
        valid_types = [choice[0] for choice in NotificationObject.TYPE_CHOICES]
        if notification_type not in valid_types:
            raise serializers.ValidationError(
                f"Invalid notification_type. Must be one of: {valid_types}"
            )
        
        return data


class NotificationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationObject
        fields = ['status']


class NotificationBulkActionSerializer(serializers.Serializer):
    notification_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False
    )
    action = serializers.ChoiceField(
        choices=['mark_read', 'mark_unread', 'delete']
    )


class SubscriptionSerializer(serializers.Serializer):
    """Serializer for push subscription data."""
    endpoint = serializers.CharField(required=True, allow_blank=False)
    p256dh = serializers.CharField(required=True, allow_blank=False)
    auth = serializers.CharField(required=True, allow_blank=False)
    user_agent = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_endpoint(self, value):
        """Validate endpoint is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Endpoint cannot be empty.")
        return value.strip()

    def validate_p256dh(self, value):
        """Validate p256dh key is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("p256dh key cannot be empty.")
        return value.strip()

    def validate_auth(self, value):
        """Validate auth key is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("auth key cannot be empty.")
        return value.strip()


class UnsubscribeSerializer(serializers.Serializer):
    """Serializer for unsubscribe request."""
    endpoint = serializers.CharField(required=True, allow_blank=False)

    def validate_endpoint(self, value):
        """Validate endpoint is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Endpoint cannot be empty.")
        return value.strip()
