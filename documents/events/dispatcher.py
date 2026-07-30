"""Domain event dispatcher.

This handles emitting and dispatching domain events to interested subscribers.
Events are stored for replay and can be sent to external systems.
"""

import logging
from typing import Callable, Dict, List
from .base import DomainEvent

logger = logging.getLogger(__name__)


class EventDispatcher:
    """Central dispatcher for domain events."""
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._event_store: List[DomainEvent] = []
    
    def subscribe(self, event_type: str, handler: Callable[[DomainEvent], None]):
        """Subscribe a handler to a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.info(f"Subscribed handler to event type: {event_type}")
    
    def unsubscribe(self, event_type: str, handler: Callable[[DomainEvent], None]):
        """Unsubscribe a handler from an event type."""
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(handler)
            logger.info(f"Unsubscribed handler from event type: {event_type}")
    
    def emit(self, event: DomainEvent):
        """Emit a domain event to all subscribers."""
        # Store event for replay
        self._event_store.append(event)
        
        # Dispatch to subscribers
        event_type = event.event_type.value
        handlers = self._subscribers.get(event_type, [])
        
        for handler in handlers:
            try:
                handler(event)
                logger.info(f"Event {event_type} handled by {handler.__name__}")
            except Exception as e:
                logger.error(
                    f"Error handling event {event_type} by {handler.__name__}: {e}",
                    exc_info=True
                )
    
    def get_events(self, event_type: str = None, limit: int = 100):
        """Retrieve events from the store."""
        if event_type:
            events = [e for e in self._event_store if e.event_type.value == event_type]
        else:
            events = self._event_store
        
        return events[-limit:]


# Global event dispatcher instance
event_dispatcher = EventDispatcher()
