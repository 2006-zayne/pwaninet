"""
Pwanimate API Serializers.
"""

from rest_framework import serializers
from pwanimate.models import PwanimateConversation, PwanimateMessage


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for individual conversation messages."""

    class Meta:
        model = PwanimateMessage
        fields = [
            "id",
            "role",
            "content",
            "citations",
            "sources",
            "created_at",
        ]
        read_only_fields = fields


class ConversationListSerializer(serializers.ModelSerializer):
    """Serializer for listing user conversations."""

    class Meta:
        model = PwanimateConversation
        fields = [
            "id",
            "title",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ConversationDetailSerializer(serializers.ModelSerializer):
    """Serializer for full conversation thread with messages."""

    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = PwanimateConversation
        fields = [
            "id",
            "title",
            "created_at",
            "updated_at",
            "messages",
        ]
        read_only_fields = fields
