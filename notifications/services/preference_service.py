"""
Notification Preference Service
Manages user notification preferences for the new notification engine.
"""

from django.utils import timezone
from notifications.models import NotificationPreference
from notifications.events import EventTypes


class NotificationPreferenceService:
    """
    Service for managing notification preferences.
    """
    
    @staticmethod
    def get_or_create_preferences(user):
        """
        Get or create notification preferences for a user.
        
        Args:
            user: User instance
            
        Returns:
            NotificationPreference instance
        """
        preferences, created = NotificationPreference.objects.get_or_create(
            user=user
        )
        return preferences
    
    @staticmethod
    def should_deliver_notification(user, notification_type, channel):
        """
        Check if a notification should be delivered to a user.
        
        User preferences always override system defaults. Only falls back to
        system defaults if user hasn't set a preference for this specific type.
        
        Args:
            user: User instance
            notification_type: Event type (e.g., 'POSTS_POST_LIKED')
            channel: Channel ('email', 'push', 'in_app')
            
        Returns:
            Boolean indicating if notification should be delivered
        """
        preferences = NotificationPreferenceService.get_or_create_preferences(user)
        
        # Check do not disturb
        if preferences.is_do_not_disturb():
            return False
        
        # Check quiet hours (only for push and in-app)
        if channel in ['push', 'in_app'] and preferences.is_quiet_hours():
            return False
        
        # Check type-specific preference (user-set preference takes precedence)
        type_pref = preferences.type_preferences.get(notification_type, {})
        if channel in type_pref:
            # User has explicitly set a preference for this type
            return type_pref[channel]
        
        # Fall back to global channel preference
        if channel == 'email':
            return preferences.email_enabled
        elif channel == 'push':
            return preferences.push_enabled
        elif channel == 'in_app':
            return preferences.in_app_enabled
        
        return True
    
    @staticmethod
    def update_global_preferences(user, email_enabled=None, push_enabled=None, 
                                  in_app_enabled=None, email_digest=None, push_sound=None,
                                  in_app_toast_enabled=None):
        """
        Update global notification preferences for a user.
        
        Args:
            user: User instance
            email_enabled: Enable email notifications
            push_enabled: Enable push notifications
            in_app_enabled: Enable in-app notifications
            email_digest: Send daily digest
            push_sound: Play sound for push notifications
            in_app_toast_enabled: Enable in-app notification toasts/banners
            
        Returns:
            Updated NotificationPreference instance
        """
        preferences = NotificationPreferenceService.get_or_create_preferences(user)
        
        if email_enabled is not None:
            preferences.email_enabled = email_enabled
        if push_enabled is not None:
            preferences.push_enabled = push_enabled
        if in_app_enabled is not None:
            preferences.in_app_enabled = in_app_enabled
        if email_digest is not None:
            preferences.email_digest = email_digest
        if push_sound is not None:
            preferences.push_sound = push_sound
        if in_app_toast_enabled is not None:
            preferences.in_app_toast_enabled = in_app_toast_enabled
        
        preferences.save()
        return preferences
    
    @staticmethod
    def update_type_preferences(user, type_preferences):
        """
        Update notification type preferences for a user.
        
        Args:
            user: User instance
            type_preferences: Dict of type preferences
                e.g., {"POSTS_POST_LIKED": {"email": true, "push": true, "in_app": true}}
                
        Returns:
            Updated NotificationPreference instance
        """
        preferences = NotificationPreferenceService.get_or_create_preferences(user)
        
        # Ensure type_preferences is a dict
        if not isinstance(preferences.type_preferences, dict):
            preferences.type_preferences = {}
        
        for notification_type, channels in type_preferences.items():
            if notification_type not in preferences.type_preferences:
                preferences.type_preferences[notification_type] = {}
            
            for channel, enabled in channels.items():
                preferences.type_preferences[notification_type][channel] = enabled
        
        preferences.save()
        return preferences
    
    @staticmethod
    def update_quiet_hours(user, enabled=None, start=None, end=None):
        """
        Update quiet hours preferences.
        
        Args:
            user: User instance
            enabled: Enable quiet hours
            start: Start time (datetime.time)
            end: End time (datetime.time)
            
        Returns:
            Updated NotificationPreference instance
        """
        preferences = NotificationPreferenceService.get_or_create_preferences(user)
        
        if enabled is not None:
            preferences.quiet_hours_enabled = enabled
        if start is not None:
            preferences.quiet_hours_start = start
        if end is not None:
            preferences.quiet_hours_end = end
        
        preferences.save()
        return preferences
    
    @staticmethod
    def set_do_not_disturb(user, duration_hours=1):
        """
        Set do not disturb for a duration.
        
        Args:
            user: User instance
            duration_hours: Duration in hours
            
        Returns:
            Updated NotificationPreference instance
        """
        preferences = NotificationPreferenceService.get_or_create_preferences(user)
        
        from datetime import timedelta
        preferences.do_not_disturb_until = timezone.now() + timedelta(hours=duration_hours)
        preferences.save()
        
        return preferences
    
    @staticmethod
    def clear_do_not_disturb(user):
        """
        Clear do not disturb.
        
        Args:
            user: User instance
            
        Returns:
            Updated NotificationPreference instance
        """
        preferences = NotificationPreferenceService.get_or_create_preferences(user)
        preferences.do_not_disturb_until = None
        preferences.save()
        
        return preferences
    
    @staticmethod
    def get_default_type_preferences():
        """
        Get default preferences for all notification types.
        
        Returns:
            Dict of default preferences
        """
        defaults = {}
        
        # Social notifications - enabled by default
        social_types = [
            EventTypes.POSTS_POST_LIKED.value,
            EventTypes.POSTS_COMMENT_CREATED.value,
            EventTypes.POSTS_COMMENT_REPLY_CREATED.value,
            EventTypes.POSTS_COMMENT_REPLIED.value,
            EventTypes.POSTS_POST_SHARED.value,
            EventTypes.POSTS_POST_REPOSTED.value,
            EventTypes.POSTS_POST_SHARED_TO_GROUP.value,
            EventTypes.USERS_USER_FOLLOWED.value,
            EventTypes.USERS_USER_PINCHED.value,
        ]
        
        for event_type in social_types:
            defaults[event_type] = {
                'email': True,
                'push': True,
                'in_app': True
            }
        
        # Group notifications - enabled by default
        group_types = [
            EventTypes.GROUPS_MEMBER_INVITED.value,
            EventTypes.GROUPS_MEMBER_REQUESTED.value,
            EventTypes.GROUPS_MEMBER_APPROVED.value,
            EventTypes.GROUPS_MEMBER_REJECTED.value,
            EventTypes.POSTS_POST_SHARED_TO_GROUP.value,
        ]
        
        for event_type in group_types:
            defaults[event_type] = {
                'email': True,
                'push': True,
                'in_app': True
            }
        
        # Document notifications - push/in-app only
        document_types = [
            EventTypes.DOCUMENTS_DOCUMENT_UPLOADED.value,
            EventTypes.DOCUMENTS_DOCUMENT_DOWNLOADED.value,
            EventTypes.DOCUMENTS_DOCUMENT_BOOKMARKED.value,
            EventTypes.DOCUMENTS_DOCUMENT_RATED.value,
        ]
        
        for event_type in document_types:
            defaults[event_type] = {
                'email': False,
                'push': True,
                'in_app': True
            }
        
        # Messaging notifications - push/in-app only
        messaging_types = [
            EventTypes.MESSAGING_MESSAGE_SENT.value,
            EventTypes.MESSAGING_CONVERSATION_CREATED.value,
            EventTypes.MESSAGING_CONVERSATION_MEMBER_ADDED.value,
        ]
        
        for event_type in messaging_types:
            defaults[event_type] = {
                'email': False,
                'push': True,
                'in_app': True
            }
        
        # Academic notifications - enabled by default
        academic_types = [
            EventTypes.COURSES_ASSIGNMENT_PUBLISHED.value,
        ]
        
        for event_type in academic_types:
            defaults[event_type] = {
                'email': True,
                'push': True,
                'in_app': True
            }
        
        return defaults
    
    @staticmethod
    def initialize_user_preferences(user):
        """
        Initialize default preferences for a new user.
        
        Args:
            user: User instance
            
        Returns:
            Created NotificationPreference instance
        """
        preferences = NotificationPreferenceService.get_or_create_preferences(user)
        
        # Set default type preferences
        defaults = NotificationPreferenceService.get_default_type_preferences()
        preferences.type_preferences = defaults
        
        preferences.save()
        return preferences


# Convenience functions
def get_user_preferences(user):
    """Get notification preferences for a user."""
    return NotificationPreferenceService.get_or_create_preferences(user)


def should_deliver(user, notification_type, channel):
    """Check if notification should be delivered."""
    return NotificationPreferenceService.should_deliver_notification(user, notification_type, channel)


def update_preferences(user, **kwargs):
    """Update notification preferences."""
    return NotificationPreferenceService.update_global_preferences(user, **kwargs)
