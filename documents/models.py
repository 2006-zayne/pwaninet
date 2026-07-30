"""Document Repository Models.

This module imports all domain models from their respective sub-packages
to maintain domain separation while providing a single import point.

Domain Organization:
- academic: University structure (Faculty, School, Department, Programme, Academic Unit, etc.)
- documents: Document content (Document, DocumentVersion, DocumentFile, etc.)
- storage: Storage abstraction (StorageBackend, FileChecksum, etc.)
- engagement: User interactions (DocumentView, DocumentDownload, etc.)
- moderation: Content moderation (ModerationStatus, DocumentModeration, etc.)
- collections: Document collections (Collection, CollectionItem, etc.)
- requests: Document requests (DocumentRequest, DocumentRequestVote, etc.)
- search: Search indexing (DocumentSearchIndex, etc.)
"""

# Academic Domain
from .academic.models import (
    AcademicYear,
    Semester,
    Faculty,
    School,
    Department,
    Programme,
    AcademicUnit,
    ProgrammeUnit,
)

# Document Domain
from .documents.models import (
    Category,
    Tag,
    Document,
    DocumentVersion,
    DocumentFile,
    DocumentAuthor,
    DocumentAcademicUnit,
    DocumentTag,
)

# Storage Domain
from .storage.models import (
    StorageBackend,
    FileChecksum,
    StorageMigration,
)

# Engagement Domain
from .engagement.models import (
    DocumentView,
    DocumentDownload,
    DocumentBookmark,
    DocumentRating,
    DocumentShare,
    DocumentReport,
)

# Moderation Domain
from .moderation.models import (
    ModerationStatus,
    DocumentModeration,
    ModerationQueue,
)

# Collections Domain
from .collections.models import (
    Collection,
    CollectionItem,
    CollectionShare,
)

# Request Domain
from .requests.models import (
    DocumentRequest,
    DocumentRequestVote,
)

# Search Domain
from .search.models import (
    DocumentSearchIndex,
)

__all__ = [
    # Academic Domain
    'AcademicYear',
    'Semester',
    'Faculty',
    'School',
    'Department',
    'Programme',
    'AcademicUnit',
    'ProgrammeUnit',
    # Document Domain
    'Category',
    'Tag',
    'Document',
    'DocumentVersion',
    'DocumentFile',
    'DocumentAuthor',
    'DocumentAcademicUnit',
    'DocumentTag',
    # Storage Domain
    'StorageBackend',
    'FileChecksum',
    'StorageMigration',
    # Engagement Domain
    'DocumentView',
    'DocumentDownload',
    'DocumentBookmark',
    'DocumentRating',
    'DocumentShare',
    'DocumentReport',
    # Moderation Domain
    'ModerationStatus',
    'DocumentModeration',
    'ModerationQueue',
    # Collections Domain
    'Collection',
    'CollectionItem',
    'CollectionShare',
    # Request Domain
    'DocumentRequest',
    'DocumentRequestVote',
    # Search Domain
    'DocumentSearchIndex',
]
