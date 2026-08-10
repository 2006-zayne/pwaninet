"""
Aggregation module for PwaniNet Notification Engine v2

This module provides the Aggregation Engine that reduces notification fatigue
by combining related Notification Objects into a single notification.
"""

from .engine import AggregationEngine, aggregate_notifications

__all__ = [
    'AggregationEngine',
    'aggregate_notifications',
]
