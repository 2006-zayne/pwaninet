"""
Base LLM Provider Interface for Pwanimate.

Defines the contract that all generative AI providers (Gemini, Groq,
OpenRouter, Mock) must implement. Kept completely separate from
BaseEmbeddingProvider.
"""

from abc import ABC, abstractmethod
import logging

from pwanimate.ai.gateway.types import LLMRequest, LLMResponse

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    """
    Abstract interface for generative LLM providers.

    All subclasses must implement generate() and is_available().
    """

    provider_name: str = "base"

    @abstractmethod
    def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Synchronously generate a response for the given request.

        Args:
            request: Validated provider-neutral LLMRequest.

        Returns:
            Normalized LLMResponse.

        Raises:
            AIProviderConfigurationError: If credentials or model are missing.
            AIProviderAuthenticationError: If credentials fail authentication.
            AIProviderRateLimitError: If rate limit/quota is hit.
            AIProviderTimeoutError: If request times out.
            AIProviderAPIError: On unexpected 4xx/5xx responses or malformed data.
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if provider is sufficiently configured to attempt generation.
        Checks local configuration/keys only; MUST NOT perform network calls.
        """
        pass
