"""
PwaniNet Search Adapter for Pwanimate.

Thin adapter that consumes the existing PwaniNet UnifiedSearchService
and translates domain search results into normalized RetrievalResult objects,
preserving all existing authorization, privacy, and ranking invariants.
"""

import logging
from typing import List, Optional
from search.services.unified_search_service import UnifiedSearchService
from pwanimate.retrieval.types import RetrievalRequest, RetrievalResult, SourceType

logger = logging.getLogger(__name__)


class PwaniNetSearchAdapter:
    """Adapter wrapping PwaniNet UnifiedSearchService for Pwanimate retrieval."""

    def __init__(self, search_service: Optional[UnifiedSearchService] = None):
        self.search_service = search_service or UnifiedSearchService()

    def search_posts(self, request: RetrievalRequest) -> List[RetrievalResult]:
        """Search posts via existing UnifiedSearchService."""
        query = (request.query or "").strip()
        if not query:
            return []

        limit = max(1, int(request.limit or 10))
        items, _ = self.search_service._search_posts(
            query=query,
            user=request.user,
            limit=limit,
            offset=0
        )

        results = []
        for item in items:
            raw_post = item.get("obj")
            author_info = item.get("author", {})
            metadata = {
                "author_id": author_info.get("id"),
                "author_username": author_info.get("username"),
                "author_name": author_info.get("name"),
                "created_at": item.get("created_at"),
                "like_count": item.get("like_count", 0),
                "comment_count": item.get("comment_count", 0),
            }
            if raw_post and hasattr(raw_post, 'share_id'):
                canonical_url = f"/post/{raw_post.share_id}/"
            else:
                canonical_url = item.get("detail_url", "")

            post_content = (getattr(raw_post, 'content', None) or item.get("snippet", "")).strip()
            results.append(
                RetrievalResult(
                    source=SourceType.POST,
                    object_id=item.get("id"),
                    title=item.get("title", ""),
                    snippet=post_content,
                    score=float(item.get("relevance_rank", 0.0)),
                    url=canonical_url,
                    citation=f"Post by @{author_info.get('username', 'user')}",
                    metadata=metadata,
                    raw_object=raw_post,
                )
            )

        return results

    def search_people(self, request: RetrievalRequest) -> List[RetrievalResult]:
        """Search people/users via existing UnifiedSearchService."""
        query = (request.query or "").strip()
        if not query:
            return []

        limit = max(1, int(request.limit or 10))
        items, _ = self.search_service._search_people(
            query=query,
            user=request.user,
            limit=limit,
            offset=0
        )

        results = []
        for item in items:
            raw_user = item.get("obj")
            username = item.get("username", "")
            results.append(
                RetrievalResult(
                    source=SourceType.USER,
                    object_id=item.get("id"),
                    title=item.get("title", username),
                    snippet=item.get("headline") or item.get("subtitle", f"@{username}"),
                    score=float(item.get("relevance_rank", 0.0)),
                    url=item.get("detail_url", f"/users/user/{username}/"),
                    citation=f"Profile @{username}",
                    metadata={
                        "username": username,
                        "global_role": item.get("global_role"),
                        "headline": item.get("headline"),
                    },
                    raw_object=raw_user,
                )
            )

        return results

    def search_groups(self, request: RetrievalRequest) -> List[RetrievalResult]:
        """Search groups via existing UnifiedSearchService."""
        query = (request.query or "").strip()
        if not query:
            return []

        limit = max(1, int(request.limit or 10))
        items, _ = self.search_service._search_groups(
            query=query,
            user=request.user,
            limit=limit,
            offset=0
        )

        results = []
        for item in items:
            raw_group = item.get("obj")
            desc = raw_group.description if raw_group and hasattr(raw_group, 'description') else ""
            results.append(
                RetrievalResult(
                    source=SourceType.GROUP,
                    object_id=item.get("id"),
                    title=item.get("title", ""),
                    snippet=desc[:160] if desc else item.get("subtitle", ""),
                    score=float(item.get("relevance_rank", 0.0)),
                    url=item.get("detail_url", f"/groups/{item.get('id')}/"),
                    citation=f"Group: {item.get('title', '')}",
                    metadata={
                        "member_count": getattr(raw_group, 'member_count', 0) if raw_group else 0,
                        "is_official": item.get("is_official", False),
                    },
                    raw_object=raw_group,
                )
            )

        return results

    def search_documents_lexical(self, request: RetrievalRequest) -> List[RetrievalResult]:
        """Lexical full-text search for documents via existing UnifiedSearchService."""
        query = (request.query or "").strip()
        if not query:
            return []

        limit = max(1, int(request.limit or 10))
        items, _ = self.search_service._search_documents(
            query=query,
            user=request.user,
            limit=limit,
            offset=0
        )

        results = []
        for item in items:
            raw_doc = item.get("obj")
            share_id = getattr(raw_doc, 'share_id', None)
            url = f"/documents/document/{share_id}/" if share_id else item.get("detail_url", "")

            results.append(
                RetrievalResult(
                    source=SourceType.DOCUMENT,
                    object_id=item.get("id"),
                    title=item.get("title", ""),
                    snippet=item.get("snippet", ""),
                    score=float(item.get("relevance_rank", 0.0)),
                    url=url,
                    citation=f"Document: {item.get('title', '')}",
                    metadata={
                        "category_display": item.get("category_display"),
                        "file_type": item.get("file_type"),
                        "download_count": item.get("download_count"),
                        "rating_average": item.get("rating_average"),
                    },
                    raw_object=raw_doc,
                )
            )

        return results
