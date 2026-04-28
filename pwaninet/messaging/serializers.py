from rest_framework import serializers
from .models import Conversation, ConversationMember, Message, MessageRead, MessageReaction
from users.serializers import UserSerializer


class MessageReactionSerializer(serializers.ModelSerializer):
    """Serializer for message reactions."""
    user = UserSerializer(read_only=True)

    class Meta:
        model = MessageReaction
        fields = ['id', 'message', 'user', 'emoji', 'created_at']
        read_only_fields = ['id', 'created_at']


class MessageReadSerializer(serializers.ModelSerializer):
    """Serializer for message read receipts."""
    user = UserSerializer(read_only=True)

    class Meta:
        model = MessageRead
        fields = ['id', 'message', 'user', 'read_at']
        read_only_fields = ['id', 'read_at']


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for messages."""
    sender = UserSerializer(read_only=True)
    reactions = MessageReactionSerializer(many=True, read_only=True)
    read_receipts = MessageReadSerializer(many=True, read_only=True)
    reply_to_details = serializers.SerializerMethodField()
    attachment_url = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'content', 'attachment',
            'attachment_type', 'reply_to', 'reactions', 'read_receipts',
            'reply_to_details', 'attachment_url', 'created_at', 'edited_at', 'is_deleted'
        ]
        read_only_fields = ['id', 'created_at', 'edited_at']

    def get_reply_to_details(self, obj):
        """Get details of the message being replied to."""
        if obj.reply_to:
            return MessageSerializer(obj.reply_to).data
        return None

    def get_attachment_url(self, obj):
        """Get the URL of the attachment."""
        if obj.attachment:
            return obj.attachment.url
        return None


class MessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating messages."""
    class Meta:
        model = Message
        fields = ['conversation', 'content', 'reply_to', 'attachment', 'attachment_type']


class MessageUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating messages."""
    class Meta:
        model = Message
        fields = ['content']
        read_only_fields = ['id', 'created_at', 'sender', 'conversation']


class ConversationMemberSerializer(serializers.ModelSerializer):
    """Serializer for conversation members."""
    user = UserSerializer(read_only=True)

    class Meta:
        model = ConversationMember
        fields = ['id', 'conversation', 'user', 'joined_at', 'last_read_message', 'is_muted']
        read_only_fields = ['id', 'joined_at']


class ConversationSerializer(serializers.ModelSerializer):
    """Serializer for conversations."""
    members = ConversationMemberSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    member_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Conversation
        fields = [
            'id', 'type', 'name', 'members', 'member_ids',
            'created_at', 'updated_at', 'last_message', 'unread_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_last_message(self, obj):
        """Get the last message in the conversation."""
        last_message = obj.messages.last()
        if last_message:
            return MessageSerializer(last_message).data
        return None

    def get_unread_count(self, obj):
        """Get the count of unread messages for the current user."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            member = obj.members.filter(user=request.user).first()
            if member and member.last_read_message:
                return obj.messages.filter(
                    created_at__gt=member.last_read_message.created_at
                ).count()
            return obj.messages.count()
        return 0

    def create(self, validated_data):
        """Create a new conversation."""
        member_ids = validated_data.pop('member_ids', [])
        conversation = Conversation.objects.create(**validated_data)
        
        if member_ids:
            from users.models import User
            members = User.objects.filter(id__in=member_ids)
            for member in members:
                ConversationMember.objects.create(
                    conversation=conversation,
                    user=member
                )
        
        return conversation


class ConversationDetailSerializer(ConversationSerializer):
    """Detailed serializer for conversations with messages."""
    messages = MessageSerializer(many=True, read_only=True)

    class Meta(ConversationSerializer.Meta):
        fields = ConversationSerializer.Meta.fields + ['messages']
