from django.db import models
from django.conf import settings
import uuid

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
