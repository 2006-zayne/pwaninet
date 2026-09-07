"""
Notification Message Engine
Generates notification messages based on lifecycle, aggregation, actor count, templates, and localization.
The renderer SHALL never construct these strings itself.
"""

from typing import Dict, Any, List
from dataclasses import is_dataclass, asdict
from .payload_models import NotificationPayload, MessageState, NotificationActor


class NotificationMessageEngine:
    """
    Generates notification messages from structured variables.
    
    Uses:
    - lifecycle
    - aggregation
    - actor count
    - templates
    - localization
    
    to generate messages like:
    - "Brian liked your post."
    - "Brian, Kevin and 18 others liked your post."
    """
    
    def __init__(self):
        self._templates = self._initialize_templates()
    
    def _initialize_templates(self) -> Dict[str, Dict[str, str]]:
        """Initialize message templates for each notification type and state."""
        return {
            "LIKE": {
                "SINGLE": "{actor} liked your post.",
                "DUAL": "{actor1} and {actor2} liked your post.",
                "FEW": "{actors} and {others} others liked your post.",
                "MANY": "{actors} and {others} others liked your post.",
                "HISTORICAL": "{actors} liked your post.",
                "SUMMARY": "Your post caught someone's eye",
            },
            "POST_LIKE": {
                "SINGLE": "{actor} liked your post.",
                "DUAL": "{actor1} and {actor2} liked your post.",
                "FEW": "{actors} and {others} others liked your post.",
                "MANY": "{actors} and {others} others liked your post.",
                "HISTORICAL": "{actors} liked your post.",
                "SUMMARY": "Your post caught someone's eye",
            },
            "COMMENT_LIKE": {
                "SINGLE": "{actor} liked your comment.",
                "DUAL": "{actor1} and {actor2} liked your comment.",
                "FEW": "{actors} and {others} others liked your comment.",
                "MANY": "{actors} and {others} others liked your comment.",
                "HISTORICAL": "{actors} liked your comment.",
                "SUMMARY": "Your comment received likes",
            },
            "POST_COMMENT": {
                "SINGLE": "{actor} commented on your post.",
                "DUAL": "{actor1} and {actor2} commented on your post.",
                "FEW": "{actors} and {others} others commented on your post.",
                "MANY": "{actors} and {others} others commented on your post.",
                "HISTORICAL": "{actors} commented on your post.",
                "SUMMARY": "Someone engaged with your post",
            },
            "COMMENT_REPLY": {
                "SINGLE": "{actor} replied to your comment.",
                "DUAL": "{actor1} and {actor2} replied to your comment.",
                "FEW": "{actors} and {others} others replied to your comment.",
                "MANY": "{actors} and {others} others replied to your comment.",
                "HISTORICAL": "{actors} replied to your comment.",
                "SUMMARY": "Your comment has new replies",
            },
            "POST_MENTION": {
                "SINGLE": "{actor} mentioned you in a post.",
                "DUAL": "{actor1} and {actor2} mentioned you in posts.",
                "FEW": "{actors} and {others} others mentioned you in posts.",
                "MANY": "{actors} and {others} others mentioned you in posts.",
                "HISTORICAL": "{actors} mentioned you in posts.",
                "SUMMARY": "You were mentioned in a post",
            },
            "FOLLOW": {
                "SINGLE": "{actor} started following you.",
                "DUAL": "{actor1} and {actor2} started following you.",
                "FEW": "{actors} and {others} others started following you.",
                "MANY": "{actors} and {others} others started following you.",
                "HISTORICAL": "{actors} started following you.",
                "SUMMARY_SINGLE": "You have a new follower",
                "SUMMARY_AGGREGATED": "You have new followers",
            },
            "POST_SHARE": {
                "SINGLE": "{actor} shared your post.",
                "DUAL": "{actor1} and {actor2} shared your post.",
                "FEW": "{actors} and {others} others shared your post.",
                "MANY": "{actors} and {others} others shared your post.",
                "HISTORICAL": "{actors} shared your post.",
                "SUMMARY": "Your post was shared",
            },
            "GROUP_REQUEST": {
                "SINGLE": "{actor} requested to join your group {group}.",
                "DUAL": "{actor1} and {actor2} requested to join your group {group}.",
                "FEW": "{actors} and {others} others requested to join your group {group}.",
                "MANY": "{actors} and {others} others requested to join your group {group}.",
                "PENDING": "{actor} requested to join your group {group}.",
                "APPROVED": "{actor}'s request to join {group} was approved.",
                "REJECTED": "{actor}'s request to join {group} was rejected.",
                "SUMMARY": "Group join request",
            },
            "GROUP_JOIN_REQUEST": {
                "SINGLE": "{actor} requested to join your group {group}.",
                "DUAL": "{actor1} and {actor2} requested to join your group {group}.",
                "FEW": "{actors} and {others} others requested to join your group {group}.",
                "MANY": "{actors} and {others} others requested to join your group {group}.",
                "PENDING": "{actor} requested to join your group {group}.",
                "APPROVED": "{actor}'s request to join {group} was approved.",
                "REJECTED": "{actor}'s request to join {group} was rejected.",
                "SUMMARY": "Group join request",
            },
            "GROUP_JOIN_REQUEST_APPROVED": {
                "SINGLE": "Your request to join {group} was approved.",
                "SUMMARY": "Group request approved",
            },
            "GROUP_JOIN_REQUEST_REJECTED": {
                "SINGLE": "Your request to join {group} was rejected.",
                "SUMMARY": "Group request rejected",
            },
            "INVITE": {
                "SINGLE": "{actor} invited you to join {group}.",
                "DUAL": "{actor1} and {actor2} invited you to join {group}.",
                "FEW": "{actors} and {others} others invited you to join {group}.",
                "MANY": "{actors} and {others} others invited you to join {group}.",
                "HISTORICAL": "{actors} invited you to join {group}.",
                "SUMMARY": "Group invitation",
            },
            "COMMENT": {
                "SINGLE": "{actor} commented on your post.",
                "DUAL": "{actor1} and {actor2} commented on your post.",
                "FEW": "{actors} and {others} others commented on your post.",
                "MANY": "{actors} and {others} others commented on your post.",
                "HISTORICAL": "{actors} commented on your post.",
                "SUMMARY": "Someone engaged with your post",
            },
            "MENTION": {
                "SINGLE": "{actor} mentioned you in a post.",
                "DUAL": "{actor1} and {actor2} mentioned you in posts.",
                "FEW": "{actors} and {others} others mentioned you in posts.",
                "MANY": "{actors} and {others} others mentioned you in posts.",
                "HISTORICAL": "{actors} mentioned you in posts.",
                "SUMMARY": "You were mentioned",
            },
            "ASSIGNMENT": {
                "SINGLE": "{actor} assigned you a task: {title}.",
                "DUAL": "{actor1} and {actor2} assigned you tasks.",
                "FEW": "{actors} assigned you tasks.",
                "MANY": "{actors} assigned you tasks.",
                "HISTORICAL": "{actors} assigned you tasks.",
            },
            "MEETING": {
                "SINGLE": "{actor} invited you to a meeting: {title}.",
                "DUAL": "{actor1} and {actor2} invited you to meetings.",
                "FEW": "{actors} invited you to meetings.",
                "MANY": "{actors} invited you to meetings.",
                "HISTORICAL": "{actors} invited you to meetings.",
            },
            "WORKSPACE": {
                "SINGLE": "{actor} added you to a workspace.",
                "DUAL": "{actor1} and {actor2} added you to workspaces.",
                "FEW": "{actors} added you to workspaces.",
                "MANY": "{actors} added you to workspaces.",
                "HISTORICAL": "{actors} added you to workspaces.",
            },
            "DOCUMENT": {
                "SINGLE": "{actor} shared a document with you: {title}.",
                "DUAL": "{actor1} and {actor2} shared documents with you.",
                "FEW": "{actors} shared documents with you.",
                "MANY": "{actors} shared documents with you.",
                "HISTORICAL": "{actors} shared documents with you.",
            },
            "SECURITY": {
                "SINGLE": "Security alert: {title}.",
                "HISTORICAL": "Security alert: {title}.",
            },
            "SYSTEM": {
                "SINGLE": "{title}",
                "HISTORICAL": "{title}",
            },
            "AI": {
                "SINGLE": "AI notification: {title}.",
                "HISTORICAL": "AI notification: {title}.",
            },
            "GROUP": {
                "SINGLE": "{actor} added you to {group}.",
                "DUAL": "{actor1} and {actor2} added you to groups.",
                "FEW": "{actors} added you to groups.",
                "MANY": "{actors} added you to groups.",
                "HISTORICAL": "{actors} added you to groups.",
            },
            "PINCH": {
                "SINGLE": "{actor} pinched you.",
                "DUAL": "{actor1} and {actor2} pinched you.",
                "FEW": "{actors} pinched you.",
                "MANY": "{actors} pinched you.",
                "HISTORICAL": "{actors} pinched you.",
            },
            "SHARE": {
                "SINGLE": "{actor} shared a post with you.",
                "DUAL": "{actor1} and {actor2} shared posts with you.",
                "FEW": "{actors} shared posts with you.",
                "MANY": "{actors} shared posts with you.",
                "HISTORICAL": "{actors} shared posts with you.",
            },
            "POST_CREATED": {
                "SINGLE": "{actor} posted a new update.",
                "DUAL": "{actor1} and {actor2} posted new updates.",
                "FEW": "{actors} and {others} others posted new updates.",
                "MANY": "{actors} and {others} others posted new updates.",
                "HISTORICAL": "{actors} posted new updates.",
                "SUMMARY": "New posts from people you follow",
            },
            "DOCUMENT_SHARED": {
                "SINGLE": "{actor} shared a document to view: {document_title}.",
                "DUAL": "{actor1} and {actor2} shared documents to view.",
                "FEW": "{actors} and {others} others shared documents to view.",
                "MANY": "{actors} and {others} others shared documents to view.",
                "HISTORICAL": "{actors} shared documents to view.",
                "SUMMARY": "New documents from people you follow",
            },
            "POST_DOCUMENT_SHARED": {
                "SINGLE": "{actor} shared a document to view: {document_title}.",
                "DUAL": "{actor1} and {actor2} shared documents to view.",
                "FEW": "{actors} and {others} others shared documents to view.",
                "MANY": "{actors} and {others} others shared documents to view.",
                "HISTORICAL": "{actors} shared documents to view.",
                "SUMMARY": "New documents from people you follow",
            },
            "POST_REPOSTED": {
                "SINGLE": "{actor} reposted your post.",
                "DUAL": "{actor1} and {actor2} reposted your post.",
                "FEW": "{actors} and {others} others reposted your post.",
                "MANY": "{actors} and {others} others reposted your post.",
                "HISTORICAL": "{actors} reposted your post.",
                "SUMMARY": "Your post was reposted",
            },
            "DOCUMENT_UPLOADED": {
                "SINGLE": "{actor} uploaded {document} to {repository}.",
                "DUAL": "{actor1} and {actor2} uploaded documents to {repository}.",
                "FEW": "{actors} uploaded documents to {repository}.",
                "MANY": "{actors} uploaded documents to {repository}.",
                "HISTORICAL": "{actors} uploaded documents to {repository}.",
            },
            "DOCUMENT_APPROVED": {
                "SINGLE": "Your document {document} was approved.",
            },
            "DOCUMENT_REJECTED": {
                "SINGLE": "Your document {document} was rejected.",
            },
            "DOCUMENT_COMMENT": {
                "SINGLE": "{actor} commented on {document}.",
                "DUAL": "{actor1} and {actor2} commented on {document}.",
                "FEW": "{actors} and {others} others commented on {document}.",
                "MANY": "{actors} and {others} others commented on {document}.",
                "HISTORICAL": "{actors} commented on {document}.",
            },
            "DOCUMENT_RATED": {
                "SINGLE": "{actor} rated {document}.",
                "DUAL": "{actor1} and {actor2} rated {document}.",
                "FEW": "{actors} and {others} others rated {document}.",
                "MANY": "{actors} and {others} others rated {document}.",
                "HISTORICAL": "{actors} rated {document}.",
            },
            "DOCUMENT_BOOKMARKED": {
                "SINGLE": "{actor} bookmarked {document}.",
                "DUAL": "{actor1} and {actor2} bookmarked {document}.",
                "FEW": "{actors} and {others} others bookmarked {document}.",
                "MANY": "{actors} and {others} others bookmarked {document}.",
                "HISTORICAL": "{actors} bookmarked {document}.",
            },
            "DOCUMENT_TRENDING": {
                "SINGLE": "{document} is trending in {repository}.",
            },
            "NEW_DEVICE_LOGIN": {
                "SINGLE": "New login detected from {device}.",
            },
            "PASSWORD_CHANGED": {
                "SINGLE": "Your password was changed.",
            },
            "ACCOUNT_WARNING": {
                "SINGLE": "Your account has been flagged for review.",
            },
            "SUSPICIOUS_ACTIVITY": {
                "SINGLE": "Suspicious activity detected on your account.",
            },
            "SYSTEM_ANNOUNCEMENT": {
                "SINGLE": "{title}",
            },
            "NEW_FEATURE": {
                "SINGLE": "New feature available: {feature}.",
            },
            "RELEASE": {
                "SINGLE": "New version {version} is now available.",
                "SUMMARY": "New release available",
            },
            "MAINTENANCE": {
                "SINGLE": "Scheduled maintenance: {message}",
            },
            "ACCOUNT_VERIFIED": {
                "SINGLE": "Your account has been verified.",
            },
            "GENERIC": {
                "SINGLE": "You have a new notification.",
            },
        }
    
    def generate_message(self, payload) -> str:
        """
        Generate the final message for a notification payload.
        
        Args:
            payload: NotificationPayload instance or dict
            
        Returns:
            Generated message string
        """
        # Handle both dict and object payloads
        if isinstance(payload, dict):
            # Extract data from dict payload
            template_name = payload.get('type', 'GENERIC')
            actors_data = payload.get('actors', [])
            context_data = payload.get('context')
            resource_data = payload.get('resource')
            
            # Convert actors to NotificationActor-like objects
            actors = []
            for actor_data in actors_data:
                actors.append(type('Actor', (), {
                    'name': actor_data.get('name', 'Someone'),
                    'username': actor_data.get('username', '')
                })())
            
            # Determine state based on actor count
            actor_count = len(actors)
            state = self.determine_state(actor_count)
            
            # Get the template for this type and state
            template = self._get_template(template_name, state)
            
            # Build context variables
            context = {}
            
            # Initialize all possible actor-related variables with defaults
            context["actor"] = "Someone"
            context["actor1"] = ""
            context["actor2"] = ""
            context["actors"] = ""
            context["others"] = "0"
            
            # Add actor names based on count
            if len(actors) == 1:
                context["actor"] = actors[0].name
                context["actors"] = actors[0].name  # For HISTORICAL templates
            elif len(actors) == 2:
                context["actor1"] = actors[0].name
                context["actor2"] = actors[1].name
                context["actors"] = f"{actors[0].name} and {actors[1].name}"  # For HISTORICAL templates
            elif len(actors) > 2:
                context["actors"] = f"{actors[0].name}, {actors[1].name}"
                context["others"] = str(len(actors) - 2)
            
            # Add context (group, repository, etc.)
            context["group"] = ""
            context["repository"] = ""
            if context_data:
                context["group"] = context_data.get('name', '')
                context["repository"] = context_data.get('name', '')
            
            # Add resource (document, post title, etc.)
            context["document"] = "a document"
            context["post"] = "a post"
            context["title"] = ""
            context["document_title"] = "a document"
            if resource_data:
                context["document"] = resource_data.get('title') or "a document"
                context["post"] = resource_data.get('title') or "a post"
                context["title"] = resource_data.get('title') or ""
                context["document_title"] = context["document"]
            if payload.get('raw_data', {}).get('document_title'):
                context["document_title"] = payload['raw_data']['document_title']
                context["document"] = context["document_title"]
            
            # Generate the message
            message = template.format(**context)
            
            return message
        
        if not payload.message:
            return "You have a new notification."
        
        template_name = payload.message.template
        state = payload.message.state.value
        variables = payload.message.variables or {}
        actors = payload.actors
        
        # Get the template for this type and state
        template = self._get_template(template_name, state)
        
        # Build context variables
        context = self._build_context(payload, actors, variables)
        
        # Generate the message
        message = template.format(**context)
        
        return message
    
    def _get_template(self, template_name: str, state: str) -> str:
        """Get the template for a notification type and state."""
        templates = self._templates.get(template_name, {})
        return templates.get(state, templates.get("SINGLE", "You have a new notification."))
    
    def get_summary(self, notification_type: str, is_aggregated: bool = False) -> str:
        """Get the summary text for a notification type."""
        templates = self._templates.get(notification_type, {})
        
        # Check for aggregated-specific summary
        if is_aggregated:
            summary = templates.get("SUMMARY_AGGREGATED")
            if summary:
                return summary
        
        # Fall back to single summary or default
        return templates.get("SUMMARY_SINGLE", templates.get("SUMMARY", "New notification"))
    
    def _build_context(self, payload: NotificationPayload, actors: List[NotificationActor], variables: Dict[str, Any]) -> Dict[str, str]:
        """Build context variables for template substitution."""
        context = {}
        
        # Initialize all possible actor-related variables with defaults
        context["actor"] = "Someone"
        context["actor1"] = ""
        context["actor2"] = ""
        context["actors"] = ""
        context["others"] = "0"
        
        # Add actor names based on count
        if len(actors) == 1:
            context["actor"] = actors[0].name
            context["actors"] = actors[0].name  # For HISTORICAL templates
        elif len(actors) == 2:
            context["actor1"] = actors[0].name
            context["actor2"] = actors[1].name
            context["actors"] = f"{actors[0].name} and {actors[1].name}"  # For HISTORICAL templates
        elif len(actors) > 2:
            # Show first 2 actors
            context["actors"] = f"{actors[0].name}, {actors[1].name}"
            # Count others
            others_count = len(actors) - 2
            context["others"] = str(others_count)
        
        # Add context (group, repository, etc.)
        context["group"] = ""
        context["repository"] = ""
        if payload.context:
            context["group"] = payload.context.name
            context["repository"] = payload.context.name
        
        # Add resource (document, post title, etc.)
        context["document"] = "a document"
        context["post"] = "a post"
        context["title"] = ""
        context["document_title"] = "a document"
        if payload.resource:
            context["document"] = payload.resource.title or "a document"
            context["post"] = payload.resource.title or "a post"
            context["title"] = payload.resource.title or ""
            context["document_title"] = context["document"]
        
        # Add additional variables from payload
        context.update(variables)
        
        # Add raw_data variables (contains event metadata like version for releases)
        if payload.raw_data:
            context.update(payload.raw_data)
            if payload.raw_data.get('document_title'):
                context["document_title"] = payload.raw_data.get('document_title')
                context["document"] = context["document_title"]
        
        # Add metadata variables for release notifications
        if payload.metadata:
            # Convert metadata object to dict if it's not already
            if hasattr(payload.metadata, 'dict'):
                context.update(payload.metadata.dict())
            elif isinstance(payload.metadata, dict):
                context.update(payload.metadata)
            elif is_dataclass(payload.metadata):
                # Convert dataclass to dict
                context.update(asdict(payload.metadata))
            else:
                # Try to get as dict representation
                context.update(dict(payload.metadata))
        
        return context
    
    def determine_state(self, actor_count: int, is_historical: bool = False) -> str:
        """
        Determine the message state based on actor count and history.
        
        Args:
            actor_count: Number of actors
            is_historical: Whether this is a historical notification
            
        Returns:
            Message state (SINGLE, DUAL, FEW, MANY, HISTORICAL)
        """
        if is_historical:
            return "HISTORICAL"
        
        if actor_count == 1:
            return "SINGLE"
        elif actor_count == 2:
            return "DUAL"
        elif actor_count <= 5:
            return "FEW"
        else:
            return "MANY"
    
    def add_template(self, notification_type: str, state: str, template: str):
        """
        Add or update a message template.
        
        Args:
            notification_type: Type of notification
            state: Message state
            template: Template string
        """
        if notification_type not in self._templates:
            self._templates[notification_type] = {}
        self._templates[notification_type][state] = template


# Global message engine instance
message_engine = NotificationMessageEngine()
