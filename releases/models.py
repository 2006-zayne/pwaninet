from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator
from django.utils import timezone


class Release(models.Model):
    """
    Release model for managing PWANINET versions and releases.
    Supports future expansion for release channels, staged rollouts, etc.
    """
    
    RELEASE_TYPE_CHOICES = [
        ('MAJOR', 'Major'),
        ('MINOR', 'Minor'),
        ('PATCH', 'Patch'),
        ('HOTFIX', 'Hotfix'),
    ]
    
    # Release identification
    version = models.CharField(
        max_length=50,
        unique=True,
        help_text="Semantic version (e.g., 1.0.0)"
    )
    build_number = models.PositiveIntegerField(
        unique=True,
        help_text="Incremental build number for ordering"
    )
    
    # Release metadata
    release_title = models.CharField(
        max_length=200,
        help_text="User-friendly title for this release"
    )
    release_summary = models.TextField(
        help_text="Brief summary of this release"
    )
    release_type = models.CharField(
        max_length=20,
        choices=RELEASE_TYPE_CHOICES,
        default='MINOR',
        help_text="Type of release"
    )
    
    # Release flags and constraints
    mandatory_update = models.BooleanField(
        default=False,
        help_text="If True, users must update to continue using the app"
    )
    published = models.BooleanField(
        default=False,
        help_text="If True, release is visible to users"
    )
    minimum_supported_version = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Minimum version required for this update"
    )
    
    # Release channel (for future expansion)
    release_channel = models.CharField(
        max_length=20,
        default='STABLE',
        choices=[
            ('STABLE', 'Stable'),
            ('BETA', 'Beta'),
            ('ALPHA', 'Alpha'),
            ('NIGHTLY', 'Nightly'),
            ('CANARY', 'Canary'),
        ],
        help_text="Release channel for future staged rollouts"
    )
    
    # Timestamps
    release_date = models.DateTimeField(
        default=timezone.now,
        help_text="When this release was published"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Author tracking
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_releases',
        help_text="Admin who created this release"
    )
    
    class Meta:
        ordering = ['-build_number', '-release_date']
        verbose_name = 'Release'
        verbose_name_plural = 'Releases'
        indexes = [
            models.Index(fields=['version']),
            models.Index(fields=['build_number']),
            models.Index(fields=['published']),
            models.Index(fields=['release_channel']),
        ]
    
    def __str__(self):
        return f"{self.version} - {self.release_title}"
    
    def is_latest(self):
        """Check if this is the latest published release"""
        latest = Release.objects.filter(published=True).order_by('-build_number').first()
        return latest == self if latest else False


class ReleaseItem(models.Model):
    """
    Individual items within a release (features, bug fixes, etc.).
    Each release can contain multiple items.
    """
    
    CATEGORY_CHOICES = [
        ('FEATURE', 'Feature'),
        ('IMPROVEMENT', 'Improvement'),
        ('BUG_FIX', 'Bug Fix'),
        ('SECURITY', 'Security'),
        ('KNOWN_ISSUE', 'Known Issue'),
        ('DEPRECATION', 'Deprecation'),
    ]
    
    release = models.ForeignKey(
        Release,
        on_delete=models.CASCADE,
        related_name='items',
        help_text="The release this item belongs to"
    )
    
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        help_text="Category of this release item"
    )
    
    title = models.CharField(
        max_length=200,
        help_text="Title of this item"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Detailed description of this item"
    )
    
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Order for displaying items within a release"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['display_order', 'category', 'id']
        verbose_name = 'Release Item'
        verbose_name_plural = 'Release Items'
        indexes = [
            models.Index(fields=['release', 'category']),
            models.Index(fields=['display_order']),
        ]
    
    def __str__(self):
        return f"{self.release.version} - {self.category}: {self.title}"


class UserReleaseView(models.Model):
    """
    Track which releases each user has viewed.
    Used for the "What's New" experience to avoid showing the same release twice.
    """
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='viewed_releases',
        help_text="User who viewed this release"
    )
    
    release = models.ForeignKey(
        Release,
        on_delete=models.CASCADE,
        related_name='viewed_by',
        help_text="Release that was viewed"
    )
    
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    # For anonymous users (stored in localStorage, but this model is for authenticated users)
    session_key = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Session key for anonymous users (optional)"
    )
    
    class Meta:
        ordering = ['-viewed_at']
        verbose_name = 'User Release View'
        verbose_name_plural = 'User Release Views'
        unique_together = [['user', 'release']]
        indexes = [
            models.Index(fields=['user', 'viewed_at']),
            models.Index(fields=['release']),
        ]
    
    def __str__(self):
        return f"{self.user.username} viewed {self.release.version}"
