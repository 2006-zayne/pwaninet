"""
Events module for PwaniNet Notification Engine v2

This module provides the event infrastructure for the platform.
Events are immutable facts representing completed actions within PwaniNet.
"""

from notifications.models import PlatformEvent, EventArchive
from .registry import EventTypes, EventSources, EventActions
from .validator import EventValidator
from .publisher import EventPublisher, publish_event

__all__ = [
    'PlatformEvent',
    'EventArchive',
    'EventTypes',
    'EventSources',
    'EventActions',
    'EventValidator',
    'EventPublisher',
    'publish_event',
]
