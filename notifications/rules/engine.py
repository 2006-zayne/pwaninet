"""
Rules Engine for PwaniNet Notification Engine v2

This module implements the Rules Engine that transforms platform events into user notifications.
Following the specification, it evaluates events against rules and creates Notification Objects.
"""
import logging
from typing import List, Dict, Any, Optional
from django.contrib.auth import get_user_model
from django.db import transaction
from notifications.models import PlatformEvent, NotificationObject, NotificationAction
from notifications.notifications.registry import NotificationTypes, NotificationCategories, NotificationPriorities, NotificationStatuses, DeliveryPolicies, ActionTypes
from .rules import get_rules_for_event, NotificationRule

User = get_user_model()

logger = logging.getLogger(__name__)


class RulesEngine:
    """
    The Rules Engine evaluates platform events and creates notifications.
    
    Responsibilities:
    - Consume platform events
    - Evaluate notification rules
    - Identify recipients
    - Assign priorities, categories, and policies
    - Generate Notification Objects
    - Pass notifications to downstream engines
    
    It does NOT:
    - Deliver notifications
    - Send push messages
    - Send emails
    - Render UI
    - Store user preferences
    """
    
    @staticmethod
    @transaction.atomic
    def process_event(event: PlatformEvent) -> List[NotificationObject]:
        """
        Process a platform event and create notifications.
        
        Args:
            event: The PlatformEvent to process
            
        Returns:
            List of created Notification Objects
        """
        logger.info(f"Processing event: {event.event_type} (ID: {event.event_id})")
        
        # Get matching rules for this event type
        rules = get_rules_for_event(event.event_type)
        
        if not rules:
            logger.info(f"No rules found for event type: {event.event_type}")
            return []
        
        notifications = []
        
        for rule in rules:
            try:
                # Evaluate rule condition
                if rule.condition and not rule.condition(RulesEngine._event_to_dict(event)):
                    logger.info(f"Rule {rule.name} condition failed for event {event.event_id}")
                    continue
                
                # Determine recipients
                recipient_ids = rule.recipients(RulesEngine._event_to_dict(event))
                
                if not recipient_ids:
                    logger.info(f"Rule {rule.name} produced no recipients for event {event.event_id}")
                    continue
                
                # Create notification for each recipient
                for recipient_id in recipient_ids:
                    try:
                        notification = RulesEngine._create_notification(
                            event=event,
                            rule=rule,
                            recipient_id=recipient_id
                        )
                        notifications.append(notification)
                        
                        # Create actions if defined
                        if rule.actions:
                            RulesEngine._create_actions(notification, rule, event)
                        
                    except Exception as e:
                        logger.error(f"Failed to create notification for recipient {recipient_id}: {e}", exc_info=True)
                        continue
                
                logger.info(f"Rule {rule.name} created {len(recipient_ids)} notifications")
                
            except Exception as e:
                logger.error(f"Rule {rule.name} failed to evaluate: {e}", exc_info=True)
                # Continue with other rules per specification
                continue
        
        logger.info(f"Event {event.event_id} processed, created {len(notifications)} notifications")
        return notifications
    
    @staticmethod
    def _event_to_dict(event: PlatformEvent) -> Dict[str, Any]:
        """
        Convert a PlatformEvent to a dictionary for rule evaluation.
        
        This extracts relevant information from the event and related objects
        to make it available to rule conditions and recipient functions.
        """
        event_dict = {
            'event_id': str(event.event_id),
            'event_type': event.event_type,
            'actor_id': event.actor.id if event.actor else None,
            'actor_username': event.actor.username if event.actor else None,
            'source': event.source,
            'action': event.action,
            'target_type': event.target_type,
            'target_id': event.target_id,
            'context_type': event.context_type,
            'context_id': event.context_id,
            'metadata': event.metadata or {},
            'timestamp': event.timestamp,
        }
        
        # Extract additional context from metadata
        # This will be enhanced when we have actual model access
        if event.metadata:
            event_dict.update(event.metadata)
        
        # Fallback: if actor relationship is None but metadata has actor info, use it
        if not event_dict['actor_id'] and event.metadata:
            if 'actor_id' in event.metadata:
                event_dict['actor_id'] = int(event.metadata['actor_id'])
            if 'actor_username' in event.metadata:
                event_dict['actor_username'] = event.metadata['actor_username']
        
        return event_dict
    
    @staticmethod
    def _create_notification(event: PlatformEvent, rule: NotificationRule, recipient_id: int) -> NotificationObject:
        """
        Create a NotificationObject from an event and rule.
        
        Args:
            event: The PlatformEvent
            rule: The NotificationRule
            recipient_id: The recipient user ID
            
        Returns:
            The created NotificationObject
        """
        event_dict = RulesEngine._event_to_dict(event)
        
        # Generate aggregation key
        aggregation_key = RulesEngine._generate_aggregation_key(event, rule)
        
        # Check if aggregation is enabled and if a similar notification exists within the aggregation window
        if rule.aggregation_policy != "NEVER" and aggregation_key:
            from notifications.aggregation.engine import AggregationEngine
            from datetime import timedelta
            from django.utils import timezone
            
            window_minutes = AggregationEngine.get_aggregation_window(rule.notification_type)
            if window_minutes:
                window_start = timezone.now() - timedelta(minutes=window_minutes)
                
                # Look for existing notification with same aggregation key for this recipient
                existing = NotificationObject.objects.filter(
                    recipient_id=recipient_id,
                    notification_type=rule.notification_type,
                    aggregation_key=aggregation_key,
                    created_at__gte=window_start
                ).order_by('-created_at').first()
                
                if existing:
                    # Update existing notification instead of creating new one
                    logger.info(f"Updating existing notification {existing.notification_id} instead of creating new one")
                    
                    # Merge source events
                    all_source_events = set(existing.source_events or [])
                    all_source_events.add(str(event.event_id))
                    existing.source_events = list(all_source_events)
                    
                    # Update event count
                    existing.event_count = len(all_source_events)
                    
                    # Update latest event time
                    existing.latest_event_time = event.timestamp
                    
                    # Update summary
                    existing.summary = AggregationEngine._generate_aggregated_summary(existing)
                    
                    # Update timestamp to move notification to the top
                    now = timezone.now()
                    existing.updated_at = event.timestamp if event.timestamp and event.timestamp > (existing.updated_at or existing.created_at) else now
                    
                    update_fields = ['source_events', 'event_count', 'latest_event_time', 'summary', 'updated_at']
                    
                    # If existing notification was already read, reset to DELIVERED so user sees new activity
                    if existing.status == NotificationStatuses.READ.value:
                        existing.status = NotificationStatuses.DELIVERED.value
                        update_fields.append('status')
                    
                    # Update metadata if target info is missing
                    meta = existing.metadata or {}
                    if not meta.get('target_id') and event.target_id:
                        meta['target_type'] = event.target_type
                        meta['target_id'] = str(event.target_id)
                        if event.metadata and event.metadata.get('thumbnail_url') and not meta.get('thumbnail_url'):
                            meta['thumbnail_url'] = event.metadata.get('thumbnail_url')
                        existing.metadata = meta
                        update_fields.append('metadata')
                    
                    # Save the changes
                    existing.save(update_fields=update_fields)
                    
                    return existing

        # Deduplication check for non-aggregated notifications (e.g. rapid duplicate approvals)
        if rule.aggregation_policy == "NEVER":
            from datetime import timedelta
            from django.utils import timezone
            dedup_window = timezone.now() - timedelta(minutes=2)
            existing_duplicate = NotificationObject.objects.filter(
                recipient_id=recipient_id,
                notification_type=rule.notification_type,
                context_type=event.context_type,
                context_id=event.context_id,
                created_at__gte=dedup_window
            ).order_by('-created_at').first()
            if existing_duplicate:
                logger.info(
                    f"Deduplicating notification {existing_duplicate.notification_id} for recipient {recipient_id} "
                    f"(event {event.event_id}, type {rule.notification_type})"
                )
                if event.event_id and str(event.event_id) not in (existing_duplicate.source_events or []):
                    existing_duplicate.source_events = list(set((existing_duplicate.source_events or []) + [str(event.event_id)]))
                    existing_duplicate.save(update_fields=['source_events'])
                return existing_duplicate
        
        # Generate title with safe formatting
        if rule.title_template:
            try:
                title = rule.title_template.format(**event_dict)
            except KeyError:
                # If template variables are missing, use default
                title = f"{rule.notification_type} notification"
        else:
            title = f"{rule.notification_type} notification"
        
        # Generate summary with safe formatting
        if rule.summary_template:
            try:
                summary = rule.summary_template.format(**event_dict)
            except KeyError:
                summary = ""
        else:
            summary = ""
        
        # Create notification
        # Include actor information in metadata for push notifications
        actor_avatar = None
        if event.actor and hasattr(event.actor, 'profile_picture'):
            actor_avatar = event.actor.profile_picture.url if event.actor.profile_picture else None

        notification = NotificationObject.objects.create(
            recipient_id=recipient_id,
            source_events=[str(event.event_id)],
            notification_type=rule.notification_type,
            category=rule.category,
            priority=rule.priority,
            title=title,
            summary=summary,
            context_type=event.context_type,
            context_id=event.context_id,
            status=NotificationStatuses.CREATED.value,
            delivery_policy=rule.delivery_policy,
            aggregation_key=aggregation_key if rule.aggregation_policy != "NEVER" else None,
            event_count=1,
            first_event_time=event.timestamp,
            latest_event_time=event.timestamp,
            updated_at=event.timestamp,
            metadata={
                'event_type': event.event_type,
                'actor_id': str(event.actor.id) if event.actor else None,
                'actor_username': event.actor.username if event.actor else None,
                'actor_avatar': actor_avatar,
                'target_type': event.target_type,
                'target_id': str(event.target_id) if event.target_id else None,
                **(event.metadata or {})
            }
        )
        
        return notification
    
    @staticmethod
    def _generate_aggregation_key(event: PlatformEvent, rule: NotificationRule) -> str:
        """
        Generate an aggregation key for the notification.
        
        The aggregation key groups related notifications together.
        Format: <notification_type>:<target_type>:<target_id>
        """
        return f"{rule.notification_type}:{event.target_type}:{event.target_id}"
    
    @staticmethod
    def _create_actions(notification: NotificationObject, rule: NotificationRule, event: PlatformEvent):
        """
        Create notification actions from the rule.
        
        Args:
            notification: The NotificationObject
            rule: The NotificationRule
            event: The PlatformEvent
        """
        if not rule.actions:
            return
        
        event_dict = RulesEngine._event_to_dict(event)
        # Add notification_id to event_dict for action builders
        event_dict['notification_id'] = str(notification.notification_id)
        action_configs = rule.actions(event_dict)
        
        for action_config in action_configs:
            NotificationAction.objects.create(
                notification=notification,
                action_type=action_config.get('action_type'),
                label=action_config.get('label'),
                url=action_config.get('url', ''),
                method=action_config.get('method', 'GET'),
                payload=action_config.get('payload', {}),
                is_primary=action_config.get('is_primary', False),
                order=action_config.get('order', 0)
            )


def process_event(event: PlatformEvent) -> List[NotificationObject]:
    """
    Convenience function to process an event through the Rules Engine.
    
    Args:
        event: The PlatformEvent to process
        
    Returns:
        List of created Notification Objects
    """
    return RulesEngine.process_event(event)
