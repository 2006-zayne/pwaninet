"""
Notification Renderers
Concrete renderer implementations for each notification type following the Notification Engine Specification.
"""

from typing import Dict, Any
from .registry import NotificationRenderer, register_renderer, register_profile


class LikeRenderer(NotificationRenderer):
    """Renderer for LIKE notifications (post likes)."""
    
    notification_type = 'LIKE'
    template = 'notifications/components/notification_card.html'
    priority = 90  # Higher priority than default
    
    def get_context(self, notification: Any) -> Dict[str, Any]:
        """Build context for like notifications."""
        return {
            'icon': 'heart',
            'icon_color': 'danger',
            'action_verb': 'liked your post'
        }
    
    def get_actions(self, notification: Any) -> list:
        """Get actions for like notifications."""
        actions = []
        if notification.resource and notification.resource.get('url'):
            actions.append({
                'label': 'View Post',
                'icon': 'arrow-right',
                'url': notification.resource['url'],
                'type': 'link',
                'style': 'primary'
            })
        return actions


class FollowRenderer(NotificationRenderer):
    """Renderer for FOLLOW notifications."""
    
    notification_type = 'FOLLOW'
    template = 'notifications/components/notification_card.html'
    priority = 90
    
    def get_context(self, notification: Any) -> Dict[str, Any]:
        """Build context for follow notifications."""
        return {
            'icon': 'person-plus',
            'icon_color': 'info',
            'action_verb': 'started following you'
        }
    
    def get_actions(self, notification: Any) -> list:
        """Get actions for follow notifications."""
        actions = []
        if notification.actor and notification.actor.get('username'):
            actions.append({
                'label': 'View Profile',
                'icon': 'person',
                'url': f'/profile/{notification.actor["username"]}',
                'type': 'link',
                'style': 'primary'
            })
        return actions


class InviteRenderer(NotificationRenderer):
    """Renderer for INVITE notifications (group invites)."""
    
    notification_type = 'INVITE'
    template = 'notifications/components/notification_card.html'
    priority = 95  # High priority for actionable notifications
    
    def get_context(self, notification: Any) -> Dict[str, Any]:
        """Build context for invite notifications."""
        return {
            'icon': 'envelope',
            'icon_color': 'primary',
            'action_verb': 'invited you to join'
        }
    
    def get_actions(self, notification: Any) -> list:
        """Get actions for invite notifications."""
        actions = []
        # Use notification ID for the respond_to_invite endpoint
        if hasattr(notification, 'id') and notification.id:
            notif_id = notification.id
            actions.append({
                'label': 'Accept',
                'icon': 'check-lg',
                'url': f'/groups/invite/respond/{notif_id}/accept/',
                'type': 'button',
                'style': 'accept',
                'htmx': f'hx-post="/groups/invite/respond/{notif_id}/accept/" hx-target="closest .notif-item" hx-swap="outerHTML"'
            })
            actions.append({
                'label': 'Decline',
                'icon': 'x-lg',
                'url': f'/groups/invite/respond/{notif_id}/decline/',
                'type': 'button',
                'style': 'decline',
                'htmx': f'hx-post="/groups/invite/respond/{notif_id}/decline/" hx-target="closest .notif-item" hx-swap="outerHTML"'
            })
        return actions


class CommentReplyRenderer(NotificationRenderer):
    """Renderer for COMMENT_REPLY notifications."""
    
    notification_type = 'COMMENT_REPLY'
    template = 'notifications/components/notification_card.html'
    priority = 90
    
    def get_context(self, notification: Any) -> Dict[str, Any]:
        """Build context for comment reply notifications."""
        return {
            'icon': 'chat-dots',
            'icon_color': 'brand',
            'action_verb': 'replied to your comment'
        }
    
    def get_actions(self, notification: Any) -> list:
        """Get actions for comment reply notifications."""
        actions = []
        if notification.resource and notification.resource.get('url'):
            actions.append({
                'label': 'View Comment',
                'icon': 'arrow-right',
                'url': notification.resource['url'],
                'type': 'link',
                'style': 'primary'
            })
        return actions


class GroupRequestRenderer(NotificationRenderer):
    """Renderer for GROUP_REQUEST notifications."""
    
    notification_type = 'GROUP_REQUEST'
    template = 'notifications/components/notification_card.html'
    priority = 95
    
    def get_context(self, notification: Any) -> Dict[str, Any]:
        """Build context for group request notifications."""
        return {
            'icon': 'person-plus',
            'icon_color': 'primary',
            'action_verb': 'requested to join your group'
        }
    
    def get_actions(self, notification: Any) -> list:
        """Get actions for group request notifications."""
        actions = []
        # Get group_id from target and user_id from metadata/context
        group_id = None
        user_id = None
        
        if hasattr(notification, 'target') and notification.target and notification.target.get('id'):
            group_id = notification.target['id']
        elif notification.context and notification.context.get('id'):
            group_id = notification.context['id']
        
        # Try to get user_id from metadata or context
        if hasattr(notification, 'metadata') and notification.metadata:
            user_id = notification.metadata.get('user_id')
        elif notification.context and notification.context.get('user_id'):
            user_id = notification.context['user_id']
        
        if group_id and user_id:
            actions.append({
                'label': 'Approve',
                'icon': 'check-lg',
                'url': f'/groups/{group_id}/approve/{user_id}/',
                'type': 'button',
                'style': 'accept',
                'htmx': f'hx-post="/groups/{group_id}/approve/{user_id}/" hx-target="closest .notif-item" hx-swap="outerHTML"'
            })
            actions.append({
                'label': 'Reject',
                'icon': 'x-lg',
                'url': f'/groups/{group_id}/reject/{user_id}/',
                'type': 'button',
                'style': 'decline',
                'htmx': f'hx-post="/groups/{group_id}/reject/{user_id}/" hx-target="closest .notif-item" hx-swap="outerHTML"'
            })
        return actions


class GroupApprovedRenderer(NotificationRenderer):
    """Renderer for GROUP_APPROVED notifications."""
    
    notification_type = 'GROUP_APPROVED'
    template = 'notifications/components/notification_card.html'
    priority = 90
    
    def get_context(self, notification: Any) -> Dict[str, Any]:
        """Build context for group approved notifications."""
        return {
            'icon': 'check-circle',
            'icon_color': 'success',
            'action_verb': 'approved your group join request'
        }
    
    def get_actions(self, notification: Any) -> list:
        """Get actions for group approved notifications."""
        actions = []
        # Add disabled "Approved" button to show completed action
        actions.append({
            'label': 'Approved',
            'icon': 'check-lg',
            'type': 'button',
            'style': 'success',
            'disabled': True
        })
        # Check target_id for group ID to construct URL
        group_id = None
        if hasattr(notification, 'target') and notification.target and notification.target.get('id'):
            group_id = notification.target['id']
        elif notification.context and notification.context.get('id'):
            group_id = notification.context['id']
        
        if group_id:
            actions.append({
                'label': 'View Group',
                'icon': 'people',
                'url': f'/groups/{group_id}/',
                'type': 'link',
                'style': 'primary'
            })
        return actions


class GroupRejectedRenderer(NotificationRenderer):
    """Renderer for GROUP_REJECTED notifications."""
    
    notification_type = 'GROUP_REJECTED'
    template = 'notifications/components/notification_card.html'
    priority = 85
    
    def get_context(self, notification: Any) -> Dict[str, Any]:
        """Build context for group rejected notifications."""
        return {
            'icon': 'x-circle',
            'icon_color': 'danger',
            'action_verb': 'rejected your group join request'
        }
    
    def get_actions(self, notification: Any) -> list:
        """Get actions for group rejected notifications."""
        return []  # No actions for rejection notifications


class DocumentSharedRenderer(NotificationRenderer):
    """Renderer for DOCUMENT_SHARED notifications."""
    
    notification_type = 'DOCUMENT_SHARED'
    template = 'notifications/components/notification_card.html'
    priority = 85
    
    def get_context(self, notification: Any) -> Dict[str, Any]:
        """Build context for document shared notifications."""
        return {
            'icon': 'file-earmark-text',
            'icon_color': 'primary',
            'action_verb': 'shared a document to view'
        }
    
    def get_actions(self, notification: Any) -> list:
        """Get actions for document shared notifications."""
        actions = []
        if notification.resource and notification.resource.get('url'):
            actions.append({
                'label': 'View Document',
                'icon': 'arrow-right',
                'url': notification.resource['url'],
                'type': 'link',
                'style': 'primary'
            })
        return actions


class PostSharedRenderer(NotificationRenderer):
    """Renderer for POST_SHARED notifications."""
    
    notification_type = 'POST_SHARED'
    template = 'notifications/components/notification_card.html'
    priority = 85
    
    def get_context(self, notification: Any) -> Dict[str, Any]:
        """Build context for post shared notifications."""
        return {
            'icon': 'share',
            'icon_color': 'info',
            'action_verb': 'shared a post with you'
        }
    
    def get_actions(self, notification: Any) -> list:
        """Get actions for post shared notifications."""
        actions = []
        if notification.resource and notification.resource.get('url'):
            actions.append({
                'label': 'View Post',
                'icon': 'arrow-right',
                'url': notification.resource['url'],
                'type': 'link',
                'style': 'primary'
            })
        return actions


class PostSharedToGroupRenderer(NotificationRenderer):
    """Renderer for POST_SHARED_TO_GROUP notifications."""
    
    notification_type = 'POST_SHARED_TO_GROUP'
    template = 'notifications/components/notification_card.html'
    priority = 85
    
    def get_context(self, notification: Any) -> Dict[str, Any]:
        """Build context for post shared to group notifications."""
        return {
            'icon': 'share',
            'icon_color': 'info',
            'action_verb': 'shared a post to your group'
        }
    
    def get_actions(self, notification: Any) -> list:
        """Get actions for post shared to group notifications."""
        actions = []
        if notification.resource and notification.resource.get('url'):
            actions.append({
                'label': 'View Post',
                'icon': 'arrow-right',
                'url': notification.resource['url'],
                'type': 'link',
                'style': 'primary'
            })
        return actions


class PinchRenderer(NotificationRenderer):
    """Renderer for PINCH notifications."""
    
    notification_type = 'PINCH'
    template = 'notifications/components/notification_card.html'
    priority = 80
    
    def get_context(self, notification: Any) -> Dict[str, Any]:
        """Build context for pinch notifications."""
        return {
            'icon': 'hand-index',
            'icon_color': 'brand',
            'action_verb': 'pinched you'
        }
    
    def get_actions(self, notification: Any) -> list:
        """Get actions for pinch notifications."""
        actions = []
        if notification.actor and notification.actor.get('username'):
            actions.append({
                'label': 'View Profile',
                'icon': 'person',
                'url': f'/profile/{notification.actor["username"]}',
                'type': 'link',
                'style': 'primary'
            })
        return actions


class AlertRenderer(NotificationRenderer):
    """Renderer for ALERTE (general alert) notifications."""
    
    notification_type = 'ALERTE'
    template = 'notifications/components/notification_card.html'
    priority = 100  # Highest priority for system alerts
    
    def get_context(self, notification: Any) -> Dict[str, Any]:
        """Build context for alert notifications."""
        return {
            'icon': 'bell',
            'icon_color': 'brand',
            'action_verb': 'alert'
        }
    
    def get_actions(self, notification: Any) -> list:
        """Get actions for alert notifications."""
        return []  # Actions depend on specific alert content


# Register all renderers
register_renderer(LikeRenderer())
register_renderer(FollowRenderer())
register_renderer(InviteRenderer())
register_renderer(CommentReplyRenderer())
register_renderer(GroupRequestRenderer())
register_renderer(GroupApprovedRenderer())
register_renderer(GroupRejectedRenderer())
register_renderer(PostSharedRenderer())
register_renderer(PostSharedToGroupRenderer())
register_renderer(DocumentSharedRenderer())
register_renderer(PinchRenderer())
register_renderer(AlertRenderer())

# Register rendering profiles
register_profile('LIKE', 'social')
register_profile('FOLLOW', 'social')
register_profile('INVITE', 'group')
register_profile('COMMENT_REPLY', 'social')
register_profile('GROUP_REQUEST', 'group')
register_profile('GROUP_APPROVED', 'group')
register_profile('GROUP_REJECTED', 'group')
register_profile('POST_SHARED', 'social')
register_profile('POST_SHARED_TO_GROUP', 'group')
register_profile('DOCUMENT_SHARED', 'social')
register_profile('PINCH', 'social')
register_profile('ALERTE', 'system')
