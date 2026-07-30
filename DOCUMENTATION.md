# PwaniNet Document Repository - Technical Documentation

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Key Components](#key-components)
4. [Libraries and Dependencies](#libraries-and-dependencies)
5. [Celery Workers](#celery-workers)
6. [Document Processing Pipeline](#document-processing-pipeline)
7. [Document Viewer System](#document-viewer-system)
8. [API Endpoints](#api-endpoints)
9. [Database Models](#database-models)
10. [Deployment](#deployment)

---

## Overview

PwaniNet is a Django-based document repository system designed for academic institutions. It provides a centralized platform for uploading, sharing, and discovering educational documents including PDFs, Word documents, presentations, and more.

### Key Features
- Multi-format document support (PDF, DOCX, PPTX, TXT, MD, Images)
- In-browser document preview with page navigation
- Advanced search with filters
- Academic unit and semester organization
- User groups and permissions
- Download tracking and analytics
- PWA support for offline access

---

## Architecture

### Project Structure

```
pwaninet/
├── pwaninet/                 # Django project settings
│   ├── settings/
│   │   ├── base.py          # Base configuration
│   │   ├── local.py         # Local development settings
│   │   └── production.py    # Production settings
│   ├── celery.py            # Celery configuration
│   └── urls.py              # Root URL configuration
├── documents/               # Main documents app
│   ├── academic/            # Academic unit management
│   ├── collections/         # Document collections
│   ├── documents/           # Document models
│   ├── engagement/          # User interactions (likes, bookmarks)
│   ├── events/              # Document events
│   ├── processing/          # File processing logic
│   ├── requests/            # Document requests
│   ├── search/              # Search functionality
│   ├── selectors/           # Optimized database queries
│   ├── services/            # Business logic
│   ├── signals/             # Django signals
│   ├── static/              # Static assets
│   │   └── vendor/          # Third-party libraries
│   ├── tasks/               # Celery tasks
│   ├── templates/           # HTML templates
│   └── urls.py              # App URL configuration
├── core/                    # Core functionality
├── courses/                 # Course management
├── groups/                  # User groups
├── media/                   # User uploads
│   ├── documents/           # Document files
│   ├── previews/            # Document preview images
│   └── covers/              # Document cover images
└── requirements.txt         # Python dependencies
```

### Technology Stack

- **Backend**: Django 5.x, Python 3.12
- **Task Queue**: Celery with Redis
- **Database**: PostgreSQL
- **Frontend**: Vanilla JavaScript, Bootstrap Icons
- **Document Processing**: PyMuPDF, python-docx, python-pptx
- **Search**: Custom search service with filters
- **Static Files**: Django staticfiles system

---

## Key Components

### 1. Document Models

**Document Model** (`documents/documents/models.py`)
- Core document entity with metadata
- Fields: title, description, category, status, visibility
- Relationships: versions, academic units, tags, uploaded_by

**DocumentVersion Model**
- Version control for documents
- Links to DocumentFile instances
- Tracks version history

**DocumentFile Model**
- Actual file storage reference
- Fields: file (FileField), extension, size_mb, preview_path
- Processing status tracking

**Category Model**
- Document categorization
- Code, name, description, icon

**AcademicUnit Model**
- Academic organization structure
- Links to documents for classification

### 2. Document Processing Pipeline

The processing pipeline handles uploaded documents through several stages:

1. **File Upload** → Django view creates Document, DocumentVersion, DocumentFile
2. **Celery Task** → `process_document` task triggered
3. **File Processing** → `process_file` task handles individual files
4. **Thumbnail Generation** → `generate_thumbnail` creates preview thumbnails
5. **Preview Generation** → `generate_preview` creates document previews
6. **Metadata Extraction** → `extract_metadata` pulls file information
7. **Search Indexing** → Document added to search index
8. **Status Update** → Document marked as 'ready'

### 3. Search System

**SearchService** (`documents/services/search_service.py`)
- Custom search implementation
- Filters by category, academic unit, semester, file type
- Text search across document metadata
- Optimized queries using selectors

**Document Selectors** (`documents/selectors/document_selectors.py`)
- Optimized database queries
- Prefetch related data to reduce N+1 queries
- Efficient filtering and sorting

---

## Libraries and Dependencies

### Core Dependencies

**Django Framework**
```python
django==5.0.7
djangorestframework==3.15.2
```
- Web framework providing ORM, templates, URL routing
- REST framework for API endpoints

**Database**
```python
psycopg2-binary==2.9.9
```
- PostgreSQL adapter for Django

**Task Queue**
```python
celery==5.4.0
redis==5.0.1
```
- Celery for asynchronous task processing
- Redis as message broker and cache backend

### Document Processing Libraries

**PyMuPDF (fitz)**
```python
PyMuPDF==1.23.8
```
- PDF rendering and manipulation
- Used for generating PDF preview images
- Extracts text and metadata from PDFs
- Renders PDF pages to images for thumbnails

**python-docx**
```python
python-docx==1.2.0
```
- Microsoft Word document processing
- Converts DOCX to HTML for preview
- Extracts text content and metadata

**python-pptx**
```python
python-pptx==1.0.2
```
- PowerPoint presentation processing
- Extracts slide count and metadata
- Limited browser preview support (download prompt)

**Pillow (PIL)**
```python
Pillow==10.4.0
```
- Image processing library
- Used for thumbnail generation
- Creates preview images for non-PDF documents

### Frontend Libraries (Self-Hosted)

**PDF.js 3.11.174**
- Mozilla's PDF rendering library
- Client-side PDF rendering in browser
- Page navigation and zoom controls
- Located at: `static/vendor/pdfjs/`

**Mammoth.js 1.6.0**
- DOCX to HTML converter
- Browser-based Word document preview
- Located at: `static/vendor/mammoth/`

**Marked.js 9.1.2**
- Markdown parser and renderer
- Converts markdown to HTML for preview
- Located at: `static/vendor/marked/`

### Additional Dependencies

**Authentication & Security**
```python
djangorestframework-simplejwt==5.3.1
PyJWT==2.12.1
pyOpenSSL==26.1.0
```
- JWT token authentication
- SSL/TLS support

**File Handling**
```python
python-decouple==3.8
python-magic==0.4.27
```
- Environment variable management
- File type detection

**Real-time**
```python
channels==4.1.0
channels-redis==4.2.1
```
- WebSocket support for real-time features

---

## Celery Workers

### Configuration

**Celery Setup** (`pwaninet/celery.py`)
```python
from celery import Celery

app = Celery('pwaninet')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

**Settings** (`pwaninet/settings/base.py`)
```python
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = 'Africa/Nairobi'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
```

### Celery Tasks

**Document Processing Tasks** (`documents/tasks/processing.py`)

1. **process_document**
   - Main entry point for document processing
   - Coordinates all processing steps
   - Handles retries on failure
   - Updates document status

2. **process_file**
   - Processes individual DocumentFile instances
   - Triggers thumbnail and preview generation
   - Initiates metadata extraction
   - Checks for duplicates

3. **generate_thumbnail**
   - Creates thumbnail images for documents
   - Uses PyMuPDF for PDFs
   - Uses Pillow for other formats
   - Saves to media/thumbnails/

4. **generate_preview**
   - Creates full-page preview images
   - Supports multiple file types:
     - PDF: PyMuPDF rendering
     - DOCX: python-docx text extraction
     - PPTX: Slide count display
     - TXT/MD: Text content rendering
   - Saves to media/previews/

5. **extract_metadata**
   - Extracts file metadata
   - Author, creation date, page count
   - File size and type information

6. **check_duplicate**
   - Checks for duplicate documents
   - Based on file hash comparison
   - Alerts users of potential duplicates

### Task Execution Flow

```
User Uploads File
    ↓
Django View Creates Document
    ↓
process_document.delay(document_id)
    ↓
Celery Worker Picks Up Task
    ↓
process_file.delay(file_id)
    ↓
Parallel Execution:
    ├─ generate_thumbnail.delay(file_id)
    ├─ generate_preview.delay(file_id)
    ├─ extract_metadata.delay(file_id)
    └─ check_duplicate.delay(file_id)
    ↓
search_service.index_document(document)
    ↓
document.status = 'ready'
```

### Worker Management

**Starting the Worker**
```bash
celery -A pwaninet worker -l info
```

**Monitoring**
```bash
celery -A pwaninet flower  # Web-based monitoring
```

**Task States**
- PENDING: Task waiting to be executed
- STARTED: Task is being executed
- SUCCESS: Task completed successfully
- FAILURE: Task failed
- RETRY: Task being retried

### Error Handling

All tasks include:
- Maximum retry limits (2-3 retries)
- Exponential backoff (countdown increases)
- Detailed error logging
- Graceful degradation on failure

---

## Document Processing Pipeline

### Upload Flow

1. **User Upload**
   - File selected via frontend form
   - AJAX upload to Django view
   - File saved to media/documents/

2. **Database Creation**
   ```python
   document = Document.objects.create(
       title=validated_data['title'],
       description=validated_data['description'],
       category=validated_data['category'],
       uploaded_by=request.user
   )
   
   version = DocumentVersion.objects.create(
       document=document,
       version_number=1
   )
   
   file = DocumentFile.objects.create(
       version=version,
       file=uploaded_file,
       extension=file_extension,
       size_mb=file_size_mb
   )
   ```

3. **Async Processing**
   ```python
   from documents.tasks.processing import process_document
   task = process_document.delay(document.id)
   ```

4. **Preview Generation**
   - PDF: PyMuPDF renders first page to JPEG
   - DOCX: python-docx extracts text to image
   - PPTX: Creates slide count preview
   - TXT/MD: Renders text content to image

### Preview Storage

```
media/
├── documents/           # Original uploaded files
├── previews/            # Generated preview images
│   ├── 1_preview.jpg   # Document file ID 1
│   ├── 2_preview.jpg   # Document file ID 2
│   └── ...
└── thumbnails/          # Thumbnail images
```

---

## Document Viewer System

### Architecture

The document viewer uses a modular, factory-pattern architecture:

```
DocumentViewer (Main Controller)
    ↓
ViewerFactory (Factory Pattern)
    ↓
Specific Viewers:
    ├─ PDFViewer (PDF.js)
    ├─ DOCXViewer (Mammoth.js)
    ├─ PPTXViewer (Download prompt)
    ├─ TextViewer (Marked.js)
    ├─ ImageViewer (Native)
    └─ UnsupportedViewer (Fallback)
```

### Component Breakdown

**DocumentViewer Class**
- Main controller for all viewers
- Manages toolbar and navigation
- Handles fullscreen mode
- Coordinates between viewer and UI

**ViewerFactory Class**
- Factory pattern for viewer creation
- Selects appropriate viewer based on file type
- Extensible for new document types

**PDFViewer Class**
- Uses PDF.js for rendering
- Page navigation (prev/next)
- Zoom controls (50% - 300%)
- Zoom percentage indicator
- Fullscreen support

**DOCXViewer Class**
- Uses Mammoth.js for DOCX to HTML conversion
- Continuous scroll interface
- Preserves formatting

**TextViewer Class**
- Renders plain text or markdown
- Uses Marked.js for markdown parsing
- Syntax highlighting support

**ImageViewer Class**
- Native browser image display
- Responsive sizing
- Supports PNG, JPG, JPEG, GIF, WEBP

### Viewer Features

**Toolbar Controls**
- Previous/Next page navigation
- Current page indicator
- Total pages display
- Zoom in/out buttons
- Zoom percentage indicator
- Fullscreen toggle
- Download button

**Responsive Design**
- Mobile-friendly controls
- Adaptive viewer height
- Touch-friendly buttons
- Fullscreen mobile support

**Error Handling**
- Loading states with spinner
- Graceful error messages
- Download fallback for unsupported formats
- Network interruption handling

---

## API Endpoints

### Document Endpoints

**Repository Home**
- `GET /documents/` - Home page with trending/recent documents

**Document Detail**
- `GET /documents/<slug>/` - Document detail page
- `GET /documents/<id>/detail/` - Detail by ID

**Search**
- `GET /documents/search/` - Search results with filters
- Query parameters: `q`, `category`, `unit`, `semester`, `file_type`

**Upload**
- `POST /documents/upload/` - Upload new document
- Returns JSON with task IDs for progress tracking

**My Library**
- `GET /documents/my-library/` - User's uploaded documents
- `GET /documents/my-library/uploads/` - Uploads only
- `POST /documents/my-library/clear-history/` - Clear view history

**Document Actions**
- `POST /documents/<id>/download/` - Track download
- `POST /documents/<id>/bookmark/` - Toggle bookmark
- `POST /documents/<id>/like/` - Like document

### API Views

**Document Upload API**
```python
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_document(request):
    # Creates document, version, file
    # Triggers Celery processing
    # Returns task IDs for progress tracking
    return JsonResponse({
        'success': True,
        'document_count': len(created_documents),
        'task_ids': task_ids
    })
```

---

## Database Models

### Core Models

**Document**
```python
class Document(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    status = models.CharField(choices=STATUS_CHOICES, default='draft')
    visibility = models.CharField(choices=VISIBILITY_CHOICES, default='private')
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['status', 'visibility']),
            models.Index(fields=['created_at']),
        ]
```

**DocumentFile**
```python
class DocumentFile(models.Model):
    version = models.ForeignKey(DocumentVersion, on_delete=models.CASCADE)
    file = models.FileField(upload_to='documents/')
    extension = models.CharField(max_length=10)
    size_mb = models.DecimalField(max_digits=6, decimal_places=2)
    preview_path = models.CharField(max_length=255, blank=True)
    processing_status = models.CharField(max_length=20, default='pending')
    
    class Meta:
        indexes = [
            models.Index(fields=['extension']),
            models.Index(fields=['processing_status']),
        ]
```

### Relationships

```
Document (1) ─────── (N) DocumentVersion
DocumentVersion (1) ─── (N) DocumentFile
Document (N) ─────────── (N) AcademicUnit
Document (N) ─────────── (N) Tag
Document (1) ─────────── (N) DocumentView
Document (1) ─────────── (N) DocumentDownload
```

---

## Deployment

### Environment Setup

**Development**
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Start development server
python manage.py runserver
```

**Production**
```bash
# Collect static files
python manage.py collectstatic --noinput

# Start Gunicorn
gunicorn pwaninet.wsgi:application

# Start Celery worker
celery -A pwaninet worker -l info

# Start Celery beat (for scheduled tasks)
celery -A pwaninet beat -l info
```

### Services Required

1. **PostgreSQL** - Database
2. **Redis** - Celery broker and cache
3. **Nginx** - Reverse proxy and static file serving
4. **Supervisor** - Process management

### Environment Variables

```bash
DJANGO_SETTINGS_MODULE=pwaninet.settings.production
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:password@localhost/pwaninet
REDIS_URL=redis://localhost:6379/0
ALLOWED_HOSTS=your-domain.com
```

### Performance Optimization

**Database**
- Use connection pooling
- Enable query caching
- Regular vacuum and analyze

**Celery**
- Configure worker concurrency
- Use task routing for different queues
- Monitor with Flower

**Static Files**
- Use CDN for production
- Enable browser caching
- Compress assets

---

## Troubleshooting

### Common Issues

**Celery Tasks Not Running**
```bash
# Check Redis connection
redis-cli ping

# Check Celery worker status
celery -A pwaninet inspect active

# View worker logs
tail -f /var/log/celery/worker.log
```

**Preview Generation Failed**
```bash
# Check PyMuPDF installation
python -c "import fitz; print(fitz.__version__)"

# Regenerate previews manually
python regenerate_previews.py
```

**Static Files Not Loading**
```bash
# Collect static files
python manage.py collectstatic

# Check STATIC_URL setting
# Should be '/static/' in production
```

---

## Contributing

### Code Style
- Follow PEP 8 guidelines
- Use meaningful variable names
- Add docstrings to functions
- Keep functions focused and small

### Testing
```bash
# Run tests
python manage.py test

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

### Git Workflow
1. Create feature branch
2. Make changes with clear commit messages
3. Write tests for new features
4. Ensure all tests pass
5. Submit pull request

---

## License

[Your License Here]

---

## Contact

For questions or support, contact [Your Contact Information]
