"""Engagement domain models.

These models track user interactions with documents, keeping analytics
separate from the document models to maintain separation of concerns.
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class DocumentView(models.Model):
    """Track document views for analytics."""
    
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name='views',
        help_text="The document that was viewed"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='document_views',
        help_text="User who viewed the document (null for anonymous)"
    )
    session_key = models.CharField(
        max_length=100,
        blank=True,
        help_text="Session key for anonymous views"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        help_text="IP address of the viewer"
    )
    user_agent = models.TextField(
        blank=True,
        help_text="User agent string"
    )
    referrer = models.URLField(
        blank=True,
        help_text="Referrer URL"
    )
    viewed_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When the document was viewed"
    )
    duration_seconds = models.PositiveIntegerField(
        null=True,
        help_text="Duration of view in seconds"
    )
    
    class Meta:
        ordering = ['-viewed_at']
        verbose_name = "Document View"
        verbose_name_plural = "Document Views"
        indexes = [
            models.Index(fields=['document', '-viewed_at']),
            models.Index(fields=['user', '-viewed_at']),
            models.Index(fields=['session_key', '-viewed_at']),
            models.Index(fields=['-viewed_at']),
        ]
    
    def __str__(self):
        user_str = self.user.username if self.user else 'Anonymous'
        return f"{self.document.title} viewed by {user_str}"


class DocumentDownload(models.Model):
    """Track document downloads for analytics."""
    
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name='downloads',
        help_text="The document that was downloaded"
    )
    document_file = models.ForeignKey(
        'documents.DocumentFile',
        on_delete=models.CASCADE,
        related_name='downloads',
        help_text="The specific file that was downloaded"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='document_downloads',
        help_text="User who downloaded the document"
    )
    session_key = models.CharField(
        max_length=100,
        blank=True,
        help_text="Session key for anonymous downloads"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        help_text="IP address of the downloader"
    )
    user_agent = models.TextField(
        blank=True,
        help_text="User agent string"
    )
    downloaded_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When the document was downloaded"
    )
    
    class Meta:
        ordering = ['-downloaded_at']
        verbose_name = "Document Download"
        verbose_name_plural = "Document Downloads"
        indexes = [
            models.Index(fields=['document', '-downloaded_at']),
            models.Index(fields=['user', '-downloaded_at']),
            models.Index(fields=['document_file', '-downloaded_at']),
            models.Index(fields=['-downloaded_at']),
        ]
    
    def __str__(self):
        user_str = self.user.username if self.user else 'Anonymous'
        return f"{self.document.title} downloaded by {user_str}"


class DocumentBookmark(models.Model):
    """Track user bookmarks for documents."""
    
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name='bookmarks',
        help_text="The bookmarked document"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='document_bookmarks',
        help_text="User who bookmarked the document"
    )
    notes = models.TextField(
        blank=True,
        help_text="User's notes about this bookmark"
    )
    is_favorite = models.BooleanField(
        default=False,
        help_text="Whether this is marked as a favorite"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['document', 'user']
        ordering = ['-created_at']
        verbose_name = "Document Bookmark"
        verbose_name_plural = "Document Bookmarks"
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['document']),
            models.Index(fields=['is_favorite']),
        ]
    
    def __str__(self):
        return f"{self.user.username} bookmarked {self.document.title}"


class DocumentRating(models.Model):
    """Track user ratings for documents using thumbs up/down system."""
    
    RATING_CHOICES = [
        (1, 'Thumbs Up'),
        (-1, 'Thumbs Down'),
    ]
    
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name='ratings',
        help_text="The rated document"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='document_ratings',
        help_text="User who rated the document"
    )
    rating = models.SmallIntegerField(
        choices=RATING_CHOICES,
        help_text="Rating: 1 for thumbs up, -1 for thumbs down"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['document', 'user']
        ordering = ['-created_at']
        verbose_name = "Document Rating"
        verbose_name_plural = "Document Ratings"
        indexes = [
            models.Index(fields=['document']),
            models.Index(fields=['user']),
            models.Index(fields=['rating']),
        ]
    
    def __str__(self):
        rating_text = "👍" if self.rating == 1 else "👎"
        return f"{self.user.username} {rating_text} {self.document.title}"


class DocumentShare(models.Model):
    """Track document shares for analytics."""
    
    SHARE_PLATFORM_CHOICES = [
        ('email', 'Email'),
        ('whatsapp', 'WhatsApp'),
        ('telegram', 'Telegram'),
        ('twitter', 'Twitter'),
        ('facebook', 'Facebook'),
        ('linkedin', 'LinkedIn'),
        ('copy_link', 'Copy Link'),
        ('profile', 'Profile'),
        ('group', 'Group'),
        ('other', 'Other'),
    ]
    
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name='shares',
        help_text="The shared document"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='document_shares',
        help_text="User who shared the document"
    )
    platform = models.CharField(
        max_length=20,
        choices=SHARE_PLATFORM_CHOICES,
        help_text="Platform where the document was shared"
    )
    shared_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When the document was shared"
    )
    
    class Meta:
        ordering = ['-shared_at']
        verbose_name = "Document Share"
        verbose_name_plural = "Document Shares"
        indexes = [
            models.Index(fields=['document', '-shared_at']),
            models.Index(fields=['user', '-shared_at']),
            models.Index(fields=['platform', '-shared_at']),
            models.Index(fields=['-shared_at']),
        ]
    
    def __str__(self):
        user_str = self.user.username if self.user else 'Anonymous'
        return f"{self.document.title} shared to {self.get_platform_display()} by {user_str}"


class DocumentAnalytics(models.Model):
    """Cached engagement analytics for documents.
    
    This model stores pre-computed engagement statistics to avoid
    expensive COUNT queries during page rendering. Analytics are
    updated asynchronously via Celery tasks.
    """
    
    document = models.OneToOneField(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name='analytics',
        help_text="The document this analytics belongs to"
    )
    
    # Engagement counts
    view_count = models.PositiveIntegerField(
        default=0,
        help_text="Total number of views"
    )
    download_count = models.PositiveIntegerField(
        default=0,
        help_text="Total number of downloads"
    )
    bookmark_count = models.PositiveIntegerField(
        default=0,
        help_text="Total number of bookmarks"
    )
    share_count = models.PositiveIntegerField(
        default=0,
        help_text="Total number of shares"
    )
    
    # Rating statistics
    rating_count = models.PositiveIntegerField(
        default=0,
        help_text="Total number of ratings"
    )
    positive_rating_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of thumbs up ratings"
    )
    negative_rating_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of thumbs down ratings"
    )
    positive_rating_percentage = models.PositiveIntegerField(
        default=0,
        help_text="Percentage of positive ratings (0-100)"
    )
    negative_rating_percentage = models.PositiveIntegerField(
        default=0,
        help_text="Percentage of negative ratings (0-100)"
    )
    
    # Trending score (computed from recent engagement)
    trending_score = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Trending score for ranking"
    )
    
    # Popularity score (computed from long-term engagement)
    popularity_score = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Popularity score for ranking"
    )
    
    # Metadata
    last_updated = models.DateTimeField(
        auto_now=True,
        help_text="When analytics were last recalculated"
    )
    last_activity = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the most recent engagement"
    )
    
    class Meta:
        verbose_name = "Document Analytics"
        verbose_name_plural = "Document Analytics"
        indexes = [
            models.Index(fields=['-trending_score']),
            models.Index(fields=['-popularity_score']),
            models.Index(fields=['-last_updated']),
        ]
    
    def __str__(self):
        return f"Analytics for {self.document.title}"
    
    def update_rating_percentages(self):
        """Recalculate rating percentages based on counts."""
        if self.rating_count > 0:
            self.positive_rating_percentage = int(
                (self.positive_rating_count / self.rating_count) * 100
            )
            self.negative_rating_percentage = int(
                (self.negative_rating_count / self.rating_count) * 100
            )
        else:
            self.positive_rating_percentage = 0
            self.negative_rating_percentage = 0


class DocumentReport(models.Model):
    """Track user reports for content moderation."""
    
    REPORT_REASON_CHOICES = [
        ('inappropriate', 'Inappropriate Content'),
        ('copyright', 'Copyright Violation'),
        ('spam', 'Spam'),
        ('duplicate', 'Duplicate'),
        ('incorrect', 'Incorrect Information'),
        ('malware', 'Malware/Virus'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('reviewing', 'Reviewing'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ]
    
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name='reports',
        help_text="The reported document"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='document_reports',
        help_text="User who reported the document"
    )
    reason = models.CharField(
        max_length=20,
        choices=REPORT_REASON_CHOICES,
        help_text="Reason for the report"
    )
    description = models.TextField(
        help_text="Detailed description of the report"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Report status"
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_reports',
        help_text="Moderator who reviewed the report"
    )
    review_notes = models.TextField(
        blank=True,
        help_text="Moderator's review notes"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the report was reviewed"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Document Report"
        verbose_name_plural = "Document Reports"
        indexes = [
            models.Index(fields=['document', '-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"Report on {self.document.title} ({self.get_reason_display()})"
