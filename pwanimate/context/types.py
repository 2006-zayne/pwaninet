"""
Context Engine Data Contracts and DTOs for Pwanimate.

Defines the bounded, citation-preserving context package consumed by
future AI Gateway and LLM components.
"""

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from pwanimate.retrieval.types import RetrievalResponse, RetrievalResult, SourceType


def estimate_tokens(text: str) -> int:
    """
    Deterministic lightweight token estimation heuristic.
    Uses ~4 characters per token approximation.
    """
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))


@dataclass
class ContextRequest:
    """
    Request parameters for context package construction.

    Attributes:
        query: User input query.
        retrieval_response: Optional RetrievalResponse from Phase 3 retrieval.
        results: Optional direct list of RetrievalResult objects.
        max_results: Maximum number of items to include in context.
        max_tokens: Maximum estimated token budget for the context package.
        max_characters: Maximum total character budget.
        max_results_per_source: Optional dictionary specifying item caps per source.
        max_chunks_per_document: Maximum chunks allowed from the same document.
        max_characters_per_item: Maximum characters permitted in an individual item.
        min_score: Minimum relevance threshold to qualify for context.
    """
    query: str
    retrieval_response: Optional[RetrievalResponse] = None
    results: Optional[List[RetrievalResult]] = None
    max_results: int = 10
    max_tokens: int = 4000
    max_characters: int = 16000
    max_results_per_source: Optional[Dict[str, int]] = None
    max_chunks_per_document: int = 4
    max_characters_per_item: int = 3000
    min_score: float = 0.0
    user_context: Optional[Any] = None

    def get_raw_results(self) -> List[RetrievalResult]:
        """Resolve candidate RetrievalResults from response or explicit list."""
        if self.results is not None:
            return self.results
        if self.retrieval_response is not None:
            return self.retrieval_response.results
        return []


@dataclass
class ContextItem:
    """
    Normalized item representation within a grounded context package.

    Attributes:
        source: Source entity type (document, post, user, group, announcement).
        object_id: Unique entity/chunk identifier.
        title: Title or headline of the entity.
        content: Grounding textual content.
        citation: Grounded citation string (e.g. '[Doc, v1: p. 4]').
        url: Canonical PwaniNet resource URL.
        relevance_score: Score from retrieval ranking.
        metadata: Detailed provenance dictionary (page, slide, section, etc.).
        estimated_tokens: Estimated token count for this item's content.
        truncated: Flag indicating if content was truncated due to budget constraints.
    """
    source: SourceType | str
    object_id: Any
    title: str
    content: str
    citation: Optional[str] = None
    url: str = ""
    relevance_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    estimated_tokens: int = 0
    truncated: bool = False

    def __post_init__(self):
        if not self.estimated_tokens:
            self.estimated_tokens = estimate_tokens(self.content)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to clean dictionary.
        Guarantees zero ORM model instances in output.
        """
        src_str = self.source.value if isinstance(self.source, SourceType) else str(self.source)
        # Ensure metadata contains only JSON-serializable primitives
        clean_metadata = {}
        for k, v in self.metadata.items():
            if isinstance(v, (str, int, float, bool, list, dict)) or v is None:
                clean_metadata[k] = v
            else:
                clean_metadata[k] = str(v)

        return {
            "source": src_str,
            "object_id": self.object_id,
            "title": self.title,
            "content": self.content,
            "citation": self.citation,
            "url": self.url,
            "relevance_score": self.relevance_score,
            "metadata": clean_metadata,
            "estimated_tokens": self.estimated_tokens,
            "truncated": self.truncated,
        }

    def format_data_block(self) -> str:
        """
        Format as an isolated XML-delimited data block.
        Treats retrieved text strictly as untrusted data.
        """
        src_str = self.source.value if isinstance(self.source, SourceType) else str(self.source)
        citation_str = f' citation="{self.citation}"' if self.citation else ""
        url_str = f' url="{self.url}"' if self.url else ""

        lines = [
            f'<grounding_data source="{src_str}" id="{self.object_id}"{citation_str}{url_str}>',
            f'  <title>{self.title}</title>',
            '  <content>',
            f'    {self.content}',
            '  </content>',
            '</grounding_data>',
        ]
        return "\n".join(lines)


@dataclass
class ContextPackage:
    """
    Bounded, provenance-preserving context container passed to downstream AI components.

    Attributes:
        query: Input query.
        items: Bounded list of selected ContextItem objects.
        citations: Deduplicated list of citation labels.
        total_items: Total number of context items included.
        estimated_tokens: Total estimated tokens across all items.
        total_characters: Total character count across all items.
        truncated: True if any item or the overall context was truncated.
        source_counts: Counts of items grouped by source type.
    """
    query: str
    items: List[ContextItem] = field(default_factory=list)
    citations: List[str] = field(default_factory=list)
    total_items: int = 0
    estimated_tokens: int = 0
    total_characters: int = 0
    truncated: bool = False
    source_counts: Dict[str, int] = field(default_factory=dict)
    user_context: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert package to JSON-serializable dictionary."""
        data = {
            "query": self.query,
            "items": [item.to_dict() for item in self.items],
            "citations": self.citations,
            "total_items": self.total_items,
            "estimated_tokens": self.estimated_tokens,
            "total_characters": self.total_characters,
            "truncated": self.truncated,
            "source_counts": self.source_counts,
        }
        if self.user_context and hasattr(self.user_context, "to_dict"):
            data["user_context"] = self.user_context.to_dict()
        elif self.user_context is not None:
            data["user_context"] = self.user_context
        return data

    def format_context_text(self) -> str:
        """
        Format the entire context package as structured, machine-readable text.
        Retrieved content is enclosed in unambiguous data boundaries.
        """
        sections = []

        if self.user_context and hasattr(self.user_context, "format_context_block"):
            user_text = self.user_context.format_context_block()
            if user_text:
                sections.append(user_text)

        if self.items:
            blocks = [item.format_data_block() for item in self.items]
            content_section = "\n\n".join(blocks)
            header = f'<retrieved_context total_items="{self.total_items}" estimated_tokens="{self.estimated_tokens}">'
            footer = "</retrieved_context>"
            sections.append(f"{header}\n\n{content_section}\n\n{footer}")

        return "\n\n".join(sections)

    def has_content(self) -> bool:
        """Check if package contains either grounding items or user context."""
        return bool(self.items or self.user_context)
