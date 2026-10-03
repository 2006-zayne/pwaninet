"""Centralized runtime configuration for the web-search subsystem."""

from dataclasses import dataclass
from typing import Any


SUPPORTED_PROVIDERS = ("tavily", "brave", "serper")
DEFAULT_PROVIDER_ORDER = SUPPORTED_PROVIDERS


def _provider_order(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        values = value.split(",")
    elif isinstance(value, (list, tuple)):
        values = value
    else:
        values = DEFAULT_PROVIDER_ORDER

    order = tuple(dict.fromkeys(
        str(item).strip().lower()
        for item in values
        if str(item).strip().lower() in SUPPORTED_PROVIDERS
    ))
    return order or DEFAULT_PROVIDER_ORDER


@dataclass(frozen=True)
class WebSearchConfig:
    enabled: bool = True
    provider_order: tuple[str, ...] = DEFAULT_PROVIDER_ORDER
    tavily_api_key: str = ""
    brave_search_api_key: str = ""
    serper_api_key: str = ""
    timeout_seconds: float = 10.0
    max_results: int = 5

    def __post_init__(self):
        object.__setattr__(self, "provider_order", _provider_order(self.provider_order))
        object.__setattr__(self, "tavily_api_key", str(self.tavily_api_key or "").strip())
        object.__setattr__(self, "brave_search_api_key", str(self.brave_search_api_key or "").strip())
        object.__setattr__(self, "serper_api_key", str(self.serper_api_key or "").strip())
        try:
            timeout = float(self.timeout_seconds)
        except (TypeError, ValueError):
            timeout = 10.0
        try:
            max_results = int(self.max_results)
        except (TypeError, ValueError):
            max_results = 5
        object.__setattr__(self, "timeout_seconds", min(max(timeout, 0.1), 60.0))
        object.__setattr__(self, "max_results", min(max(max_results, 1), 20))

    @classmethod
    def from_django_settings(cls, source: Any = None) -> "WebSearchConfig":
        if source is None:
            from django.conf import settings
            source = settings

        try:
            timeout = float(getattr(source, "WEB_SEARCH_TIMEOUT_SECONDS", 10.0))
        except (TypeError, ValueError):
            timeout = 10.0
        try:
            max_results = int(getattr(source, "WEB_SEARCH_MAX_RESULTS", 5))
        except (TypeError, ValueError):
            max_results = 5

        return cls(
            enabled=_as_bool(getattr(source, "WEB_SEARCH_ENABLED", True)),
            provider_order=_provider_order(getattr(source, "WEB_SEARCH_PROVIDER_ORDER", DEFAULT_PROVIDER_ORDER)),
            tavily_api_key=str(getattr(source, "TAVILY_API_KEY", "") or "").strip(),
            brave_search_api_key=str(getattr(source, "BRAVE_SEARCH_API_KEY", "") or "").strip(),
            serper_api_key=str(getattr(source, "SERPER_API_KEY", "") or "").strip(),
            timeout_seconds=timeout,
            max_results=max_results,
        )


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
