"""
Rules module for PwaniNet Notification Engine v2

This module provides the Rules Engine that transforms platform events into user notifications.
"""

from .rules import (
    NotificationRule,
    AggregationPolicy,
    RULES_REGISTRY,
    get_rules_for_event,
    get_all_rules
)
from .engine import RulesEngine, process_event

__all__ = [
    'NotificationRule',
    'AggregationPolicy',
    'RULES_REGISTRY',
    'get_rules_for_event',
    'get_all_rules',
    'RulesEngine',
    'process_event',
]
