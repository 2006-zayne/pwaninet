"""
Event Publisher for PwaniNet Notification Engine v2

This module provides the service for publishing platform events.
Following the specification, events are published after actions complete successfully.
"""
import logging
from typing import Optional, Dict, Any
from django.db import transaction
from django.conf import settings
from django.core.exceptions import ValidationError
from notifications.models import PlatformEvent
from .validator import EventValidator
from .registry import EventSources

logger = logging.getLogger(__name__)


# Flag to enable/disable automatic notification processing
ENABLE_NOTIFICATION_PROCESSING = getattr(settings, 'ENABLE_NOTIFICATION_PROCESSING', True)


class EventPublisher:
    """
    Service for publishing platform events.
    
    Responsibilities:
    - Validate event data
    - Create event records
    - Log event publication
    - Handle publication errors gracefully
    
    Events are published after the originating action completes successfully.
    Publication failures should not prevent the original action from succeeding.
    """
    
    @staticmethod
    @transaction.atomic
    def publish(
        event_type: str,
        source: str,
        action: str,
        target_type: str,
        target_id: str,
        actor=None,
        context_type: Optional[str] = None,
        context_id: Optional[str] = None,
        audience: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        version: str = "1.0"
    ) -> Optional[PlatformEvent]:
        """
        Publish a platform event.
        
        Args:
            event_type: Event type following <domain>.<resource>.<action> pattern
            source: Subsystem publishing the event
            action: Action that occurred (past tense)
            target_type: Type of the target object
            target_id: ID of the target object
            actor: User or system that caused the event
            context_type: Type of the context (optional)
            context_id: ID of the context (optional)
            audience: Intended audience (optional)
            metadata: Additional event-specific information (optional)
            correlation_id: Workflow grouping ID (optional)
            version: Event schema version (default: "1.0")
            
        Returns:
            PlatformEvent: The created event, or None if publication failed
            
        Raises:
            ValidationError: If event data is invalid
        """
        event_data = {
            'event_type': event_type,
            'source': source,
            'action': action,
            'target_type': target_type,
            'target_id': str(target_id),
            'actor': actor,
            'context_type': context_type,
            'context_id': str(context_id) if context_id else None,
            'audience': audience,
            'metadata': metadata or {},
            'correlation_id': correlation_id,
            'version': version
        }
        
        try:
            # Validate event data
            validated_data = EventValidator.validate_event_data(event_data)
            
            # Create event
            event = PlatformEvent.objects.create(**validated_data)
            
            # Log publication
            logger.info(
                f"Event published: {event.event_type} | "
                f"Actor: {event.actor} | "
                f"Target: {event.target_type}:{event.target_id} | "
                f"Event ID: {event.event_id}"
            )
            
            # Note: Notification processing is handled by the signal handler in event_processor.py
            # which triggers on post_save of PlatformEvent. This prevents duplicate processing.
            
            return event
            
        except ValidationError as e:
            # Validation errors should be logged but not raise
            # to avoid breaking the original action
            logger.error(f"Event validation failed: {e}")
            return None
            
        except Exception as e:
            # Other exceptions should be logged but not raise
            # to avoid breaking the original action
            logger.error(f"Event publication failed: {e}", exc_info=True)
            return None
    
    @staticmethod
    def publish_from_dict(event_data: Dict[str, Any]) -> Optional[PlatformEvent]:
        """
        Publish an event from a dictionary.
        
        Convenience method for publishing events when data is already
        structured as a dictionary.
        
        Args:
            event_data: Dictionary containing event data
            
        Returns:
            PlatformEvent: The created event, or None if publication failed
        """
        return EventPublisher.publish(
            event_type=event_data.get('event_type'),
            source=event_data.get('source'),
            action=event_data.get('action'),
            target_type=event_data.get('target_type'),
            target_id=event_data.get('target_id'),
            actor=event_data.get('actor'),
            context_type=event_data.get('context_type'),
            context_id=event_data.get('context_id'),
            audience=event_data.get('audience'),
            metadata=event_data.get('metadata'),
            correlation_id=event_data.get('correlation_id'),
            version=event_data.get('version', '1.0')
        )
    
    @staticmethod
    def publish_legacy_notification_event(
        notification_type: str,
        recipient,
        sender,
        notification_msg: str,
        post=None,
        group=None
    ) -> Optional[PlatformEvent]:
        """
        Publish an event from legacy notification creation.
        
        This is a bridge method to help with migration from the legacy
        notification system. It maps legacy notification types to
        corresponding event types.
        
        Args:
            notification_type: Legacy notification type
            recipient: User receiving the notification
            sender: User who triggered the notification
            notification_msg: Notification message
            post: Related post (optional)
            group: Related group (optional)
            
        Returns:
            PlatformEvent: The created event, or None if publication failed
        """
        # Map legacy notification types to event types
        legacy_to_event_map = {
            'LIKE': 'posts.post.liked',
            'ALERTE': 'posts.comment.created',  # Generic alert
            'FOLLOW': 'users.user.followed',
            'INVITE': 'groups.member.invited',
            'GROUP_REQUEST': 'groups.member.requested',
            'GROUP_APPROVED': 'groups.member.approved',
            'GROUP_REJECTED': 'groups.member.rejected',
            'POST_SHARED': 'posts.post.shared',
            'POST_SHARED_TO_GROUP': 'posts.post.shared_to_group',
            'PINCH': 'users.user.pinched',
            'COMMENT_REPLY': 'posts.comment_reply.created'
        }
        
        event_type = legacy_to_event_map.get(notification_type, 'posts.post.created')
        
        # Determine target
        target_type = 'Post' if post else 'Group' if group else 'User'
        target_id = str(post.id) if post else str(group.id) if group else str(recipient.id)
        
        # Determine context
        context_type = 'Group' if group else None
        context_id = str(group.id) if group else None
        
        # Build metadata
        metadata = {
            'legacy_notification_type': notification_type,
            'notification_message': notification_msg
        }
        
        return EventPublisher.publish(
            event_type=event_type,
            source=EventSources.POSTS.value,
            action=event_type.split('.')[-1],
            target_type=target_type,
            target_id=target_id,
            actor=sender,
            context_type=context_type,
            context_id=context_id,
            audience='SPECIFIC_USER',
            metadata=metadata
        )


# Convenience function for easier importing
def publish_event(**kwargs) -> Optional[PlatformEvent]:
    """
    Convenience function to publish an event.
    
    Usage:
        from notifications.events.publisher import publish_event
        
        publish_event(
            event_type=EventTypes.SOCIAL_POST_LIKED,
            source=EventSources.SOCIAL_PLATFORM,
            action=EventActions.LIKED,
            target_type='Post',
            target_id=post.id,
            actor=user
        )
    """
    return EventPublisher.publish(**kwargs)
