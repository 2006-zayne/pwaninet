"""
Template tags for notification rendering.
"""
from django import template
from notifications.rendering import render_notification as render_notification_service

register = template.Library()


@register.filter
def render_notification(notification):
    """
    Render a notification using the rendering service.
    
    Args:
        notification: NotificationObject instance
        
    Returns:
        Rendered HTML string
    """
    return render_notification_service(notification)
