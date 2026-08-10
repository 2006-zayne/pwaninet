"""
Event Validator for PwaniNet Notification Engine v2

This module validates platform events before they are published.
Ensures events conform to the specification and contain required fields.
"""
from django.core.exceptions import ValidationError
from .registry import EventTypes, EventSources, EventActions


class EventValidator:
    """
    Validates platform events before publication.
    
    Ensures events conform to the specification:
    - Has required fields
    - Uses valid event types
    - Uses valid sources
    - Uses valid actions
    - Follows naming conventions
    """
    
    REQUIRED_FIELDS = ['event_type', 'source', 'action', 'target_type', 'target_id']
    
    @classmethod
    def validate_event_data(cls, event_data):
        """
        Validate event data before publication.
        
        Args:
            event_data: Dictionary containing event data
            
        Raises:
            ValidationError: If event data is invalid
            
        Returns:
            dict: Validated event data
        """
        errors = {}
        
        # Check required fields
        for field in cls.REQUIRED_FIELDS:
            if field not in event_data or event_data[field] is None:
                errors[field] = f"{field} is required"
        
        if errors:
            raise ValidationError(errors)
        
        # Validate event type
        if not EventTypes.is_valid_event_type(event_data['event_type']):
            errors['event_type'] = f"Invalid event type: {event_data['event_type']}"
        
        # Validate source
        if not EventSources.is_valid_source(event_data['source']):
            errors['source'] = f"Invalid source: {event_data['source']}"
        
        # Validate action
        if not EventActions.is_valid_action(event_data['action']):
            errors['action'] = f"Invalid action: {event_data['action']}"
        
        # Validate event type matches action (basic check)
        if not cls._event_type_matches_action(event_data['event_type'], event_data['action']):
            errors['event_type'] = f"Event type {event_data['event_type']} does not match action {event_data['action']}"
        
        # Validate target
        if not event_data['target_type'] or not event_data['target_id']:
            errors['target'] = "Both target_type and target_id are required"
        
        # Validate metadata is a dict if provided
        if 'metadata' in event_data and event_data['metadata'] is not None:
            if not isinstance(event_data['metadata'], dict):
                errors['metadata'] = "Metadata must be a dictionary"
        
        if errors:
            raise ValidationError(errors)
        
        return event_data
    
    @classmethod
    def _event_type_matches_action(cls, event_type, action):
        """
        Check if the action in event type matches the provided action.
        
        Example:
        event_type = "social.post.created"
        action = "created"
        Returns True
        """
        # Extract action from event type (last part after last dot)
        event_type_action = event_type.split('.')[-1]
        return event_type_action == action
    
    @classmethod
    def validate_event_object(cls, event):
        """
        Validate a PlatformEvent model instance.
        
        Args:
            event: PlatformEvent instance
            
        Raises:
            ValidationError: If event is invalid
        """
        errors = {}
        
        # Check required fields
        if not event.event_type:
            errors['event_type'] = "Event type is required"
        
        if not event.source:
            errors['source'] = "Source is required"
        
        if not event.action:
            errors['action'] = "Action is required"
        
        if not event.target_type:
            errors['target_type'] = "Target type is required"
        
        if not event.target_id:
            errors['target_id'] = "Target ID is required"
        
        # Validate against registries
        if event.event_type and not EventTypes.is_valid_event_type(event.event_type):
            errors['event_type'] = f"Invalid event type: {event.event_type}"
        
        if event.source and not EventSources.is_valid_source(event.source):
            errors['source'] = f"Invalid source: {event.source}"
        
        if event.action and not EventActions.is_valid_action(event.action):
            errors['action'] = f"Invalid action: {event.action}"
        
        # Validate consistency
        if event.event_type and event.action:
            if not cls._event_type_matches_action(event.event_type, event.action):
                errors['event_type'] = f"Event type {event.event_type} does not match action {event.action}"
        
        # Validate context consistency
        if event.context_type and not event.context_id:
            errors['context'] = "context_id is required when context_type is provided"
        
        if event.context_id and not event.context_type:
            errors['context'] = "context_type is required when context_id is provided"
        
        if errors:
            raise ValidationError(errors)
