"""
Deterministic Mock LLM Provider for Pwanimate.

Used for offline testing and local development where external API calls
are not desired or credentials are not configured.
"""

from typing import List, Optional
import logging

from pwanimate.ai.gateway.base import BaseLLMProvider
from pwanimate.ai.gateway.types import LLMRequest, LLMResponse

logger = logging.getLogger(__name__)


class MockLLMProvider(BaseLLMProvider):
    """
    Deterministic mock provider producing predictable LLMResponse instances.
    """

    provider_name: str = "mock"

    def __init__(
        self,
        model_name: str = "mock-llm-v1",
        default_response_text: Optional[str] = None,
        simulated_error: Optional[Exception] = None,
    ):
        self.model_name = model_name
        self.default_response_text = default_response_text
        self.simulated_error = simulated_error
        self.call_count = 0
        self.last_request: Optional[LLMRequest] = None

    def is_available(self) -> bool:
        """Always available as an offline mock."""
        return True

    def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Produce a deterministic LLMResponse.
        """
        self.call_count += 1
        self.last_request = request

        if self.simulated_error:
            raise self.simulated_error

        # Gather citations from request context if available
        citations: List[str] = []
        context_count = 0
        if request.context:
            citations = list(request.context.citations)
            context_count = request.context.total_items

        if self.default_response_text is not None:
            content = self.default_response_text
        else:
            msg_count = len(request.messages)
            last_msg = request.messages[-1].content if request.messages else ""
            content = (
                f"[MockLLM] Processed task '{request.task}' with {msg_count} messages "
                f"and {context_count} context items. Prompt: '{last_msg[:50]}'"
            )

        # Approximate deterministic token counts
        prompt_len = sum(len(m.content) for m in request.messages)
        if request.system_instruction:
            prompt_len += len(request.system_instruction)
        if request.context:
            chars = getattr(request.context, "total_characters", 0)
            if isinstance(chars, int):
                prompt_len += chars
            if getattr(request.context, "user_context", None) and hasattr(request.context.user_context, "format_context_block"):
                prompt_len += len(request.context.user_context.format_context_block())

        prompt_tokens = max(1, prompt_len // 4)
        completion_tokens = max(1, len(content) // 4)
        total_tokens = prompt_tokens + completion_tokens

        return LLMResponse(
            content=content,
            provider=self.provider_name,
            model=request.model or self.model_name,
            finish_reason="stop",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            citations=citations,
            metadata={"mock": True, "call_count": self.call_count},
        )
