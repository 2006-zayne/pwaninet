"""
Document Detail Tool for Pwanimate.

Allows deterministic, read-only retrieval of authorized academic document metadata
and engagement statistics by share_id or slug.
"""

from typing import Any, Dict, Optional
import uuid

from pwanimate.tools.base import BaseDomainTool, ToolResult
from pwanimate.tools.exceptions import ToolValidationError, ToolPermissionError, ToolNotFoundError
from documents.models import Document


class DocumentDetailTool(BaseDomainTool):
    """
    Retrieve sanitized metadata and engagement metrics for a PwaniNet document.
    """
    name = "document_detail"
    description = (
        "Retrieve authorized metadata and engagement counts for a specific academic "
        "document using its share_id (UUID) or slug."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "share_id": {
                "type": "string",
                "description": "Document unique UUID identifier (share_id)",
            },
            "slug": {
                "type": "string",
                "description": "Document URL-friendly slug",
            },
        },
        "required": [],
    }

    def execute(
        self,
        user: Any,
        share_id: Optional[str] = None,
        slug: Optional[str] = None,
        **kwargs,
    ) -> ToolResult:
        if not share_id and not slug:
            raise ToolValidationError(
                "Either 'share_id' or 'slug' must be provided.",
                tool_name=self.name,
            )

        # Base query with active/available status
        qs = Document.objects.filter(is_available=True, status="ready").select_related("category", "uploaded_by")

        doc = None
        if share_id:
            try:
                parsed_uuid = uuid.UUID(str(share_id).strip())
                doc = qs.filter(share_id=parsed_uuid).first()
            except (ValueError, AttributeError):
                raise ToolValidationError(f"Invalid share_id UUID format: '{share_id}'", tool_name=self.name)
        elif slug:
            doc = qs.filter(slug=str(slug).strip()).first()

        if not doc:
            raise ToolNotFoundError(
                f"Document not found or is currently unavailable (share_id={share_id}, slug={slug}).",
                tool_name=self.name,
            )

        # Authorization check
        is_owner = (
            user is not None
            and getattr(user, "is_authenticated", False)
            and doc.uploaded_by_id == user.id
        )
        is_staff = (
            user is not None
            and getattr(user, "is_authenticated", False)
            and getattr(user, "is_staff", False)
        )

        if doc.visibility != "public" and not is_owner and not is_staff:
            raise ToolPermissionError(
                "You do not have permission to view this restricted or private document.",
                tool_name=self.name,
            )

        # Aggregate engagement counts
        view_count = doc.views.count()
        download_count = doc.downloads.count()

        data = {
            "share_id": str(doc.share_id),
            "slug": doc.slug,
            "title": doc.title,
            "description": doc.description or "",
            "category": doc.category.name if doc.category else None,
            "language": doc.language,
            "visibility": doc.visibility,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "published_at": doc.published_at.isoformat() if doc.published_at else None,
            "view_count": view_count,
            "download_count": download_count,
            "canonical_url": f"/documents/document/{doc.share_id}/",
        }

        return ToolResult.ok(data, share_id=str(doc.share_id))
