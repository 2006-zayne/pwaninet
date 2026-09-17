"""
Notification Summary Tool for Pwanimate.

Allows deterministic, read-only retrieval of the authenticated user's
notifications. Strictly scoped to the authenticated caller.
"""

from typing import Any, Dict, List

from pwanimate.tools.base import BaseDomainTool, ToolResult
from pwanimate.tools.exceptions import ToolPermissionError
from notifications.queries.notification_queries import (
    get_notifications_for_user,
    get_unread_count,
)


class NotificationSummaryTool(BaseDomainTool):
    """
    Summarize notifications for the authenticated user.
    """
    name = "notification_summary"
    description = (
        "Retrieve recent notifications and unread counts strictly for the "
        "currently authenticated user."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "unread_only": {
                "type": "boolean",
                "description": "If True, only return unread notifications (default True)",
                "default": True,
            },
            "limit": {
                "type": "integer",
                "description": "Maximum notifications to return (default 5, max 20)",
                "default": 5,
            },
        },
        "required": [],
    }

    def execute(
        self,
        user: Any,
        unread_only: bool = True,
        limit: int = 5,
        **kwargs,
    ) -> ToolResult:
        if not user or not getattr(user, "is_authenticated", False):
            raise ToolPermissionError(
                "Authentication required to access personal notifications.",
                tool_name=self.name,
            )

        limit = min(max(1, int(limit)), 20)

        # 1. Total unread count for the user
        unread_count = get_unread_count(user)

        # 2. Query notifications for this user
        is_read_filter = False if unread_only else None
        qs = get_notifications_for_user(user, is_read=is_read_filter)[:limit]

        notifications: List[Dict[str, Any]] = []
        for notif in qs:
            meta = notif.metadata if isinstance(notif.metadata, dict) else {}
            action_url = meta.get("action_url") or meta.get("target_url") or meta.get("url")

            notifications.append({
                "id": str(notif.notification_id),
                "type": notif.notification_type,
                "category": notif.category,
                "priority": notif.priority,
                "title": notif.title,
                "summary": notif.summary or "",
                "status": notif.status,
                "created_at": notif.created_at.isoformat() if notif.created_at else None,
                "action_url": action_url,
            })

        return ToolResult.ok(
            {
                "unread_count": unread_count,
                "count": len(notifications),
                "unread_only": unread_only,
                "notifications": notifications,
            },
            unread_count=unread_count,
            count=len(notifications),
        )
