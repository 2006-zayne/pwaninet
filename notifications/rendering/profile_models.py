"""
Rendering Profile Data Models
Declarative profiles that control how notifications are rendered.
Profiles contain NO rendering code - only configuration.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any
from enum import Enum


class ProfileCategory(Enum):
    """Profile categories"""
    SOCIAL = "social"
    GROUP = "group"
    DOCUMENT = "document"
    SECURITY = "security"
    SYSTEM = "system"
    ACADEMIC = "academic"
    WORKSPACE = "workspace"


class ProfileIntent(Enum):
    """Profile intents"""
    ACTIVITY = "activity"
    WORKFLOW = "workflow"
    AWARENESS = "awareness"
    ALERT = "alert"
    ANNOUNCEMENT = "announcement"
    REMINDER = "reminder"


class ComponentVisibility(Enum):
    """Component visibility states"""
    VISIBLE = True
    HIDDEN = False


@dataclass
class ComponentVisibilityConfig:
    """Component visibility configuration"""
    context_header: bool = False
    actor_stack: bool = True
    content: bool = True
    preview: bool = False
    metadata: bool = True
    action_bar: bool = False
    status: bool = False


@dataclass
class PreviewStrategy:
    """Preview strategy configuration"""
    enabled: bool = False
    preview_type: str = "NONE"  # POST, DOCUMENT, GROUP, PROFILE, NONE
    component: Optional[str] = None  # Component name to use


@dataclass
class MessageStrategy:
    """Message strategy configuration"""
    template: str
    supported_states: List[str] = field(default_factory=list)


@dataclass
class ActionStrategy:
    """Action strategy configuration"""
    available_actions: List[str] = field(default_factory=list)
    primary_actions: List[str] = field(default_factory=list)
    secondary_actions: List[str] = field(default_factory=list)
    disabled_actions: List[str] = field(default_factory=list)
    terminal_state_actions: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class StatusStrategy:
    """Status strategy configuration"""
    display_status: bool = False
    status_mapping: Dict[str, str] = field(default_factory=dict)  # lifecycle_state -> display_text


@dataclass
class InteractionConfig:
    """Interaction configuration for a region"""
    behavior: str  # OPEN_PRIMARY_RESOURCE, OPEN_PROFILE, NONE, etc.


@dataclass
class InteractionStrategy:
    """Interaction strategy configuration"""
    card: InteractionConfig = field(default_factory=lambda: InteractionConfig("OPEN_PRIMARY_RESOURCE"))
    actor_avatar: InteractionConfig = field(default_factory=lambda: InteractionConfig("OPEN_PROFILE"))
    actor_name: InteractionConfig = field(default_factory=lambda: InteractionConfig("OPEN_PROFILE"))
    preview: InteractionConfig = field(default_factory=lambda: InteractionConfig("OPEN_PREVIEW_RESOURCE"))
    context_header: InteractionConfig = field(default_factory=lambda: InteractionConfig("OPEN_CONTEXT"))
    action_buttons: InteractionConfig = field(default_factory=lambda: InteractionConfig("EXECUTE_ACTION"))
    status_indicator: InteractionConfig = field(default_factory=lambda: InteractionConfig("NONE"))


@dataclass
class NavigationConfig:
    """Navigation configuration"""
    target: str  # POST_DETAIL, DOCUMENT_VIEWER, GROUP_DETAIL, etc.
    resource_id_field: Optional[str] = None  # Field name in payload to get resource_id


@dataclass
class NavigationStrategy:
    """Navigation strategy configuration"""
    primary: Optional[NavigationConfig] = None
    secondary: Optional[NavigationConfig] = None


@dataclass
class ExpansionStrategy:
    """Expansion strategy configuration"""
    expandable: bool = False
    collapsed_layout: Optional[str] = None
    expanded_layout: Optional[str] = None
    data_source: Optional[str] = None  # Field in payload containing expansion data


@dataclass
class AggregationStrategy:
    """Aggregation strategy configuration"""
    enabled: bool = False
    scope: Optional[str] = None  # PER_POST, RECIPIENT, etc.
    window: Optional[str] = None  # Time window for aggregation
    rule: Optional[str] = None  # Aggregation rule


@dataclass
class RenderingProfile:
    """
    Rendering Profile - declarative configuration for notification rendering
    
    Each profile defines:
    - Which components are visible
    - How previews are displayed
    - What message template to use
    - Available actions
    - Status display
    - Interaction behavior
    - Navigation targets
    - Expansion behavior
    - Aggregation rules
    
    Profiles contain NO rendering logic - only configuration.
    """
    id: str
    category: ProfileCategory
    intent: ProfileIntent
    message_strategy: MessageStrategy
    supported_states: List[str] = field(default_factory=list)
    component_visibility: ComponentVisibilityConfig = field(default_factory=ComponentVisibilityConfig)
    preview_strategy: PreviewStrategy = field(default_factory=PreviewStrategy)
    action_strategy: ActionStrategy = field(default_factory=ActionStrategy)
    status_strategy: StatusStrategy = field(default_factory=StatusStrategy)
    interaction_strategy: InteractionStrategy = field(default_factory=InteractionStrategy)
    navigation_strategy: NavigationStrategy = field(default_factory=NavigationStrategy)
    aggregation_strategy: AggregationStrategy = field(default_factory=AggregationStrategy)
    expansion_strategy: ExpansionStrategy = field(default_factory=ExpansionStrategy)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'category': self.category.value,
            'intent': self.intent.value,
            'message_strategy': {
                'template': self.message_strategy.template,
                'supported_states': self.message_strategy.supported_states,
            } if self.message_strategy else None,
            'supported_states': self.supported_states,
            'component_visibility': {
                'context_header': self.component_visibility.context_header,
                'actor_stack': self.component_visibility.actor_stack,
                'content': self.component_visibility.content,
                'preview': self.component_visibility.preview,
                'metadata': self.component_visibility.metadata,
                'action_bar': self.component_visibility.action_bar,
                'status': self.component_visibility.status,
            } if self.component_visibility else None,
            'preview_strategy': {
                'enabled': self.preview_strategy.enabled,
                'preview_type': self.preview_strategy.preview_type,
                'component': self.preview_strategy.component,
            } if self.preview_strategy else None,
            'action_strategy': {
                'available_actions': self.action_strategy.available_actions,
                'primary_actions': self.action_strategy.primary_actions,
                'secondary_actions': self.action_strategy.secondary_actions,
                'disabled_actions': self.action_strategy.disabled_actions,
                'terminal_state_actions': self.action_strategy.terminal_state_actions,
            } if self.action_strategy else None,
            'status_strategy': {
                'display_status': self.status_strategy.display_status,
                'status_mapping': self.status_strategy.status_mapping,
            } if self.status_strategy else None,
            'interaction_strategy': {
                'card': {'behavior': self.interaction_strategy.card.behavior},
                'actor_avatar': {'behavior': self.interaction_strategy.actor_avatar.behavior},
                'actor_name': {'behavior': self.interaction_strategy.actor_name.behavior},
                'preview': {'behavior': self.interaction_strategy.preview.behavior},
                'context_header': {'behavior': self.interaction_strategy.context_header.behavior},
                'action_buttons': {'behavior': self.interaction_strategy.action_buttons.behavior},
                'status_indicator': {'behavior': self.interaction_strategy.status_indicator.behavior},
            } if self.interaction_strategy else None,
            'navigation_strategy': {
                'primary': {
                    'target': self.navigation_strategy.primary.target,
                    'resource_id_field': self.navigation_strategy.primary.resource_id_field,
                } if self.navigation_strategy and self.navigation_strategy.primary else None,
                'secondary': {
                    'target': self.navigation_strategy.secondary.target,
                    'resource_id_field': self.navigation_strategy.secondary.resource_id_field,
                } if self.navigation_strategy and self.navigation_strategy.secondary else None,
            } if self.navigation_strategy else None,
            'aggregation_strategy': {
                'enabled': self.aggregation_strategy.enabled,
                'scope': self.aggregation_strategy.scope,
                'window': self.aggregation_strategy.window,
                'rule': self.aggregation_strategy.rule,
            } if self.aggregation_strategy else None,
            'expansion_strategy': {
                'expandable': self.expansion_strategy.expandable,
                'collapsed_layout': self.expansion_strategy.collapsed_layout,
                'expanded_layout': self.expansion_strategy.expanded_layout,
                'data_source': self.expansion_strategy.data_source,
            } if self.expansion_strategy else None,
        }
