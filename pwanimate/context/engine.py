"""
Pwanimate Context Engine Service.

Transforms authorized retrieval results into a safe, deterministic,
bounded, and citation-preserving ContextPackage.
Operates purely in-memory with zero database queries.
"""

import hashlib
import logging
from typing import List, Optional, Set

from pwanimate.retrieval.types import RetrievalResponse, RetrievalResult, SourceType
from pwanimate.context.types import (
    ContextRequest,
    ContextItem,
    ContextPackage,
    estimate_tokens,
)

logger = logging.getLogger(__name__)


class ContextEngine:
    """
    Context Engine responsible for selection, deduplication, bounding,
    truncation, and citation preservation across retrieval results.
    """

    def build_context(self, request: ContextRequest) -> ContextPackage:
        """
        Build a grounded, bounded ContextPackage from a ContextRequest.

        Args:
            request: ContextRequest containing query, retrieval results, and budget parameters.

        Returns:
            ContextPackage ready for future AI Gateway consumption.
        """
        query = (request.query or "").strip()
        raw_results = request.get_raw_results()

        if not query or not raw_results:
            return ContextPackage(
                query=query,
                items=[],
                citations=[],
                total_items=0,
                estimated_tokens=0,
                total_characters=0,
                truncated=False,
                source_counts={},
            )

        selected_items: List[ContextItem] = []
        seen_objects: Set[tuple] = set()
        seen_hashes: Set[str] = set()
        doc_chunk_counts = {}
        source_counts = {}

        current_tokens = 0
        current_chars = 0
        package_truncated = False

        source_caps = request.max_results_per_source or {}

        for r in raw_results:
            # 1. Relevance threshold check
            if request.min_score > 0.0 and r.score < request.min_score:
                continue

            # 2. Source normalization
            src_type = r.source if isinstance(r.source, SourceType) else SourceType(str(r.source).lower().strip())
            src_name = src_type.value

            # 3. Source balancing quota check
            if src_name in source_caps and source_counts.get(src_name, 0) >= source_caps[src_name]:
                continue

            # 4. Exact object deduplication (e.g. post:123 encountered twice)
            obj_key = (src_name, str(r.object_id))
            if obj_key in seen_objects:
                continue

            # 5. Document chunk capping (prevent single doc from dominating all slots)
            doc_id = r.metadata.get("document_id") if src_type == SourceType.DOCUMENT else None
            if doc_id is not None:
                if doc_chunk_counts.get(doc_id, 0) >= request.max_chunks_per_document:
                    continue

            # 6. Extract and validate content
            raw_content = (r.snippet or "").strip()
            if not raw_content:
                continue

            # Content hash deduplication (detect exact duplicate text across chunks)
            content_hash = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()
            if content_hash in seen_hashes:
                continue

            # 7. Item-level character budget truncation
            item_truncated = False
            content = raw_content
            if len(content) > request.max_characters_per_item:
                content = content[:request.max_characters_per_item].rstrip() + "... [TRUNCATED]"
                item_truncated = True
                package_truncated = True

            # 8. Check remaining package budget
            remaining_chars = request.max_characters - current_chars
            remaining_tokens = request.max_tokens - current_tokens

            # If remaining budget is exhausted or too small to be meaningful, stop selection
            if remaining_chars <= 100 or remaining_tokens <= 25:
                package_truncated = True
                break

            # If content exceeds remaining characters, truncate gracefully
            if len(content) > remaining_chars:
                cutoff = max(50, remaining_chars - 17)
                content = content[:cutoff].rstrip() + "... [TRUNCATED]"
                item_truncated = True
                package_truncated = True

            # Check estimated tokens
            item_tokens = estimate_tokens(content)
            if item_tokens > remaining_tokens:
                allowed_chars = max(50, remaining_tokens * 4 - 17)
                content = content[:allowed_chars].rstrip() + "... [TRUNCATED]"
                item_tokens = estimate_tokens(content)
                item_truncated = True
                package_truncated = True

            # 9. Construct normalized ContextItem
            item = ContextItem(
                source=src_type,
                object_id=r.object_id,
                title=r.title,
                content=content,
                citation=r.citation,
                url=r.url,
                relevance_score=r.score,
                metadata=r.metadata.copy(),
                estimated_tokens=item_tokens,
                truncated=item_truncated,
            )

            # 10. Register tracking state
            seen_objects.add(obj_key)
            seen_hashes.add(content_hash)
            if doc_id is not None:
                doc_chunk_counts[doc_id] = doc_chunk_counts.get(doc_id, 0) + 1
            source_counts[src_name] = source_counts.get(src_name, 0) + 1

            current_tokens += item_tokens
            current_chars += len(content)
            selected_items.append(item)

            # 11. Max results limit
            if len(selected_items) >= request.max_results:
                break

        # Collect unique citations preserving appearance order
        citations = []
        for item in selected_items:
            if item.citation and item.citation not in citations:
                citations.append(item.citation)

        return ContextPackage(
            query=query,
            items=selected_items,
            citations=citations,
            total_items=len(selected_items),
            estimated_tokens=current_tokens,
            total_characters=current_chars,
            truncated=package_truncated,
            source_counts=source_counts,
        )

    def build_from_response(
        self,
        query: str,
        retrieval_response: RetrievalResponse,
        **kwargs
    ) -> ContextPackage:
        """Convenience method to construct context directly from a RetrievalResponse."""
        request = ContextRequest(
            query=query,
            retrieval_response=retrieval_response,
            **kwargs
        )
        return self.build_context(request)
