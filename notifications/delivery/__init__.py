"""
Delivery module for PwaniNet Notification Engine v2

This module provides the Delivery Engine that delivers approved notifications
through supported communication channels.
"""

from .engine import DeliveryEngine, deliver_notification
from .adapters import DeliveryAdapter, InAppAdapter, EmailAdapter, PushAdapter, SMSAdapter, get_adapter

__all__ = [
    'DeliveryEngine',
    'deliver_notification',
    'DeliveryAdapter',
    'InAppAdapter',
    'EmailAdapter',
    'PushAdapter',
    'SMSAdapter',
    'get_adapter',
]
