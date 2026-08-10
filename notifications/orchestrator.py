"""
Notification Orchestrator for PwaniNet Notification Engine v2

This module provides the Notification Orchestrator that coordinates all notification
engines in the correct order to create an end-to-end notification pipeline.

Pipeline: Event → Rules Engine → Aggregation Engine → Preference Engine → Delivery Engine
"""
import logging
from typing import List, Optional
from django.utils import timezone
from notifications.models import PlatformEvent, NotificationObject
from notifications.rules.engine import RulesEngine, process_event
from notifications.aggregation.engine import AggregationEngine, aggregate_notifications
from notifications.preferences.engine import PreferenceEngine, evaluate_notification
from notifications.delivery.engine import DeliveryEngine, deliver_notification

logger = logging.getLogger(__name__)


class NotificationOrchestrator:
    """
    The Notification Orchestrator coordinates all notification engines
    to create an end-to-end notification pipeline.
    
    Pipeline:
    1. Platform Event → Rules Engine (creates notifications)
    2. Notifications → Aggregation Engine (groups related notifications)
    3. Notifications → Preference Engine (evaluates user preferences)
    4. Notifications → Delivery Engine (delivers through channels)
    
    Responsibilities:
    - Coordinate engine execution order
    - Handle errors gracefully
    - Provide end-to-end notification processing
    - Log pipeline execution
    """
    
    @staticmethod
    def process_event(event: PlatformEvent) -> dict:
        """
        Process a platform event through the complete notification pipeline.
        
        Args:
            event: The PlatformEvent to process
            
        Returns:
            Dictionary with pipeline results:
            - notifications_created: Number of notifications created
            - notifications_aggregated: Number of notifications after aggregation
            - notifications_delivered: Number of notifications delivered
            - errors: List of any errors encountered
        """
        logger.info(f"Processing event {event.event_id} through notification pipeline")
        
        results = {
            'notifications_created': 0,
            'notifications_aggregated': 0,
            'notifications_delivered': 0,
            'errors': []
        }
        
        try:
            # Stage 1: Rules Engine - Create notifications from event
            logger.info(f"Stage 1: Rules Engine - Creating notifications from event {event.event_id}")
            notifications = process_event(event)
            results['notifications_created'] = len(notifications)
            
            if not notifications:
                logger.info(f"No notifications created for event {event.event_id}")
                return results
            
            logger.info(f"Created {len(notifications)} notifications for event {event.event_id}")
            
            # Stage 2: Aggregation Engine - Group related notifications
            logger.info(f"Stage 2: Aggregation Engine - Grouping {len(notifications)} notifications")
            aggregated = aggregate_notifications(notifications)
            results['notifications_aggregated'] = len(aggregated)
            
            logger.info(f"Aggregated {len(notifications)} notifications into {len(aggregated)} notifications")
            
            # Stage 3: Preference Engine - Evaluate user preferences
            logger.info(f"Stage 3: Preference Engine - Evaluating preferences for {len(aggregated)} notifications")
            approved_notifications = []
            
            for notification in aggregated:
                try:
                    # Check if notification is allowed for in-app delivery
                    allowed, channels = evaluate_notification(notification, 'IN_APP')
                    
                    if allowed:
                        approved_notifications.append((notification, channels))
                        logger.info(f"Notification {notification.notification_id} approved for channels: {channels}")
                    else:
                        logger.info(f"Notification {notification.notification_id} blocked by preferences")
                        
                except Exception as e:
                    logger.error(f"Preference evaluation failed for notification {notification.notification_id}: {e}")
                    results['errors'].append(f"Preference evaluation failed: {e}")
            
            logger.info(f"Preference engine approved {len(approved_notifications)} notifications")
            
            # Stage 4: Delivery Engine - Deliver approved notifications
            logger.info(f"Stage 4: Delivery Engine - Delivering {len(approved_notifications)} notifications")
            
            for notification, channels in approved_notifications:
                try:
                    # Deliver through allowed channels
                    attempts = deliver_notification(notification, channels)
                    results['notifications_delivered'] += len(attempts)
                    
                    logger.info(f"Delivered notification {notification.notification_id} through {len(attempts)} channels")
                    
                except Exception as e:
                    logger.error(f"Delivery failed for notification {notification.notification_id}: {e}")
                    results['errors'].append(f"Delivery failed: {e}")
            
            logger.info(f"Pipeline complete for event {event.event_id}")
            logger.info(f"Results: {results}")
            
        except Exception as e:
            logger.error(f"Pipeline failed for event {event.event_id}: {e}")
            results['errors'].append(f"Pipeline failed: {e}")
        
        return results
    
    @staticmethod
    def process_event_async(event: PlatformEvent):
        """
        Process a platform event asynchronously.
        
        This is a placeholder for future implementation with a task queue
        (e.g., Celery, Django Q). For now, it processes synchronously.
        
        Args:
            event: The PlatformEvent to process
        """
        # TODO: Implement async processing with Celery or Django Q
        # For now, process synchronously
        return NotificationOrchestrator.process_event(event)
    
    @staticmethod
    def process_batch(events: List[PlatformEvent]) -> dict:
        """
        Process multiple platform events through the notification pipeline.
        
        Args:
            events: List of PlatformEvents to process
            
        Returns:
            Dictionary with batch results:
            - events_processed: Number of events processed
            - total_notifications_created: Total notifications created
            - total_notifications_delivered: Total notifications delivered
            - errors: List of any errors encountered
        """
        logger.info(f"Processing batch of {len(events)} events")
        
        batch_results = {
            'events_processed': 0,
            'total_notifications_created': 0,
            'total_notifications_delivered': 0,
            'errors': []
        }
        
        for event in events:
            try:
                results = NotificationOrchestrator.process_event(event)
                
                batch_results['events_processed'] += 1
                batch_results['total_notifications_created'] += results['notifications_created']
                batch_results['total_notifications_delivered'] += results['notifications_delivered']
                batch_results['errors'].extend(results['errors'])
                
            except Exception as e:
                logger.error(f"Failed to process event {event.event_id}: {e}")
                batch_results['errors'].append(f"Event processing failed: {e}")
        
        logger.info(f"Batch processing complete: {batch_results}")
        return batch_results


def process_notification_event(event: PlatformEvent) -> dict:
    """
    Convenience function to process a platform event through the notification pipeline.
    
    Args:
        event: The PlatformEvent to process
        
    Returns:
        Dictionary with pipeline results
    """
    return NotificationOrchestrator.process_event(event)
