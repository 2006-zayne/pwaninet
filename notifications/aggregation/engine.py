"""
Aggregation Engine for PwaniNet Notification Engine v2

This module implements the Aggregation Engine that reduces notification fatigue
by combining related Notification Objects into a single notification.
Following Chapter 7 of the specification.
"""
import logging
from typing import List, Optional, Dict, Set
from datetime import timedelta
from django.utils import timezone
from notifications.models import NotificationObject, PlatformEvent
from notifications.notifications.registry import NotificationPriorities

logger = logging.getLogger(__name__)


class AggregationEngine:
    """
    The Aggregation Engine reduces notification fatigue by intelligently combining
    related Notification Objects into a single, coherent notification.
    
    Responsibilities:
    - Reduce notification noise
    - Preserve important information
    - Improve readability
    - Maintain event traceability
    - Support evolving notifications
    - Minimize duplicate notifications
    
    It does NOT:
    - Modify Platform Events
    - Deliver notifications
    - Generate notifications
    """
    
    # Aggregation windows for different notification types (in minutes)
    AGGREGATION_WINDOWS = {
        'LIKE': 30,           # 30 minutes
        'COMMENT': 15,        # 15 minutes
        'COMMENT_REPLY': 15,  # 15 minutes
        'COMMENT_LIKE': 30,   # 30 minutes
        'MENTION': 15,        # 15 minutes
        'FOLLOW': 24 * 60,    # 24 hours
        'PINCH': 24 * 60,     # 24 hours
        'GROUP': None,         # Until reviewed (never aggregate)
        'INVITE': None,        # Never aggregate
        'SHARE': 30,           # 30 minutes
        'ASSIGNMENT': 60,      # 1 hour
        'MEETING': None,       # Never aggregate
        'DOCUMENT': 30,        # 30 minutes
        'WORKSPACE': 60,       # 1 hour
        'SECURITY': None,      # Never aggregate
        'SYSTEM': None,        # Never aggregate
        'AI': 30,              # 30 minutes
    }
    
    # Notification types that should never be aggregated
    NEVER_AGGREGATE_TYPES = {
        'GROUP', 'INVITE', 'MEETING', 'SECURITY', 'SYSTEM'
    }
    
    @staticmethod
    def aggregate_notifications(notifications: List[NotificationObject]) -> List[NotificationObject]:
        """
        Aggregate a list of notifications.
        
        Groups notifications by aggregation key and merges eligible notifications
        within the aggregation window.
        
        Args:
            notifications: List of NotificationObjects to aggregate
            
        Returns:
            List of aggregated NotificationObjects
        """
        logger.info(f"Aggregating {len(notifications)} notifications")
        
        if not notifications:
            return []
        
        # Group notifications by aggregation key
        grouped = AggregationEngine._group_by_aggregation_key(notifications)
        
        # Aggregate each group
        aggregated = []
        for group_key, group_notifications in grouped.items():
            if len(group_notifications) == 1:
                # No aggregation needed
                aggregated.append(group_notifications[0])
            else:
                # Try to aggregate the group
                result = AggregationEngine._aggregate_group(group_notifications)
                if result:
                    aggregated.append(result)
                else:
                    # Aggregation failed, keep original notifications
                    aggregated.extend(group_notifications)
        
        logger.info(f"Aggregation complete: {len(notifications)} → {len(aggregated)} notifications")
        return aggregated
    
    @staticmethod
    def _group_by_aggregation_key(notifications: List[NotificationObject]) -> Dict[str, List[NotificationObject]]:
        """
        Group notifications by their aggregation key.
        
        Only groups notifications that have the same:
        - Recipient
        - Notification Type
        - Category
        - Context
        - Aggregation Key
        """
        grouped = {}
        
        for notification in notifications:
            # Skip notifications that should never be aggregated
            if notification.notification_type in AggregationEngine.NEVER_AGGREGATE_TYPES:
                key = f"never_aggregate_{notification.notification_id}"
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(notification)
                continue
            
            # Skip critical notifications
            if notification.priority == 'CRITICAL':
                key = f"critical_{notification.notification_id}"
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(notification)
                continue
            
            # Group by combination of recipient, type, category, context, and aggregation key
            # This ensures notifications with different recipients or categories don't get grouped
            # For notifications without aggregation_key, use notification_id to prevent grouping
            key_parts = [
                str(notification.recipient_id),
                notification.notification_type,
                notification.category,
                notification.context_type or '',
                notification.context_id or '',
                str(notification.aggregation_key or notification.notification_id)  # Use notification_id if no aggregation key
            ]
            key = '|'.join(key_parts)
            
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(notification)
        
        return grouped
    
    @staticmethod
    def _aggregate_group(notifications: List[NotificationObject]) -> Optional[NotificationObject]:
        """
        Aggregate a group of notifications with the same aggregation key.
        
        Only aggregates if all notifications are within the aggregation window.
        Uses incremental updates to minimize processing overhead.
        
        Args:
            notifications: List of notifications with same aggregation key
            
        Returns:
            Aggregated NotificationObject or None if aggregation not possible
        """
        if not notifications:
            return None
        
        if len(notifications) == 1:
            return notifications[0]
        
        # Sort by creation time (oldest first)
        notifications.sort(key=lambda n: n.created_at)
        
        # Use the oldest notification as the base
        base = notifications[0]
        
        # Check aggregation window
        if not AggregationEngine._is_within_aggregation_window(notifications):
            logger.info(f"Notifications not within aggregation window for key {base.aggregation_key}")
            return None
        
        # Merge notifications into base
        AggregationEngine._merge_notifications(base, notifications[1:])
        
        return base
    
    @staticmethod
    def _is_within_aggregation_window(notifications: List[NotificationObject]) -> bool:
        """
        Check if all notifications are within the aggregation window.
        
        Args:
            notifications: List of notifications to check
            
        Returns:
            True if all notifications are within the window
        """
        if not notifications:
            return False
        
        # Get aggregation window for this notification type
        notification_type = notifications[0].notification_type
        window_minutes = AggregationEngine.AGGREGATION_WINDOWS.get(notification_type)
        
        # If window is None, never aggregate
        if window_minutes is None:
            return False
        
        # Check if all notifications are within the window
        # Use first_event_time for window check (when the underlying event occurred)
        # This is more accurate than created_at for aggregation purposes
        oldest = min(notifications, key=lambda n: n.first_event_time if n.first_event_time else n.created_at)
        newest = max(notifications, key=lambda n: n.latest_event_time if n.latest_event_time else n.created_at)
        
        oldest_time = oldest.first_event_time if oldest.first_event_time else oldest.created_at
        newest_time = newest.latest_event_time if newest.latest_event_time else newest.created_at
        
        time_diff = newest_time - oldest_time
        window = timedelta(minutes=window_minutes)
        
        return time_diff <= window
    
    @staticmethod
    def _merge_notifications(base: NotificationObject, others: List[NotificationObject]):
        """
        Merge other notifications into the base notification.
        
        Performs incremental updates:
        - Merge source events
        - Update event count
        - Update first/latest event times
        - Update summary
        - Update timestamp
        
        Args:
            base: The base notification to merge into
            others: List of notifications to merge
        """
        # Merge source events
        all_source_events = set(base.source_events or [])
        for other in others:
            all_source_events.update(other.source_events or [])
        base.source_events = list(all_source_events)
        
        # Update event count
        base.event_count = len(all_source_events)
        
        # Update first and latest event times
        all_times = [base.first_event_time] if base.first_event_time else []
        for other in others:
            if other.first_event_time:
                all_times.append(other.first_event_time)
            if other.latest_event_time:
                all_times.append(other.latest_event_time)
        
        if all_times:
            base.first_event_time = min(all_times)
            base.latest_event_time = max(all_times)
        
        # Update summary based on event count
        base.summary = AggregationEngine._generate_aggregated_summary(base)
        
        # Update timestamp to latest event time (not current time)
        # This ensures the notification moves up based on when the last action occurred
        if base.latest_event_time:
            base.updated_at = base.latest_event_time
        else:
            base.updated_at = timezone.now()
        
        # Mark as unread if it was previously read and new events are being aggregated
        # This ensures aggregated notifications with new actions appear as unread
        if base.status == 'READ':
            base.status = 'DELIVERED'
        
        # Save the changes
        base.save(update_fields=[
            'source_events', 'event_count', 'first_event_time', 
            'latest_event_time', 'summary', 'updated_at', 'status'
        ])
        
        # Delete the merged notifications
        for other in others:
            other.delete()
    
    @staticmethod
    def _generate_aggregated_summary(notification: NotificationObject) -> str:
        """
        Generate a summary for an aggregated notification.
        
        Args:
            notification: The aggregated notification
            
        Returns:
            Generated summary string
        """
        event_count = notification.event_count or 1
        
        if event_count == 1:
            return notification.summary or ""
        
        # Generate summary based on notification type and count
        if notification.notification_type == 'LIKE':
            if event_count <= 3:
                return f"{event_count} people liked your post"
            elif event_count < 100:
                return f"{event_count} people liked your post"
            else:
                return f"100+ people liked your post"
        
        elif notification.notification_type == 'COMMENT':
            if event_count <= 3:
                return f"{event_count} people commented on your post"
            else:
                return f"{event_count} comments on your post"
        
        elif notification.notification_type == 'FOLLOW':
            return f"{event_count} new followers"
        
        elif notification.notification_type == 'SHARE':
            return f"Your post was shared {event_count} times"
        
        elif notification.notification_type == 'MENTION':
            return f"You were mentioned {event_count} times"
        
        else:
            return f"{event_count} notifications"
    
    @staticmethod
    def get_aggregation_window(notification_type: str) -> Optional[int]:
        """
        Get the aggregation window for a notification type.
        
        Args:
            notification_type: The notification type
            
        Returns:
            Aggregation window in minutes, or None if never aggregate
        """
        return AggregationEngine.AGGREGATION_WINDOWS.get(notification_type)


def aggregate_notifications(notifications: List[NotificationObject]) -> List[NotificationObject]:
    """
    Convenience function to aggregate notifications through the Aggregation Engine.
    
    Args:
        notifications: List of NotificationObjects to aggregate
        
    Returns:
        List of aggregated NotificationObjects
    """
    return AggregationEngine.aggregate_notifications(notifications)
