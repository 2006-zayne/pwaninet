"""
Unified Retrieval Service for Pwanimate.

Orchestrates multi-source retrieval across documents (semantic and lexical),
posts, people, and groups with execution timing and performance metrics.
"""

import time
import logging
from typing import List, Optional

from pwanimate.retrieval.types import (
    RetrievalRequest,
    RetrievalResponse,
    RetrievalResult,
    SourceType,
    RetrievalMode,
)
from pwanimate.retrieval.services.document_retrieval import DocumentSemanticRetrievalService
from pwanimate.retrieval.adapters.pwaninet_search import PwaniNetSearchAdapter

logger = logging.getLogger(__name__)


class UnifiedRetrievalService:
    """Orchestrator for multi-source knowledge retrieval."""

    def __init__(
        self,
        document_service: Optional[DocumentSemanticRetrievalService] = None,
        search_adapter: Optional[PwaniNetSearchAdapter] = None,
    ):
        self.document_service = document_service or DocumentSemanticRetrievalService()
        self.search_adapter = search_adapter or PwaniNetSearchAdapter()

    def retrieve(self, request: RetrievalRequest) -> RetrievalResponse:
        """
        Execute unified cross-source retrieval.

        Args:
            request: Standard RetrievalRequest.

        Returns:
            RetrievalResponse with normalized results and performance metrics.
        """
        start_time = time.perf_counter()
        query = (request.query or "").strip()

        if not query:
            return RetrievalResponse(
                query=query,
                results=[],
                total_count=0,
                execution_time_ms=0.0,
                source_metrics={}
            )

        sources = request.get_source_types()
        mode = request.mode if isinstance(request.mode, RetrievalMode) else RetrievalMode(str(request.mode).lower())

        combined_results: List[RetrievalResult] = []
        source_metrics = {}

        for source in sources:
            source_start = time.perf_counter()
            source_results: List[RetrievalResult] = []

            try:
                if source == SourceType.DOCUMENT:
                    if mode == RetrievalMode.SEMANTIC:
                        source_results = self.document_service.retrieve(request)
                    elif mode == RetrievalMode.LEXICAL:
                        source_results = self.search_adapter.search_documents_lexical(request)
                    elif mode == RetrievalMode.HYBRID:
                        # Hybrid: semantic first, supplement with lexical if needed
                        sem_results = []
                        try:
                            sem_results = self.document_service.retrieve(request)
                        except Exception as sem_exc:
                            logger.warning(
                                "Semantic document retrieval failed in hybrid mode, continuing with lexical fallback: %s",
                                sem_exc,
                                exc_info=True,
                            )

                        seen_titles = {r.title.lower() for r in sem_results}
                        source_results.extend(sem_results)

                        if len(source_results) < request.limit:
                            try:
                                lex_results = self.search_adapter.search_documents_lexical(request)
                                for lr in lex_results:
                                    if lr.title.lower() not in seen_titles:
                                        seen_titles.add(lr.title.lower())
                                        source_results.append(lr)
                                        if len(source_results) >= request.limit:
                                            break
                            except Exception as lex_exc:
                                logger.warning(
                                    "Lexical document retrieval failed in hybrid mode: %s",
                                    lex_exc,
                                    exc_info=True,
                                )
                elif source == SourceType.POST:
                    source_results = self.search_adapter.search_posts(request)
                elif source == SourceType.USER:
                    source_results = self.search_adapter.search_people(request)
                elif source == SourceType.GROUP:
                    source_results = self.search_adapter.search_groups(request)

            except Exception as exc:
                logger.error("Error retrieving from source %s: %s", source, exc, exc_info=True)
                source_results = []

            source_duration_ms = round((time.perf_counter() - source_start) * 1000.0, 2)
            source_metrics[source.value] = {
                "count": len(source_results),
                "duration_ms": source_duration_ms,
            }
            combined_results.extend(source_results)

        # Multi-source ranking: deterministic merge
        if len(sources) > 1:
            combined_results.sort(key=lambda r: r.score, reverse=True)

        final_results = combined_results[:request.limit]
        total_duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        return RetrievalResponse(
            query=query,
            results=final_results,
            total_count=len(combined_results),
            execution_time_ms=total_duration_ms,
            source_metrics=source_metrics,
        )
