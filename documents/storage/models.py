"""Storage abstraction layer.

This provides a storage-agnostic interface for file operations,
allowing migration between different storage backends without changing business logic.
"""

from django.db import models
from django.conf import settings
import hashlib


class StorageBackend(models.Model):
    """Represents a storage backend configuration.
    
    This model allows multiple storage backends to be configured and used
    simultaneously, supporting gradual migration between providers.
    """
    
    BACKEND_TYPE_CHOICES = [
        ('local', 'Local Storage'),
        ('s3', 'Amazon S3'),
        ('r2', 'Cloudflare R2'),
        ('b2', 'Backblaze B2'),
        ('azure', 'Azure Blob Storage'),
        ('minio', 'MinIO'),
    ]
    
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Human-readable name for this storage backend"
    )
    backend_type = models.CharField(
        max_length=20,
        choices=BACKEND_TYPE_CHOICES,
        help_text="Type of storage backend"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this backend is currently active"
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Whether this is the default backend for new uploads"
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Backend-specific configuration (credentials, buckets, etc.)"
    )
    priority = models.PositiveIntegerField(
        default=100,
        help_text="Priority for backend selection (lower = higher priority)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['priority', 'name']
        verbose_name = "Storage Backend"
        verbose_name_plural = "Storage Backends"
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['is_default']),
            models.Index(fields=['priority']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_backend_type_display()})"
    
    def save(self, *args, **kwargs):
        # Ensure only one default backend
        if self.is_default:
            StorageBackend.objects.filter(is_default=True).update(is_default=False)
        super().save(*args, **kwargs)


class FileChecksum(models.Model):
    """Track file checksums for duplicate detection.
    
    This model stores checksums of all uploaded files to enable
    efficient duplicate detection across the repository.
    """
    
    HASH_ALGORITHM_CHOICES = [
        ('sha256', 'SHA-256'),
        ('sha512', 'SHA-512'),
        ('md5', 'MD5'),
    ]
    
    checksum = models.CharField(
        max_length=128,
        unique=True,
        help_text="File checksum value"
    )
    algorithm = models.CharField(
        max_length=10,
        choices=HASH_ALGORITHM_CHOICES,
        default='sha256',
        help_text="Hash algorithm used"
    )
    file_count = models.PositiveIntegerField(
        default=1,
        help_text="Number of files with this checksum"
    )
    first_seen_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this checksum was first seen"
    )
    last_seen_at = models.DateTimeField(
        auto_now=True,
        help_text="When this checksum was last seen"
    )
    
    class Meta:
        ordering = ['-last_seen_at']
        verbose_name = "File Checksum"
        verbose_name_plural = "File Checksums"
        indexes = [
            models.Index(fields=['checksum']),
            models.Index(fields=['algorithm']),
            models.Index(fields=['-last_seen_at']),
        ]
    
    def __str__(self):
        return f"{self.checksum[:16]}... ({self.file_count} files)"
    
    @classmethod
    def compute_checksum(cls, file_obj, algorithm='sha256'):
        """Compute checksum for a file object."""
        hash_func = getattr(hashlib, algorithm)()
        for chunk in iter(lambda: file_obj.read(8192), b''):
            hash_func.update(chunk)
        file_obj.seek(0)
        return hash_func.hexdigest()
    
    def increment_count(self):
        """Increment the file count for this checksum."""
        self.file_count += 1
        self.save(update_fields=['file_count', 'last_seen_at'])
    
    def decrement_count(self):
        """Decrement the file count for this checksum."""
        self.file_count = max(0, self.file_count - 1)
        self.save(update_fields=['file_count', 'last_seen_at'])
        if self.file_count == 0:
            self.delete()


class StorageMigration(models.Model):
    """Track storage migrations between backends.
    
    This model records migration history for auditing and rollback purposes.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('rolled_back', 'Rolled Back'),
    ]
    
    source_backend = models.ForeignKey(
        StorageBackend,
        on_delete=models.PROTECT,
        related_name='migrations_from',
        help_text="Source storage backend"
    )
    target_backend = models.ForeignKey(
        StorageBackend,
        on_delete=models.PROTECT,
        related_name='migrations_to',
        help_text="Target storage backend"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Migration status"
    )
    files_migrated = models.PositiveIntegerField(
        default=0,
        help_text="Number of files successfully migrated"
    )
    files_failed = models.PositiveIntegerField(
        default=0,
        help_text="Number of files that failed to migrate"
    )
    total_files = models.PositiveIntegerField(
        help_text="Total number of files to migrate"
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When migration started"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When migration completed"
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error message if migration failed"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='storage_migrations',
        help_text="User who initiated the migration"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Storage Migration"
        verbose_name_plural = "Storage Migrations"
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.source_backend.name} → {self.target_backend.name} ({self.get_status_display()})"
