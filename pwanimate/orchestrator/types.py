"""
Data Contracts and DTOs for Pwanimate Orchestrator.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from pwanimate.ai.gateway.types import ChatMessage
from pwanimate.orchestrator.exceptions import OrchestratorValidationError
from pwanimate.retrieval.types import SourceType


@dataclass
class OrchestrationRequest:
    """
    End-to-end user request passed to PwanimateOrchestrator.

    Attributes:
        query: User input query text.
        user: Authenticated or anonymous Django user model instance.
        history: Previous conversational dialogue turns.
        task: Operational task mode ('rag', 'general', 'summary').
        sources: Optional explicit list of knowledge sources to query.
        provider: Optional explicit LLM provider override.
        model: Optional explicit LLM model override.
        temperature: Sampling temperature (default 0.2 for academic grounding).
        max_tokens: Maximum tokens in generated response.
    """
    query: str
    user: Optional[Any] = None
    history: List[ChatMessage] = field(default_factory=list)
    task: str = "rag"
    sources: Optional[List[SourceType | str]] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.2
    max_tokens: Optional[int] = None
    user_context: Optional[Any] = None

    def __post_init__(self):
        if not isinstance(self.query, str) or not self.query.strip():
            raise OrchestratorValidationError("Query must be a non-empty string.")

        if not isinstance(self.history, list):
            raise OrchestratorValidationError("History must be a list of ChatMessage instances.")

        # Normalize any raw dicts in history to ChatMessage
        normalized_history: List[ChatMessage] = []
        for item in self.history:
            if isinstance(item, ChatMessage):
                normalized_history.append(item)
            elif isinstance(item, dict):
                role = item.get("role")
                content = item.get("content")
                if not role or not content:
                    raise OrchestratorValidationError("History item dict must have 'role' and 'content'.")
                normalized_history.append(ChatMessage(role=role, content=content))
            else:
                raise OrchestratorValidationError(
                    f"Invalid history item type '{type(item).__name__}'. Expected ChatMessage or dict."
                )
        self.history = normalized_history

        if self.temperature < 0.0 or self.temperature > 2.0:
            raise OrchestratorValidationError(
                f"Temperature must be between 0.0 and 2.0, got {self.temperature}"
            )
        if self.max_tokens is not None and self.max_tokens <= 0:
            raise OrchestratorValidationError(f"max_tokens must be positive, got {self.max_tokens}")


@dataclass
class OrchestrationResponse:
    """
    Complete end-to-end response returned by PwanimateOrchestrator.

    Attributes:
        answer: Generated textual answer.
        citations: Unique citation strings associated with grounding sources.
        sources: Detailed metadata list of grounding entities used in context.
        provider: Identifier of AI provider that fulfilled generation.
        model: Model used for generation.
        prompt_tokens: Prompt token count if reported.
        completion_tokens: Completion token count if reported.
        total_tokens: Total token count if reported.
        retrieval_time_ms: Upstream retrieval duration in milliseconds.
        generation_time_ms: Gateway generation duration in milliseconds.
        total_time_ms: End-to-end pipeline execution time in milliseconds.
        metadata: Additional diagnostic or task metadata.
    """
    answer: str
    citations: List[str] = field(default_factory=list)
    sources: List[Dict[str, Any]] = field(default_factory=list)
    provider: str = ""
    model: str = ""
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    retrieval_time_ms: float = 0.0
    generation_time_ms: float = 0.0
    total_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    quota_info: Optional[Dict[str, Any]] = None
    people: List[Dict[str, Any]] = field(default_factory=list)
    finish_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to clean JSON-serializable dictionary."""
        d = {
            "answer": self.answer,
            "citations": list(self.citations),
            "sources": list(self.sources),
            "people": list(self.people),
            "provider": self.provider,
            "model": self.model,
            "finish_reason": self.finish_reason,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "timing": {
                "retrieval_ms": self.retrieval_time_ms,
                "generation_ms": self.generation_time_ms,
                "total_ms": self.total_time_ms,
            },
            "metadata": dict(self.metadata),
            "quota_info": dict(self.quota_info) if self.quota_info else None,
        }
        if self.people:
            d["blocks"] = [{"type": "people", "people": list(self.people)}]
        else:
            d["blocks"] = []
        return d
