# Document Repository Architecture

## Overview

The Document Repository module is designed as a scalable, component-driven frontend foundation for PwaniNet's academic knowledge hub. This architecture prioritizes UI/UX while providing clear extension points for future backend integration.

## Design Philosophy

- **Frontend-First**: UI architecture established before backend implementation
- **Component-Driven**: Reusable components for consistency and maintainability
- **Mobile-First**: Responsive design with touch-friendly interactions
- **Progressive Enhancement**: Core functionality works without JavaScript, enhanced with HTMX
- **Backend-Agnostic**: Templates designed to work with various backend implementations

## Directory Structure

```
documents/
├── __init__.py
├── apps.py                          # Django app configuration
├── admin.py                         # Admin interface (placeholder)
├── urls.py                          # URL routing
├── views.py                         # View functions and API endpoints
├── models.py                        # [FUTURE] Document models
├── forms.py                         # [FUTURE] Form definitions
├── serializers.py                   # [FUTURE] DRF serializers
├── filters.py                       # [FUTURE] Django filters
├── services/                        # [FUTURE] Business logic layer
│   ├── __init__.py
│   ├── document_service.py          # Document CRUD operations
│   ├── search_service.py            # Search and filtering
│   ├── upload_service.py            # File upload handling
│   └── metadata_service.py          # Metadata extraction
├── queries/                         # [FUTURE] Database query layer
│   ├── __init__.py
│   └── document_queries.py
├── tasks.py                         # [FUTURE] Celery async tasks
└── templates/documents/
    ├── base.html                    # Base template with repository layout
    ├── home.html                    # Repository landing page
    ├── search.html                  # Search results page
    ├── document_detail.html         # Document detail page
    ├── upload.html                  # Multi-stage upload flow
    ├── my_library.html              # Personal library dashboard
    ├── library_uploads.html         # User's uploads
    ├── library_bookmarks.html       # User's bookmarks
    ├── library_downloads.html       # Download history
    ├── library_history.html         # Viewing history
    └── partials/
        ├── document_card.html        # Reusable document card
        ├── search_bar.html          # Search input component
        ├── category_pills.html      # Category filter pills
        ├── section_header.html      # Section header component
        ├── empty_state.html         # Empty state component
        ├── loading_skeleton.html    # Loading skeleton
        └── upload_progress.html     # Upload progress indicator
```

## URL Structure

### Page Routes
- `/documents/` - Repository home
- `/documents/search/` - Search results with filters
- `/documents/document/<id>/` - Document detail page
- `/documents/upload/` - Upload flow
- `/documents/library/` - Personal library overview
- `/documents/library/uploads/` - User's uploads
- `/documents/library/bookmarks/` - User's bookmarks
- `/documents/library/downloads/` - Download history
- `/documents/library/history/` - Viewing history

### API Routes (for HTMX/future integration)
- `/documents/api/documents/` - Document list (GET/POST)
- `/documents/api/documents/<id>/` - Document detail (GET/PUT/PATCH/DELETE)
- `/documents/api/upload/` - Document upload (POST)
- `/documents/api/bookmark/<id>/` - Toggle bookmark (POST)

## Component Hierarchy

### Base Components
```
base.html (extends templates/base.html)
├── repository_content block
└── Floating upload button (conditional)
```

### Page Components
```
home.html
├── Hero section with search bar
├── Category pills
├── Trending documents section
├── Recently added section
├── Most downloaded section
└── Your units section

search.html
├── Search header
├── Filters bar (category, unit, semester, type, sort)
├── Results count
├── Results grid
└── Pagination

document_detail.html
├── Back navigation
├── Preview area
├── Description
├── Related documents
└── Sidebar (info card, actions, stats)

upload.html
├── Stage 1: File selection (drag & drop)
├── Stage 2: Metadata form
└── Stage 3: Upload progress

my_library.html
├── Library header
├── Navigation tabs
├── Stats cards
├── Recent activity
└── Collections (placeholder)
```

### Reusable Components

#### document_card.html
**Purpose**: Display document information in a card format

**Props (template context)**:
- `document.title` - Document title
- `document.unit` - Academic unit code
- `document.category` - Document category
- `document.file_type` - File extension (PDF, DOCX, etc.)
- `document.download_count` - Number of downloads
- `document.uploaded` - Upload time (relative)

**Extension Points**:
- Add rating display
- Add bookmark indicator
- Add version badge
- Add author info

#### search_bar.html
**Purpose**: Large, centered search input

**Props**:
- `query` - Current search query
- `show_recent` - Show recent searches

**Extension Points**:
- Add autocomplete dropdown
- Add voice search
- Add advanced search toggle

#### category_pills.html
**Purpose**: Horizontal scrollable category filters

**Props**:
- `active_category` - Currently selected category

**Extension Points**:
- Add category counts
- Add custom categories
- Add nested categories

#### section_header.html
**Purpose**: Section title with optional "View All" link

**Props**:
- `title` - Section title
- `show_view_all` - Show view all link
- `view_all_url` - URL for view all

**Extension Points**:
- Add sort dropdown
- Add filter toggle
- Add section actions

#### empty_state.html
**Purpose**: Encouraging empty state messages

**Props**:
- `title` - Empty state title
- `message` - Descriptive message
- `action_url` - Call-to-action URL
- `action_text` - Button text

**Extension Points**:
- Add illustration
- Add tips
- Add suggested actions

#### loading_skeleton.html
**Purpose**: Skeleton loading placeholder

**Extension Points**:
- Add shimmer animation variants
- Add pulse animation
- Add skeleton for different content types

## Design Tokens

### Colors
```css
--repo-primary: #2563eb;
--repo-primary-hover: #1d4ed8;
--repo-primary-light: #dbeafe;
--repo-success: #10b981;
--repo-warning: #f59e0b;
--repo-danger: #ef4444;
```

### Spacing
```css
--repo-spacing-xs: 4px;
--repo-spacing-sm: 8px;
--repo-spacing-md: 16px;
--repo-spacing-lg: 24px;
--repo-spacing-xl: 32px;
--repo-spacing-2xl: 48px;
--repo-spacing-3xl: 64px;
```

### Border Radius
```css
--repo-radius-sm: 8px;
--repo-radius-md: 12px;
--repo-radius-lg: 16px;
--repo-radius-xl: 20px;
--repo-radius-full: 50%;
```

### Shadows
```css
--repo-shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.05);
--repo-shadow-md: 0 4px 12px rgba(0, 0, 0, 0.08);
--repo-shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.12);
--repo-shadow-xl: 0 16px 40px rgba(0, 0, 0, 0.15);
```

### Transitions
```css
--repo-transition-fast: 150ms ease;
--repo-transition-base: 250ms ease;
--repo-transition-slow: 350ms ease;
```

## Responsive Breakpoints

- **Mobile**: < 576px (single column, stacked layouts)
- **Tablet**: 576px - 768px (2 columns, adjusted spacing)
- **Desktop**: 768px - 992px (3 columns, full features)
- **Large Desktop**: 992px - 1200px (4 columns)
- **Extra Large**: > 1200px (5 columns)

## Backend Extension Points

### 1. Model Layer (Future)

**Required Models**:
```python
class Document(models.Model):
    """Core document model"""
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='documents/')
    file_type = models.CharField(max_length=10)
    file_size = models.PositiveIntegerField()
    preview_image = models.ImageField(upload_to='previews/', blank=True)
    
    # Academic metadata
    unit = models.ForeignKey('courses.Unit', on_delete=SET_NULL, null=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    academic_year = models.CharField(max_length=20)
    semester = models.PositiveSmallIntegerField(choices=SEMESTER_CHOICES)
    tags = models.ManyToManyField('DocumentTag', blank=True)
    
    # Engagement
    download_count = models.PositiveIntegerField(default=0)
    view_count = models.PositiveIntegerField(default=0)
    
    # Timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Relationships
    uploaded_by = models.ForeignKey('users.User', on_delete=CASCADE)
    bookmarks = models.ManyToManyField('users.User', through='DocumentBookmark', related_name='bookmarked_documents')
    
class DocumentBookmark(models.Model):
    """Through model for bookmarks with metadata"""
    user = models.ForeignKey('users.User', on_delete=CASCADE)
    document = models.ForeignKey('Document', on_delete=CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

class DocumentTag(models.Model):
    """Tag model for categorization"""
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
```

### 2. Service Layer (Future)

**DocumentService**:
- `create_document(user, file, metadata)` - Create document with metadata extraction
- `update_document(document_id, data)` - Update document
- `delete_document(document_id)` - Soft delete with archive
- `get_document(document_id)` - Get document with related data
- `list_documents(filters)` - List with pagination and filtering
- `increment_download(document_id)` - Track downloads
- `toggle_bookmark(user, document_id)` - Add/remove bookmark

**SearchService**:
- `search_documents(query, filters)` - Full-text search
- `get_suggestions(query)` - Autocomplete suggestions
- `get_related_documents(document_id)` - Find similar documents

**UploadService**:
- `handle_upload(file, user)` - Process file upload
- `generate_preview(document)` - Create preview image
- `extract_metadata(document)` - Extract from file content
- `validate_upload(file)` - Check file constraints

### 3. API Layer (Future)

**ViewSet Structure**:
```python
class DocumentViewSet(viewsets.ModelViewSet):
    """Full CRUD for documents"""
    queryset = Document.objects.select_related('uploaded_by', 'unit').prefetch_related('tags')
    serializer_class = DocumentSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = DocumentFilter
    search_fields = ['title', 'description', 'tags__name']
    ordering_fields = ['uploaded_at', 'download_count', 'title']
    
    @action(detail=True, methods=['post'])
    def bookmark(self, request, pk=None):
        """Toggle bookmark"""
        pass
    
    @action(detail=True, methods=['post'])
    def download(self, request, pk=None):
        """Track and serve download"""
        pass
```

### 4. Async Tasks (Future)

**Celery Tasks**:
```python
@shared_task
def generate_document_preview(document_id):
    """Generate preview image asynchronously"""
    pass

@shared_task
def extract_document_metadata(document_id):
    """Extract metadata from file content"""
    pass

@shared_task
def update_search_index(document_id):
    """Update search index for document"""
    pass

@shared_task
def process_upload_batch(upload_session_id):
    """Process multiple file uploads"""
    pass
```

### 5. HTMX Integration Points

**Dynamic Loading**:
- Infinite scroll for document lists
- Real-time search results
- Dynamic filter updates
- Upload progress polling

**Partial Templates**:
- `documents/partials/document_card.html` - Can be loaded via HTMX
- `documents/partials/upload_progress.html` - Progress updates
- `documents/partials/loading_skeleton.html` - Loading states

**HTMX Attributes to Add**:
```html
<!-- Infinite scroll -->
<div hx-get="/documents/api/documents/?page=2" 
     hx-trigger="scroll threshold:100px"
     hx-swap="beforeend">
</div>

<!-- Real-time search -->
<input hx-get="/documents/api/search/" 
       hx-trigger="keyup changed delay:300ms"
       hx-target="#search-results">

<!-- Upload progress -->
<div hx-get="/documents/upload/progress/" 
     hx-trigger="every 1s"
     hx-swap="outerHTML">
</div>
```

## Future Features Architecture

### Document Versions
- Add `DocumentVersion` model
- Version history UI in detail page
- Compare versions functionality
- Rollback capability

### OCR Search
- Integrate with Tesseract or cloud OCR
- Store extracted text in `Document.ocr_text`
- Search within document content
- Highlight search results in preview

### Collections
- Add `DocumentCollection` model
- Collection management UI
- Share collections
- Collection templates

### Document Requests
- Add `DocumentRequest` model
- Request submission form
- Voting system
- Fulfillment tracking

### Ratings
- Add `DocumentRating` model
- Star rating UI
- Weighted average calculation
- Rating breakdown display

### Comments
- Reuse existing comment system
- Document-specific comments
- Comment threading
- Rich text support

### Verified Uploads
- Add verification workflow
- Verified badge display
- Verification queue for admins
- Verification criteria

### Offline Documents
- PWA caching strategy
- Offline document viewer
- Sync on reconnect
- Storage quota management

### AI-Powered Recommendations
- Recommendation engine
- Personalized home page
- "You might also like" section
- Trending in your units

## Integration with Existing PwaniNet

### Navigation Integration
Add to main navigation in `templates/base.html`:
```html
<a href="{% url 'documents:home' %}" class="nav-chip">
    <i class="bi bi-folder"></i>
    Documents
</a>
```

### User Profile Integration
Add document stats to user profile:
- Upload count
- Download count
- Contribution level

### Groups Integration
- Share documents to groups
- Group document repositories
- Collaborative collections

### Courses Integration
- Link documents to course units
- Unit-specific document sections
- Course resource pages

## Performance Considerations

### Caching Strategy
- Cache document lists by filters
- Cache search results
- Cache preview images
- Cache user library data

### Database Optimization
- Index on frequently filtered fields
- Use select_related/prefetch_related
- Denormalize aggregate counts
- Partition large tables

### File Storage
- Use CDN for document storage
- Implement lazy loading for previews
- Compress images
- Use WebP format for previews

## Security Considerations

### File Upload Security
- Validate file types
- Scan for malware
- Limit file sizes
- Sanitize filenames
- Store outside web root

### Access Control
- Permission-based access
- Unit-based visibility
- Download rate limiting
- API authentication

### Data Privacy
- User consent for analytics
- Anonymize usage data
- Secure file storage
- GDPR compliance

## Testing Strategy

### Frontend Testing
- Component unit tests
- Integration tests for pages
- Responsive design tests
- Accessibility tests

### Backend Testing (Future)
- Model tests
- Service layer tests
- API endpoint tests
- Task tests

### E2E Testing (Future)
- User flow tests
- Upload flow tests
- Search flow tests
- Cross-browser tests

## Migration Path

### Phase 1: UI Foundation (Current)
- ✅ Template structure
- ✅ Component library
- ✅ Responsive design
- ✅ Design tokens

### Phase 2: Backend Integration
- Models and migrations
- Service layer
- API endpoints
- Admin interface

### Phase 3: Feature Implementation
- File upload handling
- Search functionality
- User library
- Bookmarking

### Phase 4: Advanced Features
- Document versions
- OCR search
- Collections
- AI recommendations

## Maintenance Guidelines

### Adding New Components
1. Create component in `templates/documents/partials/`
2. Add props documentation
3. Include responsive styles
4. Add to component inventory
5. Update this documentation

### Modifying Existing Components
1. Check all usages
2. Maintain backward compatibility
3. Update documentation
4. Test responsive behavior
5. Verify accessibility

### Adding New Pages
1. Create URL pattern in `urls.py`
2. Add view function in `views.py`
3. Create template extending `base.html`
4. Add navigation link
5. Update documentation

## Conclusion

This architecture provides a solid foundation for the Document Repository module while maintaining flexibility for future enhancements. The component-driven approach ensures consistency and maintainability, while the clear extension points allow for seamless backend integration when ready.
