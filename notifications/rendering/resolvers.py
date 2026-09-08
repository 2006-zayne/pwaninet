"""
Rendering Resolvers
Individual resolvers for each stage of the rendering pipeline.
Each resolver has a single responsibility.
"""

from typing import Dict, Any, List, Optional
from .payload_models import NotificationPayload, NotificationAction, NavigationTarget
from .profile_models import RenderingProfile


class ComponentVisibilityResolver:
    """
    Resolves which components should be visible based on the profile.
    The renderer simply obeys the profile - no conditional logic in renderer.
    """
    
    def resolve(self, profile: RenderingProfile, payload) -> Dict[str, bool]:
        """
        Resolve component visibility.
        
        Args:
            profile: RenderingProfile instance
            payload: NotificationPayload instance or dict
            
        Returns:
            Dict mapping component names to visibility booleans
        """
        visibility = profile.component_visibility if profile else None
        
        # Check if resource has an image or thumbnail
        has_resource_image = False
        if isinstance(payload, dict):
            resource = payload.get('resource')
            if isinstance(resource, dict):
                has_resource_image = bool(resource.get('image_url') or resource.get('thumbnail_url'))
            elif resource:
                has_resource_image = bool(getattr(resource, 'image_url', None) or getattr(resource, 'thumbnail_url', None))
        elif payload and hasattr(payload, 'resource') and payload.resource:
            has_resource_image = bool(payload.resource.image_url or getattr(payload.resource, 'thumbnail_url', None))
        
        return {
            'context_header': visibility.context_header if visibility else False,
            'actor_stack': visibility.actor_stack if visibility else True,
            'content': visibility.content if visibility else True,
            'preview': (visibility.preview if visibility else False) or has_resource_image,
            'metadata': visibility.metadata if visibility else True,
            'action_bar': visibility.action_bar if visibility else False,
            'status': visibility.status if visibility else False,
        }


class PreviewResolver:
    """
    Resolves the correct preview component based on the profile.
    Reuses existing preview components - no notification-specific implementations.
    """
    
    def resolve(self, profile: RenderingProfile, payload) -> Dict[str, Any]:
        """
        Resolve preview configuration.
        
        Args:
            profile: RenderingProfile instance
            payload: NotificationPayload instance or dict
            
        Returns:
            Dict with preview configuration
        """
        preview_strategy = profile.preview_strategy if profile else None
        
        # Check if resource has an image or thumbnail
        has_resource_image = False
        resource_id = None
        if isinstance(payload, dict):
            preview_data = payload.get('preview', {})
            resource_id = preview_data.get('resource_id') if preview_data else None
            resource = payload.get('resource')
            if isinstance(resource, dict):
                has_resource_image = bool(resource.get('image_url') or resource.get('thumbnail_url'))
                if not resource_id and resource.get('id'):
                    resource_id = resource.get('id')
            elif resource:
                has_resource_image = bool(getattr(resource, 'image_url', None) or getattr(resource, 'thumbnail_url', None))
                if not resource_id and getattr(resource, 'id', None):
                    resource_id = getattr(resource, 'id', None)
        else:
            resource_id = payload.preview.resource_id if (payload and payload.preview) else None
            if payload and hasattr(payload, 'resource') and payload.resource:
                has_resource_image = bool(payload.resource.image_url or getattr(payload.resource, 'thumbnail_url', None))
                if not resource_id and payload.resource.id:
                    resource_id = payload.resource.id
        
        # Handle case where preview_strategy is None
        if preview_strategy is None:
            return {
                'enabled': has_resource_image,
                'type': 'POST' if has_resource_image else None,
                'component': 'post_preview' if has_resource_image else None,
                'resource_id': resource_id,
            }
        
        enabled = preview_strategy.enabled or has_resource_image
        
        return {
            'enabled': enabled,
            'type': preview_strategy.preview_type or ('POST' if has_resource_image else None),
            'component': preview_strategy.component or ('post_preview' if has_resource_image else None),
            'resource_id': resource_id,
        }


class ActionResolver:
    """
    Resolves available actions based on profile and lifecycle state.
    Action behavior comes entirely from profile and payload.
    """
    
    def resolve(self, profile: RenderingProfile, payload) -> List[Dict[str, Any]]:
        """
        Resolve available actions.
        
        Args:
            profile: RenderingProfile instance
            payload: NotificationPayload instance or dict
            
        Returns:
            List of action configurations
        """
        action_strategy = profile.action_strategy
        
        # Handle case where action_strategy is None
        if action_strategy is None:
            # Return actions from payload if available
            if isinstance(payload, dict):
                return payload.get('actions', [])
            else:
                return []
        
        # Handle both dict and object payloads
        if isinstance(payload, dict):
            lifecycle_state = payload.get('lifecycle', {}).get('state', 'LIVE')
            payload_actions = payload.get('actions', [])
        else:
            lifecycle_state = payload.lifecycle.state.value
            payload_actions = payload.actions
        
        # Check if we're in a terminal state with specific actions
        if lifecycle_state in action_strategy.terminal_state_actions:
            # Use terminal state actions
            terminal_actions = action_strategy.terminal_state_actions[lifecycle_state]
            return self._build_actions(terminal_actions, payload_actions, action_strategy)
        
        # Use standard available actions
        return self._build_actions(action_strategy.available_actions, payload_actions, action_strategy)
    
    def _build_actions(self, action_ids: List[str], payload_actions: List, strategy) -> List[Dict[str, Any]]:
        """Build action configurations from action IDs."""
        actions = []
        
        for action_id in action_ids:
            # Try to get action from payload actions first
            payload_action = None
            if isinstance(payload_actions, list):
                # Handle both dict and object payload actions
                for a in payload_actions:
                    if isinstance(a, dict):
                        if a.get('id') == action_id:
                            payload_action = a
                            break
                    else:
                        if a.id == action_id:
                            payload_action = a
                            break
            
            if payload_action:
                if isinstance(payload_action, dict):
                    actions.append({
                        'id': payload_action.get('id'),
                        'label': payload_action.get('label'),
                        'style': payload_action.get('style'),
                        'enabled': payload_action.get('enabled', True),
                        'url': payload_action.get('url'),
                        'method': payload_action.get('method', 'GET'),
                        'payload': payload_action.get('payload', {}),
                        'is_primary': action_id in strategy.primary_actions,
                        'is_secondary': action_id in strategy.secondary_actions,
                        'is_disabled': action_id in strategy.disabled_actions,
                    })
                else:
                    actions.append({
                        'id': payload_action.id,
                        'label': payload_action.label,
                        'style': payload_action.style,
                        'enabled': payload_action.enabled,
                        'url': payload_action.url,
                        'method': payload_action.method,
                        'payload': payload_action.payload,
                        'is_primary': action_id in strategy.primary_actions,
                        'is_secondary': action_id in strategy.secondary_actions,
                        'is_disabled': action_id in strategy.disabled_actions,
                    })
            else:
                # Build action from strategy defaults
                actions.append({
                    'id': action_id,
                    'label': action_id.replace('_', ' ').title(),
                    'style': 'primary' if action_id in strategy.primary_actions else 'secondary',
                    'enabled': action_id not in strategy.disabled_actions,
                    'url': None,
                    'method': 'GET',
                    'payload': {},
                    'is_primary': action_id in strategy.primary_actions,
                    'is_secondary': action_id in strategy.secondary_actions,
                    'is_disabled': action_id in strategy.disabled_actions,
                })
        
        return actions


class StatusResolver:
    """
    Resolves status display based on lifecycle state and profile.
    The renderer MUST NOT infer lifecycle states.
    """
    
    def resolve(self, profile: RenderingProfile, payload) -> Dict[str, Any]:
        """
        Resolve status configuration.
        
        Args:
            profile: RenderingProfile instance
            payload: NotificationPayload instance or dict
            
        Returns:
            Dict with status configuration
        """
        status_strategy = profile.status_strategy
        
        # Handle case where status_strategy is None
        if status_strategy is None:
            return {
                'display': False,
                'text': None,
            }
        
        # Handle both dict and object payloads
        if isinstance(payload, dict):
            lifecycle_state = payload.get('lifecycle', {}).get('state', 'LIVE')
            terminal = payload.get('lifecycle', {}).get('terminal', False)
        else:
            lifecycle_state = payload.lifecycle.state.value
            terminal = payload.lifecycle.terminal
        
        if not status_strategy.display_status:
            return {
                'display': False,
                'text': None,
            }
        
        # Get status text from mapping
        status_text = status_strategy.status_mapping.get(lifecycle_state, lifecycle_state)
        
        return {
            'display': True,
            'text': status_text,
            'state': lifecycle_state,
            'terminal': terminal,
        }


class InteractionResolver:
    """
    Resolves interaction behavior for each interactive region.
    Profiles define interactions for: Card, Actor Avatar, Actor Name, Preview, Context Header, Action Buttons, Status Indicator.
    """
    
    def resolve(self, profile: RenderingProfile, payload) -> Dict[str, str]:
        """
        Resolve interaction configurations.
        
        Args:
            profile: RenderingProfile instance
            payload: NotificationPayload instance or dict
            
        Returns:
            Dict mapping regions to interaction behaviors
        """
        interaction = profile.interaction_strategy
        
        # Handle case where interaction_strategy is None
        if interaction is None:
            return {
                'card': 'NAVIGATE',
                'actor_avatar': 'NAVIGATE',
                'actor_name': 'NAVIGATE',
                'preview': 'NAVIGATE',
                'context_header': 'NAVIGATE',
                'action_buttons': 'EXECUTE',
                'status_indicator': 'NONE',
            }
        
        return {
            'card': interaction.card.behavior,
            'actor_avatar': interaction.actor_avatar.behavior,
            'actor_name': interaction.actor_name.behavior,
            'preview': interaction.preview.behavior,
            'context_header': interaction.context_header.behavior,
            'action_buttons': interaction.action_buttons.behavior,
            'status_indicator': interaction.status_indicator.behavior,
        }


class NavigationResolver:
    """
    Resolves canonical navigation destinations.
    The renderer must not construct URLs itself - consumes navigation objects from payload.
    """
    
    def resolve(self, profile: RenderingProfile, payload) -> Dict[str, Any]:
        """
        Resolve navigation configuration.
        
        Args:
            profile: RenderingProfile instance
            payload: NotificationPayload instance or dict
            
        Returns:
            Dict with navigation configuration
        """
        nav_strategy = profile.navigation_strategy
        
        # Handle case where navigation_strategy is None
        if nav_strategy is None:
            return {
                'primary': None,
                'secondary': None,
            }
        
        # Resolve primary navigation
        primary = self._resolve_navigation_target(nav_strategy.primary, payload)
        
        # Resolve secondary navigation
        secondary = self._resolve_navigation_target(nav_strategy.secondary, payload)
        
        return {
            'primary': primary,
            'secondary': secondary,
        }
    
    def _resolve_navigation_target(self, nav_config, payload) -> Optional[Dict[str, Any]]:
        """Resolve a single navigation target."""
        if not nav_config:
            return None
        
        # Handle both dict and object payloads
        if isinstance(payload, dict):
            navigation = payload.get('navigation', {})
            primary_nav = navigation.get('primary') if navigation else None
            if primary_nav and nav_config.target == "POST_DETAIL":
                return {
                    'target': nav_config.target,
                    'resource_id': primary_nav.get('resource_id'),
                    'url': primary_nav.get('url'),
                }
        else:
            # Try to get from payload navigation first renderer should consume navigation objects from payload
            if payload.navigation.primary and nav_config.target == "POST_DETAIL":
                return {
                    'target': nav_config.target,
                    'resource_id': payload.navigation.primary.resource_id,
                    'url': payload.navigation.primary.url,
                }
        
        # Build from profile configuration
        resource_id = self._extract_resource_id(nav_config.resource_id_field, payload)
        
        return {
            'target': nav_config.target,
            'resource_id': resource_id,
            'url': None,  # URL will be constructed by frontend based on target and resource_id
        }
    
    def _extract_resource_id(self, field_path: Optional[str], payload) -> Optional[int]:
        """Extract resource ID from payload using field path (e.g., 'resource.id', 'actors.0.id')."""
        if not field_path:
            return None
        
        parts = field_path.split('.')
        value = payload
        
        for part in parts:
            if hasattr(value, part):
                value = getattr(value, part)
            elif isinstance(value, dict) and part in value:
                value = value[part]
            elif isinstance(value, list) and part.isdigit():
                index = int(part)
                if index < len(value):
                    value = value[index]
                else:
                    return None
            else:
                return None
        
        return value if isinstance(value, int) else None


class ExpansionResolver:
    """
    Resolves expansion behavior based on profile.
    """
    
    def resolve(self, profile: RenderingProfile, payload) -> Dict[str, Any]:
        """
        Resolve expansion configuration.
        
        Args:
            profile: RenderingProfile instance
            payload: NotificationPayload instance or dict
            
        Returns:
            Dict with expansion configuration
        """
        expansion_strategy = profile.expansion_strategy
        
        # Handle case where expansion_strategy is None
        if expansion_strategy is None:
            return {
                'expandable': False,
                'collapsed_layout': None,
                'expanded_layout': None,
                'data_source': None,
            }
        
        return {
            'expandable': expansion_strategy.expandable,
            'collapsed_layout': expansion_strategy.collapsed_layout,
            'expanded_layout': expansion_strategy.expanded_layout,
            'data_source': expansion_strategy.data_source,
        }


class AggregationResolver:
    """
    Resolves aggregation configuration based on profile.
    """
    
    def resolve(self, profile: RenderingProfile, payload) -> Dict[str, Any]:
        """
        Resolve aggregation configuration.
        
        Args:
            profile: RenderingProfile instance
            payload: NotificationPayload instance or dict
            
        Returns:
            Dict with aggregation configuration
        """
        aggregation_strategy = profile.aggregation_strategy
        
        # Handle case where aggregation_strategy is None
        if aggregation_strategy is None:
            return {
                'enabled': False,
                'scope': None,
                'window': None,
                'rule': None,
            }
        
        return {
            'enabled': aggregation_strategy.enabled,
            'scope': aggregation_strategy.scope,
            'window': aggregation_strategy.window,
            'rule': aggregation_strategy.rule,
        }


# Global resolver instances
component_visibility_resolver = ComponentVisibilityResolver()
preview_resolver = PreviewResolver()
action_resolver = ActionResolver()
status_resolver = StatusResolver()
interaction_resolver = InteractionResolver()
navigation_resolver = NavigationResolver()
expansion_resolver = ExpansionResolver()
aggregation_resolver = AggregationResolver()
