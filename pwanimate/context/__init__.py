"""
Pwanimate Context Engine Package.

Provides contracts and services to transform authorized retrieval results
into bounded, provenance-preserving ContextPackages for future AI Gateway consumption.
"""

from .types import (
    ContextRequest,
    ContextItem,
    ContextPackage,
    estimate_tokens,
)
from .engine import ContextEngine

__all__ = [
    'ContextRequest',
    'ContextItem',
    'ContextPackage',
    'ContextEngine',
    'estimate_tokens',
]
