"""
Unified Retrieval Contracts and DTOs for Pwanimate.

Provides standard abstractions for querying diverse knowledge sources
(documents, posts, people, groups) with normalized result structures,
citations, and navigation provenance.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class SourceType(str, Enum):
    """Supported knowledge source types in PwaniNet/Pwanimate."""
    DOCUMENT = "document"
    POST = "post"
    USER = "user"
    GROUP = "group"
    ANNOUNCEMENT = "announcement"


class RetrievalMode(str, Enum):
    """Retrieval strategies."""
    SEMANTIC = "semantic"
    LEXICAL = "lexical"
    HYBRID = "hybrid"


@dataclass
class RetrievalRequest:
    """
    Standard request parameters for cross-source retrieval.

    Attributes:
        query: Raw query text.
        user: Authenticated or anonymous Django user model instance.
        sources: Explicit list of SourceType or string values to search.
        mode: Retrieval strategy (semantic, lexical, hybrid).
        limit: Maximum results to return per source or total.
        filters: Optional source-specific metadata filters (category, programme, etc.).
        min_score: Minimum similarity/relevance threshold.
    """
    query: str
    user: Optional[Any] = None
    sources: List[SourceType | str] = field(default_factory=lambda: [SourceType.DOCUMENT])
    mode: RetrievalMode | str = RetrievalMode.SEMANTIC
    limit: int = 10
    filters: Optional[Dict[str, Any]] = None
    min_score: float = 0.0

    def get_source_types(self) -> List[SourceType]:
        """Normalize sources to a list of SourceType enums."""
        normalized = []
        for src in self.sources:
            if isinstance(src, SourceType):
                normalized.append(src)
            elif isinstance(src, str):
                try:
                    normalized.append(SourceType(src.lower().strip()))
                except ValueError:
                    pass
        return normalized or [SourceType.DOCUMENT]


@dataclass
class RetrievalResult:
    """
    Normalized item representation returned across all retrieval sources.

    Attributes:
        source: Entity source type.
        object_id: Primary key or unique identifier of the retrieved entity/chunk.
        title: Human-readable title or headline.
        snippet: Core textual excerpt or content fragment.
        score: Normalized relevance or cosine similarity score (typically 0.0 - 1.0).
        url: Canonical web URL for direct navigation.
        citation: Deterministic citation string for academic grounding.
        metadata: Detailed provenance dictionary (page, slide, section, author, etc.).
        raw_object: Optional underlying domain or chunk model (internal pipeline only).
    """
    source: SourceType
    object_id: Any
    title: str
    snippet: str
    score: float
    url: str
    citation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_object: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert normalized result to a clean dictionary safe for downstream context."""
        return {
            "source": self.source.value if isinstance(self.source, SourceType) else str(self.source),
            "object_id": self.object_id,
            "title": self.title,
            "snippet": self.snippet,
            "score": self.score,
            "url": self.url,
            "citation": self.citation,
            "metadata": self.metadata,
        }


@dataclass
class RetrievalResponse:
    """
    Aggregated response returned by retrieval orchestrator.

    Attributes:
        query: Original input query.
        results: Ordered list of normalized retrieval results.
        total_count: Total count of candidate results found.
        execution_time_ms: Total latency in milliseconds.
        source_metrics: Per-source breakdown of candidate counts and execution timing.
    """
    query: str
    results: List[RetrievalResult] = field(default_factory=list)
    total_count: int = 0
    execution_time_ms: float = 0.0
    source_metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        return {
            "query": self.query,
            "results": [r.to_dict() for r in self.results],
            "total_count": self.total_count,
            "execution_time_ms": self.execution_time_ms,
            "source_metrics": self.source_metrics,
        }
