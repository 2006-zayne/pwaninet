"""
Notification Rendering Service
Coordinates the rendering pipeline using the new profile-driven system.
"""

from typing import Dict, Any, List
from django.template.loader import render_to_string
from .profile_driven_renderer import profile_driven_renderer
from .adapters import get_payload_adapter


class NotificationRenderingService:
    """
    Service for rendering notifications using the profile-driven system.
    """
    
    def render_notification(self, notification, template_name: str = None) -> str:
        """
        Render a single notification to HTML using the profile-driven renderer.
        
        Args:
            notification: Notification instance (NotificationObject or legacy)
            template_name: Optional custom template name
            
        Returns:
            Rendered HTML string
        """
        # Get appropriate adapter to convert notification to payload
        adapter = get_payload_adapter(notification)
        
        # Convert to canonical NotificationPayload
        payload = adapter.to_standard_payload(notification)
        
        # Use the new profile-driven renderer with the payload object
        rendering_context = profile_driven_renderer.render(payload)
        
        # Determine template
        if template_name:
            template = template_name
        else:
            template = 'notifications/components/notification_card_profile_driven.html'
        
        # Render with the complete rendering context
        return render_to_string(template, rendering_context)
    
    def render_notification_list(self, notifications: List, template_name: str = None) -> str:
        """
        Render a list of notifications to HTML.
        
        Args:
            notifications: List of notification instances
            template_name: Optional custom template name
            
        Returns:
            Rendered HTML string
        """
        rendered = []
        for notification in notifications:
            rendered.append(self.render_notification(notification, template_name))
        return '\n'.join(rendered)
    
    def get_rendering_context(self, notification) -> Dict[str, Any]:
        """
        Get the rendering context for a notification without rendering.
        
        Args:
            notification: Notification instance
            
        Returns:
            Rendering context dict
        """
        adapter = get_payload_adapter(notification)
        payload = adapter.to_standard_payload(notification)
        payload_dict = payload.to_dict()
        
        try:
            renderer = registry.get_renderer(payload_dict['type'])
        except KeyError:
            renderer = None
        
        return self._build_rendering_context(payload_dict, renderer)
    
    def _build_rendering_context(self, payload: Dict[str, Any], renderer = None) -> Dict[str, Any]:
        """
        Build the complete rendering context for a notification.
        
        Args:
            payload: Standardized notification payload
            renderer: Optional renderer instance
            
        Returns:
            Complete rendering context
        """
        context = {
            'notification': payload
        }
        
        # Add renderer-specific context if available
        if renderer:
            try:
                renderer_context = renderer.get_context(payload)
                context.update(renderer_context)
            except NotImplementedError:
                pass
        
        # Add actions
        if renderer:
            try:
                context['actions'] = renderer.get_actions(payload)
            except NotImplementedError:
                context['actions'] = payload.get('actions', [])
        else:
            context['actions'] = payload.get('actions', [])
        
        # Add rendering profile if registered
        try:
            profile = registry.get_profile(payload['type'])
            context['rendering_profile'] = profile
        except KeyError:
            context['rendering_profile'] = 'default'
        
        return context
    
    def get_available_renderers(self) -> List[str]:
        """
        Get list of all registered notification types.
        
        Returns:
            List of notification type strings
        """
        return registry.list_types()
    
    def get_rendering_profiles(self) -> Dict[str, str]:
        """
        Get all registered rendering profiles.
        
        Returns:
            Dict mapping notification types to profiles
        """
        return registry.list_profiles()


# Global service instance
rendering_service = NotificationRenderingService()


def render_notification(notification, template_name: str = None) -> str:
    """
    Convenience function to render a notification.
    
    Args:
        notification: Notification instance
        template_name: Optional custom template name
        
    Returns:
        Rendered HTML string
    """
    return rendering_service.render_notification(notification, template_name)


def render_notification_list(notifications: List, template_name: str = None) -> str:
    """
    Convenience function to render a list of notifications.
    
    Args:
        notifications: List of notification instances
        template_name: Optional custom template name
        
    Returns:
        Rendered HTML string
    """
    return rendering_service.render_notification_list(notifications, template_name)
