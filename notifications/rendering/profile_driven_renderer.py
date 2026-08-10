"""
Profile-Driven Notification Renderer
Orchestrates the complete rendering pipeline following the Rendering Decision Engine specification.

Pipeline:
Notification Payload → Rendering Profile Resolver → Notification Message Engine → 
Component Visibility Resolver → Preview Resolver → Action Resolver → Status Resolver → 
Interaction Resolver → Navigation Resolver → Notification Card Renderer
"""

from typing import Dict, Any, Optional
from .payload_models import NotificationPayload
from .profile_models import RenderingProfile
from .profile_resolver import profile_resolver
from .message_engine import message_engine
from .resolvers import (
    component_visibility_resolver,
    preview_resolver,
    action_resolver,
    status_resolver,
    interaction_resolver,
    navigation_resolver,
    expansion_resolver,
    aggregation_resolver,
)


class ProfileDrivenRenderer:
    """
    Profile-driven notification renderer.
    
    The renderer MUST NOT contain notification-specific conditionals.
    It only understands Rendering Profiles.
    
    Incorrect:
        if (notification.type === "POST_LIKE") { ... }
    
    Correct:
        payload → profile resolver → profile → renderer
    """
    
    def render(self, payload) -> Dict[str, Any]:
        """
        Render a notification using the profile-driven pipeline.
        
        Args:
            payload: NotificationPayload instance or dict
            
        Returns:
            Complete rendering context for the notification card
        """
        # Step 1: Resolve Rendering Profile
        profile = profile_resolver.resolve(payload)
        
        # Step 2: Generate Message
        message = message_engine.generate_message(payload)
        
        # Step 2.5: Generate Summary
        notification_type = payload.type if hasattr(payload, 'type') else payload.get('type', 'GENERIC')
        
        # Determine if this is an aggregated notification based on actor count
        is_aggregated = False
        actors = payload.actors if hasattr(payload, 'actors') else payload.get('actors', [])
        if len(actors) > 1:
            is_aggregated = True
        
        summary = message_engine.get_summary(notification_type, is_aggregated)
        
        # Step 3: Resolve Component Visibility
        component_visibility = component_visibility_resolver.resolve(profile, payload)
        
        # Step 4: Resolve Preview
        preview = preview_resolver.resolve(profile, payload)
        
        # Step 5: Resolve Actions
        # For now, use the adapter to build actions with proper URLs
        # This is a temporary fix until the action_resolver can handle URL building
        from .adapters import get_payload_adapter
        try:
            # Get the original notification object from the payload
            if isinstance(payload, dict):
                notification_id = payload.get('identity', {}).get('notification_id')
            else:
                notification_id = payload.identity.notification_id
            
            if notification_id:
                from notifications.models import NotificationObject
                notification = NotificationObject.objects.get(notification_id=notification_id)
                adapter = get_payload_adapter(notification)
                adapter_actions = adapter._resolve_actions(notification)
                # Convert to dict format for template
                actions = []
                for action in adapter_actions:
                    if isinstance(action, dict):
                        actions.append(action)
                    else:
                        actions.append({
                            'id': action.id,
                            'label': action.label,
                            'style': action.style,
                            'enabled': action.enabled,
                            'url': action.url,
                            'method': action.method,
                            'payload': action.payload,
                        })
            else:
                actions = action_resolver.resolve(profile, payload)
        except Exception:
            # Fallback to action_resolver if adapter fails
            actions = action_resolver.resolve(profile, payload)
        
        # Step 6: Resolve Status
        status = status_resolver.resolve(profile, payload)
        
        # Step 7: Resolve Interactions
        interactions = interaction_resolver.resolve(profile, payload)
        
        # Step 8: Resolve Navigation
        navigation = navigation_resolver.resolve(profile, payload)
        
        # Step 9: Resolve Expansion
        expansion = expansion_resolver.resolve(profile, payload)
        
        # Step 10: Resolve Aggregation
        aggregation = aggregation_resolver.resolve(profile, payload)
        
        # Convert payload to dict if it's a NotificationPayload object
        if isinstance(payload, dict):
            payload_dict = payload
            payload_obj = None
        else:
            payload_dict = payload.to_dict()
            payload_obj = payload
        
        # Assemble complete rendering context
        rendering_context = {
            # Original payload (use object if available for datetime access, otherwise dict)
            'payload': payload_obj if payload_obj else payload_dict,
            
            # Profile information
            'profile': profile.to_dict(),
            
            # Generated message
            'message': message,
            
            # Summary for header
            'summary': summary,
            
            # Component visibility
            'components': component_visibility,
            
            # Preview configuration
            'preview': preview,
            
            # Actions
            'actions': actions,
            
            # Status
            'status': status,
            
            # Interactions
            'interactions': interactions,
            
            # Navigation
            'navigation': navigation,
            
            # Expansion
            'expansion': expansion,
            
            # Aggregation
            'aggregation': aggregation,
        }
        
        return rendering_context
    
    def render_batch(self, payloads: list) -> list:
        """
        Render multiple notifications using the profile-driven pipeline.
        
        Args:
            payloads: List of NotificationPayload instances
            
        Returns:
            List of rendering contexts
        """
        return [self.render(payload) for payload in payloads]
    
    def get_profile_info(self, notification_type: str) -> Dict[str, Any]:
        """
        Get profile information for a notification type.
        
        Args:
            notification_type: Type of notification
            
        Returns:
            Profile information
        """
        profile = profile_resolver.resolve_by_type(notification_type)
        return profile.to_dict()
    
    def list_available_profiles(self) -> Dict[str, Dict[str, Any]]:
        """
        List all available rendering profiles.
        
        Returns:
            Dict mapping notification types to profile information
        """
        from .profile_registry import profile_registry
        profiles = profile_registry.list_profiles()
        return {
            notification_type: profile.to_dict()
            for notification_type, profile in profiles.items()
        }


# Global renderer instance
profile_driven_renderer = ProfileDrivenRenderer()
