"""
Abstract base class for Pwanimate embedding providers.

Provides a unified interface that isolates provider-specific SDKs,
endpoints, and authentication from the rest of the application.
"""

from abc import ABC, abstractmethod
from typing import List


class EmbeddingProviderError(Exception):
    """Base exception for all embedding generation errors."""
    pass


class EmbeddingConfigurationError(EmbeddingProviderError):
    """Raised when an embedding provider is not properly configured (e.g. missing API key)."""
    pass


class EmbeddingDimensionMismatchError(EmbeddingProviderError):
    """Raised when returned vectors do not match the expected dimensionality."""
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
