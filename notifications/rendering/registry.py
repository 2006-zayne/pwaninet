"""
Notification Renderer Registry
Maps notification types to their respective renderers following the Notification Engine Specification.
"""

from typing import Dict, Type, Callable, Any
from dataclasses import dataclass


class NotificationRenderer:
    """
    Base class for notification renderers.
    Each renderer knows how to render a specific notification type.
    """
    
    notification_type: str = ""
    template: str = ""
    priority: int = 100  # Lower priority = higher precedence
    
    def __init__(self, notification_type: str = None, template: str = None, priority: int = None):
        if notification_type is not None:
            self.notification_type = notification_type
        if template is not None:
            self.template = template
        if priority is not None:
            self.priority = priority
    
    def get_context(self, notification: Any) -> Dict[str, Any]:
        """
        Build template context for this notification.
        Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement get_context")
    
    def get_actions(self, notification: Any) -> list:
        """
        Get available actions for this notification.
        Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement get_actions")


class NotificationRegistry:
    """
    Registry for notification renderers.
    Maps notification types to their renderer classes.
    """
    
    def __init__(self):
        self._renderers: Dict[str, NotificationRenderer] = {}
        self._profiles: Dict[str, str] = {}  # Maps type to rendering profile
    
    def register(self, renderer: NotificationRenderer):
        """
        Register a notification renderer.
        
        Args:
            renderer: NotificationRenderer instance
        """
        self._renderers[renderer.notification_type] = renderer
    
    def register_profile(self, notification_type: str, profile: str):
        """
        Register a rendering profile for a notification type.
        
        Args:
            notification_type: Type of notification (e.g., 'LIKE', 'FOLLOW')
            profile: Rendering profile (e.g., 'social', 'academic', 'document')
        """
        self._profiles[notification_type] = profile
    
    def get_renderer(self, notification_type: str) -> NotificationRenderer:
        """
        Get the renderer for a notification type.
        
        Args:
            notification_type: Type of notification
            
        Returns:
            NotificationRenderer instance
            
        Raises:
            KeyError: If no renderer registered for this type
        """
        if notification_type not in self._renderers:
            raise KeyError(f"No renderer registered for notification type: {notification_type}")
        return self._renderers[notification_type]
    
    def get_profile(self, notification_type: str) -> str:
        """
        Get the rendering profile for a notification type.
        
        Args:
            notification_type: Type of notification
            
        Returns:
            Profile name (e.g., 'social', 'academic')
            
        Raises:
            KeyError: If no profile registered for this type
        """
        if notification_type not in self._profiles:
            raise KeyError(f"No profile registered for notification type: {notification_type}")
        return self._profiles[notification_type]
    
    def has_renderer(self, notification_type: str) -> bool:
        """Check if a renderer is registered for this type."""
        return notification_type in self._renderers
    
    def has_profile(self, notification_type: str) -> bool:
        """Check if a profile is registered for this type."""
        return notification_type in self._profiles
    
    def list_types(self) -> list:
        """List all registered notification types."""
        return list(self._renderers.keys())
    
    def list_profiles(self) -> Dict[str, str]:
        """List all registered type-to-profile mappings."""
        return self._profiles.copy()


# Global registry instance
registry = NotificationRegistry()


def register_renderer(renderer: NotificationRenderer):
    """
    Decorator to register a notification renderer.
    
    Usage:
        @register_renderer
        class LikeRenderer(NotificationRenderer):
            notification_type = 'LIKE'
            template = 'notifications/components/notification_card.html'
            
            def get_context(self, notification):
                return {...}
    """
    registry.register(renderer)
    return renderer


def register_profile(notification_type: str, profile: str):
    """
    Decorator to register a rendering profile.
    
    Usage:
        @register_profile('LIKE', 'social')
        def like_profile():
            pass
    """
    registry.register_profile(notification_type, profile)
    return lambda f: f
