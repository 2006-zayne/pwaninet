"""Moderation domain models.

These models handle content moderation with extensible status workflows,
avoiding boolean fields to support future moderation workflows.
"""

from django.db import models
from django.conf import settings


class ModerationStatus(models.Model):
    """Extensible moderation status for documents.
    
    This model replaces boolean fields with a proper status system
    that can support complex moderation workflows.
    """
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('verified', 'Verified'),
        ('flagged', 'Flagged'),
        ('duplicate', 'Duplicate'),
        ('archived', 'Archived'),
        ('removed', 'Removed'),
    ]
    
    code = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        unique=True,
        help_text="Unique status code"
    )
    name = models.CharField(
        max_length=50,
        help_text="Human-readable status name"
    )
    description = models.TextField(
        help_text="Description of when this status applies"
    )
    is_public = models.BooleanField(
        default=True,
        help_text="Whether documents with this status are visible to public"
    )
    is_searchable = models.BooleanField(
        default=True,
        help_text="Whether documents with this status appear in search"
    )
    is_downloadable = models.BooleanField(
        default=True,
        help_text="Whether documents with this status can be downloaded"
    )
    requires_action = models.BooleanField(
        default=False,
        help_text="Whether this status requires moderator action"
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'code']
        verbose_name = "Moderation Status"
        verbose_name_plural = "Moderation Statuses"
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['is_public']),
            models.Index(fields=['is_searchable']),
        ]
    
    def __str__(self):
        return self.name


class DocumentModeration(models.Model):
    """Track moderation status for individual documents."""
    
    document = models.OneToOneField(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name='moderation',
        help_text="The document being moderated"
    )
    status = models.ForeignKey(
        ModerationStatus,
        on_delete=models.PROTECT,
        related_name='documents',
        help_text="Current moderation status"
    )
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moderated_documents',
        help_text="Moderator who last changed the status"
    )
    moderation_notes = models.TextField(
        blank=True,
        help_text="Notes about moderation decisions"
    )
    status_changed_at = models.DateTimeField(
        auto_now=True,
        help_text="When the status last changed"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Document Moderation"
        verbose_name_plural = "Document Moderations"
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['status_changed_at']),
        ]
    
    def __str__(self):
        return f"{self.document.title} - {self.status.name}"
    
    def approve(self, user, notes=''):
        """Approve the document."""
        approved_status = ModerationStatus.objects.get(code='approved')
        self.status = approved_status
        self.moderated_by = user
        self.moderation_notes = notes
        self.save()
    
    def verify(self, user, notes=''):
        """Verify the document."""
        verified_status = ModerationStatus.objects.get(code='verified')
        self.status = verified_status
        self.moderated_by = user
        self.moderation_notes = notes
        self.save()
    
    def flag(self, user, notes=''):
        """Flag the document."""
        flagged_status = ModerationStatus.objects.get(code='flagged')
        self.status = flagged_status
        self.moderated_by = user
        self.moderation_notes = notes
        self.save()
    
    def remove(self, user, notes=''):
        """Remove the document."""
        removed_status = ModerationStatus.objects.get(code='removed')
        self.status = removed_status
        self.moderated_by = user
        self.moderation_notes = notes
        self.save()


class ModerationQueue(models.Model):
    """Queue for documents awaiting moderation."""
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    document = models.OneToOneField(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name='queue_entry',
        help_text="The document awaiting moderation"
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='normal',
        help_text="Moderation priority"
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='queued_documents',
        help_text="User who submitted the document"
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_moderations',
        help_text="Moderator assigned to this document"
    )
    assigned_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the document was assigned"
    )
    estimated_review_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Estimated time for review completion"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['priority', 'created_at']
        verbose_name = "Moderation Queue"
        verbose_name_plural = "Moderation Queue"
        indexes = [
            models.Index(fields=['priority', 'created_at']),
            models.Index(fields=['assigned_to']),
            models.Index(fields=['assigned_at']),
        ]
    
    def __str__(self):
        return f"{self.document.title} ({self.get_priority_display()})"
    
    def assign(self, moderator):
        """Assign this document to a moderator."""
        self.assigned_to = moderator
        self.assigned_at = models.timezone.now()
        self.save()
    
    def unassign(self):
        """Unassign this document."""
        self.assigned_to = None
        self.assigned_at = None
        self.save()
