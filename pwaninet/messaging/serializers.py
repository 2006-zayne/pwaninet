from rest_framework import serializers
from .models import Conversation, ConversationMember, Message, MessageRead, MessageReaction, ConversationTheme
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
            'id', 'conversation', 'sender', 'content', 'encrypted_content', 'is_encrypted',
            'attachment', 'attachment_type', 'reply_to', 'reactions', 'read_receipts',
            'reply_to_details', 'attachment_url', 'created_at', 'edited_at', 'is_deleted'
        ]
        read_only_fields = ['id', 'created_at', 'edited_at', 'is_encrypted']

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
        fields = ['conversation', 'content', 'encrypted_content', 'is_encrypted', 'reply_to', 'attachment', 'attachment_type']


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
        fields = ['id', 'conversation', 'user', 'joined_at', 'last_read_message', 'is_muted', 'public_key']
        read_only_fields = ['id', 'joined_at']


class ConversationSerializer(serializers.ModelSerializer):
    """Serializer for conversations."""
    members = ConversationMemberSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    existing = serializers.SerializerMethodField()
    member_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Conversation
        fields = [
            'id', 'type', 'name', 'is_encrypted', 'members', 'member_ids',
            'created_at', 'updated_at', 'last_message', 'unread_count', 'existing'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_encrypted']

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

    def get_existing(self, obj):
        """Check if this conversation already existed (for direct conversations)."""
        return getattr(obj, '_existing', False)

    def create(self, validated_data):
        """
        Create a new conversation or return existing one for direct messages.
        For direct conversations between two users, only one conversation is allowed.
        """
        member_ids = validated_data.pop('member_ids', [])
        request = self.context.get('request')
        current_user = request.user if request else None

        # For direct conversations, check if one already exists between these users
        if validated_data.get('type') == Conversation.DIRECT and current_user:
            # Include current user in the check
            all_member_ids = set(member_ids + [current_user.id])

            # Only check for duplicates if there are exactly 2 members (1-on-1 conversation)
            if len(all_member_ids) == 2:
                other_user_id = list(all_member_ids - {current_user.id})[0]
                from users.models import User
                try:
                    other_user = User.objects.get(id=other_user_id)
                    existing = Conversation.get_direct_conversation_between(
                        current_user, other_user
                    )
                    if existing:
                        # Mark as existing and return it
                        existing._existing = True
                        return existing
                except User.DoesNotExist:
                    pass

        # Create new conversation
        conversation = Conversation.objects.create(**validated_data)
        conversation._existing = False

        # Add members
        if member_ids:
            from users.models import User
            members = User.objects.filter(id__in=member_ids)
            for member in members:
                ConversationMember.objects.create(
                    conversation=conversation,
                    user=member
                )

        return conversation


class ConversationThemeSerializer(serializers.ModelSerializer):
    """Serializer for conversation themes."""
    light_image_url = serializers.SerializerMethodField()
    dark_image_url = serializers.SerializerMethodField()
    css_variables_light = serializers.SerializerMethodField()
    css_variables_dark = serializers.SerializerMethodField()
    overlay_light = serializers.SerializerMethodField()
    overlay_dark = serializers.SerializerMethodField()

    class Meta:
        model = ConversationTheme
        fields = [
            'id', 'conversation', 'theme_type', 'light_color', 'dark_color',
            'light_gradient_start', 'light_gradient_end', 'dark_gradient_start', 
            'dark_gradient_end', 'gradient_angle', 'light_image_url', 'dark_image_url',
            'image_fit', 'overlay_opacity', 'light_overlay_color', 'dark_overlay_color',
            'css_variables_light', 'css_variables_dark', 'overlay_light', 'overlay_dark',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_light_image_url(self, obj):
        if obj.light_image:
            return obj.light_image.url
        return None

    def get_dark_image_url(self, obj):
        if obj.dark_image:
            return obj.dark_image.url
        return None

    def get_css_variables_light(self, obj):
        return obj.get_css_variables('light')

    def get_css_variables_dark(self, obj):
        return obj.get_css_variables('dark')

    def get_overlay_light(self, obj):
        return obj.get_overlay_css('light')

    def get_overlay_dark(self, obj):
        return obj.get_overlay_css('dark')


class ConversationThemeCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating conversation themes."""
    
    class Meta:
        model = ConversationTheme
        fields = [
            'theme_type', 'light_color', 'dark_color',
            'light_gradient_start', 'light_gradient_end', 'dark_gradient_start', 
            'dark_gradient_end', 'gradient_angle', 'light_image', 'dark_image',
            'image_fit', 'overlay_opacity', 'light_overlay_color', 'dark_overlay_color'
        ]

    def validate(self, data):
        theme_type = data.get('theme_type')
        
        if theme_type == 'solid':
            if not data.get('light_color') or not data.get('dark_color'):
                raise serializers.ValidationError(
                    "Solid color theme requires both light_color and dark_color"
                )
        elif theme_type == 'gradient':
            required_fields = ['light_gradient_start', 'light_gradient_end', 
                             'dark_gradient_start', 'dark_gradient_end']
            if not all(data.get(field) for field in required_fields):
                raise serializers.ValidationError(
                    "Gradient theme requires all gradient color fields"
                )
        elif theme_type == 'image':
            if not data.get('light_image') and not data.get('dark_image'):
                raise serializers.ValidationError(
                    "Image theme requires at least one image (light or dark mode)"
                )
        
        return data


class ConversationDetailSerializer(ConversationSerializer):
    """Detailed serializer for conversations with messages."""
    messages = MessageSerializer(many=True, read_only=True)

    class Meta(ConversationSerializer.Meta):
        fields = ConversationSerializer.Meta.fields + ['messages']
