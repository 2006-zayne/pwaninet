"""
Deterministic Tool Router for Pwanimate.

Provides high-confidence, application-side intent matching and parameter extraction
for Pwanimate domain tools. Prioritizes conservative false negatives (falling back
to Unified Retrieval) over false positives (invoking the wrong tool).
"""

import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ToolRoute:
    """
    Result of a successful high-confidence tool route match.

    Attributes:
        tool_name: Registered name of the domain tool.
        parameters: Validated keyword arguments for tool execution.
        confidence: Confidence score (1.0 for exact pattern matches).
        matched_intent: Descriptive label of the matched intent.
    """
    tool_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    matched_intent: str = ""


class ToolRouter:
    """
    Evaluates natural-language user queries to determine if an authorized domain tool
    should be deterministically invoked instead of broad retrieval.
    """

    # 1. Notification Patterns (first-person notifications only)
    NOTIFICATION_PATTERNS = [
        r"^(?:show\s+me\s+|what\s+are\s+|check\s+)?(?:all\s+)?my\s+unread\s+notifications[\s\?\.]*$",
        r"^(?:show\s+me\s+|what\s+are\s+|check\s+)?(?:all\s+)?my\s+notifications[\s\?\.]*$",
        r"^do\s+i\s+have\s+(?:any\s+)?(?:new\s+|unread\s+)?notifications[\s\?\.]*$",
        r"^how\s+many\s+unread\s+notifications\s+(?:do\s+i\s+have)?[\s\?\.]*$",
        r"^what\s+notifications\s+do\s+i\s+have[\s\?\.]*$",
    ]

    # 2. User Profile Patterns (requires explicit @username to avoid ambiguous name guessing)
    USER_PROFILE_PATTERNS = [
        r"^(?:who\s+is|tell\s+me\s+about|lookup|show\s+me|view)\s+@([a-zA-Z0-9_\-\.]+)[\s\?\.]*$",
        r"^(?:profile\s+(?:of|for)|user\s+profile\s+for)\s+@?([a-zA-Z0-9_\-\.]+)[\s\?\.]*$",
        r"^@([a-zA-Z0-9_\-\.]+)[\s\?\.]*$",
    ]

    # 3. Document Detail Patterns (explicit share_id UUID or explicit document slug)
    DOC_UUID_PATTERN = r"(?:tell\s+me\s+about|details?\s+(?:of|for)|what\s+is\s+in)\s+document\s+([0-9a-fA-F\-]{32,36})"
    DOC_SLUG_PATTERN = r"(?:tell\s+me\s+about|details?\s+(?:of|for)|what\s+is\s+in)\s+document\s+([a-z0-9\-]{3,80})[\s\?\.]*$"

    # 4. Group Announcements Patterns
    GROUP_ANNOUNCEMENT_PATTERNS = [
        r"^(?:what\s+are\s+the\s+|what\s+)?announcements?\s+(?:are\s+)?in\s+([a-zA-Z0-9\s\-]+?)(?:\s+group|\s+club)?[\s\?\.]*$",
        r"^(?:what\s+was\s+posted|latest\s+posts?)\s+in\s+([a-zA-Z0-9\s\-]+?)(?:\s+group|\s+club)?[\s\?\.]*$",
    ]

    # 5. Academic Lookup Patterns (explicit PU statutory codes or programme structure)
    ACADEMIC_CODE_PATTERN = r"^(?:what\s+is|tell\s+me\s+about|lookup)\s+([A-Z]{2,6}(?:-[A-Z0-9]{2,10})?)[\s\?\.]*$"
    ACADEMIC_STRUCTURE_PATTERN = r"^(?:structure|curriculum|units)\s+(?:of|for|in)\s+([a-zA-Z0-9\s\-]+?)\s+(?:programme|program|department|school)[\s\?\.]*$"

    def route(self, query: str, user: Any = None) -> Optional[ToolRoute]:
        """
        Evaluate query against high-confidence patterns.
        Returns a ToolRoute if matched with high confidence, or None.
        """
        if not query or not isinstance(query, str):
            return None

        clean_query = query.strip()
        lower_query = clean_query.lower()

        # 1. Notifications check
        route = self._match_notifications(clean_query, lower_query)
        if route:
            return route

        # 2. User Profile check
        route = self._match_user_profile(clean_query)
        if route:
            return route

        # 3. Document Detail check
        route = self._match_document_detail(clean_query)
        if route:
            return route

        # 4. Group Announcements check
        route = self._match_group_announcements(clean_query)
        if route:
            return route

        # 5. Academic Lookup check
        route = self._match_academic_lookup(clean_query)
        if route:
            return route

        return None

    def _match_notifications(self, query: str, lower_query: str) -> Optional[ToolRoute]:
        for pattern in self.NOTIFICATION_PATTERNS:
            if re.match(pattern, lower_query, re.IGNORECASE):
                unread_only = "all" not in lower_query
                return ToolRoute(
                    tool_name="notification_summary",
                    parameters={"unread_only": unread_only, "limit": 5},
                    confidence=1.0,
                    matched_intent="notification_summary",
                )
        return None

    def _match_user_profile(self, query: str) -> Optional[ToolRoute]:
        for pattern in self.USER_PROFILE_PATTERNS:
            m = re.match(pattern, query, re.IGNORECASE)
            if m:
                raw_username = m.group(1).strip().lower()
                # Exclude purely common English words that might follow "profile of"
                if raw_username in {"me", "mine", "user", "someone", "system"}:
                    return None
                return ToolRoute(
                    tool_name="user_profile",
                    parameters={"username": raw_username},
                    confidence=1.0,
                    matched_intent="user_profile",
                )
        return None

    def _match_document_detail(self, query: str) -> Optional[ToolRoute]:
        # Check UUID
        m_uuid = re.search(self.DOC_UUID_PATTERN, query, re.IGNORECASE)
        if m_uuid:
            raw_uuid = m_uuid.group(1).strip()
            try:
                parsed = str(uuid.UUID(raw_uuid))
                return ToolRoute(
                    tool_name="document_detail",
                    parameters={"share_id": parsed},
                    confidence=1.0,
                    matched_intent="document_detail_by_id",
                )
            except ValueError:
                pass

        # Check Slug (must follow "document <slug>")
        # Ensure we do not match general phrases like "document about operating systems"
        m_slug = re.search(self.DOC_SLUG_PATTERN, query, re.IGNORECASE)
        if m_slug:
            slug = m_slug.group(1).strip().lower()
            stop_words = {"about", "for", "on", "in", "related", "with", "summary", "notes"}
            if slug not in stop_words and " " not in slug:
                return ToolRoute(
                    tool_name="document_detail",
                    parameters={"slug": slug},
                    confidence=0.95,
                    matched_intent="document_detail_by_slug",
                )
        return None

    def _match_group_announcements(self, query: str) -> Optional[ToolRoute]:
        for pattern in self.GROUP_ANNOUNCEMENT_PATTERNS:
            m = re.match(pattern, query, re.IGNORECASE)
            if m:
                group_name = m.group(1).strip()
                # Exclude generic search terms
                if group_name.lower() in {"a", "the", "my", "any", "all", "some", "this"}:
                    return None
                return ToolRoute(
                    tool_name="group_announcements",
                    parameters={"group_name": group_name, "limit": 5},
                    confidence=1.0,
                    matched_intent="group_announcements",
                )
        return None

    def _match_academic_lookup(self, query: str) -> Optional[ToolRoute]:
        # 1. Exact uppercase code (e.g. BSC-CS, SPAS, COMP)
        m_code = re.match(self.ACADEMIC_CODE_PATTERN, query)
        if m_code:
            code = m_code.group(1).strip().upper()
            return ToolRoute(
                tool_name="academic_lookup",
                parameters={"code": code, "entity_type": "all"},
                confidence=1.0,
                matched_intent="academic_code_lookup",
            )

        # 2. Programme structure by name
        m_struct = re.match(self.ACADEMIC_STRUCTURE_PATTERN, query, re.IGNORECASE)
        if m_struct:
            prog_name = m_struct.group(1).strip()
            return ToolRoute(
                tool_name="academic_lookup",
                parameters={"query": prog_name, "entity_type": "programme", "limit": 5},
                confidence=0.9,
                matched_intent="academic_structure_lookup",
            )

        return None
