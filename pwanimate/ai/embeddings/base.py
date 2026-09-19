"""
Abstract base class for Pwanimate embedding providers.

Provides a unified interface that isolates provider-specific SDKs,
endpoints, and authentication from the rest of the application.
"""

from abc import ABC, abstractmethod
from typing import List


class EmbeddingProviderError(Exception):
    """Base exception for all embedding generation errors."""
    def __init__(self, message: str, provider: str = "", status_code: int = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.status_code = status_code
        self.details = details or {}

    def __str__(self):
        prefix = f"[{self.provider}] " if self.provider else ""
        code = f" (status {self.status_code})" if self.status_code else ""
        return f"{prefix}{self.message}{code}"


class EmbeddingConfigurationError(EmbeddingProviderError):
    """Raised when an embedding provider is not properly configured (e.g. missing API key)."""
    pass


class EmbeddingAuthenticationError(EmbeddingProviderError):
    """Raised when external provider returns 401 or 403 authentication failure."""
    pass


class EmbeddingDimensionMismatchError(EmbeddingProviderError):
    """Raised when returned vectors do not match the expected dimensionality."""
    pass


class EmbeddingQuotaExhaustedError(EmbeddingProviderError):
    """Raised when the API quota is exhausted (HTTP 429 / rate limit).

    Unlike hard failures, quota errors are transient — the request should be
    retried after a sufficient back-off window, and chunks must NOT be marked
    'failed' while waiting for quota to reset.
    """
    pass


class EmbeddingTimeoutError(EmbeddingProviderError):
    """Raised when connection or read timeout occurs during provider call."""
    pass


class EmbeddingInvalidRequestError(EmbeddingProviderError):
    """Raised when external provider returns 400 or 422 client payload error."""
    pass


class EmbeddingServerResponseError(EmbeddingProviderError):
    """Raised when external provider returns 5xx server error or unhandled error status."""
    pass


class EmbeddingMalformedResponseError(EmbeddingProviderError):
    """Raised when external provider returns unparseable or unexpected response payload."""
    pass


class BaseEmbeddingProvider(ABC):
    """
    Abstract interface for vector embedding providers in Pwanimate.
    """

    @abstractmethod
    def embed_texts(self, texts: List[str], task_type: str = "RETRIEVAL_DOCUMENT") -> List[List[float]]:
        """
        Generate embedding vectors for a list of document chunk texts.

        Args:
            texts: List of text strings to embed.
            task_type: Task purpose (e.g., 'RETRIEVAL_DOCUMENT' or 'RETRIEVAL_QUERY').

        Returns:
            List of float vectors, one per input text.
        """
        pass

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """
        Generate an embedding vector for a single query text.

        Args:
            text: Query string to embed.

        Returns:
            Float vector of embedding dimensions.
        """
        pass

    @abstractmethod
    def get_dimensions(self) -> int:
        """Return the vector dimensionality produced by this provider and model."""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the canonical model identifier string."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Check whether the provider has the necessary credentials and configuration."""
        pass
