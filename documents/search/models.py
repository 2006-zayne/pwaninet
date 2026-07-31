"""Search index models.

This provides an indexing layer for search functionality, allowing
migration between different search backends without changing document models.
"""

from django.db import models
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex, GistIndex


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
    
    # Individual weighted search vectors for different field priorities
    # Title: Highest weight (A)
    title_vector = SearchVectorField(
        null=True,
        help_text="Weighted search vector for title (highest priority)"
    )
    # Tags: High weight (B)
    tags_vector = SearchVectorField(
        null=True,
        help_text="Weighted search vector for tags (high priority)"
    )
    # Academic units: High weight (B)
    academic_units_vector = SearchVectorField(
        null=True,
        help_text="Weighted search vector for academic units (high priority)"
    )
    # Category: Medium weight (C)
    category_vector = SearchVectorField(
        null=True,
        help_text="Weighted search vector for category (medium priority)"
    )
    # Description: Medium weight (C)
    description_vector = SearchVectorField(
        null=True,
        help_text="Weighted search vector for description (medium priority)"
    )
    # Authors: Medium weight (C)
    authors_vector = SearchVectorField(
        null=True,
        help_text="Weighted search vector for authors (medium priority)"
    )
    # OCR text: Lower weight (D)
    ocr_text_vector = SearchVectorField(
        null=True,
        help_text="Weighted search vector for OCR text (lower priority)"
    )
    # Filename: Lowest weight (D)
    filename_vector = SearchVectorField(
        null=True,
        help_text="Weighted search vector for filename (lowest priority)"
    )
    
    # Combined searchable text for autocomplete (trigram search)
    searchable_text = models.TextField(
        blank=True,
        help_text="Combined text for trigram similarity search"
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
    primary_filename = models.CharField(
        max_length=500,
        blank=True,
        help_text="Primary filename for search"
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
    
    # Trending score (computed for recent activity)
    trending_score = models.FloatField(
        default=0.0,
        db_index=True,
        help_text="Computed trending score for recent activity"
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
            GinIndex(fields=['title_vector']),
            GinIndex(fields=['tags_vector']),
            GinIndex(fields=['academic_units_vector']),
            GinIndex(fields=['category_vector']),
            GinIndex(fields=['description_vector']),
            GinIndex(fields=['authors_vector']),
            GinIndex(fields=['ocr_text_vector']),
            GinIndex(fields=['filename_vector']),
            # Trigram GIN index for fuzzy search on searchable_text
            GinIndex(
                fields=['searchable_text'],
                opclasses=['gin_trgm_ops'],
                name='doc_search_text_trgm_idx'
            ),
            models.Index(fields=['title']),
            models.Index(fields=['category_code']),
            models.Index(fields=['semester_code']),
            models.Index(fields=['academic_year_code']),
            models.Index(fields=['view_count']),
            models.Index(fields=['download_count']),
            models.Index(fields=['bookmark_count']),
            models.Index(fields=['popularity_score']),
            models.Index(fields=['trending_score']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['-updated_at']),
            models.Index(fields=['-published_at']),
        ]
    
    def __str__(self):
        return f"Search index for {self.title}"
    
    def update_popularity_score(self):
        """Compute and update the popularity score (long-term popularity)."""
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
            from django.utils import timezone
            days_since_publish = (timezone.now() - self.published_at).days
            time_factor = max(0.1, 1 - (days_since_publish / 365))  # Decay over a year
            score *= time_factor
        
        self.popularity_score = score
        self.save(update_fields=['popularity_score'])
    
    def update_trending_score(self):
        """Compute and update the trending score (recent activity)."""
        from django.utils import timezone
        from datetime import timedelta
        
        # Calculate recent engagement (last 7 days)
        cutoff_date = timezone.now() - timedelta(days=7)
        
        # This would be calculated from engagement models
        # For now, use a simpler formula based on total metrics with recency boost
        recent_factor = 1.0
        
        if self.published_at:
            days_since_publish = (timezone.now() - self.published_at).days
            if days_since_publish < 7:
                recent_factor = 2.0  # Boost for very recent
            elif days_since_publish < 30:
                recent_factor = 1.5  # Moderate boost
        
        # Trending formula: recent engagement weighted
        score = (
            self.download_count * 2 +
            self.view_count * 0.5 +
            self.bookmark_count * 1.5 +
            self.share_count * 1.5
        ) * recent_factor
        
        self.trending_score = score
        self.save(update_fields=['trending_score'])
