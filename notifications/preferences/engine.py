"""
Preference Engine for PwaniNet Notification Engine v2

This module implements the Preference Engine that evaluates user-specific notification
preferences before delivery. Following Chapter 8 of the specification.
"""
import logging
from typing import Dict, List, Optional, Tuple
from django.contrib.auth import get_user_model
from django.utils import timezone
from notifications.models import NotificationObject, NotificationPreference
from notifications.notifications.registry import NotificationPriorities

User = get_user_model()

logger = logging.getLogger(__name__)


class PreferenceEngine:
    """
    The Preference Engine determines whether a Notification Object should proceed
    to delivery based on user-defined notification preferences and platform policies.
    
    Responsibilities:
    - Load recipient preferences
    - Evaluate notification eligibility
    - Apply platform policies
    - Determine allowed delivery channels
    - Forward approved notifications
    
    It does NOT:
    - Modify Platform Events
    - Deliver notifications
    - Aggregate notifications
    - Generate notifications
    """
    
    # Mandatory notification types (cannot be disabled)
    MANDATORY_NOTIFICATION_TYPES = ['SECURITY', 'SYSTEM']
    MANDATORY_CATEGORIES = ['SECURITY', 'SYSTEM']
    
    @staticmethod
    def evaluate_notification(notification: NotificationObject, channel: str = 'IN_APP') -> Tuple[bool, List[str]]:
        """
        Evaluate a notification against user preferences.
        
        Args:
            notification: The NotificationObject to evaluate
            channel: The delivery channel to check (IN_APP, PUSH, EMAIL)
            
        Returns:
            Tuple of (allowed, allowed_channels)
            - allowed: Whether notification is allowed for this channel
            - allowed_channels: List of all allowed channels for this notification
        """
        logger.info(f"Evaluating notification {notification.notification_id} for channel {channel}")
        
        # Check platform policy first (mandatory notifications)
        if PreferenceEngine._is_mandatory(notification):
            logger.info(f"Notification {notification.notification_id} is mandatory, allowing")
            return True, ['IN_APP', 'PUSH', 'EMAIL']
        
        # Load user preferences
        preferences = PreferenceEngine._load_preferences(notification.recipient)
        
        # Evaluate preferences in hierarchy order
        # Platform Policy → User Account Settings → Category → Type → Context → Channel
        allowed_channels = PreferenceEngine._evaluate_preference_hierarchy(
            notification, preferences
        )
        
        # Check if requested channel is allowed
        allowed = channel in allowed_channels
        
        # Check quiet hours
        if allowed and PreferenceEngine._is_in_quiet_hours(notification, preferences):
            # During quiet hours, low and normal priority may be delayed
            if notification.priority in ['LOW', 'NORMAL']:
                logger.info(f"Notification {notification.notification_id} delayed due to quiet hours")
                return False, allowed_channels
        
        # Check temporary mute
        if allowed and PreferenceEngine._is_temporarily_muted(notification, preferences):
            logger.info(f"Notification {notification.notification_id} temporarily muted")
            return False, allowed_channels
        
        logger.info(f"Notification {notification.notification_id} evaluation result: {allowed}")
        return allowed, allowed_channels
    
    @staticmethod
    def _is_mandatory(notification: NotificationObject) -> bool:
        """
        Check if notification is mandatory (cannot be disabled).
        
        Mandatory notifications bypass user preferences.
        """
        # Check category
        if notification.category in PreferenceEngine.MANDATORY_CATEGORIES:
            return True
        
        # Check type
        if notification.notification_type in PreferenceEngine.MANDATORY_NOTIFICATION_TYPES:
            return True
        
        # Check priority (CRITICAL notifications are mandatory)
        if notification.priority == 'CRITICAL':
            return True
        
        return False
    
    @staticmethod
    def _load_preferences(user: User) -> Optional[NotificationPreference]:
        """
        Load preferences for a user.
        
        Returns the user's notification preferences (OneToOne relationship).
        """
        try:
            return NotificationPreference.objects.get(user=user)
        except NotificationPreference.DoesNotExist:
            return None
    
    @staticmethod
    def _evaluate_preference_hierarchy(
        notification: NotificationObject,
        preferences: Optional[NotificationPreference]
    ) -> List[str]:
        """
        Evaluate preferences for a notification.
        
        Uses type-specific preferences if available, otherwise falls back to global channel preferences.
        """
        allowed_channels = []
        
        if not preferences:
            # Default: all channels allowed
            return ['IN_APP', 'PUSH', 'EMAIL']
        
        # Check type-specific preference using the event_type from metadata
        # The event_type should be stored in the notification's metadata or source_events
        event_type = notification.metadata.get('event_type') if hasattr(notification, 'metadata') and notification.metadata else None
        
        if event_type and event_type in preferences.type_preferences:
            # Use type-specific preferences
            type_pref = preferences.type_preferences.get(event_type, {})
            if type_pref.get('email'):
                allowed_channels.append('EMAIL')
            if type_pref.get('push'):
                allowed_channels.append('PUSH')
            if type_pref.get('in_app'):
                allowed_channels.append('IN_APP')
        else:
            # Use global channel preferences
            if preferences.email_enabled:
                allowed_channels.append('EMAIL')
            if preferences.push_enabled:
                allowed_channels.append('PUSH')
            if preferences.in_app_enabled:
                allowed_channels.append('IN_APP')
        
        return allowed_channels if allowed_channels else ['IN_APP']
    
    @staticmethod
    def _find_specific_preference(
        notification: NotificationObject,
        preferences: Optional[NotificationPreference]
    ) -> Optional[NotificationPreference]:
        """
        Find the most specific preference for this notification.
        
        For the simplified model, this just returns the user's preferences.
        Type-specific preferences are handled via the type_preferences JSON field.
        """
        return preferences
    
    @staticmethod
    def _is_in_quiet_hours(
        notification: NotificationObject,
        preferences: Optional[NotificationPreference]
    ) -> bool:
        """
        Check if current time is within user's quiet hours.
        """
        if not preferences or not preferences.quiet_hours_enabled:
            return False
        
        return preferences.is_quiet_hours()
    
    @staticmethod
    def _is_temporarily_muted(
        notification: NotificationObject,
        preferences: NotificationPreference
    ) -> bool:
        """
        Check if notifications are temporarily muted.
        """
        if not preferences:
            return False
        return preferences.is_do_not_disturb()
    
    @staticmethod
    def create_default_preferences(user: User):
        """
        Create default preferences for a new user.
        
        Following specification defaults:
        - In-app: Enabled
        - Push: Disabled
        - Email: Enabled
        """
        NotificationPreference.objects.create(
            user=user,
            email_enabled=True,
            email_digest=False,
            push_enabled=False,
            push_sound=True,
            in_app_enabled=True,
            type_preferences={},
            quiet_hours_enabled=False,
            max_notifications_per_hour=50
        )
        
        logger.info(f"Created default preferences for user {user.username}")


def evaluate_notification(notification: NotificationObject, channel: str = 'IN_APP') -> Tuple[bool, List[str]]:
    """
    Convenience function to evaluate a notification through the Preference Engine.
    
    Args:
        notification: The NotificationObject to evaluate
        channel: The delivery channel to check
        
    Returns:
        Tuple of (allowed, allowed_channels)
    """
    return PreferenceEngine.evaluate_notification(notification, channel)
