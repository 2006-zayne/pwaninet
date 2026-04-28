from django.db import models
from django.conf import settings


class Conversation(models.Model):
    """Conversation model for direct messages and group chats."""
    DIRECT = "direct"
    GROUP = "group"

    TYPE_CHOICES = [
        (DIRECT, "Direct"),
        (GROUP, "Group"),
    ]

    type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        default=DIRECT
    )
    name = models.CharField(max_length=255, null=True, blank=True)
    is_encrypted = models.BooleanField(default=True, help_text="End-to-end encryption enabled")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        if self.type == self.GROUP and self.name:
            return self.name
        return f"Conversation ({self.id})"

    @property
    def last_message(self):
        """Get the most recent message in this conversation."""
        return self.messages.order_by('-created_at').first()

    def get_last_message_read_status(self, user):
        """Get the read status of the last message for a specific user."""
        last_msg = self.last_message
        if not last_msg or last_msg.sender != user:
            return None
        
        # Check if any other member has read this message
        other_members = self.members.exclude(user=user)
        for member in other_members:
            if MessageRead.objects.filter(message=last_msg, user=member.user).exists():
                return 'read'
        
        # Check if message was delivered (exists in database)
        # For now, we'll consider it delivered if it's been sent
        return 'delivered' if last_msg else 'sent'

    @classmethod
    def get_direct_conversation_between(cls, user1, user2):
        """
        Find existing direct conversation between two users.
        Returns the conversation if found, None otherwise.
        """
        return cls.objects.filter(
            type=cls.DIRECT,
            members__user=user1
        ).filter(
            members__user=user2
        ).distinct().first()


class ConversationMember(models.Model):
    """Model to track conversation participants and their state."""
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='members'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversation_memberships'
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_message = models.ForeignKey(
        'Message',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='read_by_members'
    )
    is_muted = models.BooleanField(default=False)
    # E2E encryption: Store public key for each participant
    public_key = models.TextField(blank=True, null=True, help_text="User's public key for this conversation")

    class Meta:
        unique_together = ('conversation', 'user')
        indexes = [
            models.Index(fields=['conversation', 'user']),
            models.Index(fields=['user', 'conversation']),
        ]

    def __str__(self):
        return f"{self.user.username} in {self.conversation}"


class Message(models.Model):
    """Message model for conversations with E2E encryption support."""
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
        db_index=True
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        db_index=True
    )
    # Plaintext content (for non-encrypted or server-side storage)
    content = models.TextField(blank=True, null=True)
    # Encrypted content (for E2E encrypted messages)
    encrypted_content = models.TextField(blank=True, null=True)
    is_encrypted = models.BooleanField(default=False)
    attachment = models.FileField(
        upload_to='message_attachments/%Y/%m/%d/',
        null=True,
        blank=True
    )
    attachment_type = models.CharField(
        max_length=20,
        choices=[
            ('image', 'Image'),
            ('video', 'Video'),
            ('audio', 'Audio'),
            ('document', 'Document'),
        ],
        null=True,
        blank=True
    )
    reply_to = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='replies'
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
        ]

    def __str__(self):
        if self.is_encrypted:
            return f"Encrypted message from {self.sender.username}"
        preview = self.content[:50] + '...' if self.content and len(self.content) > 50 else self.content
        return f"Message from {self.sender.username}: {preview}"


class MessageRead(models.Model):
    """Per-user read receipts for messages."""
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='read_receipts'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='message_reads'
    )
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('message', 'user')
        indexes = [
            models.Index(fields=['message', 'user']),
            models.Index(fields=['user', 'read_at']),
        ]

    def __str__(self):
        return f"{self.user.username} read message {self.message.id}"


class MessageReaction(models.Model):
    """Reaction model for messages."""
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='reactions'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='message_reactions'
    )
    emoji = models.CharField(max_length=10, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('message', 'user', 'emoji')

    def __str__(self):
        return f"{self.user.username} reacted {self.emoji} to message {self.message.id}"
