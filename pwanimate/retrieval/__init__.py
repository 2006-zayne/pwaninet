"""
Pwanimate Unified Retrieval Package.

Exposes contracts, services, and adapters for cross-source retrieval.
"""

from .types import (
    SourceType,
    RetrievalMode,
    RetrievalRequest,
    RetrievalResult,
    RetrievalResponse,
)
from .services.document_retrieval import DocumentSemanticRetrievalService
from .services.unified_retrieval import UnifiedRetrievalService
from .adapters.pwaninet_search import PwaniNetSearchAdapter

__all__ = [
    'SourceType',
    'RetrievalMode',
    'RetrievalRequest',
    'RetrievalResult',
    'RetrievalResponse',
    'DocumentSemanticRetrievalService',
    'UnifiedRetrievalService',
    'PwaniNetSearchAdapter',
]
