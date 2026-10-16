from django.db import models
from django.conf import settings
import uuid
from django.utils import timezone

class FeedbackTicket(models.Model):
    class Status(models.TextChoices):
        UNREAD = 'UNREAD', 'Unread'
        OPEN = 'OPEN', 'Open'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        RESOLVED = 'RESOLVED', 'Resolved'
        CLOSED = 'CLOSED', 'Closed'

    class Priority(models.TextChoices):
        LOW = 'LOW', 'Low'
        NORMAL = 'NORMAL', 'Normal'
        URGENT = 'URGENT', 'Urgent'
        
    class Category(models.TextChoices):
        BUG = 'BUG', 'Bug Report'
        FEATURE = 'FEATURE', 'Feature Request'
        ACADEMIC = 'ACADEMIC', 'Academic Issue'
        ACCOUNT = 'ACCOUNT', 'Account Help'
        OTHER = 'OTHER', 'Other'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='feedback_tickets')
    subject = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    message = models.TextField()
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UNREAD, db_index=True)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.NORMAL)
    
    assigned_admin = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_tickets')
    admin_notes = models.TextField(blank=True, null=True)
    
    # Context telemetry
    device_info = models.TextField(blank=True, null=True)
    current_url = models.CharField(max_length=500, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_category_display()} from {self.sender.username}: {self.subject}"


class FeedbackReply(models.Model):
    ticket = models.ForeignKey(FeedbackTicket, on_delete=models.CASCADE, related_name='replies')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        
    def __str__(self):
        return f"Reply on {self.ticket.id} by {self.sender.username}"


class UserDailyActivity(models.Model):
    """One activity heartbeat per account and local calendar day."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='daily_activity',
    )
    activity_date = models.DateField(db_index=True)
    last_seen_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'activity_date'], name='unique_user_daily_activity'),
        ]
        indexes = [models.Index(fields=['activity_date', 'last_seen_at'], name='admin_daily_activity_idx')]

    def __str__(self):
        return f"{self.user_id} active on {self.activity_date}"


class PageMaintenance(models.Model):
    """Per-page maintenance lock, managed from the Django admin.

    When ``is_active`` is True, ``MaintenanceModeMiddleware`` short-circuits
    any request whose path starts with ``path_prefix`` and renders
    ``maintenance.html`` (HTTP 503), so a single page/section can be locked
    while the rest of the site keeps working.
    """

    DEFAULT_HEADLINE = "This section is temporarily unavailable"
    DEFAULT_MESSAGE = (
        "We are performing scheduled maintenance on this part of Vasto. "
        "No data has been affected. Thank you for your patience."
    )

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Admin label, e.g. Messaging. Shown as the affected area.",
    )
    path_prefix = models.CharField(
        max_length=255,
        unique=True,
        help_text="Requests starting with this path show the maintenance page, e.g. /messaging/",
    )
    is_active = models.BooleanField(default=False, db_index=True)
    headline = models.CharField(max_length=255, default=DEFAULT_HEADLINE)
    message = models.TextField(default=DEFAULT_MESSAGE)
    eta = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional estimated return time shown to users.",
    )
    show_eta = models.BooleanField(
        default=True,
        help_text="Display the ETA on the maintenance page (hidden when no ETA is set).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        state = "ACTIVE" if self.is_active else "off"
        return f"{self.name} ({self.path_prefix}) [{state}]"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._bust_lock_cache()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self._bust_lock_cache()

    @staticmethod
    def _bust_lock_cache():
        from django.core.cache import cache
        cache.delete("maintenance:active_locks")
