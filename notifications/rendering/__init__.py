"""
Notification Rendering Package
Provides the renderer registry, payload adapters, renderers, and service for the Notification Engine.
"""

from .registry import (
    NotificationRenderer,
    NotificationRegistry,
    registry,
    register_renderer,
    register_profile
)

from .adapters import (
    PayloadAdapter,
    NotificationObjectAdapter,
    get_payload_adapter
)

from .service import (
    NotificationRenderingService,
    rendering_service,
    render_notification,
    render_notification_list
)

__all__ = [
    'NotificationRenderer',
    'NotificationRegistry',
    'registry',
    'register_renderer',
    'register_profile',
    'PayloadAdapter',
    'NotificationObjectAdapter',
    'get_payload_adapter',
    'NotificationRenderingService',
    'rendering_service',
    'render_notification',
    'render_notification_list'
]
