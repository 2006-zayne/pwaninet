"""
Notification Payload Models
Conforms to PwaniNet Notification Payload Contract (Version 1.0)
The payload is declarative, self-describing, and renderer-independent.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class NotificationIntent(Enum):
    """Intent describes behavioral class"""
    ACTIVITY = "activity"
    WORKFLOW = "workflow"
    AWARENESS = "awareness"
    ALERT = "alert"
    ANNOUNCEMENT = "announcement"
    REMINDER = "reminder"


class LifecycleState(Enum):
    """Lifecycle states"""
    LIVE = "LIVE"
    UPDATED = "UPDATED"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    COMPLETED = "COMPLETED"
    HISTORICAL = "HISTORICAL"


class ContextType(Enum):
    """Supported context types"""
    GROUP = "GROUP"
    DOCUMENT = "DOCUMENT"
    DOCUMENT_REPOSITORY = "DOCUMENT_REPOSITORY"
    SYSTEM = "SYSTEM"
    SECURITY = "SECURITY"
    POST = "POST"
    PROFILE = "PROFILE"
    WORKSPACE = "WORKSPACE"
    COURSE = "COURSE"


class ResourceType(Enum):
    """Supported resource types"""
    POST = "POST"
    DOCUMENT = "DOCUMENT"
    COMMENT = "COMMENT"
    GROUP = "GROUP"
    PROFILE = "PROFILE"
    SYSTEM = "SYSTEM"


class PreviewType(Enum):
    """Supported preview types"""
    POST = "POST"
    DOCUMENT = "DOCUMENT"
    GROUP = "GROUP"
    PROFILE = "PROFILE"
    NONE = "NONE"


class MessageState(Enum):
    """Message aggregation states"""
    SINGLE = "SINGLE"
    DUAL = "DUAL"
    FEW = "FEW"
    MANY = "MANY"
    HISTORICAL = "HISTORICAL"


@dataclass
class NotificationIdentity:
    """Notification identity section"""
    notification_id: str
    recipient_id: int
    event_id: str


@dataclass
class NotificationLifecycle:
    """Lifecycle section"""
    state: LifecycleState
    terminal: bool = False


@dataclass
class NotificationProfile:
    """Rendering profile section"""
    id: str
    version: str = "1.0"


@dataclass
class NotificationActor:
    """Actor information"""
    id: int
    name: str
    username: str
    avatar: Optional[str] = None
    verified: bool = False
    timestamp: Optional[Any] = None


@dataclass
class NotificationContext:
    """Context information"""
    type: ContextType
    id: int
    name: str
    icon: Optional[str] = None
    avatar_url: Optional[str] = None


@dataclass
class NotificationResource:
    """Resource information"""
    type: ResourceType
    id: int
    url: Optional[str] = None
    title: Optional[str] = None
    image_url: Optional[str] = None
    content: Optional[str] = None


@dataclass
class NotificationMessage:
    """Message section - provides structured variables for Message Engine"""
    template: str
    state: MessageState
    variables: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NotificationComponents:
    """Components visibility - renderer obeys this exactly"""
    context_header: bool = False
    actor_stack: bool = True
    content: bool = True
    preview: bool = False
    metadata: bool = True
    action_bar: bool = False
    status: bool = False


@dataclass
class NotificationPreview:
    """Preview configuration"""
    enabled: bool = False
    type: PreviewType = PreviewType.NONE
    resource_id: Optional[int] = None


@dataclass
class NotificationMetadata:
    """Rendering metadata"""
    read: bool = False
    priority: str = "NORMAL"
    pinned: bool = False
    aggregated: bool = False


@dataclass
class NotificationAction:
    """Action configuration"""
    id: str
    label: str
    style: str  # primary, danger, success, etc.
    enabled: bool = True
    url: Optional[str] = None
    method: str = "GET"
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NavigationTarget:
    """Navigation target"""
    target: str  # POST_DETAIL, DOCUMENT_VIEWER, etc.
    resource_id: Optional[int] = None
    url: Optional[str] = None


@dataclass
class NotificationNavigation:
    """Navigation section"""
    primary: Optional[NavigationTarget] = None
    secondary: Optional[NavigationTarget] = None


@dataclass
class NotificationPermissions:
    """Permissions section"""
    can_expand: bool = True
    can_reply: bool = False
    can_dismiss: bool = True
    can_execute_actions: bool = True


@dataclass
class NotificationAnalytics:
    """Optional telemetry"""
    aggregation_count: int = 0
    view_count: int = 0
    interaction_count: int = 0


@dataclass
class NotificationTimestamps:
    """Timestamps section"""
    created_at: str
    updated_at: Optional[str] = None
    read_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class NotificationCapabilities:
    """Capabilities section"""
    expandable: bool = False
    aggregatable: bool = False
    actionable: bool = False
    previewable: bool = False
    navigable: bool = True
    dismissible: bool = True
    shareable: bool = False


@dataclass
class NotificationPayload:
    """
    Canonical notification payload structure
    Every notification SHALL conform to this structure
    """
    version: str
    identity: NotificationIdentity
    type: str
    intent: NotificationIntent
    lifecycle: NotificationLifecycle
    profile: NotificationProfile
    actors: List[NotificationActor]
    context: Optional[NotificationContext] = None
    resource: Optional[NotificationResource] = None
    message: Optional[NotificationMessage] = None
    components: NotificationComponents = field(default_factory=NotificationComponents)
    preview: NotificationPreview = field(default_factory=NotificationPreview)
    metadata: NotificationMetadata = field(default_factory=NotificationMetadata)
    actions: List[NotificationAction] = field(default_factory=list)
    navigation: NotificationNavigation = field(default_factory=NotificationNavigation)
    permissions: NotificationPermissions = field(default_factory=NotificationPermissions)
    analytics: Optional[NotificationAnalytics] = None
    timestamps: Optional[NotificationTimestamps] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)
    capabilities: NotificationCapabilities = field(default_factory=NotificationCapabilities)

    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style access for backwards compatibility with tests and callers."""
        if key == 'id':
            return self.identity.notification_id
        elif key == 'actor':
            return {
                'id': str(self.actors[0].id) if self.actors else None,
                'username': self.actors[0].username if self.actors else None,
                'name': self.actors[0].name if self.actors else None,
                'avatar': self.actors[0].avatar if self.actors else None,
            } if self.actors else None
        elif key == 'read':
            return self.metadata.read
        elif key == 'priority':
            return self.metadata.priority
        elif key == 'created_at':
            return self.timestamps.created_at if self.timestamps else None
        elif key == 'timestamps':
            return self.timestamps
        elif key == 'resource':
            return self.resource
        elif key == 'status':
            return self.lifecycle.state.value
        elif key == 'content':
            return self.message.variables.get('title', '') if self.message else ''
        elif key == 'rendering_hints':
            return {}
        d = self.to_dict()
        if key in d:
            return d[key]
        raise KeyError(key)

    def __contains__(self, key: str) -> bool:
        """Allow 'in' operator for dictionary-style compatibility."""
        if key in ('id', 'type', 'created_at', 'read', 'priority', 'actor', 'content', 'metadata', 'status', 'rendering_hints'):
            return True
        return key in self.to_dict()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'version': self.version,
            'identity': {
                'notification_id': self.identity.notification_id,
                'recipient_id': self.identity.recipient_id,
                'event_id': self.identity.event_id,
            },
            'type': self.type,
            'intent': self.intent.value,
            'lifecycle': {
                'state': self.lifecycle.state.value,
                'terminal': self.lifecycle.terminal,
            },
            'profile': {
                'id': self.profile.id,
                'version': self.profile.version,
            },
            'actors': [
                {
                    'id': actor.id,
                    'name': actor.name,
                    'username': actor.username,
                    'avatar': actor.avatar,
                    'verified': actor.verified,
                }
                for actor in self.actors
            ],
            'context': {
                'type': self.context.type.value,
                'id': self.context.id,
                'name': self.context.name,
                'icon': self.context.icon,
                'avatar_url': self.context.avatar_url,
            } if self.context else None,
            'resource': {
                'type': self.resource.type.value,
                'id': self.resource.id,
                'url': self.resource.url,
                'title': self.resource.title,
                'image_url': self.resource.image_url,
                'content': self.resource.content,
            } if self.resource else None,
            'message': {
                'template': self.message.template,
                'state': self.message.state.value,
                'variables': self.message.variables,
            } if self.message else None,
            'components': {
                'context_header': self.components.context_header,
                'actor_stack': self.components.actor_stack,
                'content': self.components.content,
                'preview': self.components.preview,
                'metadata': self.components.metadata,
                'action_bar': self.components.action_bar,
                'status': self.components.status,
            },
            'preview': {
                'enabled': self.preview.enabled,
                'type': self.preview.type.value,
                'resource_id': self.preview.resource_id,
            },
            'metadata': {
                'read': self.metadata.read,
                'priority': self.metadata.priority,
                'pinned': self.metadata.pinned,
                'aggregated': self.metadata.aggregated,
            },
            'actions': [
                {
                    'id': action.id,
                    'label': action.label,
                    'style': action.style,
                    'enabled': action.enabled,
                    'url': action.url,
                    'method': action.method,
                    'payload': action.payload,
                }
                for action in self.actions
            ],
            'navigation': {
                'primary': {
                    'target': self.navigation.primary.target,
                    'resource_id': self.navigation.primary.resource_id,
                    'url': self.navigation.primary.url,
                } if self.navigation.primary else None,
                'secondary': {
                    'target': self.navigation.secondary.target,
                    'resource_id': self.navigation.secondary.resource_id,
                    'url': self.navigation.secondary.url,
                } if self.navigation.secondary else None,
            },
            'permissions': {
                'can_expand': self.permissions.can_expand,
                'can_reply': self.permissions.can_reply,
                'can_dismiss': self.permissions.can_dismiss,
                'can_execute_actions': self.permissions.can_execute_actions,
            },
            'analytics': {
                'aggregation_count': self.analytics.aggregation_count,
                'view_count': self.analytics.view_count,
                'interaction_count': self.analytics.interaction_count,
            } if self.analytics else None,
            'timestamps': {
                'created_at': self.timestamps.created_at.isoformat() if self.timestamps.created_at else None,
                'updated_at': self.timestamps.updated_at.isoformat() if self.timestamps.updated_at else None,
                'read_at': self.timestamps.read_at.isoformat() if self.timestamps.read_at else None,
                'completed_at': self.timestamps.completed_at.isoformat() if self.timestamps.completed_at else None,
            } if self.timestamps else None,
            'raw_data': self.raw_data,
            'capabilities': {
                'expandable': self.capabilities.expandable,
                'aggregatable': self.capabilities.aggregatable,
                'actionable': self.capabilities.actionable,
                'previewable': self.capabilities.previewable,
                'navigable': self.capabilities.navigable,
                'dismissible': self.capabilities.dismissible,
                'shareable': self.capabilities.shareable,
            },
        }
