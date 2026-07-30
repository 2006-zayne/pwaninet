# PwaniNet Document Repository - Backend Architecture

## Overview

This document describes the backend architecture for the PwaniNet Document Repository, a scalable, modular academic document management system designed to become the central knowledge hub of PwaniNet.

## Design Philosophy

### Core Principles

1. **Domain-Driven Design (DDD)**: The repository is organized into independent domains, each with clear responsibilities and boundaries.

2. **Separation of Concerns**: Each domain handles a specific aspect of the system (academic structure, document content, storage, search, etc.) without tight coupling.

3. **Scalability**: The architecture supports growth to hundreds of thousands of documents through efficient indexing, asynchronous processing, and database optimization.

4. **Extensibility**: Future features (OCR, AI metadata extraction, cloud storage, recommendations) can be added without major schema redesign.

5. **Maintainability**: Modular organization and clear separation between models, services, and business logic make the system easy to understand and modify.

### Key Architectural Decisions

#### Document ≠ File

A fundamental design decision is that a **document is not a file**. A document represents an academic resource that may have:
- Multiple versions
- Multiple files per version
- Multiple academic unit mappings
- Multiple tags and authors
- Multiple file formats

This separation allows for:
- Version history tracking
- File format flexibility
- Academic context preservation
- Rich metadata without file coupling

#### Domain Separation

The repository is divided into 9 independent domains:

1. **Academic Domain**: University structure (Faculty, School, Department, Programme, Academic Unit)
2. **Document Domain**: Academic content (Document, DocumentVersion, DocumentFile, DocumentAuthor)
3. **Storage Domain**: File storage abstraction (StorageBackend, FileChecksum, StorageMigration)
4. **Search Domain**: Search indexing (DocumentSearchIndex)
5. **Processing Domain**: Asynchronous processing pipeline
6. **Engagement Domain**: User interactions (views, downloads, bookmarks, ratings, shares, reports)
7. **Moderation Domain**: Content moderation (ModerationStatus, DocumentModeration, ModerationQueue)
8. **Collections Domain**: Document collections (Collection, CollectionItem, CollectionShare)
9. **Request Domain**: Document requests (DocumentRequest, DocumentRequestVote)

## Domain Models

### Academic Domain

**Purpose**: Reusable university structure that can be used across PwaniNet modules.

**Models**:
- `AcademicYear`: Represents an academic year (e.g., 2024/2025)
- `Semester`: Represents a semester within an academic year
- `Faculty`: Top-level academic division
- `School`: School within a faculty
- `Department`: Department within a school
- `Programme`: Academic programme (e.g., BSc Computer Science)
- `AcademicUnit`: Individual course/unit (e.g., CSC221 Database Systems)
- `ProgrammeUnit`: Junction table for many-to-many programme-unit relationships

**Key Design Decisions**:
- Junction table for Programme ↔ Academic Unit to prevent duplicate units
- Many programmes can share the same unit (e.g., Database Systems shared by CS, IT, SE)
- Hierarchical structure follows university organization
- All models include validation and indexing for performance

### Document Domain

**Purpose**: Core document metadata without coupling to files, storage, or analytics.

**Models**:
- `Category`: Normalized document categories (Past Paper, Lecture Notes, etc.)
- `Tag`: Normalized tags for flexible categorization
- `Document`: Core document metadata only (title, description, visibility, status, language, category)
- `DocumentVersion`: Explicit versioning with change notes
- `DocumentFile`: Independent file objects belonging to versions
- `DocumentAuthor`: Multiple authors with different roles (original, uploader, contributor, editor)
- `DocumentAcademicUnit`: Junction for multiple academic unit mappings
- `DocumentTag`: Junction for normalized tagging

**Key Design Decisions**:
- Document model contains only metadata (no files, storage, analytics)
- Explicit versioning with `is_latest` flag
- Files are independent objects with storage abstraction
- Multiple academic units supported via junction table
- Normalized categories and tags (no free text)
- Uploader and author are separate concepts

### Storage Domain

**Purpose**: Storage abstraction to enable migration between backends without business logic changes.

**Models**:
- `StorageBackend`: Configuration for storage backends (local, S3, R2, B2, Azure, MinIO)
- `FileChecksum`: Checksum tracking for duplicate detection
- `StorageMigration`: Migration history between backends

**Key Design Decisions**:
- Multiple backends can be active simultaneously
- Priority-based backend selection
- Checksum-based duplicate detection
- Migration tracking for audit and rollback
- Storage-specific configuration isolated in JSON field

### Search Domain

**Purpose**: Search indexing layer to enable efficient queries without hitting main document models.

**Models**:
- `DocumentSearchIndex`: Denormalized search data with PostgreSQL Full Text Search

**Key Design Decisions**:
- Denormalized data for fast queries
- PostgreSQL FTS with GIN index
- Computed popularity score for ranking
- Time decay factor for freshness
- Compatible with future Meilisearch/ElasticSearch migration
- Includes OCR text field for future implementation

### Engagement Domain

**Purpose**: Track user interactions separately from document models to maintain separation of concerns.

**Models**:
- `DocumentView`: Track document views
- `DocumentDownload`: Track document downloads
- `DocumentBookmark`: User bookmarks with notes
- `DocumentRating`: User ratings (1-5) with reviews
- `DocumentShare`: Track shares to platforms
- `DocumentReport`: Content moderation reports

**Key Design Decisions**:
- Analytics stored separately from document model
- Supports anonymous tracking via session keys
- Rich metadata (IP, user agent, referrer) for analytics
- Cached analytics can be added later without schema changes

### Moderation Domain

**Purpose**: Extensible moderation system avoiding boolean fields.

**Models**:
- `ModerationStatus`: Configurable moderation statuses with visibility rules
- `DocumentModeration`: Status tracking for individual documents
- `ModerationQueue`: Queue for documents awaiting moderation

**Key Design Decisions**:
- No boolean fields - uses status system
- Configurable visibility per status (public, searchable, downloadable)
- Priority-based queue for moderation
- Status change tracking with audit trail

### Collections Domain

**Purpose**: Future feature for document collections, prepared without coupling to document model.

**Models**:
- `Collection`: User-created document collections
- `CollectionItem`: Documents within collections
- `CollectionShare`: Collection sharing between users

**Key Design Decisions**:
- Independent of document model
- Support for private, public, unlisted visibility
- Edit permissions for shared collections
- Orderable items within collections

### Request Domain

**Purpose**: Future feature for document requests, prepared for notification integration.

**Models**:
- `DocumentRequest`: User requests for specific documents
- `DocumentRequestVote`: Voting system for requests

**Key Design Decisions**:
- Academic context (unit, semester, category)
- Priority and status tracking
- Fulfillment linking to documents
- Voting system for demand indication

## Service Layer

Business logic is encapsulated in service classes to keep models lightweight and maintainable.

### UploadService

**Responsibilities**:
- File validation (size, extension)
- Checksum computation
- Duplicate detection
- Document creation with metadata
- Version creation with files
- Upload completion and processing queue

**Key Features**:
- Transactional operations
- Checksum-based duplicate detection
- Automatic version numbering
- Processing task queuing

### StorageService

**Responsibilities**:
- Storage-agnostic file operations
- Backend selection and routing
- File storage, retrieval, deletion
- URL generation
- Storage migration initiation

**Key Features**:
- Multiple backend support
- Fallback mechanisms
- Migration tracking
- Configuration isolation

### SearchService

**Responsibilities**:
- Search-agnostic query interface
- PostgreSQL FTS implementation
- Filter application
- Sorting and pagination
- Document indexing
- Search index removal

**Key Features**:
- Switchable backends (PostgreSQL FTS, Meilisearch, ElasticSearch)
- Denormalized index updates
- Popularity score computation
- Time decay for freshness

## Processing Pipeline

Asynchronous processing using Celery to avoid blocking HTTP requests.

### Pipeline Stages

1. **Upload**: Persist file and create document record
2. **Queue**: Trigger processing task
3. **Thumbnail Generation**: Create thumbnail images
4. **Preview Generation**: Create document previews
5. **Metadata Extraction**: Extract file metadata
6. **OCR**: Extract text from images/PDFs (future)
7. **Virus Scan**: Scan for malware (future)
8. **Duplicate Detection**: Check for duplicate files
9. **Search Indexing**: Update search index
10. **Mark Ready**: Change status to ready

### Task Architecture

**Tasks**:
- `process_document`: Main coordinator task
- `process_file`: File-specific processing coordinator
- `generate_thumbnail`: Thumbnail generation
- `generate_preview`: Preview generation
- `extract_metadata`: Metadata extraction
- `check_duplicate`: Duplicate detection
- `perform_ocr`: OCR processing (future)
- `virus_scan`: Virus scanning (future)
- `update_search_index`: Search index update
- `remove_from_search_index`: Search index removal
- `reindex_all_documents`: Bulk reindexing

**Key Features**:
- Independent retry for each stage
- Error handling with status updates
- Parallel processing capability
- Graceful degradation

## Domain Events

Repository models emit domain events instead of directly sending notifications, keeping the repository decoupled from other PwaniNet modules.

### Event Types

- `DOCUMENT_UPLOADED`: New document uploaded
- `DOCUMENT_PUBLISHED`: Document published
- `DOCUMENT_DOWNLOADED`: Document downloaded
- `DOCUMENT_REPORTED`: Document reported
- `REQUEST_FULFILLED`: Document request fulfilled
- `MODERATION_STATUS_CHANGED`: Moderation status changed

### Event Architecture

**Components**:
- `DomainEvent`: Base event class
- `EventDispatcher`: Central event dispatcher
- Signal Handlers: Django signal handlers that emit events

**Integration Points**:
- Notifications module can subscribe to events
- Activity feeds can track events
- Achievements can be triggered by events
- Analytics can aggregate events

## Query Selectors

Optimized query selectors to avoid N+1 query problems and ensure efficient database usage.

### DocumentSelector

**Methods**:
- `get_document_with_relations`: Single query with all related data
- `list_documents_for_home`: Optimized home page listing
- `list_documents_for_user`: User library listings
- `get_trending_documents`: Trending based on recent engagement
- `get_documents_by_category`: Category-based filtering
- `get_documents_by_academic_unit`: Unit-based filtering
- `search_documents`: Search with filters
- `get_document_statistics`: Engagement statistics

**Key Features**:
- `select_related` for foreign keys
- `prefetch_related` for many-to-many
- Annotation for computed fields
- Efficient pagination

## Database Indexing Strategy

### Index Categories

1. **Primary Keys**: All tables have indexed primary keys
2. **Foreign Keys**: All foreign keys are indexed
3. **Unique Constraints**: Slug fields and natural keys
4. **Composite Indexes**: Frequently queried field combinations
5. **GIN Indexes**: PostgreSQL full-text search vectors

### Performance Considerations

- Indexes on timestamp fields for sorting
- Indexes on status fields for filtering
- Composite indexes for common query patterns
- GIN indexes for search vectors
- Partial indexes for filtered queries

## Package Structure

```
documents/
├── __init__.py
├── models.py                    # Central import point
├── academic/                    # Academic domain
│   ├── __init__.py
│   └── models.py
├── documents/                   # Document domain
│   ├── __init__.py
│   └── models.py
├── storage/                     # Storage domain
│   ├── __init__.py
│   └── models.py
├── search/                      # Search domain
│   ├── __init__.py
│   └── models.py
├── engagement/                  # Engagement domain
│   ├── __init__.py
│   └── models.py
├── moderation/                  # Moderation domain
│   ├── __init__.py
│   └── models.py
├── collections/                 # Collections domain
│   ├── __init__.py
│   └── models.py
├── requests/                    # Request domain
│   ├── __init__.py
│   └── models.py
├── services/                    # Business logic
│   ├── __init__.py
│   ├── upload_service.py
│   ├── storage_service.py
│   └── search_service.py
├── selectors/                   # Query optimization
│   ├── __init__.py
│   └── document_selectors.py
├── tasks/                       # Celery tasks
│   ├── __init__.py
│   └── processing.py
├── signals/                     # Django signals
│   ├── __init__.py
│   └── handlers.py
└── events/                      # Domain events
    ├── __init__.py
    ├── base.py
    └── dispatcher.py
```

## Future Extension Points

### OCR Integration
- `DocumentFile.ocr_text` field already exists
- `perform_ocr` task placeholder ready
- Search index includes OCR text field

### AI-Assisted Metadata Extraction
- Processing pipeline can be extended
- New Celery tasks can be added
- Document model has metadata fields

### Cloud Storage Migration
- Storage abstraction already in place
- Multiple backends supported
- Migration tracking implemented

### Document Recommendations
- Search index has popularity scores
- Engagement data available
- Can add recommendation service

### Collections
- Collections domain already implemented
- Sharing and permissions ready
- Can add collaborative features

### Document Requests
- Request domain already implemented
- Voting system ready
- Notification integration via events

### Offline Synchronization
- Document model has versioning
- File checksums for integrity
- Can add sync service

### Advanced Search
- Search index is backend-agnostic
- Can migrate to Meilisearch/ElasticSearch
- OCR text field ready for content search

### Moderation Workflows
- Extensible status system
- Queue with priorities
- Can add workflow automation

## Trade-offs and Decisions

### PostgreSQL FTS vs External Search Engine

**Decision**: Start with PostgreSQL Full Text Search

**Rationale**:
- No additional infrastructure required
- Sufficient for initial scale
- Easy migration path to Meilisearch/ElasticSearch
- Search index abstraction allows switch

**Trade-off**: Less advanced features than dedicated search engines, but adequate for MVP.

### Normalized Categories vs Free Text

**Decision**: Normalized categories with choices

**Rationale**:
- Consistent categorization
- Better filtering and analytics
- Easier to maintain
- Can be extended without schema changes

**Trade-off**: Less flexibility than free text, but better data quality.

### Explicit Versioning vs Automatic Versioning

**Decision**: Explicit version records with manual version creation

**Rationale**:
- Clear version history
- Change notes for each version
- User control over versioning
- Better audit trail

**Trade-off**: More manual than automatic, but provides better control and transparency.

### Separate Engagement Models vs Document Counters

**Decision**: Separate engagement models

**Rationale**:
- Rich metadata (IP, user agent, referrer)
- Anonymous tracking support
- Future analytics capabilities
- Separation of concerns

**Trade-off**: More complex than simple counters, but provides much richer data.

### Domain Events vs Direct Notifications

**Decision**: Domain events with dispatcher

**Rationale**:
- Decoupled from other modules
- Multiple subscribers possible
- Event replay capability
- Testable in isolation

**Trade-off**: More complex than direct calls, but provides better modularity.

## Performance Considerations

### Database Optimization

- **Indexing**: Strategic indexes on frequently queried fields
- **Query Optimization**: Selectors use select_related and prefetch_related
- **Denormalization**: Search index for fast queries
- **Connection Pooling**: Django's built-in connection pooling

### Caching Strategy

- **Query Caching**: Can be added at selector level
- **Search Index**: Denormalized data acts as cache
- **Analytics**: Can add cached analytics model
- **Session Caching**: Django session framework

### Asynchronous Processing

- **Heavy Operations**: All processing in Celery tasks
- **Independent Retry**: Each stage can retry independently
- **Parallel Processing**: Tasks can run in parallel
- **Queue Priorities**: Celery priority queues

### Scalability

- **Horizontal Scaling**: Stateless services allow horizontal scaling
- **Database Sharding**: Domain separation enables future sharding
- **Storage Migration**: Cloud storage for file storage
- **Search Backend**: Dedicated search engine for large scale

## Security Considerations

### File Upload Security

- File type validation
- Size limits
- Checksum verification
- Virus scanning (future)

### Access Control

- Document visibility levels
- Moderation status enforcement
- User-based permissions
- Collection sharing controls

### Data Privacy

- Anonymous tracking via session keys
- IP address logging
- User agent tracking
- Referrer logging

## Integration with Existing PwaniNet

### Authentication

- Uses existing `AUTH_USER_MODEL`
- No custom user models
- Leverages existing authentication system

### Notifications

- Domain events for integration
- No direct coupling
- Event-based architecture

### Database

- PostgreSQL (existing)
- No new database requirements
- Compatible with existing schema

### Infrastructure

- Celery (existing)
- Redis (existing)
- Django Storage (existing)
- No new infrastructure requirements

## Migration Strategy

### Phase 1: Core Models
- Create academic domain models
- Create document domain models
- Basic upload functionality

### Phase 2: Processing Pipeline
- Implement Celery tasks
- Add processing pipeline
- Search indexing

### Phase 3: Engagement
- Add engagement models
- Implement tracking
- Analytics

### Phase 4: Advanced Features
- Collections
- Document requests
- Advanced moderation

### Phase 5: Future Features
- OCR
- AI metadata extraction
- Cloud storage migration
- Advanced search

## Conclusion

The PwaniNet Document Repository backend architecture provides a solid foundation for a scalable, maintainable, and extensible academic document management system. The domain-driven design ensures clear separation of concerns, while the service layer encapsulates business logic. The architecture supports future growth and feature additions without requiring major redesign, making it a long-term solution for PwaniNet's academic knowledge hub.
