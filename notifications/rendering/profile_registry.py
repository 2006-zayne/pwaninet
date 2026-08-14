"""
Rendering Profile Registry
Centralized registry for all notification rendering profiles.
"""

from typing import Dict, Optional
from .profile_models import (
    RenderingProfile, ProfileCategory, ProfileIntent,
    ComponentVisibilityConfig, PreviewStrategy, MessageStrategy,
    ActionStrategy, StatusStrategy, InteractionStrategy,
    InteractionConfig, NavigationStrategy, NavigationConfig,
    ExpansionStrategy, AggregationStrategy,
)


class RenderingProfileRegistry:
    """Centralized registry for Rendering Profiles."""
    
    def __init__(self):
        self._profiles: Dict[str, RenderingProfile] = {}
        self._initialize_profiles()
    
    def _initialize_profiles(self):
        """Initialize all rendering profiles"""
        self._register_social_profiles()
        self._register_group_profiles()
        self._register_document_profiles()
        self._register_security_profiles()
        self._register_system_profiles()
        self._register_generic_profile()
    
    def _register_social_profiles(self):
        """Register social notification profiles"""
        # LIKE
        self._profiles["LIKE"] = RenderingProfile(
            id="LIKE", category=ProfileCategory.SOCIAL, intent=ProfileIntent.ACTIVITY,
            message_strategy=MessageStrategy(template="LIKE", supported_states=["SINGLE", "DUAL", "FEW", "MANY"]),
            component_visibility=ComponentVisibilityConfig(actor_stack=True, preview=True, action_bar=True),
            preview_strategy=PreviewStrategy(enabled=True, preview_type="POST"),
            action_strategy=ActionStrategy(available_actions=["VIEW_POST"], primary_actions=["VIEW_POST"]),
            navigation_strategy=NavigationStrategy(
                primary=NavigationConfig(target="POST_DETAIL", resource_id_field="resource.id")
            ),
            aggregation_strategy=AggregationStrategy(enabled=True, scope="PER_POST"),
            expansion_strategy=ExpansionStrategy(expandable=True, data_source="actors")
        )
        
        # POST_LIKE
        self._profiles["POST_LIKE"] = RenderingProfile(
            id="POST_LIKE", category=ProfileCategory.SOCIAL, intent=ProfileIntent.ACTIVITY,
            message_strategy=MessageStrategy(template="POST_LIKE", supported_states=["SINGLE", "DUAL", "FEW", "MANY"]),
            component_visibility=ComponentVisibilityConfig(actor_stack=True, preview=True, action_bar=True),
            preview_strategy=PreviewStrategy(enabled=True, preview_type="POST"),
            action_strategy=ActionStrategy(available_actions=["VIEW_POST"], primary_actions=["VIEW_POST"]),
            navigation_strategy=NavigationStrategy(
                primary=NavigationConfig(target="POST_DETAIL", resource_id_field="resource.id")
            ),
            aggregation_strategy=AggregationStrategy(enabled=True, scope="PER_POST"),
            expansion_strategy=ExpansionStrategy(expandable=True, data_source="actors")
        )
        
        # POST_COMMENT
        self._profiles["POST_COMMENT"] = RenderingProfile(
            id="POST_COMMENT", category=ProfileCategory.SOCIAL, intent=ProfileIntent.ACTIVITY,
            message_strategy=MessageStrategy(template="POST_COMMENT", supported_states=["SINGLE", "DUAL", "FEW", "MANY"]),
            component_visibility=ComponentVisibilityConfig(actor_stack=True, preview=True),
            preview_strategy=PreviewStrategy(enabled=True, preview_type="POST"),
            navigation_strategy=NavigationStrategy(
                primary=NavigationConfig(target="POST_DETAIL", resource_id_field="resource.id")
            ),
            aggregation_strategy=AggregationStrategy(enabled=True, scope="PER_POST"),
            expansion_strategy=ExpansionStrategy(expandable=True, data_source="actors")
        )
        
        # POST_MENTION
        self._profiles["POST_MENTION"] = RenderingProfile(
            id="POST_MENTION", category=ProfileCategory.SOCIAL, intent=ProfileIntent.AWARENESS,
            message_strategy=MessageStrategy(template="POST_MENTION", supported_states=["SINGLE", "DUAL", "FEW", "MANY"]),
            component_visibility=ComponentVisibilityConfig(actor_stack=True, preview=True),
            preview_strategy=PreviewStrategy(enabled=True, preview_type="POST"),
            navigation_strategy=NavigationStrategy(
                primary=NavigationConfig(target="POST_DETAIL", resource_id_field="resource.id")
            ),
            aggregation_strategy=AggregationStrategy(enabled=True, scope="PER_POST"),
            expansion_strategy=ExpansionStrategy(expandable=True, data_source="actors")
        )
        
        # COMMENT
        self._profiles["COMMENT"] = RenderingProfile(
            id="COMMENT", category=ProfileCategory.SOCIAL, intent=ProfileIntent.ACTIVITY,
            message_strategy=MessageStrategy(template="COMMENT", supported_states=["SINGLE", "DUAL", "FEW", "MANY"]),
            component_visibility=ComponentVisibilityConfig(actor_stack=True, preview=True, action_bar=True),
            preview_strategy=PreviewStrategy(enabled=True, preview_type="POST"),
            action_strategy=ActionStrategy(available_actions=["VIEW_COMMENT"], primary_actions=["VIEW_COMMENT"]),
            navigation_strategy=NavigationStrategy(
                primary=NavigationConfig(target="POST_DETAIL", resource_id_field="resource.id")
            ),
            aggregation_strategy=AggregationStrategy(enabled=True, scope="PER_POST"),
            expansion_strategy=ExpansionStrategy(expandable=True, data_source="actors")
        )
        
        # COMMENT_REPLY
        self._profiles["COMMENT_REPLY"] = RenderingProfile(
            id="COMMENT_REPLY", category=ProfileCategory.SOCIAL, intent=ProfileIntent.ACTIVITY,
            message_strategy=MessageStrategy(template="COMMENT_REPLY", supported_states=["SINGLE", "DUAL", "FEW", "MANY"]),
            component_visibility=ComponentVisibilityConfig(actor_stack=True, preview=True, action_bar=True),
            preview_strategy=PreviewStrategy(enabled=True, preview_type="POST"),
            action_strategy=ActionStrategy(available_actions=["VIEW_COMMENT"], primary_actions=["VIEW_COMMENT"]),
            navigation_strategy=NavigationStrategy(
                primary=NavigationConfig(target="POST_DETAIL", resource_id_field="resource.id")
            ),
            aggregation_strategy=AggregationStrategy(enabled=True, scope="PER_POST"),
            expansion_strategy=ExpansionStrategy(expandable=True, data_source="actors")
        )
        
        # COMMENT_LIKE
        self._profiles["COMMENT_LIKE"] = RenderingProfile(
            id="COMMENT_LIKE", category=ProfileCategory.SOCIAL, intent=ProfileIntent.ACTIVITY,
            message_strategy=MessageStrategy(template="COMMENT_LIKE", supported_states=["SINGLE", "DUAL", "FEW", "MANY"]),
            component_visibility=ComponentVisibilityConfig(actor_stack=True, preview=True, action_bar=True),
            preview_strategy=PreviewStrategy(enabled=True, preview_type="POST"),
            action_strategy=ActionStrategy(available_actions=["VIEW_COMMENT"], primary_actions=["VIEW_COMMENT"]),
            navigation_strategy=NavigationStrategy(
                primary=NavigationConfig(target="POST_DETAIL", resource_id_field="resource.id")
            ),
            aggregation_strategy=AggregationStrategy(enabled=True, scope="PER_POST"),
            expansion_strategy=ExpansionStrategy(expandable=True, data_source="actors")
        )
        
        # MENTION
        self._profiles["MENTION"] = RenderingProfile(
            id="MENTION", category=ProfileCategory.SOCIAL, intent=ProfileIntent.AWARENESS,
            message_strategy=MessageStrategy(template="MENTION", supported_states=["SINGLE", "DUAL", "FEW", "MANY"]),
            component_visibility=ComponentVisibilityConfig(actor_stack=True, preview=True),
            preview_strategy=PreviewStrategy(enabled=True, preview_type="POST"),
            navigation_strategy=NavigationStrategy(
                primary=NavigationConfig(target="POST_DETAIL", resource_id_field="resource.id")
            ),
            aggregation_strategy=AggregationStrategy(enabled=True, scope="PER_POST"),
            expansion_strategy=ExpansionStrategy(expandable=True, data_source="actors")
        )
        
        # SHARE
        self._profiles["SHARE"] = RenderingProfile(
            id="SHARE", category=ProfileCategory.SOCIAL, intent=ProfileIntent.ACTIVITY,
            message_strategy=MessageStrategy(template="SHARE", supported_states=["SINGLE", "DUAL", "FEW", "MANY"]),
            component_visibility=ComponentVisibilityConfig(actor_stack=True, preview=True),
            preview_strategy=PreviewStrategy(enabled=True, preview_type="POST"),
            navigation_strategy=NavigationStrategy(
                primary=NavigationConfig(target="POST_DETAIL", resource_id_field="resource.id")
            ),
            aggregation_strategy=AggregationStrategy(enabled=True, scope="PER_POST"),
            expansion_strategy=ExpansionStrategy(expandable=True, data_source="actors")
        )
        
        # POST_CREATED
        self._profiles["POST_CREATED"] = RenderingProfile(
            id="POST_CREATED", category=ProfileCategory.SOCIAL, intent=ProfileIntent.ACTIVITY,
            message_strategy=MessageStrategy(template="POST_CREATED", supported_states=["SINGLE", "DUAL", "FEW", "MANY"]),
            component_visibility=ComponentVisibilityConfig(actor_stack=True, preview=True),
            preview_strategy=PreviewStrategy(enabled=True, preview_type="POST"),
            navigation_strategy=NavigationStrategy(
                primary=NavigationConfig(target="POST_DETAIL", resource_id_field="resource.id")
            ),
            aggregation_strategy=AggregationStrategy(enabled=True, scope="PER_POST"),
            expansion_strategy=ExpansionStrategy(expandable=True, data_source="actors")
        )
        
        # POST_REPOSTED
        self._profiles["POST_REPOSTED"] = RenderingProfile(
            id="POST_REPOSTED", category=ProfileCategory.SOCIAL, intent=ProfileIntent.ACTIVITY,
            message_strategy=MessageStrategy(template="POST_REPOSTED", supported_states=["SINGLE", "DUAL", "FEW", "MANY"]),
            component_visibility=ComponentVisibilityConfig(actor_stack=True, preview=True),
            preview_strategy=PreviewStrategy(enabled=True, preview_type="POST"),
            navigation_strategy=NavigationStrategy(
                primary=NavigationConfig(target="POST_DETAIL", resource_id_field="resource.id")
            ),
            aggregation_strategy=AggregationStrategy(enabled=True, scope="PER_POST"),
            expansion_strategy=ExpansionStrategy(expandable=True, data_source="actors")
        )
        
        # PINCH
        self._profiles["PINCH"] = RenderingProfile(
            id="PINCH", category=ProfileCategory.SOCIAL, intent=ProfileIntent.ACTIVITY,
            message_strategy=MessageStrategy(template="PINCH", supported_states=["SINGLE", "DUAL", "FEW", "MANY"]),
            component_visibility=ComponentVisibilityConfig(actor_stack=True),
            navigation_strategy=NavigationStrategy(
                primary=NavigationConfig(target="USER_PROFILE", resource_id_field="actors.0.id")
            ),
            aggregation_strategy=AggregationStrategy(enabled=True, scope="RECIPIENT"),
            expansion_strategy=ExpansionStrategy(expandable=True, data_source="actors")
        )
        
        # FOLLOW
        self._profiles["FOLLOW"] = RenderingProfile(
            id="FOLLOW", category=ProfileCategory.SOCIAL, intent=ProfileIntent.ACTIVITY,
            message_strategy=MessageStrategy(template="FOLLOW", supported_states=["SINGLE", "DUAL", "FEW", "MANY"]),
            component_visibility=ComponentVisibilityConfig(actor_stack=True, action_bar=True),
            action_strategy=ActionStrategy(available_actions=["FOLLOW_BACK", "VIEW_PROFILE"], primary_actions=["FOLLOW_BACK"]),
            navigation_strategy=NavigationStrategy(
                primary=NavigationConfig(target="USER_PROFILE", resource_id_field="actors.0.id")
            ),
            aggregation_strategy=AggregationStrategy(enabled=True, scope="RECIPIENT"),
            expansion_strategy=ExpansionStrategy(expandable=True, data_source="actors")
        )
        
        # POST_SHARE
        self._profiles["POST_SHARE"] = RenderingProfile(
            id="POST_SHARE", category=ProfileCategory.SOCIAL, intent=ProfileIntent.ACTIVITY,
            message_strategy=MessageStrategy(template="POST_SHARE", supported_states=["SINGLE", "DUAL", "FEW", "MANY"]),
            component_visibility=ComponentVisibilityConfig(actor_stack=True, preview=True),
            preview_strategy=PreviewStrategy(enabled=True, preview_type="POST"),
            navigation_strategy=NavigationStrategy(
                primary=NavigationConfig(target="POST_DETAIL", resource_id_field="resource.id")
            )
        )
        
        # ASSIGNMENT
        self._profiles["ASSIGNMENT"] = RenderingProfile(
            id="ASSIGNMENT", category=ProfileCategory.ACADEMIC, intent=ProfileIntent.WORKFLOW,
            message_strategy=MessageStrategy(template="ASSIGNMENT", supported_states=["SINGLE", "DUAL", "FEW", "MANY"]),
            component_visibility=ComponentVisibilityConfig(actor_stack=True, action_bar=True),
            action_strategy=ActionStrategy(available_actions=["VIEW_ASSIGNMENT"], primary_actions=["VIEW_ASSIGNMENT"]),
            navigation_strategy=NavigationStrategy(
                primary=NavigationConfig(target="ASSIGNMENT_DETAIL", resource_id_field="resource.id")
            ),
            aggregation_strategy=AggregationStrategy(enabled=True, scope="PER_RECIPIENT"),
            expansion_strategy=ExpansionStrategy(expandable=True, data_source="actors")
        )
        
        # MEETING
        self._profiles["MEETING"] = RenderingProfile(
            id="MEETING", category=ProfileCategory.ACADEMIC, intent=ProfileIntent.WORKFLOW,
            message_strategy=MessageStrategy(template="MEETING", supported_states=["SINGLE", "DUAL", "FEW", "MANY"]),
            component_visibility=ComponentVisibilityConfig(actor_stack=True, action_bar=True),
            action_strategy=ActionStrategy(available_actions=["ACCEPT", "DECLINE"], primary_actions=["ACCEPT"]),
            navigation_strategy=NavigationStrategy(
                primary=NavigationConfig(target="MEETING_DETAIL", resource_id_field="resource.id")
            ),
            aggregation_strategy=AggregationStrategy(enabled=True, scope="PER_RECIPIENT"),
            expansion_strategy=ExpansionStrategy(expandable=True, data_source="actors")
        )
        
        # WORKSPACE
        self._profiles["WORKSPACE"] = RenderingProfile(
            id="WORKSPACE", category=ProfileCategory.WORKSPACE, intent=ProfileIntent.WORKFLOW,
            message_strategy=MessageStrategy(template="WORKSPACE", supported_states=["SINGLE", "DUAL", "FEW", "MANY"]),
            component_visibility=ComponentVisibilityConfig(actor_stack=True, context_header=True),
            navigation_strategy=NavigationStrategy(
                primary=NavigationConfig(target="WORKSPACE_DETAIL", resource_id_field="context.id")
            ),
            aggregation_strategy=AggregationStrategy(enabled=True, scope="PER_WORKSPACE"),
            expansion_strategy=ExpansionStrategy(expandable=True, data_source="actors")
        )
    
    def _register_group_profiles(self):
        """Register group notification profiles"""
        # GROUP_INVITE (group invitation to user)
        self._profiles["INVITE"] = RenderingProfile(
            id="INVITE", category=ProfileCategory.GROUP, intent=ProfileIntent.WORKFLOW,
            message_strategy=MessageStrategy(template="INVITE", supported_states=["SINGLE"]),
            component_visibility=ComponentVisibilityConfig(context_header=True, action_bar=True, status=True),
            action_strategy=ActionStrategy(available_actions=["ACCEPT", "DECLINE"], primary_actions=["ACCEPT"]),
            status_strategy=StatusStrategy(display_status=True, status_mapping={"PENDING": "🟡 Pending", "ACCEPTED": "🟢 Accepted", "DECLINED": "🔴 Declined"}),
            navigation_strategy=NavigationStrategy(
                primary=NavigationConfig(target="GROUP_DETAIL", resource_id_field="context.id")
            )
        )
        
        # GROUP_REQUEST (user requesting to join group)
        self._profiles["GROUP_REQUEST"] = RenderingProfile(
            id="GROUP_REQUEST", category=ProfileCategory.GROUP, intent=ProfileIntent.WORKFLOW,
            message_strategy=MessageStrategy(template="GROUP_REQUEST", supported_states=["SINGLE"]),
            component_visibility=ComponentVisibilityConfig(context_header=True, action_bar=True, status=True),
            action_strategy=ActionStrategy(available_actions=["APPROVE", "REJECT"], primary_actions=["APPROVE"]),
            status_strategy=StatusStrategy(display_status=True, status_mapping={"PENDING": "🟡 Pending", "APPROVED": "🟢 Approved", "REJECTED": "🔴 Rejected"}),
            navigation_strategy=NavigationStrategy(
                primary=NavigationConfig(target="GROUP_DETAIL", resource_id_field="context.id")
            )
        )
        
        # GROUP_JOIN_REQUEST
        self._profiles["GROUP_JOIN_REQUEST"] = RenderingProfile(
            id="GROUP_JOIN_REQUEST", category=ProfileCategory.GROUP, intent=ProfileIntent.WORKFLOW,
            message_strategy=MessageStrategy(template="GROUP_JOIN_REQUEST", supported_states=["SINGLE"]),
            component_visibility=ComponentVisibilityConfig(context_header=True, action_bar=True, status=True),
            action_strategy=ActionStrategy(available_actions=["APPROVE", "REJECT"], primary_actions=["APPROVE"]),
            status_strategy=StatusStrategy(display_status=True, status_mapping={"PENDING": "🟡 Pending", "APPROVED": "🟢 Approved", "REJECTED": "🔴 Rejected"}),
            navigation_strategy=NavigationStrategy(
                primary=NavigationConfig(target="GROUP_DETAIL", resource_id_field="context.id")
            )
        )
        
        # GROUP_JOIN_REQUEST_APPROVED
        self._profiles["GROUP_JOIN_REQUEST_APPROVED"] = RenderingProfile(
            id="GROUP_JOIN_REQUEST_APPROVED", category=ProfileCategory.GROUP, intent=ProfileIntent.WORKFLOW,
            message_strategy=MessageStrategy(template="GROUP_JOIN_REQUEST_APPROVED", supported_states=["SINGLE"]),
            component_visibility=ComponentVisibilityConfig(context_header=True, action_bar=True, status=True),
            status_strategy=StatusStrategy(display_status=True, status_mapping={"COMPLETED": "✅ Approved"}),
            navigation_strategy=NavigationStrategy(
                primary=NavigationConfig(target="GROUP_DETAIL", resource_id_field="context.id")
            )
        )
        
        # GROUP_JOIN_REQUEST_REJECTED
        self._profiles["GROUP_JOIN_REQUEST_REJECTED"] = RenderingProfile(
            id="GROUP_JOIN_REQUEST_REJECTED", category=ProfileCategory.GROUP, intent=ProfileIntent.WORKFLOW,
            message_strategy=MessageStrategy(template="GROUP_JOIN_REQUEST_REJECTED", supported_states=["SINGLE"]),
            component_visibility=ComponentVisibilityConfig(context_header=True, action_bar=True, status=True),
            status_strategy=StatusStrategy(display_status=True, status_mapping={"COMPLETED": "🔴 Rejected"}),
            navigation_strategy=NavigationStrategy(
                primary=NavigationConfig(target="USER_PROFILE", resource_id_field="actors.0.id")
            )
        )
        
        # GROUP (added to group)
        self._profiles["GROUP"] = RenderingProfile(
            id="GROUP", category=ProfileCategory.GROUP, intent=ProfileIntent.WORKFLOW,
            message_strategy=MessageStrategy(template="GROUP", supported_states=["SINGLE", "DUAL", "FEW", "MANY"]),
            component_visibility=ComponentVisibilityConfig(context_header=True, actor_stack=True),
            navigation_strategy=NavigationStrategy(
                primary=NavigationConfig(target="GROUP_DETAIL", resource_id_field="context.id")
            ),
            aggregation_strategy=AggregationStrategy(enabled=True, scope="PER_GROUP"),
            expansion_strategy=ExpansionStrategy(expandable=True, data_source="actors")
        )
    
    def _register_document_profiles(self):
        """Register document notification profiles"""
        # DOCUMENT
        self._profiles["DOCUMENT"] = RenderingProfile(
            id="DOCUMENT", category=ProfileCategory.DOCUMENT, intent=ProfileIntent.ACTIVITY,
            message_strategy=MessageStrategy(template="DOCUMENT", supported_states=["SINGLE", "DUAL", "FEW", "MANY"]),
            component_visibility=ComponentVisibilityConfig(actor_stack=True, preview=True),
            preview_strategy=PreviewStrategy(enabled=True, preview_type="DOCUMENT"),
            navigation_strategy=NavigationStrategy(
                primary=NavigationConfig(target="DOCUMENT_DETAIL", resource_id_field="resource.id")
            ),
            aggregation_strategy=AggregationStrategy(enabled=True, scope="PER_DOCUMENT"),
            expansion_strategy=ExpansionStrategy(expandable=True, data_source="actors")
        )
        
        # DOCUMENT_UPLOADED
        self._profiles["DOCUMENT_UPLOADED"] = RenderingProfile(
            id="DOCUMENT_UPLOADED", category=ProfileCategory.DOCUMENT, intent=ProfileIntent.ACTIVITY,
            message_strategy=MessageStrategy(template="DOCUMENT_UPLOADED", supported_states=["SINGLE", "DUAL", "FEW", "MANY"]),
            component_visibility=ComponentVisibilityConfig(context_header=True, actor_stack=True, preview=True),
            preview_strategy=PreviewStrategy(enabled=True, preview_type="DOCUMENT", component="rich_document_preview"),
            navigation_strategy=NavigationStrategy(
                primary=NavigationConfig(target="DOCUMENT_VIEWER", resource_id_field="resource.id")
            ),
            aggregation_strategy=AggregationStrategy(enabled=True, scope="PER_REPOSITORY"),
            expansion_strategy=ExpansionStrategy(expandable=True, data_source="actors")
        )
        
        # DOCUMENT_APPROVED
        self._profiles["DOCUMENT_APPROVED"] = RenderingProfile(
            id="DOCUMENT_APPROVED", category=ProfileCategory.DOCUMENT, intent=ProfileIntent.WORKFLOW,
            message_strategy=MessageStrategy(template="DOCUMENT_APPROVED", supported_states=["SINGLE"]),
            component_visibility=ComponentVisibilityConfig(context_header=True, action_bar=True, status=True, preview=True),
            preview_strategy=PreviewStrategy(enabled=True, preview_type="DOCUMENT", component="rich_document_preview"),
            status_strategy=StatusStrategy(display_status=True, status_mapping={"COMPLETED": "✅ Approved"}),
            navigation_strategy=NavigationStrategy(
                primary=NavigationConfig(target="DOCUMENT_VIEWER", resource_id_field="resource.id")
            )
        )
        
        # DOCUMENT_REJECTED
        self._profiles["DOCUMENT_REJECTED"] = RenderingProfile(
            id="DOCUMENT_REJECTED", category=ProfileCategory.DOCUMENT, intent=ProfileIntent.WORKFLOW,
            message_strategy=MessageStrategy(template="DOCUMENT_REJECTED", supported_states=["SINGLE"]),
            component_visibility=ComponentVisibilityConfig(context_header=True, action_bar=True, status=True, preview=True),
            preview_strategy=PreviewStrategy(enabled=True, preview_type="DOCUMENT", component="rich_document_preview"),
            status_strategy=StatusStrategy(display_status=True, status_mapping={"COMPLETED": "🔴 Rejected"}),
            navigation_strategy=NavigationStrategy(
                primary=NavigationConfig(target="DOCUMENT_VIEWER", resource_id_field="resource.id")
            )
        )
        
        # DOCUMENT_COMMENT, DOCUMENT_RATED, DOCUMENT_BOOKMARKED, DOCUMENT_TRENDING
        for doc_type in ["DOCUMENT_COMMENT", "DOCUMENT_RATED", "DOCUMENT_BOOKMARKED"]:
            self._profiles[doc_type] = RenderingProfile(
                id=doc_type, category=ProfileCategory.DOCUMENT, intent=ProfileIntent.ACTIVITY,
                message_strategy=MessageStrategy(template=doc_type, supported_states=["SINGLE", "DUAL", "FEW", "MANY"]),
                component_visibility=ComponentVisibilityConfig(context_header=True, actor_stack=True, preview=True),
                preview_strategy=PreviewStrategy(enabled=True, preview_type="DOCUMENT", component="rich_document_preview"),
                navigation_strategy=NavigationStrategy(
                    primary=NavigationConfig(target="DOCUMENT_VIEWER", resource_id_field="resource.id")
                ),
                aggregation_strategy=AggregationStrategy(enabled=True, scope="PER_DOCUMENT"),
                expansion_strategy=ExpansionStrategy(expandable=True, data_source="actors")
            )
        
        self._profiles["DOCUMENT_TRENDING"] = RenderingProfile(
            id="DOCUMENT_TRENDING", category=ProfileCategory.DOCUMENT, intent=ProfileIntent.AWARENESS,
            message_strategy=MessageStrategy(template="DOCUMENT_TRENDING", supported_states=["SINGLE"]),
            component_visibility=ComponentVisibilityConfig(context_header=True, preview=True),
            preview_strategy=PreviewStrategy(enabled=True, preview_type="DOCUMENT", component="rich_document_preview"),
            navigation_strategy=NavigationStrategy(
                primary=NavigationConfig(target="DOCUMENT_VIEWER", resource_id_field="resource.id")
            )
        )
    
    def _register_security_profiles(self):
        """Register security notification profiles"""
        # SECURITY
        self._profiles["SECURITY"] = RenderingProfile(
            id="SECURITY", category=ProfileCategory.SECURITY, intent=ProfileIntent.ALERT,
            message_strategy=MessageStrategy(template="SECURITY", supported_states=["SINGLE"]),
            component_visibility=ComponentVisibilityConfig(actor_stack=False),
            navigation_strategy=NavigationStrategy(
                primary=NavigationConfig(target="ACCOUNT_SETTINGS")
            )
        )
        
        # NEW_DEVICE_LOGIN
        self._profiles["NEW_DEVICE_LOGIN"] = RenderingProfile(
            id="NEW_DEVICE_LOGIN", category=ProfileCategory.SECURITY, intent=ProfileIntent.ALERT,
            message_strategy=MessageStrategy(template="NEW_DEVICE_LOGIN", supported_states=["SINGLE"]),
            navigation_strategy=NavigationStrategy(primary=NavigationConfig(target="SECURITY_SETTINGS"))
        )
        
        # PASSWORD_CHANGED
        self._profiles["PASSWORD_CHANGED"] = RenderingProfile(
            id="PASSWORD_CHANGED", category=ProfileCategory.SECURITY, intent=ProfileIntent.ALERT,
            message_strategy=MessageStrategy(template="PASSWORD_CHANGED", supported_states=["SINGLE"])
        )
        
        # ACCOUNT_WARNING
        self._profiles["ACCOUNT_WARNING"] = RenderingProfile(
            id="ACCOUNT_WARNING", category=ProfileCategory.SECURITY, intent=ProfileIntent.ALERT,
            message_strategy=MessageStrategy(template="ACCOUNT_WARNING", supported_states=["SINGLE"]),
            component_visibility=ComponentVisibilityConfig(action_bar=True, status=True),
            status_strategy=StatusStrategy(display_status=True, status_mapping={"LIVE": "⚠️ Warning"}),
            navigation_strategy=NavigationStrategy(primary=NavigationConfig(target="ACCOUNT_SETTINGS"))
        )
        
        # SUSPICIOUS_ACTIVITY
        self._profiles["SUSPICIOUS_ACTIVITY"] = RenderingProfile(
            id="SUSPICIOUS_ACTIVITY", category=ProfileCategory.SECURITY, intent=ProfileIntent.ALERT,
            message_strategy=MessageStrategy(template="SUSPICIOUS_ACTIVITY", supported_states=["SINGLE"]),
            component_visibility=ComponentVisibilityConfig(action_bar=True, status=True),
            status_strategy=StatusStrategy(display_status=True, status_mapping={"LIVE": "🔴 Suspicious Activity"}),
            navigation_strategy=NavigationStrategy(primary=NavigationConfig(target="SECURITY_SETTINGS"))
        )
    
    def _register_system_profiles(self):
        """Register system notification profiles"""
        # RELEASE
        self._profiles["RELEASE"] = RenderingProfile(
            id="RELEASE", category=ProfileCategory.SYSTEM, intent=ProfileIntent.ANNOUNCEMENT,
            message_strategy=MessageStrategy(template="RELEASE", supported_states=["SINGLE"]),
            component_visibility=ComponentVisibilityConfig(content=True, action_bar=True),
            action_strategy=ActionStrategy(available_actions=["SEE_WHATS_NEW"], primary_actions=["SEE_WHATS_NEW"]),
            navigation_strategy=None
        )
        
        # SYSTEM
        self._profiles["SYSTEM"] = RenderingProfile(
            id="SYSTEM", category=ProfileCategory.SYSTEM, intent=ProfileIntent.ANNOUNCEMENT,
            message_strategy=MessageStrategy(template="SYSTEM", supported_states=["SINGLE"]),
            component_visibility=ComponentVisibilityConfig(content=True),
            navigation_strategy=None
        )
        
        # SYSTEM_ANNOUNCEMENT
        self._profiles["SYSTEM_ANNOUNCEMENT"] = RenderingProfile(
            id="SYSTEM_ANNOUNCEMENT", category=ProfileCategory.SYSTEM, intent=ProfileIntent.ANNOUNCEMENT,
            message_strategy=MessageStrategy(template="SYSTEM_ANNOUNCEMENT", supported_states=["SINGLE"]),
            navigation_strategy=NavigationStrategy(primary=NavigationConfig(target="ANNOUNCEMENT_DETAIL"))
        )
        
        # NEW_FEATURE
        self._profiles["NEW_FEATURE"] = RenderingProfile(
            id="NEW_FEATURE", category=ProfileCategory.SYSTEM, intent=ProfileIntent.ANNOUNCEMENT,
            message_strategy=MessageStrategy(template="NEW_FEATURE", supported_states=["SINGLE"])
        )
        
        # MAINTENANCE
        self._profiles["MAINTENANCE"] = RenderingProfile(
            id="MAINTENANCE", category=ProfileCategory.SYSTEM, intent=ProfileIntent.ANNOUNCEMENT,
            message_strategy=MessageStrategy(template="MAINTENANCE", supported_states=["SINGLE"])
        )
        
        # ACCOUNT_VERIFIED
        self._profiles["ACCOUNT_VERIFIED"] = RenderingProfile(
            id="ACCOUNT_VERIFIED", category=ProfileCategory.SYSTEM, intent=ProfileIntent.ANNOUNCEMENT,
            message_strategy=MessageStrategy(template="ACCOUNT_VERIFIED", supported_states=["SINGLE"]),
            component_visibility=ComponentVisibilityConfig(status=True),
            status_strategy=StatusStrategy(display_status=True, status_mapping={"COMPLETED": "✅ Verified"})
        )
        
        # AI
        self._profiles["AI"] = RenderingProfile(
            id="AI", category=ProfileCategory.SYSTEM, intent=ProfileIntent.ANNOUNCEMENT,
            message_strategy=MessageStrategy(template="AI", supported_states=["SINGLE"]),
            component_visibility=ComponentVisibilityConfig(content=True),
            navigation_strategy=None
        )
    
    def _register_generic_profile(self):
        """Generic fallback profile for unknown notification types"""
        self._profiles["GENERIC"] = RenderingProfile(
            id="GENERIC", category=ProfileCategory.SYSTEM, intent=ProfileIntent.AWARENESS,
            message_strategy=MessageStrategy(template="GENERIC", supported_states=["SINGLE"]),
            component_visibility=ComponentVisibilityConfig(content=True, metadata=True),
            navigation_strategy=None
        )
    
    def get_profile(self, notification_type: str) -> RenderingProfile:
        """Get profile for notification type, fallback to GENERIC if not found"""
        return self._profiles.get(notification_type, self._profiles["GENERIC"])
    
    def has_profile(self, notification_type: str) -> bool:
        """Check if profile exists for notification type"""
        return notification_type in self._profiles
    
    def list_profiles(self) -> Dict[str, RenderingProfile]:
        """List all registered profiles"""
        return self._profiles.copy()


# Global registry instance
profile_registry = RenderingProfileRegistry()
