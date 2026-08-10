"""
Preferences module for PwaniNet Notification Engine v2

This module provides the Preference Engine that evaluates user-specific notification
preferences before delivery.
"""

from .engine import PreferenceEngine, evaluate_notification

__all__ = [
    'PreferenceEngine',
    'evaluate_notification',
]
