"""
Rendering Profile Resolver
Resolves notification types to their Rendering Profiles.
Input: Notification Payload
Output: Rendering Profile
"""

from typing import Optional
from .payload_models import NotificationPayload
from .profile_models import RenderingProfile
from .profile_registry import profile_registry


class RenderingProfileResolver:
    """
    Resolves notification types to Rendering Profiles.
    
    The resolver MUST:
    - Validate the notification type
    - Locate the correct profile
    - Expose the profile to the renderer
    - Fail gracefully for unknown types (use Generic Profile)
    """
    
    def __init__(self):
        self._registry = profile_registry
        self._cache = {}  # Cache for resolved profiles
    
    def resolve(self, payload) -> RenderingProfile:
        """
        Resolve the Rendering Profile for a notification payload.
        
        Args:
            payload: NotificationPayload instance or dict
            
        Returns:
            RenderingProfile instance
        """
        # Handle both NotificationPayload objects and dict payloads
        if isinstance(payload, dict):
            notification_type = payload.get('type')
        else:
            notification_type = payload.type
        
        # Check cache first
        if notification_type in self._cache:
            return self._cache[notification_type]
        
        # Validate notification type
        if not notification_type or not isinstance(notification_type, str):
            # Fallback to generic profile for invalid types
            profile = self._registry.get_profile("GENERIC")
            self._cache["GENERIC"] = profile
            return profile
        
        # Locate the correct profile
        profile = self._registry.get_profile(notification_type)
        
        # Cache the resolved profile
        self._cache[notification_type] = profile
        
        return profile
    
    def resolve_by_type(self, notification_type: str) -> RenderingProfile:
        """
        Resolve profile by notification type directly.
        
        Args:
            notification_type: String notification type
            
        Returns:
            RenderingProfile instance
        """
        # Check cache first
        if notification_type in self._cache:
            return self._cache[notification_type]
        
        # Get profile from registry (falls back to GENERIC if not found)
        profile = self._registry.get_profile(notification_type)
        
        # Cache the resolved profile
        self._cache[notification_type] = profile
        
        return profile
    
    def is_known_type(self, notification_type: str) -> bool:
        """
        Check if a notification type is known (has a specific profile).
        
        Args:
            notification_type: String notification type
            
        Returns:
            True if type has a specific profile, False if it would use GENERIC
        """
        return self._registry.has_profile(notification_type) and notification_type != "GENERIC"
    
    def clear_cache(self):
        """Clear the profile cache."""
        self._cache.clear()
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        return {
            'cached_profiles': len(self._cache),
            'cached_types': list(self._cache.keys())
        }


# Global resolver instance
profile_resolver = RenderingProfileResolver()
