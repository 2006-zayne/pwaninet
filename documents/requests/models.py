"""Request domain models.

These models support a document request system where users can request
specific documents, and others can fulfill those requests.
"""

from django.db import models
from django.conf import settings
from django.utils.text import slugify


class DocumentRequest(models.Model):
    """Represents a user request for a specific document."""
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('fulfilled', 'Fulfilled'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
    ]
    
    title = models.CharField(
        max_length=500,
        help_text="Title of the requested document"
    )
    slug = models.SlugField(
        max_length=550,
        unique=True,
        help_text="URL-friendly slug"
    )
    description = models.TextField(
        help_text="Detailed description of what is being requested"
    )
    
    # Academic context
    academic_unit = models.ForeignKey(
        'documents.AcademicUnit',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='document_requests',
        help_text="The academic unit this request is for"
    )
    category = models.ForeignKey(
        'documents.Category',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='document_requests',
        help_text="The category of the requested document"
    )
    semester = models.ForeignKey(
        'documents.Semester',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='document_requests',
        help_text="The semester this request is for"
    )
    
    # Request metadata
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='document_requests',
        help_text="User who made the request"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='open',
        help_text="Request status"
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='normal',
        help_text="Request priority"
    )
    
    # Fulfillment
    fulfilled_document = models.ForeignKey(
        'documents.Document',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fulfilled_requests',
        help_text="The document that fulfilled this request"
    )
    fulfilled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fulfilled_document_requests',
        help_text="User who fulfilled the request"
    )
    fulfilled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the request was fulfilled"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this request expires"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Document Request"
        verbose_name_plural = "Document Requests"
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['requested_by']),
            models.Index(fields=['academic_unit']),
            models.Index(fields=['category']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.requested_by.username}-{self.title}")
        super().save(*args, **kwargs)
    
    @property
    def vote_count(self):
        """Get the total number of votes for this request."""
        return self.votes.count()
    
    def fulfill(self, document, user):
        """Mark this request as fulfilled."""
        self.status = 'fulfilled'
        self.fulfilled_document = document
        self.fulfilled_by = user
        self.fulfilled_at = models.timezone.now()
        self.save()


class DocumentRequestVote(models.Model):
    """Track votes for document requests."""
    
    document_request = models.ForeignKey(
        DocumentRequest,
        on_delete=models.CASCADE,
        related_name='votes',
        help_text="The request being voted on"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='request_votes',
        help_text="User who voted"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['document_request', 'user']
        ordering = ['-created_at']
        verbose_name = "Document Request Vote"
        verbose_name_plural = "Document Request Votes"
        indexes = [
            models.Index(fields=['document_request']),
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"{self.user.username} voted for {self.document_request.title}"
