from rest_framework import serializers
from .models import Notifications
from users.serializers import UserPublicSerializer
from groups.serializers import GroupSerializer
from posts.serializers import PostSerializer


class NotificationSerializer(serializers.ModelSerializer):
    sender = UserPublicSerializer(read_only=True)
    recipient = UserPublicSerializer(read_only=True)
    group = GroupSerializer(read_only=True)
    post = PostSerializer(read_only=True)
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)

    class Meta:
        model = Notifications
        fields = [
            'id', 'recipient', 'sender', 'group', 'post',
            'notification_type', 'notification_type_display',
            'msg', 'timestamp', 'is_read'
        ]
        read_only_fields = ['timestamp']


class NotificationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notifications
        fields = [
            'recipient', 'sender', 'group', 'post',
            'notification_type', 'msg'
        ]

    def validate(self, data):
        # Ensure notification_type is valid
        notification_type = data.get('notification_type')
        valid_types = [choice[0] for choice in Notifications.TYPE_CHOICES]
        if notification_type not in valid_types:
            raise serializers.ValidationError(
                f"Invalid notification_type. Must be one of: {valid_types}"
            )
        
        # Ensure required fields are present based on notification type
        if notification_type == Notifications.INVITE and not data.get('group'):
            raise serializers.ValidationError("Group is required for INVITE notifications")
        
        if notification_type == Notifications.LIKE and not data.get('post'):
            raise serializers.ValidationError("Post is required for LIKE notifications")
        
        if notification_type == Notifications.FOLLOW and not data.get('sender'):
            raise serializers.ValidationError("Sender is required for FOLLOW notifications")
        
        return data


class NotificationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notifications
        fields = ['is_read']


class NotificationBulkActionSerializer(serializers.Serializer):
    notification_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False
    )
    action = serializers.ChoiceField(
        choices=['mark_read', 'mark_unread', 'delete']
    )
