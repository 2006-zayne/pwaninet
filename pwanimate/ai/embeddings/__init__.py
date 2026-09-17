"""
Pwanimate Embedding Provider Subsystem.
"""

from .base import (
    BaseEmbeddingProvider,
    EmbeddingProviderError,
    EmbeddingConfigurationError,
    EmbeddingDimensionMismatchError,
)
from .gemini import GeminiEmbeddingProvider
from .mock import MockEmbeddingProvider
from .factory import get_embedding_provider

__all__ = [
    'BaseEmbeddingProvider',
    'EmbeddingProviderError',
    'EmbeddingConfigurationError',
    'EmbeddingDimensionMismatchError',
    'GeminiEmbeddingProvider',
    'MockEmbeddingProvider',
    'get_embedding_provider',
]
