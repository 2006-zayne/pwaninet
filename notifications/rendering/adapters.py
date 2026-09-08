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


def _post_share_id(post_pk):
    """Return the UUID share_id for a post given its integer PK, or None on failure."""
    if not post_pk:
        return None
    try:
        from posts.models import Post
        return Post.objects.values_list('share_id', flat=True).get(pk=post_pk)
    except Exception:
        return None


def _get_post_safely(val):
    """Safely fetch a Post by either integer PK or UUID share_id without throwing ValueError or DB error."""
    if not val:
        return None
    from posts.models import Post
    import uuid
    # Try as UUID
    try:
        u = uuid.UUID(str(val))
        p = Post.objects.filter(share_id=u).first()
        if p:
            return p
    except Exception:
        pass
    # Try as integer PK
    try:
        p = Post.objects.filter(id=int(val)).first()
        if p:
            return p
    except Exception:
        pass
    return None


def _clean_media_url(url: Optional[str]) -> Optional[str]:
    """Clean and normalize a media URL so it is guaranteed to be a valid absolute or relative URL."""
    if not url:
        return None
    url_str = str(url).strip()
    if not url_str or url_str in ('None', 'null', 'undefined'):
        return None
    # Fully qualified or data URI
    if url_str.startswith(('http://', 'https://', 'data:', '//')):
        return url_str
    # Normalize path
    clean = url_str.lstrip('/')
    from django.conf import settings
    media_url = getattr(settings, 'MEDIA_URL', '/media/')
    path = clean
    if path.startswith('media/'):
        path = path[6:]
    elif path.startswith('static/'):
        return f'/{clean}'
    if media_url and media_url.startswith(('http://', 'https://', '//')):
        return f'{media_url.rstrip("/")}/{path.lstrip("/")}'
    return f'/media/{path.lstrip("/")}'


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
        components = self._build_components(notification, resource)
        
        # Build preview
        preview = self._build_preview(notification, resource)
        
        # Build metadata
        metadata = NotificationMetadata(
            read=notification.status == 'READ',
            priority=notification.priority,
            pinned=(notification.metadata or {}).get('pinned', False),
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
        is_system_notification = notification.notification_type in ['SYSTEM', 'MAINTENANCE', 'ACCOUNT_VERIFIED']
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
                                full_name = (event.actor.get_full_name() or '').strip()
                                actor_name = full_name if full_name and full_name != 'None None' else event.actor.username
                                actors.append(NotificationActor(
                                    id=actor_id,
                                    name=actor_name,
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
                    full_name = (user.get_full_name() or '').strip()
                    actor_name = full_name if full_name and full_name != 'None None' else user.username
                    actors.append(NotificationActor(
                        id=user.id,
                        name=actor_name,
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
            except (Group.DoesNotExist, ValueError):
                if notification.metadata and notification.metadata.get('group_name'):
                    context_name = notification.metadata.get('group_name')
            if str(context_name).isdigit() and notification.metadata and notification.metadata.get('group_name'):
                context_name = notification.metadata.get('group_name')
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
        metadata = notification.metadata or {}
        thumbnail_url = _clean_media_url(metadata.get('thumbnail_url'))
        
        # 1. Check if resource is directly specified in metadata
        resource_data = metadata.get('resource')
        if resource_data and isinstance(resource_data, dict):
            resource_type_enum = None
            try:
                resource_type_enum = ResourceType[resource_data.get('type', 'SYSTEM')]
            except KeyError:
                resource_type_enum = ResourceType.SYSTEM
            
            # Fix old integer-ID post URLs in stored resource data
            resource_url = resource_data.get('url')
            if resource_url:
                import re
                m = re.match(r'^/post/(\d+)(/.*)?$', resource_url)
                if m:
                    sid = _post_share_id(int(m.group(1)))
                    if sid:
                        resource_url = f'/post/{sid}/{m.group(2) or ""}'.replace('//', '/')
            
            image_url = thumbnail_url or _clean_media_url(resource_data.get('image_url'))
            if not image_url:
                post = _get_post_safely(resource_data.get('id') or metadata.get('target_id') or notification.context_id)
                if post:
                    image_url = self._get_post_image_url(post)
            
            return NotificationResource(
                type=resource_type_enum,
                id=int(resource_data.get('id', 0)),
                url=resource_url,
                title=resource_data.get('title'),
                image_url=image_url
            )
        
        # Resolve post robustly from metadata, context, aggregation_key, or source_events
        target_type = str(metadata.get('target_type') or '').upper()
        target_id = metadata.get('target_id') or metadata.get('post_id')
        context_type = str(notification.context_type or '').upper()
        context_id = notification.context_id
        
        # Check aggregation_key for target info (format: <notification_type>:<target_type>:<target_id>)
        if not target_id and notification.aggregation_key:
            parts = str(notification.aggregation_key).split(':')
            if len(parts) >= 3:
                agg_type = parts[1].upper()
                if agg_type in ['POST', 'POSTS']:
                    target_type = 'POST'
                    target_id = parts[2]
                elif agg_type == 'COMMENT':
                    target_type = 'COMMENT'
                    target_id = parts[2]
        
        # Check source_events if target_id or thumbnail_url is still missing
        if (not target_id or not thumbnail_url) and notification.source_events:
            try:
                from notifications.models import PlatformEvent
                event = PlatformEvent.objects.filter(event_id__in=notification.source_events).first()
                if event:
                    if not target_id and event.target_id:
                        target_id = event.target_id
                        target_type = str(event.target_type or '').upper()
                    if not thumbnail_url and event.metadata:
                        thumbnail_url = _clean_media_url(event.metadata.get('thumbnail_url'))
            except Exception:
                pass
        
        post = None
        if target_type in ['POST', 'POSTS'] and target_id:
            post = _get_post_safely(target_id)
        if not post and context_type in ['POST', 'POSTS'] and context_id:
            post = _get_post_safely(context_id)
        if not post and notification.notification_type in [
            'LIKE', 'POST_LIKE', 'POST_COMMENT', 'COMMENT', 'COMMENT_REPLY',
            'COMMENT_LIKE', 'SHARE', 'POST_SHARE', 'POST_SHARED', 'POST_REPOSTED',
            'POST_CREATED', 'DOCUMENT_SHARED', 'POST_DOCUMENT_SHARED'
        ]:
            post = _get_post_safely(target_id) or _get_post_safely(context_id)
        
        # Resolve comment to parent post
        if not post and (target_type == 'COMMENT' or notification.notification_type in ['COMMENT', 'COMMENT_REPLY', 'COMMENT_LIKE']):
            comment_pk = target_id or metadata.get('comment_id') or metadata.get('parent_comment_id')
            if comment_pk:
                try:
                    from posts.models import Comment
                    c = Comment.objects.filter(id=int(comment_pk)).select_related('post').first()
                    if c:
                        post = c.post
                except Exception:
                    pass
        
        if post:
            image_url = self._get_post_image_url(post) or thumbnail_url
            comment_content = None
            
            # For comment notifications, link to the specific comment
            if notification.notification_type in ['COMMENT', 'COMMENT_REPLY', 'COMMENT_LIKE', 'POST_COMMENT', 'POST_COMMENT_REPLY', 'POST_COMMENTED', 'DOCUMENT_COMMENT']:
                cid = metadata.get('target_id') or metadata.get('comment_id')
                if not cid and notification.notification_type in ['COMMENT_REPLY', 'POST_COMMENT_REPLY']:
                    cid = metadata.get('parent_comment_id')
                if cid:
                    url = f'/post/{post.share_id}/#comment-{cid}'
                else:
                    url = f'/post/{post.share_id}/'
                comment_content = metadata.get('comment_content', '')
                if not comment_content and cid:
                    try:
                        from posts.models import Comment
                        c_obj = Comment.objects.filter(id=int(cid)).first()
                        if c_obj and c_obj.content:
                            comment_content = c_obj.content
                    except Exception:
                        pass
            elif notification.notification_type in ['DOCUMENT_SHARED', 'POST_DOCUMENT_SHARED'] or metadata.get('is_document_share'):
                doc = getattr(post, 'shared_document', None)
                doc_id = getattr(doc, 'id', None) or metadata.get('shared_document_id') or metadata.get('document_id')
                doc_share_id = getattr(doc, 'share_id', None)
                doc_title = (doc.title if doc else None) or metadata.get('document_title') or 'Document'
                if not doc_share_id and doc_id:
                    try:
                        from documents.models import Document
                        d_obj = Document.objects.filter(id=int(doc_id)).first()
                        if d_obj:
                            doc_share_id = d_obj.share_id
                            doc_title = d_obj.title
                    except Exception:
                        pass
                
                doc_url = f'/documents/document/{doc_share_id}/' if doc_share_id else f'/post/{post.share_id}/'
                return NotificationResource(
                    type=ResourceType.DOCUMENT,
                    id=doc_id or post.id,
                    url=doc_url,
                    title=doc_title,
                    image_url=image_url or _clean_media_url(thumbnail_url),
                    content=comment_content
                )
            else:
                url = f'/post/{post.share_id}/'
            
            return NotificationResource(
                type=ResourceType.POST,
                id=post.id,
                url=url,
                title=post.content[:100] if post.content else 'Post',
                image_url=image_url,
                content=comment_content
            )
        
        # Fallback 1: try to resolve from context, target, or metadata if it's a document
        doc_id = None
        if context_type == 'DOCUMENT' and context_id:
            doc_id = context_id
        elif target_type == 'DOCUMENT' and target_id:
            doc_id = target_id
        elif notification.notification_type in ['DOCUMENT_SHARED', 'POST_DOCUMENT_SHARED']:
            doc_id = metadata.get('shared_document_id') or metadata.get('document_id')
        
        if doc_id:
            from documents.models import Document
            try:
                document = Document.objects.get(id=int(doc_id))
                doc_thumb = None
                if hasattr(document, 'latest_version') and document.latest_version:
                    first_file = document.latest_version.files.first()
                    if first_file:
                        doc_thumb = first_file.thumbnail_path or first_file.preview_path
                if not doc_thumb and hasattr(document, 'thumbnail') and document.thumbnail:
                    doc_thumb = document.thumbnail.url
                return NotificationResource(
                    type=ResourceType.DOCUMENT,
                    id=document.id,
                    url=f'/documents/document/{document.share_id}/' if document.share_id else f'/documents/{document.id}',
                    title=document.title,
                    image_url=_clean_media_url(doc_thumb) or _clean_media_url(thumbnail_url)
                )
            except (Document.DoesNotExist, ValueError):
                pass

        # Fallback 2: If post lookup failed or post was deleted, BUT thumbnail_url exists, STILL return NotificationResource
        if thumbnail_url:
            target_url = '#'
            res_id = 0
            if target_id:
                sid = _post_share_id(target_id) or target_id
                target_url = f'/post/{sid}/'
                if str(target_id).isdigit():
                    res_id = int(target_id)
            elif context_id and context_type in ['POST', 'POSTS']:
                sid = _post_share_id(context_id) or context_id
                target_url = f'/post/{sid}/'
                if str(context_id).isdigit():
                    res_id = int(context_id)
            
            return NotificationResource(
                type=ResourceType.POST,
                id=res_id,
                url=target_url,
                title=metadata.get('post_content', 'Post') or 'Post',
                image_url=_clean_media_url(thumbnail_url)
            )
        
        return None
    
    def _get_post_image_url(self, post) -> Optional[str]:
        """Get image URL from post based on content type."""
        try:
            # Priority 1: Post images
            if post.images.exists():
                first_img = post.images.first()
                if first_img:
                    if hasattr(first_img, 'get_thumbnail_url'):
                        url = first_img.get_thumbnail_url('400')
                        if url:
                            return _clean_media_url(url)
                    if hasattr(first_img, 'image') and first_img.image:
                        return _clean_media_url(first_img.image.url)
            
            # Priority 2: Video poster
            if post.video_poster:
                return _clean_media_url(post.video_poster.url)
            elif hasattr(post, 'get_video_poster') and post.get_video_poster:
                return _clean_media_url(post.get_video_poster)
            
            # Priority 3: Shared document preview
            if post.shared_document:
                doc = post.shared_document
                if hasattr(doc, 'latest_version') and doc.latest_version:
                    first_file = doc.latest_version.files.first()
                    if first_file:
                        thumb = first_file.thumbnail_path or first_file.preview_path
                        if thumb:
                            return _clean_media_url(thumb)
                if hasattr(doc, 'thumbnail') and doc.thumbnail:
                    return _clean_media_url(doc.thumbnail.url)
            
            # Priority 4: Post thumbnail (for gradient/text posts)
            if post.thumbnail:
                return _clean_media_url(post.thumbnail.url)
            
            # Priority 5: If this is a repost, check original post
            if getattr(post, 'repost_of', None):
                repost_img = self._get_post_image_url(post.repost_of)
                if repost_img:
                    return repost_img
            
            # Priority 6: Fallback to get_intel_file if it's an image
            if hasattr(post, 'get_intel_file') and post.get_intel_file:
                try:
                    intel = post.get_intel_file
                    if hasattr(intel, 'url') and intel.url:
                        f_url = intel.url.lower()
                        if any(f_url.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                            return _clean_media_url(intel.url)
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Error resolving post image URL: {e}")
        
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
                    
                    # Fix old integer-ID post URLs → UUID share_id
                    if url:
                        import re
                        m = re.match(r'^/post/(\d+)(/.*)?$', url)
                        if m:
                            share_id = _post_share_id(int(m.group(1)))
                            if share_id:
                                url = f'/post/{share_id}/{m.group(2) or ""}'.replace('//', '/')
                    
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
            actor_id = (notification.metadata or {}).get('actor_id')
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
            # Skip FOLLOW_BACK and PINCH for aggregated notifications
            if is_aggregated and action_id in ('FOLLOW_BACK', 'PINCH'):
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
                'url_builder': lambda n: f'/groups/invite/respond/{getattr(n, "notification_id", getattr(n, "id", None))}/accept/' if getattr(n, "notification_id", getattr(n, "id", None)) else None,
                'method': 'POST'
            },
            'DECLINE': {
                'label': 'Decline',
                'style': 'danger',
                'url_builder': lambda n: f'/groups/invite/respond/{getattr(n, "notification_id", getattr(n, "id", None))}/decline/' if getattr(n, "notification_id", getattr(n, "id", None)) else None,
                'method': 'POST'
            },
            'APPROVE': {
                'label': 'Approve',
                'style': 'primary',
                'url_builder': lambda n: f'/groups/{n.context_id}/approve/{(n.metadata or {}).get("user_id")}/' if n.context_type == 'GROUP' and n.context_id and (n.metadata or {}).get('user_id') else None,
                'method': 'POST'
            },
            'REJECT': {
                'label': 'Reject',
                'style': 'danger',
                'url_builder': lambda n: f'/groups/{n.context_id}/reject/{(n.metadata or {}).get("user_id")}/' if n.context_type == 'GROUP' and n.context_id and (n.metadata or {}).get('user_id') else None,
                'method': 'POST'
            },
            'VIEW_POST': {
                'label': 'View Post',
                'style': 'primary',
                'url_builder': lambda n: f'/post/{_post_share_id(n.context_id)}/' if n.context_type == 'POST' and n.context_id and _post_share_id(n.context_id) else None,
                'method': 'GET'
            },
            'VIEW_COMMENT': {
                'label': 'View Comment',
                'style': 'primary',
                'url_builder': lambda n: f'/post/{_post_share_id(n.context_id)}/#comment-{(n.metadata or {}).get("target_id")}' if n.context_type == 'POST' and n.context_id and (n.metadata or {}).get('target_id') and _post_share_id(n.context_id) else None,
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
                'url_builder': lambda n: f'/groups/{n.context_id}/' if n.context_type == 'GROUP' and n.context_id else None,
                'method': 'GET'
            },
            'VIEW_ANNOUNCEMENT': {
                'label': 'Read Announcement',
                'style': 'primary',
                'url_builder': lambda n: f'/groups/{n.context_id}/#announcements' if n.context_id else None,
                'method': 'GET'
            },
            'FOLLOW_BACK': {
                'label': 'Follow Back',
                'style': 'primary',
                'url_builder': lambda n: f'/notifications/follow-back/{getattr(n, "notification_id", getattr(n, "id", None))}/' if getattr(n, "notification_id", getattr(n, "id", None)) else None,
                'method': 'POST'
            },
            'VIEW_PROFILE': {
                'label': 'View Profile',
                'style': 'secondary',
                'url_builder': lambda n: f'/users/user/{(n.metadata or {}).get("actor_username")}/' if (n.metadata or {}).get('actor_username') else None,
                'method': 'GET'
            },
            'PINCH': {
                'label': 'Pinch',
                'style': 'secondary',
                'url_builder': lambda n: f'/notifications/pinch/{getattr(n, "notification_id", getattr(n, "id", None))}/' if getattr(n, "notification_id", getattr(n, "id", None)) else None,
                'method': 'POST'
            },
            'SEE_WHATS_NEW': {
                'label': "See What's New",
                'style': 'primary',
                'url_builder': lambda n: f'/system/releases/{(n.metadata or {}).get("target_id")}/' if (n.metadata or {}).get('target_id') else None,
                'method': 'GET',
                'data_attrs': {'data-release-id': lambda n: (n.metadata or {}).get('target_id')}
            },
            'VIEW_DOCUMENT': {
                'label': 'View Document',
                'style': 'primary',
                'icon': 'file-earmark-text',
                'url_builder': lambda n: self._build_document_view_url(n),
                'method': 'GET'
            },
        }
        
        config = action_configs.get(action_id)
        if not config:
            return None
        
        url = config['url_builder'](notification)
        if not url:
            return None

        enabled = True
        label = config['label']
        if action_id == 'PINCH':
            actor_id = notification.metadata.get('actor_id') if notification.metadata else None
            if actor_id and hasattr(notification, 'recipient') and notification.recipient:
                from users.models import Pinch
                from django.utils import timezone
                try:
                    pinched_id = int(actor_id)
                except (ValueError, TypeError):
                    pinched_id = None
                if pinched_id and Pinch.objects.filter(
                    pinch_user=notification.recipient,
                    pinched_user_id=pinched_id,
                    created_at__date=timezone.now().date()
                ).exists():
                    enabled = False
                    label = 'Pinched'
        
        return PayloadNotificationAction(
            id=action_id,
            label=label,
            style=config['style'],
            enabled=enabled,
            url=url,
            method=config['method'],
            payload={}
        )
    
    def _build_document_view_url(self, n) -> Optional[str]:
        """Build URL to view document for document notifications."""
        meta = n.metadata or {}
        doc_id = meta.get('shared_document_id') or meta.get('document_id')
        if doc_id:
            try:
                from documents.models import Document
                doc = Document.objects.filter(id=int(doc_id)).first()
                if doc and doc.share_id:
                    return f"/documents/document/{doc.share_id}/"
            except Exception:
                pass

        if str(n.context_type or '').upper() == 'DOCUMENT' and n.context_id:
            try:
                from documents.models import Document
                doc = Document.objects.filter(id=int(n.context_id)).first()
                if doc and doc.share_id:
                    return f"/documents/document/{doc.share_id}/"
            except Exception:
                pass

        post_id = meta.get('target_id') or meta.get('post_id')
        if not post_id and str(n.context_type or '').upper() in ['POST', 'POSTS']:
            post_id = n.context_id
        if post_id:
            post = _get_post_safely(post_id)
            if post and post.shared_document and post.shared_document.share_id:
                return f"/documents/document/{post.shared_document.share_id}/"

        return None
    
    def _determine_intent(self, notification_type: str) -> NotificationIntent:
        """Determine notification intent based on type."""
        intent_map = {
            'LIKE': NotificationIntent.ACTIVITY,
            'COMMENT': NotificationIntent.ACTIVITY,
            'FOLLOW': NotificationIntent.ACTIVITY,
            'INVITE': NotificationIntent.WORKFLOW,
            'GROUP_REQUEST': NotificationIntent.WORKFLOW,
            'GROUP_JOIN_REQUEST': NotificationIntent.WORKFLOW,
            'GROUP_APPROVED': NotificationIntent.WORKFLOW,
            'GROUP_REJECTED': NotificationIntent.WORKFLOW,
            'GROUP_ANNOUNCEMENT': NotificationIntent.ANNOUNCEMENT,
            'POST_CREATED': NotificationIntent.ACTIVITY,
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
        
        metadata = notification.metadata or {}
        variables = {
            'actor_username': metadata.get('actor_username', 'Someone'),
            'group_name': metadata.get('group_name', ''),
            'title': notification.title,
            'summary': notification.summary
        }
        return NotificationMessage(
            template=message_strategy.template,
            state=message_state,
            variables=variables
        )
    
    def _build_components(self, notification, resource: Optional[NotificationResource] = None) -> NotificationComponents:
        """Build component visibility configuration using profile registry."""
        from .profile_registry import profile_registry
        
        # Get the profile for this notification type
        profile = profile_registry.get_profile(notification.notification_type)
        
        # Use the profile's component visibility configuration
        visibility_config = profile.component_visibility if profile else None
        
        # If resource has an image or thumbnail, ensure preview is visible
        has_preview_image = bool(resource and (resource.image_url or getattr(resource, 'thumbnail_url', None)))
        preview_visible = (visibility_config.preview if visibility_config else False) or has_preview_image
        
        return NotificationComponents(
            context_header=visibility_config.context_header if visibility_config else False,
            actor_stack=visibility_config.actor_stack if visibility_config else True,
            content=visibility_config.content if visibility_config else True,
            preview=preview_visible,
            metadata=visibility_config.metadata if visibility_config else True,
            action_bar=visibility_config.action_bar if visibility_config else False,
            status=visibility_config.status if visibility_config else False
        )
    
    def _build_preview(self, notification, resource: Optional[NotificationResource]) -> NotificationPreview:
        """Build preview configuration using profile registry."""
        from .profile_registry import profile_registry
        
        # Get the profile for this notification type
        profile = profile_registry.get_profile(notification.notification_type)
        
        # Use the profile's preview strategy configuration
        preview_strategy = profile.preview_strategy if profile else None
        
        # Map preview_type string to PreviewType enum
        preview_type_enum = PreviewType.NONE
        has_image = bool(resource and (resource.image_url or getattr(resource, 'thumbnail_url', None)))
        
        if preview_strategy:
            if preview_strategy.preview_type == "POST":
                preview_type_enum = PreviewType.POST
            elif preview_strategy.preview_type == "DOCUMENT":
                preview_type_enum = PreviewType.DOCUMENT
            elif preview_strategy.preview_type == "GROUP":
                preview_type_enum = PreviewType.GROUP
        elif has_image:
            preview_type_enum = PreviewType.POST
        
        enabled = (preview_strategy.enabled if preview_strategy else False) or has_image
        
        return NotificationPreview(
            enabled=enabled,
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
