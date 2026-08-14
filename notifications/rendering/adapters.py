"""
Payload Adapter Layer
Normalizes notification payloads from NotificationObject
into the standardized payload contract defined in the Notification Engine Specification.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from django.utils import timezone
from django.contrib.auth import get_user_model
from .payload_models import (
    NotificationPayload, NotificationIdentity, NotificationLifecycle,
    NotificationProfile, NotificationActor, NotificationContext,
    NotificationResource, NotificationMessage, NotificationComponents,
    NotificationPreview, NotificationMetadata, NotificationAction as PayloadNotificationAction,
    NavigationTarget, NotificationNavigation, NotificationPermissions,
    NotificationAnalytics, NotificationTimestamps, NotificationCapabilities,
    NotificationIntent, LifecycleState, ContextType, ResourceType,
    PreviewType, MessageState
)

User = get_user_model()


class PayloadAdapter:
    """
    Base class for payload adapters.
    Converts notification data to the standardized payload format.
    """
    
    def to_standard_payload(self, notification: Any) -> Dict[str, Any]:
        """
        Convert notification to standard payload format.
        Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement to_standard_payload")


class NotificationObjectAdapter(PayloadAdapter):
    """
    Adapter for new NotificationObject model.
    Converts new notification objects to the standard payload format.
    """
    
    def to_standard_payload(self, notification) -> NotificationPayload:
        """
        Convert NotificationObject model to canonical NotificationPayload.
        
        Args:
            notification: NotificationObject model instance
            
        Returns:
            NotificationPayload instance conforming to canonical structure
        """
        # Resolve actors from source_events or metadata
        actors = self._resolve_actors(notification)
        actor_count = len(actors)
        
        # Resolve context from context_type/context_id
        context = self._resolve_context(notification)
        
        # Resolve resource from metadata
        resource = self._resolve_resource(notification)
        
        # Resolve actions from NotificationAction model (if exists)
        actions = self._resolve_actions(notification)
        
        # Determine intent based on notification type
        intent = self._determine_intent(notification.notification_type)
        
        # Determine lifecycle state
        lifecycle = self._determine_lifecycle(notification)
        
        # Determine message state based on actor count
        message_state = self._determine_message_state(notification, actor_count)
        
        # Build message
        message = self._build_message(notification, message_state)
        
        # Build components visibility
        components = self._build_components(notification)
        
        # Build preview
        preview = self._build_preview(notification, resource)
        
        # Build metadata
        metadata = NotificationMetadata(
            read=notification.status == 'READ',
            priority=notification.priority,
            pinned=notification.metadata.get('pinned', False),
            aggregated=notification.event_count > 1
        )
        
        # Build navigation
        navigation = self._build_navigation(notification, context, resource)
        
        # Build permissions
        permissions = self._build_permissions(notification)
        
        # Build capabilities
        capabilities = self._build_capabilities(notification, actions)
        
        # Build timestamps - keep as datetime objects for template filters
        timestamps = NotificationTimestamps(
            created_at=notification.created_at,
            updated_at=notification.updated_at,
            read_at=None,  # Could be tracked separately
            completed_at=None
        )
        
        # Build analytics if aggregated
        analytics = None
        if notification.event_count > 1:
            analytics = NotificationAnalytics(
                aggregation_count=notification.event_count,
                view_count=0,
                interaction_count=0
            )
        
        # Build identity
        identity = NotificationIdentity(
            notification_id=str(notification.notification_id),
            recipient_id=notification.recipient.id,
            event_id=notification.source_events[0] if notification.source_events else ''
        )
        
        # Build profile
        profile = NotificationProfile(
            id=notification.notification_type,
            version="1.0"
        )
        
        return NotificationPayload(
            version="1.0",
            identity=identity,
            type=notification.notification_type,
            intent=intent,
            lifecycle=lifecycle,
            profile=profile,
            actors=actors,
            context=context,
            resource=resource,
            message=message,
            components=components,
            preview=preview,
            metadata=metadata,
            actions=actions,
            navigation=navigation,
            permissions=permissions,
            analytics=analytics,
            timestamps=timestamps,
            raw_data=notification.metadata or {},  # Store original event metadata
            capabilities=capabilities
        )
    
    def _resolve_actors(self, notification) -> List[NotificationActor]:
        """Resolve actors from metadata or source_events as list of NotificationActor."""
        actors = []
        
        # System notifications use PwaniNet icon instead of user avatar
        is_system_notification = notification.notification_type in ['RELEASE', 'SYSTEM', 'MAINTENANCE', 'ACCOUNT_VERIFIED']
        system_avatar = '/static/images/favicon.svg'  # PwaniNet system icon
        
        # For aggregated notifications, get all actors from source events
        if notification.event_count and notification.event_count > 1:
            if notification.source_events:
                from notifications.models import PlatformEvent
                
                # Get all unique actors from source events with their timestamps
                actor_events = []
                for event_id in notification.source_events:
                    try:
                        event = PlatformEvent.objects.get(event_id=event_id)
                        if event.actor:
                            actor_id = event.actor.id
                            # Check if this actor is already in the list to avoid duplicates
                            if not any(a.id == actor_id for a in actors):
                                actors.append(NotificationActor(
                                    id=actor_id,
                                    name=event.actor.get_full_name() or event.actor.username,
                                    username=event.actor.username or '',
                                    avatar=system_avatar if is_system_notification else (event.actor.profile_pic.url if event.actor.profile_pic else None),
                                    verified=getattr(event.actor, 'is_verified', False),
                                    timestamp=event.timestamp
                                ))
                    except PlatformEvent.DoesNotExist:
                        pass
                
                # Sort actors by timestamp descending (most recent first)
                actors.sort(key=lambda a: a.timestamp if a.timestamp else timezone.now(), reverse=True)
            
            return actors
        
        # First check metadata for actor information
        if notification.metadata:
            actor_id = notification.metadata.get('actor_id')
            actor_username = notification.metadata.get('actor_username')
            
            if actor_id:
                try:
                    user = User.objects.get(id=actor_id)
                    # Try to get timestamp from notification metadata or use created_at
                    actor_timestamp = notification.metadata.get('actor_timestamp') or notification.created_at
                    actors.append(NotificationActor(
                        id=user.id,
                        name=user.get_full_name() or user.username,
                        username=user.username or '',
                        avatar=system_avatar if is_system_notification else (user.profile_pic.url if user.profile_pic else None),
                        verified=getattr(user, 'is_verified', False),
                        timestamp=actor_timestamp
                    ))
                    return actors
                except User.DoesNotExist:
                    # Return minimal actor info from metadata
                    actors.append(NotificationActor(
                        id=int(actor_id),
                        name=actor_username or 'Unknown',
                        username=actor_username or '',
                        avatar=system_avatar if is_system_notification else None,
                        verified=False,
                        timestamp=notification.created_at
                    ))
                    return actors
        
        # Fallback: try to resolve from source_events
        if notification.source_events:
            from notifications.models import PlatformEvent
            
            event_id = notification.source_events[0]
            try:
                event = PlatformEvent.objects.get(event_id=event_id)
                if event.actor:
                    actors.append(NotificationActor(
                        id=event.actor.id,
                        name=event.actor.get_full_name() or event.actor.username,
                        username=event.actor.username or '',
                        avatar=system_avatar if is_system_notification else (event.actor.profile_pic.url if event.actor.profile_pic else None),
                        verified=getattr(event.actor, 'is_verified', False),
                        timestamp=event.timestamp
                    ))
                    return actors
            except PlatformEvent.DoesNotExist:
                pass
        
        return actors
    
    def _resolve_context(self, notification) -> Optional[NotificationContext]:
        """Resolve context from context_type/context_id as NotificationContext."""
        if not notification.context_type or not notification.context_id:
            return None
        
        context_name = notification.context_id  # Fallback
        context_icon = self._get_context_icon(notification.context_type)
        
        # Resolve actual context name based on type
        context_avatar_url = None
        if notification.context_type == 'GROUP':
            from groups.models import Group
            try:
                group = Group.objects.get(id=notification.context_id)
                context_name = group.name
                context_icon = 'people'
                # Include group avatar if available
                if hasattr(group, 'group_pic') and group.group_pic:
                    context_avatar_url = group.group_pic.url
            except Group.DoesNotExist:
                pass
        elif notification.context_type == 'WORKSPACE':
            context_icon = 'grid-3x3'
        elif notification.context_type == 'COURSE':
            context_icon = 'book'
        elif notification.context_type == 'POST':
            context_icon = 'chat-text'
        elif notification.context_type == 'DOCUMENT':
            context_icon = 'file-earmark-text'
        
        # Map context_type to enum
        context_type_enum = None
        try:
            context_type_enum = ContextType[notification.context_type]
        except KeyError:
            # Default to SYSTEM if unknown
            context_type_enum = ContextType.SYSTEM
        
        return NotificationContext(
            type=context_type_enum,
            id=int(notification.context_id),
            name=context_name,
            icon=context_icon,
            avatar_url=context_avatar_url
        )
    
    def _resolve_resource(self, notification) -> Optional[NotificationResource]:
        """Resolve resource from metadata or related models as NotificationResource."""
        # First check metadata for thumbnail_url (priority for notification previews)
        thumbnail_url = notification.metadata.get('thumbnail_url')
        resource_type_str = notification.metadata.get('resource_type')
        
        # First check metadata
        resource_data = notification.metadata.get('resource')
        if resource_data:
            resource_type_enum = None
            try:
                resource_type_enum = ResourceType[resource_data.get('type', 'SYSTEM')]
            except KeyError:
                resource_type_enum = ResourceType.SYSTEM
            
            return NotificationResource(
                type=resource_type_enum,
                id=int(resource_data.get('id', 0)),
                url=resource_data.get('url'),
                title=resource_data.get('title'),
                image_url=thumbnail_url or resource_data.get('image_url')
            )
        
        # Try to resolve from target_type and target_id in metadata
        target_type = notification.metadata.get('target_type')
        target_id = notification.metadata.get('target_id')
        
        if target_type == 'Post' and target_id:
            from posts.models import Post
            try:
                post = Post.objects.get(id=target_id)
                # Use thumbnail_url from metadata if available, otherwise get from post
                image_url = thumbnail_url
                if not image_url:
                    image_url = self._get_post_image_url(post)
                
                return NotificationResource(
                    type=ResourceType.POST,
                    id=post.id,
                    url=f'/post/{post.id}',
                    title=post.content[:100] if post.content else 'Post',
                    image_url=image_url
                )
            except Post.DoesNotExist:
                pass
        
        # Fallback: try to resolve from context if it's a post
        if notification.context_type == 'POST' and notification.context_id:
            from posts.models import Post
            try:
                post = Post.objects.get(id=notification.context_id)
                # Use thumbnail_url from metadata if available, otherwise get from post
                image_url = thumbnail_url
                if not image_url:
                    image_url = self._get_post_image_url(post)
                
                # For comment notifications, link to the specific comment
                if notification.notification_type in ['COMMENT', 'COMMENT_REPLY', 'COMMENT_LIKE']:
                    # Try to get target_id from metadata (for COMMENT and COMMENT_LIKE)
                    # or from the notification's target_id field (for COMMENT_REPLY)
                    target_id = notification.metadata.get('target_id') or notification.metadata.get('comment_id')
                    
                    # For COMMENT_REPLY, the target_id might be stored differently
                    if not target_id and notification.notification_type == 'COMMENT_REPLY':
                        target_id = notification.metadata.get('parent_comment_id')
                    
                    if target_id:
                        url = f'/post/{post.id}/#comment-{target_id}'
                    else:
                        url = f'/post/{post.id}'
                    # Get comment content for display
                    comment_content = notification.metadata.get('comment_content', '')
                else:
                    url = f'/post/{post.id}'
                    comment_content = None
                
                return NotificationResource(
                    type=ResourceType.POST,
                    id=post.id,
                    url=url,
                    title=post.content[:100] if post.content else 'Post',
                    image_url=image_url,
                    content=comment_content
                )
            except Post.DoesNotExist:
                pass
        
        # Fallback: try to resolve from context if it's a document
        if notification.context_type == 'DOCUMENT' and notification.context_id:
            from documents.models import Document
            try:
                document = Document.objects.get(id=notification.context_id)
                return NotificationResource(
                    type=ResourceType.DOCUMENT,
                    id=document.id,
                    url=f'/documents/{document.id}',
                    title=document.title,
                    image_url=thumbnail_url
                )
            except Document.DoesNotExist:
                pass
        
        return None
    
    def _get_post_image_url(self, post) -> Optional[str]:
        """Get image URL from post based on content type."""
        # Priority 1: Post images
        if post.images.exists():
            return post.images.first().get_thumbnail_url('400') if hasattr(post.images.first(), 'get_thumbnail_url') else post.images.first().image.url
        
        # Priority 2: Video poster
        elif post.video_poster:
            return post.video_poster.url
        
        # Priority 3: Shared document preview
        elif post.shared_document and post.shared_document.latest_version:
            first_file = post.shared_document.latest_version.files.first()
            if first_file and first_file.preview_path:
                return f"/media/{first_file.preview_path}"
            elif first_file and first_file.thumbnail_path:
                return f"/media/{first_file.thumbnail_path}"
        
        # Priority 4: Post thumbnail (for gradient/text posts)
        elif post.thumbnail:
            return post.thumbnail.url
        
        return None
    
    def _resolve_actions(self, notification) -> List[PayloadNotificationAction]:
        """Resolve actions from NotificationAction model or profile strategy as list of PayloadNotificationAction."""
        actions = []
        
        # First, check if there are actions in the NotificationAction model
        from notifications.models import NotificationAction as ModelNotificationAction
        notification_actions = ModelNotificationAction.objects.filter(notification=notification)
        
        if notification_actions.exists():
            # Deduplicate actions by label to prevent duplicates from multiple actors
            seen_labels = set()
            for idx, action in enumerate(notification_actions):
                if action.label not in seen_labels:
                    # Fix old URL format for VIEW_POST actions
                    url = action.url
                    if action.action_type == 'VIEW_POST' and url and url.startswith('/posts/'):
                        url = url.replace('/posts/', '/post/')
                    
                    actions.append(PayloadNotificationAction(
                        id=action.action_type,  # Use action_type instead of database ID
                        label=action.label,
                        style='primary' if action.is_primary else 'secondary',
                        enabled=True,
                        url=url,
                        method=action.method or 'GET',
                        payload={}
                    ))
                    seen_labels.add(action.label)
            return actions
        
        # Use profile registry to determine available actions
        from .profile_registry import profile_registry
        profile = profile_registry.get_profile(notification.notification_type)
        action_strategy = profile.action_strategy
        
        if not action_strategy or not action_strategy.available_actions:
            return []
        
        # Check if this is an aggregated notification (multiple actors)
        is_aggregated = notification.event_count and notification.event_count > 1
        
        # For FOLLOW notifications, check if user already follows the actor
        if notification.notification_type == 'FOLLOW' and not is_aggregated:
            actor_id = notification.metadata.get('actor_id')
            if actor_id:
                # Check if recipient already follows the actor using the Follow model
                from users.models import Follow
                is_following = Follow.objects.filter(
                    follower=notification.recipient,
                    followed_id=actor_id
                ).exists()
                if is_following:
                    # Replace FOLLOW_BACK with PINCH
                    action_strategy.available_actions = ['PINCH', 'VIEW_PROFILE']
                else:
                    # Ensure FOLLOW_BACK is in available actions
                    action_strategy.available_actions = ['FOLLOW_BACK', 'VIEW_PROFILE']
        
        # Build actions based on profile's available_actions
        seen_action_ids = set()
        for action_id in action_strategy.available_actions:
            # Skip FOLLOW_BACK for aggregated notifications
            if is_aggregated and action_id == 'FOLLOW_BACK':
                continue
            
            # For aggregated notifications, only show one instance of each action type
            if is_aggregated and action_id in seen_action_ids:
                continue
            
            action = self._build_action_from_id(action_id, notification)
            if action:
                actions.append(action)
                seen_action_ids.add(action_id)
        
        return actions
    
    def _build_action_from_id(self, action_id: str, notification) -> Optional[PayloadNotificationAction]:
        """Build a single action from action ID using notification context."""
        # Map action IDs to their configurations
        action_configs = {
            'ACCEPT': {
                'label': 'Accept',
                'style': 'primary',
                'url_builder': lambda n: f'/groups/{n.context_id}/accept-invite/' if n.context_type == 'GROUP' and n.context_id else None,
                'method': 'POST'
            },
            'DECLINE': {
                'label': 'Decline',
                'style': 'danger',
                'url_builder': lambda n: f'/groups/{n.context_id}/decline-invite/' if n.context_type == 'GROUP' and n.context_id else None,
                'method': 'POST'
            },
            'APPROVE': {
                'label': 'Approve',
                'style': 'primary',
                'url_builder': lambda n: f'/groups/{n.context_id}/approve-from-notification/{n.metadata.get("actor_id")}/' if n.context_type == 'GROUP' and n.context_id and n.metadata.get('actor_id') else None,
                'method': 'POST'
            },
            'REJECT': {
                'label': 'Reject',
                'style': 'danger',
                'url_builder': lambda n: f'/groups/{n.context_id}/reject-from-notification/{n.metadata.get("actor_id")}/' if n.context_type == 'GROUP' and n.context_id and n.metadata.get('actor_id') else None,
                'method': 'POST'
            },
            'VIEW_POST': {
                'label': 'View Post',
                'style': 'primary',
                'url_builder': lambda n: f'/post/{n.context_id}/' if n.context_type == 'POST' and n.context_id else None,
                'method': 'GET'
            },
            'VIEW_COMMENT': {
                'label': 'View Comment',
                'style': 'primary',
                'url_builder': lambda n: f'/post/{n.context_id}/#comment-{n.metadata.get("target_id")}' if n.context_type == 'POST' and n.context_id and n.metadata.get('target_id') else None,
                'method': 'GET'
            },
            'VIEW_ASSIGNMENT': {
                'label': 'View Assignment',
                'style': 'primary',
                'url_builder': lambda n: f'/assignments/{n.context_id}' if n.context_type == 'ASSIGNMENT' and n.context_id else None,
                'method': 'GET'
            },
            'VIEW_GROUP': {
                'label': 'View Group',
                'style': 'secondary',
                'url_builder': lambda n: f'/groups/{n.context_id}' if n.context_type == 'GROUP' and n.context_id else None,
                'method': 'GET'
            },
            'FOLLOW_BACK': {
                'label': 'Follow Back',
                'style': 'primary',
                'url_builder': lambda n: f'/users/{n.metadata.get("actor_id")}/follow/' if n.metadata.get('actor_id') else None,
                'method': 'POST'
            },
            'VIEW_PROFILE': {
                'label': 'View Profile',
                'style': 'secondary',
                'url_builder': lambda n: f'/users/{n.metadata.get("actor_username")}/' if n.metadata.get('actor_username') else None,
                'method': 'GET'
            },
            'PINCH': {
                'label': 'Pinch',
                'style': 'secondary',
                'url_builder': lambda n: f'/users/{n.metadata.get("actor_id")}/pinch/' if n.metadata.get('actor_id') else None,
                'method': 'POST'
            },
            'SEE_WHATS_NEW': {
                'label': "See What's New",
                'style': 'primary',
                'url_builder': lambda n: f'/system/releases/{n.metadata.get("target_id")}/' if n.metadata.get('target_id') else None,
                'method': 'GET',
                'data_attrs': {'data-release-id': lambda n: n.metadata.get('target_id')}
            },
        }
        
        config = action_configs.get(action_id)
        if not config:
            return None
        
        url = config['url_builder'](notification)
        if not url:
            return None
        
        return PayloadNotificationAction(
            id=action_id,
            label=config['label'],
            style=config['style'],
            enabled=True,
            url=url,
            method=config['method'],
            payload={}
        )
    
    def _determine_intent(self, notification_type: str) -> NotificationIntent:
        """Determine notification intent based on type."""
        intent_map = {
            'LIKE': NotificationIntent.ACTIVITY,
            'COMMENT': NotificationIntent.ACTIVITY,
            'FOLLOW': NotificationIntent.ACTIVITY,
            'INVITE': NotificationIntent.WORKFLOW,
            'GROUP_REQUEST': NotificationIntent.WORKFLOW,
            'GROUP': NotificationIntent.WORKFLOW,
            'ASSIGNMENT': NotificationIntent.AWARENESS,
            'DOCUMENT': NotificationIntent.ACTIVITY,
            'SECURITY': NotificationIntent.ALERT,
            'SYSTEM': NotificationIntent.ANNOUNCEMENT
        }
        return intent_map.get(notification_type, NotificationIntent.AWARENESS)
    
    def _determine_lifecycle(self, notification) -> NotificationLifecycle:
        """Determine lifecycle state based on notification status."""
        state_map = {
            'CREATED': LifecycleState.LIVE,
            'DELIVERED': LifecycleState.LIVE,
            'READ': LifecycleState.HISTORICAL,
            'ARCHIVED': LifecycleState.HISTORICAL,
            'PENDING': LifecycleState.PENDING,
            'FAILED': LifecycleState.EXPIRED
        }
        state = state_map.get(notification.status, LifecycleState.LIVE)
        return NotificationLifecycle(
            state=state,
            terminal=notification.status in ['READ', 'ARCHIVED', 'FAILED']
        )
    
    def _determine_message_state(self, notification, actor_count: int) -> MessageState:
        """Determine message state based on actor count."""
        if actor_count == 1:
            return MessageState.SINGLE
        elif actor_count == 2:
            return MessageState.DUAL
        elif actor_count <= 5:
            return MessageState.FEW
        else:
            return MessageState.MANY
    
    def _build_message(self, notification, message_state: MessageState) -> Optional[NotificationMessage]:
        """Build notification message using profile registry."""
        from .profile_registry import profile_registry
        
        # Get the profile for this notification type
        profile = profile_registry.get_profile(notification.notification_type)
        
        # Use the profile's message strategy configuration
        message_strategy = profile.message_strategy
        
        variables = {
            'actor_username': notification.metadata.get('actor_username', 'Someone'),
            'group_name': notification.metadata.get('group_name', ''),
            'title': notification.title,
            'summary': notification.summary
        }
        return NotificationMessage(
            template=message_strategy.template,
            state=message_state,
            variables=variables
        )
    
    def _build_components(self, notification) -> NotificationComponents:
        """Build component visibility configuration using profile registry."""
        from .profile_registry import profile_registry
        
        # Get the profile for this notification type
        profile = profile_registry.get_profile(notification.notification_type)
        
        # Use the profile's component visibility configuration
        visibility_config = profile.component_visibility
        
        return NotificationComponents(
            context_header=visibility_config.context_header,
            actor_stack=visibility_config.actor_stack,
            content=visibility_config.content,
            preview=visibility_config.preview,
            metadata=visibility_config.metadata,
            action_bar=visibility_config.action_bar,
            status=visibility_config.status
        )
    
    def _build_preview(self, notification, resource: Optional[NotificationResource]) -> NotificationPreview:
        """Build preview configuration using profile registry."""
        from .profile_registry import profile_registry
        
        # Get the profile for this notification type
        profile = profile_registry.get_profile(notification.notification_type)
        
        # Use the profile's preview strategy configuration
        preview_strategy = profile.preview_strategy
        
        # Map preview_type string to PreviewType enum
        preview_type_enum = PreviewType.NONE
        if preview_strategy.preview_type == "POST":
            preview_type_enum = PreviewType.POST
        elif preview_strategy.preview_type == "DOCUMENT":
            preview_type_enum = PreviewType.DOCUMENT
        elif preview_strategy.preview_type == "GROUP":
            preview_type_enum = PreviewType.GROUP
        
        return NotificationPreview(
            enabled=preview_strategy.enabled,
            type=preview_type_enum,
            resource_id=resource.id if resource else None
        )
    
    def _build_navigation(self, notification, context: Optional[NotificationContext], resource: Optional[NotificationResource]) -> NotificationNavigation:
        """Build navigation configuration using profile registry."""
        from .profile_registry import profile_registry
        
        # Get the profile for this notification type
        profile = profile_registry.get_profile(notification.notification_type)
        
        # Use the profile's navigation strategy configuration
        nav_strategy = profile.navigation_strategy
        
        primary = None
        if nav_strategy and nav_strategy.primary:
            # Extract resource ID from the field specified in the profile
            resource_id = self._extract_resource_id_from_payload(nav_strategy.primary.resource_id_field, notification, context, resource)
            
            primary = NavigationTarget(
                target=nav_strategy.primary.target,
                resource_id=resource_id,
                url=resource.url if resource else None
            )
        
        secondary = None
        if nav_strategy and nav_strategy.secondary:
            resource_id = self._extract_resource_id_from_payload(nav_strategy.secondary.resource_id_field, notification, context, resource)
            secondary = NavigationTarget(
                target=nav_strategy.secondary.target,
                resource_id=resource_id,
                url=None
            )
        
        return NotificationNavigation(primary=primary, secondary=secondary)
    
    def _extract_resource_id_from_payload(self, field_path: Optional[str], notification, context: Optional[NotificationContext], resource: Optional[NotificationResource]) -> Optional[int]:
        """Extract resource ID from notification data using field path."""
        if not field_path:
            return None
        
        # Handle dot notation paths like 'resource.id', 'actors.0.id', 'context.id'
        parts = field_path.split('.')
        
        # Start with available data
        if parts[0] == 'resource' and resource:
            value = resource.id
        elif parts[0] == 'context' and context:
            value = context.id
        elif parts[0] == 'actors' and notification.metadata:
            # Try to get actor_id from metadata
            actor_id = notification.metadata.get('actor_id')
            if actor_id:
                value = int(actor_id)
            else:
                return None
        else:
            return None
        
        # Handle nested paths (e.g., 'actors.0.id')
        if len(parts) > 1:
            for part in parts[1:]:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                elif isinstance(value, list) and part.isdigit():
                    index = int(part)
                    if index < len(value):
                        value = value[index]
                    else:
                        return None
                else:
                    return None
        
        return value if isinstance(value, int) else None
    
    def _build_permissions(self, notification) -> NotificationPermissions:
        """Build permissions configuration."""
        return NotificationPermissions(
            can_expand=True,
            can_reply=notification.notification_type in ['COMMENT', 'MESSAGE'],
            can_dismiss=True,
            can_execute_actions=True
        )
    
    def _build_capabilities(self, notification, actions: List[PayloadNotificationAction]) -> NotificationCapabilities:
        """Build capabilities configuration using profile registry."""
        from .profile_registry import profile_registry
        
        # Get the profile for this notification type
        profile = profile_registry.get_profile(notification.notification_type)
        
        # Use the profile's aggregation and expansion strategies
        agg_strategy = profile.aggregation_strategy
        exp_strategy = profile.expansion_strategy
        
        return NotificationCapabilities(
            expandable=exp_strategy.expandable if exp_strategy else True,
            aggregatable=agg_strategy.enabled if agg_strategy else notification.event_count > 1,
            actionable=len(actions) > 0,
            previewable=profile.component_visibility.preview,
            navigable=bool(profile.navigation_strategy and profile.navigation_strategy.primary),
            dismissible=True,
            shareable=False
        )
    
    def _get_action_icon(self, action_type: str) -> str:
        """Get icon for action type."""
        icon_map = {
            'ACCEPT': 'check-lg',
            'DECLINE': 'x-lg',
            'APPROVE': 'check-lg',
            'REJECT': 'x-lg',
            'FOLLOW': 'person-plus',
            'UNFOLLOW': 'person-dash',
            'VIEW': 'eye',
            'OPEN': 'box-arrow-up-right',
            'REPLY': 'reply',
            'LIKE': 'heart',
            'BOOKMARK': 'bookmark',
            'DOWNLOAD': 'download',
            'DELETE': 'trash',
            'ARCHIVE': 'archive',
            'MARK_READ': 'check2',
            'MARK_UNREAD': 'envelope'
        }
        return icon_map.get(action_type, 'arrow-right')
    
    def _get_context_icon(self, context_type: str) -> str:
        """Get icon for context type."""
        icon_map = {
            'GROUP': 'people',
            'WORKSPACE': 'grid-3x3',
            'COURSE': 'book',
            'ASSIGNMENT': 'clipboard-check',
            'MEETING': 'calendar-check',
            'PROFILE': 'person'
        }
        return icon_map.get(context_type, 'folder')
    
    def _get_resource_icon(self, resource_type: str) -> str:
        """Get icon for resource type."""
        icon_map = {
            'POST': 'chat-text',
            'DOCUMENT': 'file-earmark-text',
            'PDF': 'file-earmark-pdf',
            'DOCX': 'file-earmark-word',
            'DOC': 'file-earmark-word',
            'IMAGE': 'file-earmark-image',
            'VIDEO': 'file-earmark-play',
            'ASSIGNMENT': 'clipboard-check',
            'MEETING': 'calendar-check',
            'TASK': 'check2-square',
            'COMMENT': 'chat-dots'
        }
        return icon_map.get(resource_type.upper(), 'file-earmark')


def get_payload_adapter(notification) -> PayloadAdapter:
    """
    Factory function to get the appropriate adapter for a notification.
    
    Args:
        notification: NotificationObject instance
        
    Returns:
        NotificationObjectAdapter instance
    """
    from notifications.models import NotificationObject
    
    if isinstance(notification, NotificationObject):
        return NotificationObjectAdapter()
    else:
        raise ValueError(f"Unknown notification type: {type(notification)}")
