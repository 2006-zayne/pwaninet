from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator


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

        # If message exists but hasn't been read yet, it's just 'sent'
        # 'delivered' status should only be set when receiver confirms receipt via WebSocket
        return 'sent' if last_msg else None

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
        indexes = [
            models.Index(fields=['message', 'emoji']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} reacted {self.emoji} to message {self.message.id}"


class ConversationTheme(models.Model):
    """Per-user per-conversation theme settings."""
    
    THEME_TYPES = [
        ('solid', 'Solid Color'),
        ('gradient', 'CSS Gradient'),
        ('image', 'Image Wallpaper'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversation_themes'
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='themes'
    )
    theme_type = models.CharField(
        max_length=10,
        choices=THEME_TYPES,
        default='solid'
    )
    
    # Solid color theme
    light_color = models.CharField(
        max_length=7,
        validators=[RegexValidator(r'^#[0-9A-Fa-f]{6}$', 'Enter a valid hex color')],
        blank=True,
        null=True,
        help_text="Hex color for light mode"
    )
    dark_color = models.CharField(
        max_length=7,
        validators=[RegexValidator(r'^#[0-9A-Fa-f]{6}$', 'Enter a valid hex color')],
        blank=True,
        null=True,
        help_text="Hex color for dark mode"
    )
    
    # Gradient theme
    light_gradient_start = models.CharField(
        max_length=7,
        validators=[RegexValidator(r'^#[0-9A-Fa-f]{6}$', 'Enter a valid hex color')],
        blank=True,
        null=True,
        help_text="Start color for light mode gradient"
    )
    light_gradient_end = models.CharField(
        max_length=7,
        validators=[RegexValidator(r'^#[0-9A-Fa-f]{6}$', 'Enter a valid hex color')],
        blank=True,
        null=True,
        help_text="End color for light mode gradient"
    )
    dark_gradient_start = models.CharField(
        max_length=7,
        validators=[RegexValidator(r'^#[0-9A-Fa-f]{6}$', 'Enter a valid hex color')],
        blank=True,
        null=True,
        help_text="Start color for dark mode gradient"
    )
    dark_gradient_end = models.CharField(
        max_length=7,
        validators=[RegexValidator(r'^#[0-9A-Fa-f]{6}$', 'Enter a valid hex color')],
        blank=True,
        null=True,
        help_text="End color for dark mode gradient"
    )
    gradient_angle = models.IntegerField(
        default=45,
        help_text="Gradient angle in degrees"
    )
    
    # Image theme
    light_image = models.ImageField(
        upload_to='chat_themes/light/%Y/%m/',
        blank=True,
        null=True,
        help_text="Image for light mode",
        validators=[
            RegexValidator(
                r'.*\.(jpg|jpeg|png|gif|webp)$',
                'Only image files (JPG, PNG, GIF, WebP) are allowed'
            )
        ]
    )
    dark_image = models.ImageField(
        upload_to='chat_themes/dark/%Y/%m/',
        blank=True,
        null=True,
        help_text="Image for dark mode",
        validators=[
            RegexValidator(
                r'.*\.(jpg|jpeg|png|gif|webp)$',
                'Only image files (JPG, PNG, GIF, WebP) are allowed'
            )
        ]
    )
    
    # Image optimization fields
    light_image_hash = models.CharField(
        max_length=32,
        blank=True,
        null=True,
        help_text="Hash for image deduplication"
    )
    dark_image_hash = models.CharField(
        max_length=32,
        blank=True,
        null=True,
        help_text="Hash for image deduplication"
    )
    light_image_size = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Optimized image size in bytes"
    )
    dark_image_size = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Optimized image size in bytes"
    )
    image_fit = models.CharField(
        max_length=10,
        choices=[
            ('cover', 'Cover'),
            ('contain', 'Contain'),
            ('repeat', 'Repeat'),
        ],
        default='cover',
        help_text="How to fit the image"
    )
    
    # Overlay settings for readability
    overlay_opacity = models.FloatField(
        default=0.3,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Overlay opacity (0.0-1.0)"
    )
    light_overlay_color = models.CharField(
        max_length=7,
        default='#ffffff',
        validators=[RegexValidator(r'^#[0-9A-Fa-f]{6}$', 'Enter a valid hex color')],
        help_text="Overlay color for light mode"
    )
    dark_overlay_color = models.CharField(
        max_length=7,
        default='#000000',
        validators=[RegexValidator(r'^#[0-9A-Fa-f]{6}$', 'Enter a valid hex color')],
        help_text="Overlay color for dark mode"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'conversation')
        indexes = [
            models.Index(fields=['user', 'conversation']),
        ]
    
    def __str__(self):
        return f"{self.user.username}'s theme for conversation {self.conversation.id}"
    
    def get_css_variables(self, theme_mode='light'):
        """Generate CSS variables for this theme."""
        if self.theme_type == 'solid':
            color = self.light_color if theme_mode == 'light' else self.dark_color
            return {
                '--chat-bg': color or '#f8fafc',
                '--chat-bg-type': 'solid',
            }
        elif self.theme_type == 'gradient':
            start = self.light_gradient_start if theme_mode == 'light' else self.dark_gradient_start
            end = self.light_gradient_end if theme_mode == 'light' else self.dark_gradient_end
            return {
                '--chat-bg': f'linear-gradient({self.gradient_angle}deg, {start}, {end})',
                '--chat-bg-type': 'gradient',
            }
        elif self.theme_type == 'image':
            image = self.light_image.url if theme_mode == 'light' and self.light_image else \
                   (self.dark_image.url if theme_mode == 'dark' and self.dark_image else None)
            return {
                '--chat-bg': f'url({image})' if image else 'none',
                '--chat-bg-type': 'image',
                '--chat-bg-fit': self.image_fit,
            }
        
        return {'--chat-bg': '#f8fafc', '--chat-bg-type': 'solid'}
    
    def get_overlay_css(self, theme_mode='light'):
        """Generate overlay CSS variables."""
        overlay_color = self.light_overlay_color if theme_mode == 'light' else self.dark_overlay_color
        return {
            '--chat-overlay-color': overlay_color,
            '--chat-overlay-opacity': str(self.overlay_opacity),
        }
