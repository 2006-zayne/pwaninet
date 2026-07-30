"""Collections domain models.

These models support document collections, allowing users to organize
documents into custom groups without coupling to the document model.
"""

from django.db import models
from django.conf import settings
from django.utils.text import slugify


class Collection(models.Model):
    """Represents a user-created collection of documents."""
    
    VISIBILITY_CHOICES = [
        ('private', 'Private'),
        ('public', 'Public'),
        ('unlisted', 'Unlisted'),
    ]
    
    name = models.CharField(
        max_length=200,
        help_text="Collection name"
    )
    slug = models.SlugField(
        max_length=250,
        unique=True,
        help_text="URL-friendly slug"
    )
    description = models.TextField(
        blank=True,
        help_text="Collection description"
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='collections',
        help_text="User who owns this collection"
    )
    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default='private',
        help_text="Collection visibility"
    )
    cover_image = models.ImageField(
        upload_to='collection_covers/',
        blank=True,
        help_text="Cover image for the collection"
    )
    is_featured = models.BooleanField(
        default=False,
        help_text="Whether this collection is featured"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Collection"
        verbose_name_plural = "Collections"
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['owner']),
            models.Index(fields=['visibility']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.owner.username}-{self.name}")
        super().save(*args, **kwargs)
    
    @property
    def document_count(self):
        """Get the number of documents in this collection."""
        return self.items.count()


class CollectionItem(models.Model):
    """Represents a document within a collection."""
    
    collection = models.ForeignKey(
        Collection,
        on_delete=models.CASCADE,
        related_name='items',
        help_text="The collection this item belongs to"
    )
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name='collection_items',
        help_text="The document in this collection"
    )
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='added_collection_items',
        help_text="User who added this document to the collection"
    )
    notes = models.TextField(
        blank=True,
        help_text="Notes about this document in the collection"
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order within the collection"
    )
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['collection', 'document']
        ordering = ['collection', 'order', 'added_at']
        verbose_name = "Collection Item"
        verbose_name_plural = "Collection Items"
        indexes = [
            models.Index(fields=['collection', 'order']),
            models.Index(fields=['document']),
        ]
    
    def __str__(self):
        return f"{self.collection.name} - {self.document.title}"


class CollectionShare(models.Model):
    """Track collection sharing with other users."""
    
    collection = models.ForeignKey(
        Collection,
        on_delete=models.CASCADE,
        related_name='shares',
        help_text="The shared collection"
    )
    shared_with = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='shared_collections',
        help_text="User the collection is shared with"
    )
    shared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='shared_by_collections',
        help_text="User who shared the collection"
    )
    can_edit = models.BooleanField(
        default=False,
        help_text="Whether the recipient can edit the collection"
    )
    shared_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['collection', 'shared_with']
        ordering = ['-shared_at']
        verbose_name = "Collection Share"
        verbose_name_plural = "Collection Shares"
        indexes = [
            models.Index(fields=['collection']),
            models.Index(fields=['shared_with']),
        ]
    
    def __str__(self):
        return f"{self.collection.name} shared with {self.shared_with.username}"
