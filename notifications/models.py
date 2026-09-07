from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid


class PushSubscription(models.Model):
    """Model for storing web push notification subscriptions."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='push_subscriptions',
        db_index=True
    )
    endpoint = models.TextField(unique=True)
    p256dh = models.TextField()
    auth = models.TextField()
    user_agent = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"PushSubscription for {self.user.username} (active={self.is_active})"


# ============================================================================
# Notification Engine v2 - Event Infrastructure
# ============================================================================

class PlatformEvent(models.Model):
    """
    A Platform Event represents a meaningful occurrence within PwaniNet.
    
    Events are immutable historical facts that describe what happened.
    They do not decide whether notifications should be created - that is the
    responsibility of the Rules Engine.
    
    Architecture:
    - Events are published by platform modules
    - Events are consumed by the Notification Engine and other services
    - Events are never modified after creation
    - Events support versioning for schema evolution
    """
    
    # Event Identity
    event_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Globally unique event identifier"
    )
    
    # Event Type (follows <domain>.<resource>.<action> pattern)
    event_type = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Event type following canonical naming convention"
    )
    
    # Actor - who/what caused the event
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='authored_events',
        db_index=True,
        help_text="The user or system that caused this event"
    )
    
    # Source - which subsystem published the event
    SOURCE_CHOICES = [
        ('POSTS', 'Posts'),
        ('GROUPS', 'Groups'),
        ('USERS', 'Users'),
        ('DOCUMENTS', 'Documents'),
        ('COURSES', 'Courses'),
        ('MESSAGING', 'Messaging'),
        ('PROJECTS', 'Projects'),
        ('RELEASES', 'Releases'),
        ('CORE', 'Core'),
        ('NOTIFICATIONS', 'Notifications'),
        ('AUTHENTICATION', 'Authentication'),
        ('ADMIN', 'Admin'),
        ('STORAGE', 'Storage'),
        ('SYSTEM', 'System'),
    ]
    source = models.CharField(
        max_length=50,
        choices=SOURCE_CHOICES,
        db_index=True,
        help_text="The subsystem that published this event"
    )
    
    # Action - what occurred (past tense verb)
    action = models.CharField(
        max_length=50,
        db_index=True,
        help_text="The action that occurred (past tense)"
    )
    
    # Target - what the action was performed upon
    target_type = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Type of the target object (e.g., Post, Comment, Group)"
    )
    target_id = models.CharField(
        max_length=100,
        db_index=True,
        help_text="ID of the target object"
    )
    
    # Context - where the event occurred
    context_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
        help_text="Type of the context (e.g., Workspace, Course)"
    )
    context_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        help_text="ID of the context"
    )
    
    # Audience - intended scope of the event
    AUDIENCE_CHOICES = [
        ('SPECIFIC_USER', 'Specific User'),
        ('WORKSPACE_MEMBERS', 'Workspace Members'),
        ('COURSE_MEMBERS', 'Course Members'),
        ('FOLLOWERS', 'Followers'),
        ('ADMINISTRATORS', 'Administrators'),
        ('EVERYONE', 'Everyone'),
        ('CUSTOM_GROUP', 'Custom Group'),
    ]
    audience = models.CharField(
        max_length=50,
        choices=AUDIENCE_CHOICES,
        null=True,
        blank=True,
        help_text="Intended audience for this event"
    )
    
    # Metadata - event-specific information
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional event-specific information"
    )
    
    # Timestamp - when the event occurred
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When the event occurred"
    )
    
    # Version - event schema version
    version = models.CharField(
        max_length=10,
        default='1.0',
        help_text="Event schema version"
    )
    
    # Correlation - workflow grouping
    correlation_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Groups related events into workflows"
    )
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['event_type']),
            models.Index(fields=['actor']),
            models.Index(fields=['source']),
            models.Index(fields=['target_type', 'target_id']),
            models.Index(fields=['context_type', 'context_id']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['correlation_id']),
        ]
        verbose_name = 'Platform Event'
        verbose_name_plural = 'Platform Events'
    
    def __str__(self):
        return f"{self.event_type} by {self.actor} at {self.timestamp}"
    
    @property
    def target(self):
        """Get the actual target object if possible."""
        return f"{self.target_type}:{self.target_id}"
    
    @property
    def context(self):
        """Get the actual context object if possible."""
        if self.context_type and self.context_id:
            return f"{self.context_type}:{self.context_id}"
        return None
    
    def get_correlation_events(self):
        """Get all events sharing the same correlation ID."""
        if self.correlation_id:
            return PlatformEvent.objects.filter(correlation_id=self.correlation_id)
        return PlatformEvent.objects.none()


class NotificationPreference(models.Model):
    """
    User notification preferences for the new notification engine.
    Controls which notifications a user receives and how they are delivered.
    """
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
        db_index=True
    )
    
    # Email delivery preferences
    email_enabled = models.BooleanField(default=True, help_text="Enable email notifications")
    email_digest = models.BooleanField(default=False, help_text="Send daily digest instead of immediate emails")
    
    # Push notification preferences
    push_enabled = models.BooleanField(default=True, help_text="Enable push notifications")
    push_sound = models.BooleanField(default=True, help_text="Play sound for push notifications")
    
    # In-app notification preferences
    in_app_enabled = models.BooleanField(default=True, help_text="Enable in-app notifications")
    
    # Notification type preferences (JSON field for flexibility)
    # Structure: { "POSTS_POST_LIKED": {"email": true, "push": true, "in_app": true}, ... }
    type_preferences = models.JSONField(
        default=dict,
        blank=True,
        help_text="Per-notification-type delivery preferences"
    )
    
    # Quiet hours
    quiet_hours_enabled = models.BooleanField(default=False, help_text="Enable quiet hours")
    quiet_hours_start = models.TimeField(null=True, blank=True, help_text="Quiet hours start time")
    quiet_hours_end = models.TimeField(null=True, blank=True, help_text="Quiet hours end time")
    
    # Frequency limits
    max_notifications_per_hour = models.PositiveIntegerField(
        default=50,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text="Maximum notifications per hour"
    )
    
    # Do not disturb
    do_not_disturb_until = models.DateTimeField(null=True, blank=True, help_text="Do not disturb until this time")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Notification Preference"
        verbose_name_plural = "Notification Preferences"
    
    def __str__(self):
        return f"Preferences for {self.user.username}"
    
    def get_type_preference(self, notification_type, channel):
        """
        Get preference for a specific notification type and channel.
        
        Args:
            notification_type: Event type (e.g., 'POSTS_POST_LIKED')
            channel: Channel ('email', 'push', 'in_app')
            
        Returns:
            Boolean indicating if this notification should be delivered
        """
        # Check if type-specific preference exists
        type_pref = self.type_preferences.get(notification_type, {})
        if channel in type_pref:
            return type_pref[channel]
        
        # Fall back to global channel preference
        if channel == 'email':
            return self.email_enabled
        elif channel == 'push':
            return self.push_enabled
        elif channel == 'in_app':
            return self.in_app_enabled
        
        return True
    
    def set_type_preference(self, notification_type, channel, enabled):
        """
        Set preference for a specific notification type and channel.
        
        Args:
            notification_type: Event type (e.g., 'POSTS_POST_LIKED')
            channel: Channel ('email', 'push', 'in_app')
            enabled: Boolean indicating if notification should be delivered
        """
        if notification_type not in self.type_preferences:
            self.type_preferences[notification_type] = {}
        
        self.type_preferences[notification_type][channel] = enabled
        self.save()
    
    def is_quiet_hours(self):
        """Check if current time is within quiet hours."""
        if not self.quiet_hours_enabled:
            return False
        
        from django.utils import timezone
        now = timezone.now().time()
        
        if self.quiet_hours_start and self.quiet_hours_end:
            if self.quiet_hours_start <= self.quiet_hours_end:
                # Same day range (e.g., 22:00 to 08:00)
                return self.quiet_hours_start <= now <= self.quiet_hours_end
            else:
                # Crosses midnight (e.g., 22:00 to 08:00 next day)
                return now >= self.quiet_hours_start or now <= self.quiet_hours_end
        
        return False
    
    def is_do_not_disturb(self):
        """Check if do not disturb is currently active."""
        if not self.do_not_disturb_until:
            return False
        
        from django.utils import timezone
        return timezone.now() < self.do_not_disturb_until


class EventArchive(models.Model):
    """
    Archive for old platform events.
    
    Events are moved here after a configured retention period
    to maintain database performance while preserving historical records.
    """
    
    event_id = models.UUIDField(primary_key=True)
    event_data = models.JSONField(help_text="Complete event data as JSON")
    archived_at = models.DateTimeField(auto_now_add=True)
    original_timestamp = models.DateTimeField(db_index=True)
    
    class Meta:
        ordering = ['-original_timestamp']
        verbose_name = 'Event Archive'
        verbose_name_plural = 'Event Archives'
    
    def __str__(self):
        return f"Archived event {self.event_id} from {self.original_timestamp}"


# ============================================================================
# Notification Engine v2 - Notification Models
# ============================================================================

class NotificationObject(models.Model):
    """
    A Notification Object represents information intended for a specific user.
    
    Unlike Platform Events (which are immutable system facts), Notification Objects
    are mutable user-centric messages that may evolve through aggregation and
    lifecycle state changes.
    
    Architecture:
    - One notification, one recipient (never shared)
    - Mutable: may be updated during aggregation
    - References one or more Platform Events
    - Contains notification actions
    - Follows specification exactly
    """
    
    # Notification Identity
    notification_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Globally unique notification identifier"
    )
    
    # Recipient - exactly one user
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_objects',
        db_index=True,
        help_text="The user who receives this notification"
    )
    
    # Source Events - references to originating Platform Events
    # Stored as JSON array of event IDs for flexibility
    source_events = models.JSONField(
        default=list,
        help_text="List of Platform Event IDs that generated this notification"
    )
    
    # Type - semantic purpose of the notification
    TYPE_CHOICES = [
        ('LIKE', 'Like'),
        ('COMMENT', 'Comment'),
        ('MENTION', 'Mention'),
        ('ASSIGNMENT', 'Assignment'),
        ('MEETING', 'Meeting'),
        ('WORKSPACE', 'Workspace'),
        ('DOCUMENT', 'Document'),
        ('SECURITY', 'Security'),
        ('SYSTEM', 'System'),
        ('AI', 'AI'),
        ('GROUP', 'Group'),
        ('FOLLOW', 'Follow'),
        ('PINCH', 'Pinch'),
        ('INVITE', 'Invite'),
        ('SHARE', 'Share'),
        ('DOCUMENT_SHARED', 'Document Shared'),
    ]
    notification_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        db_index=True,
        help_text="Semantic type of the notification"
    )
    
    # Category - broader grouping for preference management
    CATEGORY_CHOICES = [
        ('SOCIAL', 'Social'),
        ('ACADEMIC', 'Academic'),
        ('WORKSPACE', 'Workspace'),
        ('DOCUMENT', 'Document'),
        ('SECURITY', 'Security'),
        ('SYSTEM', 'System'),
        ('AI', 'AI'),
    ]
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        db_index=True,
        help_text="Broader category for preference management"
    )
    
    # Priority - influences delivery timing and presentation
    PRIORITY_CHOICES = [
        ('CRITICAL', 'Critical'),
        ('HIGH', 'High'),
        ('NORMAL', 'Normal'),
        ('LOW', 'Low'),
    ]
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='NORMAL',
        db_index=True,
        help_text="Priority level for delivery and presentation"
    )
    
    # Title - concise human-readable headline
    title = models.CharField(
        max_length=255,
        help_text="Concise human-readable headline"
    )
    
    # Summary - additional context (may evolve during aggregation)
    summary = models.TextField(
        blank=True,
        help_text="Additional context that may evolve during aggregation"
    )
    
    # Context - where the notification belongs
    context_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
        help_text="Type of context (e.g., Course, Workspace)"
    )
    context_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        help_text="ID of the context"
    )
    
    # Status - lifecycle state
    STATUS_CHOICES = [
        ('CREATED', 'Created'),
        ('QUEUED', 'Queued'),
        ('DELIVERED', 'Delivered'),
        ('SEEN', 'Seen'),
        ('READ', 'Read'),
        ('ARCHIVED', 'Archived'),
        ('EXPIRED', 'Expired'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='CREATED',
        db_index=True,
        help_text="Current lifecycle status"
    )
    
    # Delivery Policy - intended delivery timing
    DELIVERY_POLICY_CHOICES = [
        ('IMMEDIATE', 'Immediate'),
        ('SCHEDULED', 'Scheduled'),
        ('DELAYED', 'Delayed'),
        ('DIGEST', 'Digest'),
    ]
    delivery_policy = models.CharField(
        max_length=20,
        choices=DELIVERY_POLICY_CHOICES,
        default='IMMEDIATE',
        help_text="Intended delivery policy"
    )
    
    # Aggregation Data - information for aggregation
    aggregation_key = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text="Key for grouping related notifications"
    )
    event_count = models.PositiveIntegerField(
        default=1,
        help_text="Number of merged events"
    )
    first_event_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of first event"
    )
    latest_event_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of latest event"
    )
    
    # Metadata - notification-specific information
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional notification-specific information"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When the notification was first created (immutable)"
    )
    updated_at = models.DateTimeField(
        auto_now=False,
        null=True,
        blank=True,
        db_index=True,
        help_text="Last modification time (only updated during aggregation, not on read status changes)"
    )
    
    # Expiration
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="When this notification becomes irrelevant"
    )
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['recipient']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['category']),
            models.Index(fields=['priority']),
            models.Index(fields=['status']),
            models.Index(fields=['aggregation_key']),
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['context_type', 'context_id']),
        ]
        verbose_name = 'Notification Object'
        verbose_name_plural = 'Notification Objects'
    
    def __str__(self):
        return f"{self.notification_type} for {self.recipient.username}"
    
    @property
    def is_read(self):
        """Convenience property for compatibility with legacy system."""
        return self.status == 'READ'
    
    @property
    def is_delivered(self):
        """Check if notification has been delivered."""
        return self.status in ['DELIVERED', 'SEEN', 'READ', 'ARCHIVED']
    
    def mark_as_read(self):
        """Mark notification as read."""
        self.status = 'READ'
        self.save(update_fields=['status', 'updated_at'])
    
    def mark_as_delivered(self):
        """Mark notification as delivered."""
        self.status = 'DELIVERED'
        self.save(update_fields=['status', 'updated_at'])


class NotificationAction(models.Model):
    """
    Actions that can be performed on a notification.
    
    Actions are first-class citizens in the notification system, not buried
    in metadata. This enables consistent support for workflows across all clients.
    
    Examples:
    - Group join: Accept, Decline
    - Meeting: Join, Snooze
    - Assignment: Open Assignment
    """
    
    ACTION_TYPES = [
        ('ACCEPT', 'Accept'),
        ('DECLINE', 'Decline'),
        ('JOIN', 'Join'),
        ('SNOOZE', 'Snooze'),
        ('REVIEW', 'Review'),
        ('OPEN', 'Open'),
        ('VIEW', 'View'),
        ('DELETE', 'Delete'),
        ('ARCHIVE', 'Archive'),
        ('MARK_READ', 'Mark as Read'),
        ('CUSTOM', 'Custom'),
    ]
    
    notification = models.ForeignKey(
        NotificationObject,
        on_delete=models.CASCADE,
        related_name='actions',
        help_text="The notification this action belongs to"
    )
    
    action_type = models.CharField(
        max_length=20,
        choices=ACTION_TYPES,
        help_text="Type of action"
    )
    
    label = models.CharField(
        max_length=50,
        help_text="Human-readable label for the action"
    )
    
    url = models.CharField(
        max_length=500,
        blank=True,
        help_text="URL to navigate when action is clicked"
    )
    
    method = models.CharField(
        max_length=10,
        default='GET',
        help_text="HTTP method for the action (GET, POST, etc.)"
    )
    
    payload = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional payload data for the action"
    )
    
    is_primary = models.BooleanField(
        default=False,
        help_text="Whether this is the primary action"
    )
    
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order for the action"
    )
    
    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Notification Action'
        verbose_name_plural = 'Notification Actions'
    
    def __str__(self):
        return f"{self.label} for notification {self.notification.notification_id}"


# ============================================================================
# Notification Engine v2 - Delivery Models
# ============================================================================

class DeliveryAttempt(models.Model):
    """
    A delivery attempt for a notification through a specific channel.
    
    Each delivery channel maintains its own delivery history.
    This allows independent tracking for each channel.
    """
    
    # Delivery channels
    CHANNEL_CHOICES = [
        ('IN_APP', 'In-App'),
        ('PUSH', 'Push'),
        ('EMAIL', 'Email'),
        ('SMS', 'SMS'),
    ]
    
    # Delivery status
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('QUEUED', 'Queued'),
        ('SENDING', 'Sending'),
        ('DELIVERED', 'Delivered'),
        ('FAILED', 'Failed'),
        ('RETRY_SCHEDULED', 'Retry Scheduled'),
        ('CANCELLED', 'Cancelled'),
        ('EXPIRED', 'Expired'),
    ]
    
    # Notification
    notification = models.ForeignKey(
        NotificationObject,
        on_delete=models.CASCADE,
        related_name='delivery_attempts',
        db_index=True,
        help_text="The notification being delivered"
    )
    
    # Channel
    channel = models.CharField(
        max_length=20,
        choices=CHANNEL_CHOICES,
        db_index=True,
        help_text="Delivery channel"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        db_index=True,
        help_text="Delivery status"
    )
    
    # Retry tracking
    attempt_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of delivery attempts"
    )
    next_retry_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Scheduled time for next retry"
    )
    
    # Error information
    error_message = models.TextField(
        blank=True,
        help_text="Error message if delivery failed"
    )
    error_code = models.CharField(
        max_length=50,
        blank=True,
        help_text="Error code if delivery failed"
    )
    
    # Timestamps
    queued_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the delivery was queued"
    )
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the delivery was sent"
    )
    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the delivery was confirmed"
    )
    failed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the delivery failed"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['notification']),
            models.Index(fields=['channel']),
            models.Index(fields=['status']),
            models.Index(fields=['next_retry_at']),
            models.Index(fields=['created_at']),
            models.Index(fields=['notification', 'channel']),
        ]
        verbose_name = 'Delivery Attempt'
        verbose_name_plural = 'Delivery Attempts'
    
    def __str__(self):
        return f"{self.channel} delivery for {self.notification.notification_id} - {self.status}"
    
    def mark_as_queued(self):
        """Mark delivery as queued."""
        self.status = 'QUEUED'
        self.queued_at = timezone.now()
        self.save(update_fields=['status', 'queued_at', 'updated_at'])
    
    def mark_as_sending(self):
        """Mark delivery as sending."""
        self.status = 'SENDING'
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at', 'updated_at'])
    
    def mark_as_delivered(self):
        """Mark delivery as delivered."""
        self.status = 'DELIVERED'
        self.delivered_at = timezone.now()
        self.save(update_fields=['status', 'delivered_at', 'updated_at'])
    
    def mark_as_failed(self, error_message=None, error_code=None):
        """Mark delivery as failed."""
        self.status = 'FAILED'
        self.failed_at = timezone.now()
        if error_message:
            self.error_message = error_message
        if error_code:
            self.error_code = error_code
        self.save(update_fields=['status', 'failed_at', 'error_message', 'error_code', 'updated_at'])
    
    def schedule_retry(self, delay_seconds):
        """Schedule a retry with exponential backoff."""
        from django.utils import timezone
        from datetime import timedelta
        
        self.status = 'RETRY_SCHEDULED'
        self.attempt_count += 1
        self.next_retry_at = timezone.now() + timedelta(seconds=delay_seconds)
        self.save(update_fields=['status', 'attempt_count', 'next_retry_at', 'updated_at'])
    
    def mark_as_expired(self):
        """Mark delivery as expired."""
        self.status = 'EXPIRED'
        self.save(update_fields=['status', 'updated_at'])
    
    def mark_as_cancelled(self):
        """Mark delivery as cancelled."""
        self.status = 'CANCELLED'
        self.save(update_fields=['status', 'updated_at'])
