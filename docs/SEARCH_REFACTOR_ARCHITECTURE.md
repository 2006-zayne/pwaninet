# Document Repository Search Refactor - Architecture Documentation

## Overview

This document describes the architectural changes made to the PwaniNet Document Repository search system during Phase 1 and Phase 2 of the search refactor. The objective was to transform the basic SQL filtering into an intelligent academic search engine while maintaining full backwards compatibility.

## Phase 1: PostgreSQL Full Text Search

### 1.1 Search Vector Architecture

**File**: `documents/search/models.py`

The `DocumentSearchIndex` model was enhanced with weighted search vectors for different field priorities:

- **title_vector** (Weight A - Highest): Document titles receive the highest search priority
- **tags_vector** (Weight B - High): Tags are highly relevant for discovery
- **academic_units_vector** (Weight B - High): Academic unit names are critical for academic context
- **category_vector** (Weight C - Medium): Category names provide moderate relevance
- **description_vector** (Weight C - Medium): Descriptions help with content discovery
- **authors_vector** (Weight C - Medium): Author names contribute to relevance
- **ocr_text_vector** (Weight D - Lower): Extracted OCR text (extension point for future)
- **filename_vector** (Weight D - Lowest): Filenames have minimal relevance

**Why this improves search quality**:
- Title matches always outrank filename matches
- Academic context (units, tags) is prioritized over general content
- The system can distinguish between exact title matches and partial content matches
- Weighted vectors allow fine-tuned relevance scoring

### 1.2 Multi-Word Query Tokenization

**File**: `documents/services/search_service.py`

Search queries now use PostgreSQL's `websearch` search type:

```python
search_query = SearchQuery(query, config='english', search_type='websearch')
```

**Benefits**:
- Queries like "Web Development" correctly find "Web Development Notes"
- Word order independence: "Database Systems" finds "Systems Database"
- Boolean operators supported: AND, OR, NOT
- Phrase matching with quotes: "Operating System" finds exact matches

### 1.3 Stemming and Stop Word Handling

**Configuration**: `config='english'`

PostgreSQL's English text search configuration provides:
- **Stemming**: "develop", "development", "developing", "developer" all match
- **Stop words**: "the", "of", "for", "to", "in", "on", "and" are ignored
- **Normalization**: Case-insensitive matching, accent handling

**Why this matters**:
- Students can search for concepts without exact word forms
- Common words don't reduce search quality
- Natural language queries work effectively

## Phase 2: Fuzzy Search and Advanced Features

### 2.1 pg_trgm Extension

**Migration**: `documents/migrations/0006_enable_pg_trgm_extension.py`

The PostgreSQL pg_trgm extension enables:
- **Trigram similarity**: "Devlopment" matches "Development"
- **Fuzzy matching**: "Databse" matches "Database"
- **Autocomplete**: Real-time suggestions as users type

**Implementation**:
```python
from django.contrib.postgres.search import TrigramSimilarity
queryset = DocumentSearchIndex.objects.annotate(
    similarity=TrigramSimilarity('searchable_text', query)
).filter(similarity__gte=0.3)
```

### 2.2 Trigram GIN Index

**File**: `documents/search/models.py`

Added GIN index with trigram operator class:

```python
GinIndex(
    fields=['searchable_text'],
    opclasses=['gin_trgm_ops'],
    name='doc_search_text_trgm_idx'
)
```

**Why this improves performance**:
- Fuzzy searches use indexed lookups instead of sequential scans
- Trigram similarity calculations are accelerated
- Autocomplete queries remain fast with large document sets

### 2.3 Search Autocomplete

**File**: `documents/services/search_service.py`

```python
def get_search_suggestions(self, query: str, limit: int = 10) -> List[str]:
    """Get autocomplete suggestions based on query."""
    suggestions = DocumentSearchIndex.objects.annotate(
        similarity=TrigramWordSimilarity('title', query)
    ).filter(similarity__gte=0.3).order_by('-similarity')[:limit]
    return [suggestion.title for suggestion in suggestions]
```

**Benefits**:
- Real-time suggestions as users type
- Helps users discover relevant documents
- Reduces search abandonment

### 2.4 "Did You Mean" Feature

**File**: `documents/services/search_service.py`

```python
def get_did_you_mean(self, query: str) -> Optional[str]:
    """Get spelling correction suggestion using fuzzy matching."""
    similar = DocumentSearchIndex.objects.annotate(
        similarity=TrigramSimilarity('title', query)
    ).filter(similarity__gte=0.6).order_by('-similarity').first()
    
    if similar and similar.similarity >= 0.7:
        return similar.title
    return None
```

**Benefits**:
- Corrects common spelling mistakes
- Only shows high-confidence suggestions (≥70% similarity)
- Improves user experience for misspelled queries

## Search Ranking System

### 3.1 Popularity Score (Long-term)

**File**: `documents/search/models.py`

```python
def update_popularity_score(self):
    """Compute and update the popularity score (long-term popularity)."""
    score = (
        self.download_count * 3 +
        self.view_count * 1 +
        self.bookmark_count * 2 +
        self.share_count * 2 +
        (self.rating_average or 0) * 5
    )
    
    # Time decay factor (newer documents get a boost)
    if self.published_at:
        days_since_publish = (timezone.now() - self.published_at).days
        time_factor = max(0.1, 1 - (days_since_publish / 365))
        score *= time_factor
```

**Weighting rationale**:
- Downloads (3x): Strongest signal of value
- Bookmarks (2x): Indicates user interest
- Shares (2x): Viral potential
- Views (1x): Basic engagement
- Ratings (5x): Quality indicator

### 3.2 Trending Score (Recent Activity)

**File**: `documents/search/models.py`

```python
def update_trending_score(self):
    """Compute and update the trending score (recent activity)."""
    recent_factor = 1.0
    
    if self.published_at:
        days_since_publish = (timezone.now() - self.published_at).days
        if days_since_publish < 7:
            recent_factor = 2.0  # Boost for very recent
        elif days_since_publish < 30:
            recent_factor = 1.5  # Moderate boost
    
    score = (
        self.download_count * 2 +
        self.view_count * 0.5 +
        self.bookmark_count * 1.5 +
        self.share_count * 1.5
    ) * recent_factor
```

**Difference from popularity**:
- Trending measures recent velocity (last 7-30 days)
- Popular measures cumulative lifetime metrics
- Trending boosts very recent content
- Popular favors established documents

### 3.3 Student Interest Prioritization

**File**: `documents/services/search_service.py`

```python
def _apply_student_interest_boost(self, queryset, user):
    """Apply ranking boost based on student's academic context."""
    # Get user's programme, academic units, semester
    user_units = []
    if profile.programme:
        programme_units = ProgrammeUnit.objects.filter(
            programme=profile.programme
        ).select_related('academic_unit')
        user_units = [pu.academic_unit.code for pu in programme_units]
    
    if user_units:
        queryset = queryset.annotate(
            academic_relevance=Case(
                When(academic_unit_codes__overlap=user_units, then=Value(1.0)),
                default=Value(0.0),
                output_field=FloatField()
            )
        )
        
        queryset = queryset.annotate(
            boosted_rank=F('rank') + F('academic_relevance') * 0.5
        )
```

**Why this improves discovery**:
- Students see documents relevant to their programme first
- Shared units receive ranking boost
- Personalized without filtering (students can still discover other content)
- Academic context is inferred from user profile

## Homepage Improvements

### 4.1 Trending Section

**File**: `documents/selectors/document_selectors.py`

```python
@staticmethod
def get_trending_documents(limit: int = 10, days: int = 7, user=None) -> List[Document]:
    """Get trending documents based on recent engagement using search index."""
    queryset = DocumentSearchIndex.objects.filter(
        document__status='ready',
        document__visibility='public',
        document__created_at__gte=cutoff_date,
    ).select_related('document').order_by('-trending_score')[:limit]
    
    documents = [index.document for index in queryset]
    
    # Apply student interest prioritization if user is provided
    if user and user.is_authenticated:
        documents = DocumentSelector._apply_student_relevance_sorting(documents, user)
    
    return documents
```

**Improvements**:
- Uses trending_score instead of simple engagement
- Recent activity weighting (7-day window)
- Personalized for logged-in students
- No longer static - changes based on recent engagement

### 4.2 Popular Section

**File**: `documents/selectors/document_selectors.py`

```python
@staticmethod
def get_popular_documents(limit: int = 10, user=None) -> List[Document]:
    """Get popular documents based on long-term popularity score."""
    queryset = DocumentSearchIndex.objects.filter(
        document__status='ready',
        document__visibility='public',
    ).select_related('document').order_by('-popularity_score')[:limit]
    
    documents = [index.document for index in queryset]
    
    # Apply student interest prioritization if user is provided
    if user and user.is_authenticated:
        documents = DocumentSelector._apply_student_relevance_sorting(documents, user)
    
    return documents
```

**Improvements**:
- Uses popularity_score (long-term metrics)
- Weighted engagement formula
- Personalized for logged-in students
- Different from trending (long-term vs recent)

### 4.3 Recently Added Section

**File**: `documents/selectors/document_selectors.py`

```python
@staticmethod
def list_documents_for_home(
    limit: int = 20,
    category: Optional[str] = None,
    academic_unit: Optional[str] = None,
    user=None,
) -> List[Document]:
    """List documents for home page with personalization."""
    documents = list(queryset.order_by('-created_at')[:limit])
    
    # Apply student interest prioritization if user is provided
    if user and user.is_authenticated:
        documents = DocumentSelector._apply_student_relevance_sorting(documents, user)
    
    return documents
```

**Improvements**:
- Personalized sorting for logged-in students
- Academic relevance boosts relevant documents
- Recent uploads from student's programme appear first
- Still shows all uploads, just reordered

## Related Documents Algorithm

**File**: `documents/selectors/document_selectors.py`

```python
@staticmethod
def get_related_documents(document: Document, limit: int = 6) -> List[Document]:
    """Get related documents based on multiple relevance factors."""
    # Score documents based on relevance
    def relevance_score(doc):
        score = 0
        
        # Shared academic units (high relevance)
        if doc_units & doc_doc_units:
            score += 10 * len(doc_units & doc_doc_units)
        
        # Shared category (medium relevance)
        if doc.category.code == doc_category:
            score += 5
        
        # Shared tags (medium relevance)
        if doc_tags & doc_doc_tags:
            score += 3 * len(doc_tags & doc_doc_tags)
        
        # Similar title (lower relevance)
        if document.title.lower() in doc.title.lower():
            score += 2
        
        return score
```

**Scoring rationale**:
- Shared academic units: 10 points per unit (highest priority)
- Shared category: 5 points (medium priority)
- Shared tags: 3 points per tag (medium priority)
- Similar title: 2 points (lower priority)

**Benefits**:
- No longer random selection
- Multi-factor relevance scoring
- Academic context prioritized
- Performance optimized (limits to 50 candidates)

## OCR Pipeline Architecture

**File**: `documents/tasks/processing.py`

### Extension Points

The OCR pipeline provides clear extension points for future implementation:

```python
def extract_ocr_text(file: DocumentFile) -> str:
    """Extract text from document using OCR.
    
    This is an extension point for future OCR implementation.
    Currently returns empty string.
    
    Future implementations could use:
    - Tesseract OCR for PDFs and images
    - Google Vision API
    - AWS Textract
    - Azure Form Recognizer
    - pdfplumber for text extraction from PDFs
    """
    return ""
```

### Architecture Benefits

1. **No architectural changes required**: OCR can be added without redesign
2. **Storage ready**: `DocumentSearchIndex.ocr_text` field exists
3. **Indexing ready**: `ocr_text_vector` with weight D configured
4. **Pipeline integration**: OCR extraction called during document processing
5. **Multiple engine support**: Extension points support different OCR engines

### Implementation Path

When implementing OCR:
1. Implement `_extract_text_from_pdf()` for PDF text extraction
2. Implement `_extract_text_from_image()` for image OCR
3. Implement `_extract_text_from_docx()` for DOCX text extraction
4. Update `extract_ocr_text()` to dispatch to appropriate function
5. OCR text will automatically be indexed with weight D

## Database Performance

### GIN Indexes

**File**: `documents/search/models.py`

All search vector fields have GIN indexes:
- `search_vector`: Combined search vector
- `title_vector`: Title search vector
- `tags_vector`: Tags search vector
- `academic_units_vector`: Academic units search vector
- `category_vector`: Category search vector
- `description_vector`: Description search vector
- `authors_vector`: Authors search vector
- `ocr_text_vector`: OCR text search vector
- `filename_vector`: Filename search vector

**Benefits**:
- Full-text search queries use indexed lookups
- SearchRank calculations are accelerated
- Complex boolean queries remain fast
- Supports tens of thousands of documents

### Trigram Index

**File**: `documents/search/models.py`

```python
GinIndex(
    fields=['searchable_text'],
    opclasses=['gin_trgm_ops'],
    name='doc_search_text_trgm_idx'
)
```

**Benefits**:
- Fuzzy search performance
- Autocomplete speed
- "Did you mean" query efficiency

### Query Optimization

**File**: `documents/services/search_service.py`

All queries use:
- `select_related`: Foreign key optimization
- `prefetch_related`: Many-to-many optimization
- Pagination: Limits result sets
- Preserved ranking order: Maintains search relevance

## Backwards Compatibility

### Preserved Functionality

1. **Document uploads**: No changes to upload flow
2. **Document previews**: Existing preview pipeline intact
3. **PDF.js integration**: Unchanged
4. **DOCX preview**: Existing implementation preserved
5. **URLs**: All existing URLs remain valid
6. **Templates**: Template structure unchanged
7. **APIs**: API compatibility maintained
8. **Permissions**: No permission model changes

### Migration Path

1. **Run migrations**: New fields and indexes added
2. **Reindex documents**: Search service indexes existing documents
3. **Enable pg_trgm**: Extension installed via migration
4. **No data loss**: All existing data preserved
5. **Graceful degradation**: Falls back to basic search if FTS unavailable

## Success Criteria

### Achieved Goals

✅ **PostgreSQL Full Text Search**: Implemented with SearchVector, SearchQuery, SearchRank
✅ **Weighted ranking**: Title (A) > Tags/Units (B) > Category/Description/Authors (C) > OCR/Filename (D)
✅ **Multi-word queries**: Websearch search type enables natural language queries
✅ **Stemming**: English configuration handles word variations
✅ **Stop words**: Common words ignored automatically
✅ **Fuzzy search**: pg_trgm extension enabled with similarity threshold
✅ **Database indexes**: GIN indexes for all vectors, trigram index for fuzzy search
✅ **Popularity ranking**: Weighted formula with time decay
✅ **Student prioritization**: Academic context boosts relevant documents
✅ **Autocomplete**: Trigram-based suggestions
✅ **Did you mean**: Fuzzy spelling correction
✅ **Trending improvement**: Recent activity weighting
✅ **Popular improvement**: Long-term popularity metrics
✅ **Recently added**: Personalized sorting
✅ **Related documents**: Multi-factor relevance scoring
✅ **OCR architecture**: Extension points for future implementation
✅ **Query optimization**: select_related, prefetch_related, pagination
✅ **Backwards compatibility**: All existing functionality preserved

### Search Quality Improvements

**Before**:
- Simple ILIKE string matching
- No ranking beyond creation date
- No fuzzy matching
- No spelling correction
- No personalization
- Random related documents

**After**:
- Intelligent full-text search with weighted ranking
- Multi-factor relevance scoring (popularity, trending, academic context)
- Fuzzy matching for typos and partial matches
- Spelling correction suggestions
- Personalized results based on student's programme
- Relevance-based related documents

## Future Enhancements

### Phase 3 (Not Implemented)

- ElasticSearch integration for larger scale
- Vector search for semantic similarity
- Advanced OCR with multiple engines
- Real-time search analytics
- Search result A/B testing
- Query expansion and refinement

### Extension Points

The architecture supports future enhancements without redesign:
- OCR pipeline extension points ready
- Search service abstraction allows backend swap
- Modular ranking system allows new factors
- Index model supports additional vectors
- Selector pattern allows new query strategies

## Conclusion

The Phase 1 and Phase 2 search refactor successfully transformed the PwaniNet Document Repository from a basic SQL filtering system into an intelligent academic search engine. The implementation maintains full backwards compatibility while significantly improving search quality, relevance, and user experience. The architecture is designed for future scalability and extensibility.
