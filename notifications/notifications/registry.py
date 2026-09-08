"""
Notification Registry for PwaniNet Notification Engine v2

This module provides centralized registries for notification-related enums.
Following the specification and avoiding string literals throughout the codebase.
"""
from enum import Enum


class NotificationTypes(Enum):
    """
    Canonical notification type registry.
    
    These represent the semantic purpose of notifications.
    """
    
    LIKE = "LIKE"
    COMMENT = "COMMENT"
    COMMENT_REPLY = "COMMENT_REPLY"
    COMMENT_LIKE = "COMMENT_LIKE"
    MENTION = "MENTION"
    ASSIGNMENT = "ASSIGNMENT"
    MEETING = "MEETING"
    WORKSPACE = "WORKSPACE"
    DOCUMENT = "DOCUMENT"
    SECURITY = "SECURITY"
    SYSTEM = "SYSTEM"
    AI = "AI"
    GROUP = "GROUP"
    GROUP_REQUEST = "GROUP_REQUEST"
    GROUP_APPROVED = "GROUP_APPROVED"
    GROUP_REJECTED = "GROUP_REJECTED"
    GROUP_ANNOUNCEMENT = "GROUP_ANNOUNCEMENT"
    FOLLOW = "FOLLOW"
    PINCH = "PINCH"
    INVITE = "INVITE"
    SHARE = "SHARE"
    POST_CREATED = "POST_CREATED"
    
    @classmethod
    def get_all_types(cls):
        """Return all notification type strings."""
        return [ntype.value for ntype in cls]
    
    @classmethod
    def is_valid_type(cls, type_str):
        """Check if a notification type string is valid."""
        return type_str in cls.get_all_types()


class NotificationCategories(Enum):
    """
    Canonical notification category registry.
    
    Categories group related notification types for preference management.
    """
    
    SOCIAL = "SOCIAL"
    ACADEMIC = "ACADEMIC"
    WORKSPACE = "WORKSPACE"
    DOCUMENT = "DOCUMENT"
    SECURITY = "SECURITY"
    SYSTEM = "SYSTEM"
    AI = "AI"
    
    @classmethod
    def get_all_categories(cls):
        """Return all category strings."""
        return [category.value for category in cls]
    
    @classmethod
    def is_valid_category(cls, category_str):
        """Check if a category string is valid."""
        return category_str in cls.get_all_categories()
    
    @classmethod
    def get_types_for_category(cls, category):
        """Get all notification types for a specific category."""
        # Map categories to their types
        category_type_map = {
            'SOCIAL': ['LIKE', 'COMMENT', 'MENTION', 'FOLLOW', 'PINCH', 'SHARE'],
            'ACADEMIC': ['ASSIGNMENT'],
            'WORKSPACE': ['WORKSPACE', 'GROUP', 'INVITE'],
            'DOCUMENT': ['DOCUMENT'],
            'SECURITY': ['SECURITY'],
            'SYSTEM': ['SYSTEM'],
            'AI': ['AI'],
        }
        return category_type_map.get(category, [])


class NotificationPriorities(Enum):
    """
    Canonical notification priority registry.
    
    Priority influences delivery timing, quiet-hour behavior, and presentation order.
    """
    
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"
    
    @classmethod
    def get_all_priorities(cls):
        """Return all priority strings."""
        return [priority.value for priority in cls]
    
    @classmethod
    def is_valid_priority(cls, priority_str):
        """Check if a priority string is valid."""
        return priority_str in cls.get_all_priorities()
    
    @classmethod
    def get_priority_order(cls, priority_str):
        """Get numeric order for priority (higher = more important)."""
        order_map = {
            'CRITICAL': 4,
            'HIGH': 3,
            'NORMAL': 2,
            'LOW': 1,
        }
        return order_map.get(priority_str, 2)


class NotificationStatuses(Enum):
    """
    Canonical notification status registry.
    
    Status represents the lifecycle state of a notification.
    """
    
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    DELIVERED = "DELIVERED"
    SEEN = "SEEN"
    READ = "READ"
    ARCHIVED = "ARCHIVED"
    EXPIRED = "EXPIRED"
    
    @classmethod
    def get_all_statuses(cls):
        """Return all status strings."""
        return [status.value for status in cls]
    
    @classmethod
    def is_valid_status(cls, status_str):
        """Check if a status string is valid."""
        return status_str in cls.get_all_statuses()
    
    @classmethod
    def is_terminal_status(cls, status_str):
        """Check if a status is terminal (no further transitions)."""
        terminal_statuses = ['READ', 'ARCHIVED', 'EXPIRED']
        return status_str in terminal_statuses


class DeliveryPolicies(Enum):
    """
    Canonical delivery policy registry.
    
    Delivery policy defines the intended timing of notification delivery.
    """
    
    IMMEDIATE = "IMMEDIATE"
    SCHEDULED = "SCHEDULED"
    DELAYED = "DELAYED"
    DIGEST = "DIGEST"
    
    @classmethod
    def get_all_policies(cls):
        """Return all policy strings."""
        return [policy.value for policy in cls]
    
    @classmethod
    def is_valid_policy(cls, policy_str):
        """Check if a policy string is valid."""
        return policy_str in cls.get_all_policies()


class ActionTypes(Enum):
    """
    Canonical action type registry for notification actions.
    
    Actions are first-class citizens in the notification system.
    """
    
    ACCEPT = "ACCEPT"
    DECLINE = "DECLINE"
    JOIN = "JOIN"
    SNOOZE = "SNOOZE"
    REVIEW = "REVIEW"
    OPEN = "OPEN"
    VIEW = "VIEW"
    DELETE = "DELETE"
    ARCHIVE = "ARCHIVE"
    MARK_READ = "MARK_READ"
    CUSTOM = "CUSTOM"
    
    @classmethod
    def get_all_action_types(cls):
        """Return all action type strings."""
        return [action.value for action in cls]
    
    @classmethod
    def is_valid_action_type(cls, action_str):
        """Check if an action type string is valid."""
        return action_str in cls.get_all_action_types()
