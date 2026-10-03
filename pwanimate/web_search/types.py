"""Normalized data contracts shared by web-search providers and Pwanimate."""

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class WebSearchProvider(Protocol):
    """Common interface implemented by each provider adapter."""

    provider_name: str

    def is_available(self) -> bool:
        """Whether this provider has the credentials required to call it."""

    def search(
        self,
        query: str,
        *,
        recency: str | None = None,
        domains: list[str] | None = None,
        max_results: int = 5,
    ) -> "WebSearchResponse":
        """Return normalized public web results for a query."""


@dataclass(frozen=True)
class WebSearchResult:
    title: str
    url: str
    snippet: str
    source: str
    published_at: str | None = None
    score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "published_at": self.published_at,
            "score": self.score,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class WebSearchResponse:
    provider: str
    query: str
    results: list[WebSearchResult]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "query": self.query,
            "results": [result.to_dict() for result in self.results],
            "metadata": dict(self.metadata),
        }
