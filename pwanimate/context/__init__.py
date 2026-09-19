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
from .user_context import (
    UserContext,
    UserContextService,
    normalize_interests,
    normalize_skills,
    resolve_display_name,
)

__all__ = [
    'ContextRequest',
    'ContextItem',
    'ContextPackage',
    'ContextEngine',
    'estimate_tokens',
    'UserContext',
    'UserContextService',
    'normalize_interests',
    'normalize_skills',
    'resolve_display_name',
]

