"""Base domain event classes.

Domain events provide a decoupled way for the repository to communicate
with other PwaniNet modules (notifications, activity feeds, achievements, etc.)
without creating direct dependencies.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional
from enum import Enum


class EventType(Enum):
    """Enumeration of all repository domain events."""
    DOCUMENT_UPLOADED = 'document.uploaded'
    DOCUMENT_UPDATED = 'document.updated'
    DOCUMENT_PUBLISHED = 'document.published'
    DOCUMENT_ARCHIVED = 'document.archived'
    DOCUMENT_REMOVED = 'document.removed'
    VERSION_CREATED = 'version.created'
    VERSION_PUBLISHED = 'version.published'
    DOCUMENT_VIEWED = 'document.viewed'
    DOCUMENT_DOWNLOADED = 'document.downloaded'
    DOCUMENT_BOOKMARKED = 'document.bookmarked'
    DOCUMENT_RATED = 'document.rated'
    DOCUMENT_SHARED = 'document.shared'
    DOCUMENT_REPORTED = 'document.reported'
    DOCUMENT_REQUESTED = 'document.requested'
    REQUEST_FULFILLED = 'request.fulfilled'
    COLLECTION_CREATED = 'collection.created'
    COLLECTION_UPDATED = 'collection.updated'
    MODERATION_STATUS_CHANGED = 'moderation.status_changed'


@dataclass
class DomainEvent:
    """Base class for all domain events."""
    
    event_type: EventType
    aggregate_id: str
    aggregate_type: str
    data: Dict[str, Any]
    occurred_at: datetime
    user_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            'event_type': self.event_type.value,
            'aggregate_id': self.aggregate_id,
            'aggregate_type': self.aggregate_type,
            'data': self.data,
            'occurred_at': self.occurred_at.isoformat(),
            'user_id': self.user_id,
            'metadata': self.metadata or {},
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DomainEvent':
        """Create event from dictionary."""
        return cls(
            event_type=EventType(data['event_type']),
            aggregate_id=data['aggregate_id'],
            aggregate_type=data['aggregate_type'],
            data=data['data'],
            occurred_at=datetime.fromisoformat(data['occurred_at']),
            user_id=data.get('user_id'),
            metadata=data.get('metadata'),
        )


@dataclass
class DocumentUploadedEvent(DomainEvent):
    """Emitted when a new document is uploaded."""
    
    def __init__(
        self,
        document_id: int,
        document_title: str,
        user_id: int,
        category: str,
        academic_units: list,
        **kwargs
    ):
        super().__init__(
            event_type=EventType.DOCUMENT_UPLOADED,
            aggregate_id=str(document_id),
            aggregate_type='document',
            data={
                'document_id': document_id,
                'document_title': document_title,
                'category': category,
                'academic_units': academic_units,
            },
            occurred_at=datetime.utcnow(),
            user_id=user_id,
            metadata=kwargs,
        )


@dataclass
class DocumentPublishedEvent(DomainEvent):
    """Emitted when a document is published."""
    
    def __init__(
        self,
        document_id: int,
        document_title: str,
        user_id: int,
        **kwargs
    ):
        super().__init__(
            event_type=EventType.DOCUMENT_PUBLISHED,
            aggregate_id=str(document_id),
            aggregate_type='document',
            data={
                'document_id': document_id,
                'document_title': document_title,
            },
            occurred_at=datetime.utcnow(),
            user_id=user_id,
            metadata=kwargs,
        )


@dataclass
class DocumentDownloadedEvent(DomainEvent):
    """Emitted when a document is downloaded."""
    
    def __init__(
        self,
        document_id: int,
        document_title: str,
        user_id: Optional[int],
        file_name: str,
        **kwargs
    ):
        super().__init__(
            event_type=EventType.DOCUMENT_DOWNLOADED,
            aggregate_id=str(document_id),
            aggregate_type='document',
            data={
                'document_id': document_id,
                'document_title': document_title,
                'file_name': file_name,
            },
            occurred_at=datetime.utcnow(),
            user_id=user_id,
            metadata=kwargs,
        )


@dataclass
class DocumentReportedEvent(DomainEvent):
    """Emitted when a document is reported."""
    
    def __init__(
        self,
        document_id: int,
        document_title: str,
        user_id: int,
        reason: str,
        **kwargs
    ):
        super().__init__(
            event_type=EventType.DOCUMENT_REPORTED,
            aggregate_id=str(document_id),
            aggregate_type='document',
            data={
                'document_id': document_id,
                'document_title': document_title,
                'reason': reason,
            },
            occurred_at=datetime.utcnow(),
            user_id=user_id,
            metadata=kwargs,
        )


@dataclass
class RequestFulfilledEvent(DomainEvent):
    """Emitted when a document request is fulfilled."""
    
    def __init__(
        self,
        request_id: int,
        request_title: str,
        document_id: int,
        fulfilled_by_user_id: int,
        requested_by_user_id: int,
        **kwargs
    ):
        super().__init__(
            event_type=EventType.REQUEST_FULFILLED,
            aggregate_id=str(request_id),
            aggregate_type='document_request',
            data={
                'request_id': request_id,
                'request_title': request_title,
                'document_id': document_id,
                'fulfilled_by_user_id': fulfilled_by_user_id,
                'requested_by_user_id': requested_by_user_id,
            },
            occurred_at=datetime.utcnow(),
            user_id=fulfilled_by_user_id,
            metadata=kwargs,
        )


@dataclass
class ModerationStatusChangedEvent(DomainEvent):
    """Emitted when a document's moderation status changes."""
    
    def __init__(
        self,
        document_id: int,
        document_title: str,
        old_status: str,
        new_status: str,
        moderated_by_user_id: int,
        **kwargs
    ):
        super().__init__(
            event_type=EventType.MODERATION_STATUS_CHANGED,
            aggregate_id=str(document_id),
            aggregate_type='document',
            data={
                'document_id': document_id,
                'document_title': document_title,
                'old_status': old_status,
                'new_status': new_status,
            },
            occurred_at=datetime.utcnow(),
            user_id=moderated_by_user_id,
            metadata=kwargs,
        )
