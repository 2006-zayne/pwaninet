"""Search index models.

This provides an indexing layer for search functionality, allowing
migration between different search backends without changing document models.
"""

from django.db import models
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex


class DocumentSearchIndex(models.Model):
    """Search index for documents using PostgreSQL Full Text Search.
    
    This model stores denormalized search data to enable efficient queries
    without hitting the main document models. It can be replaced with
    Meilisearch or ElasticSearch in the future.
    """
    
    document = models.OneToOneField(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name='search_index',
        help_text="The document being indexed"
    )
    
    # Searchable text fields (combined for full-text search)
    search_vector = SearchVectorField(
        null=True,
        help_text="PostgreSQL search vector for full-text search"
    )
    
    # Denormalized fields for filtering and sorting
    title = models.CharField(
        max_length=500,
        db_index=True,
        help_text="Document title"
    )
    description = models.TextField(
        blank=True,
        help_text="Document description"
    )
    category_code = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Category code for filtering"
    )
    category_name = models.CharField(
        max_length=100,
        help_text="Category name for display"
    )
    
    # Academic context
    academic_unit_codes = models.JSONField(
        default=list,
        blank=True,
        help_text="List of academic unit codes"
    )
    academic_unit_names = models.JSONField(
        default=list,
        blank=True,
        help_text="List of academic unit names"
    )
    semester_code = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
        help_text="Semester code"
    )
    academic_year_code = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        db_index=True,
        help_text="Academic year code"
    )
    
    # Tags
    tag_names = models.JSONField(
        default=list,
        blank=True,
        help_text="List of tag names"
    )
    tag_slugs = models.JSONField(
        default=list,
        blank=True,
        help_text="List of tag slugs"
    )
    
    # Authors
    author_names = models.JSONField(
        default=list,
        blank=True,
        help_text="List of author names"
    )
    author_usernames = models.JSONField(
        default=list,
        blank=True,
        help_text="List of author usernames"
    )
    
    # File metadata
    file_types = models.JSONField(
        default=list,
        blank=True,
        help_text="List of file extensions"
    )
    file_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of files in the document"
    )
    
    # OCR text (future)
    ocr_text = models.TextField(
        blank=True,
        help_text="Extracted text from OCR (future feature)"
    )
    
    # Engagement metrics (for sorting)
    view_count = models.PositiveIntegerField(
        default=0,
        db_index=True,
        help_text="Total view count"
    )
    download_count = models.PositiveIntegerField(
        default=0,
        db_index=True,
        help_text="Total download count"
    )
    bookmark_count = models.PositiveIntegerField(
        default=0,
        db_index=True,
        help_text="Total bookmark count"
    )
    share_count = models.PositiveIntegerField(
        default=0,
        db_index=True,
        help_text="Total share count"
    )
    rating_average = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        db_index=True,
        help_text="Average rating"
    )
    rating_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of ratings"
    )
    
    # Popularity score (computed)
    popularity_score = models.FloatField(
        default=0.0,
        db_index=True,
        help_text="Computed popularity score for ranking"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        db_index=True,
        help_text="When the document was created"
    )
    updated_at = models.DateTimeField(
        db_index=True,
        help_text="When the document was last updated"
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="When the document was published"
    )
    indexed_at = models.DateTimeField(
        auto_now=True,
        help_text="When this index was last updated"
    )
    
    class Meta:
        verbose_name = "Document Search Index"
        verbose_name_plural = "Document Search Indices"
        indexes = [
            GinIndex(fields=['search_vector']),
            models.Index(fields=['title']),
            models.Index(fields=['category_code']),
            models.Index(fields=['semester_code']),
            models.Index(fields=['academic_year_code']),
            models.Index(fields=['view_count']),
            models.Index(fields=['download_count']),
            models.Index(fields=['bookmark_count']),
            models.Index(fields=['popularity_score']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['-updated_at']),
            models.Index(fields=['-published_at']),
        ]
    
    def __str__(self):
        return f"Search index for {self.title}"
    
    def update_popularity_score(self):
        """Compute and update the popularity score."""
        # Weighted formula: downloads*3 + views*1 + bookmarks*2 + shares*2 + rating*5
        score = (
            self.download_count * 3 +
            self.view_count * 1 +
            self.bookmark_count * 2 +
            self.share_count * 2 +
            (self.rating_average or 0) * 5
        )
        
        # Time decay factor (newer documents get a boost)
        if self.published_at:
            days_since_publish = (models.timezone.now() - self.published_at).days
            time_factor = max(0.1, 1 - (days_since_publish / 365))  # Decay over a year
            score *= time_factor
        
        self.popularity_score = score
        self.save(update_fields=['popularity_score'])
