"""HTTP adapters for supported web-search providers."""

import math
from typing import Any
from urllib.parse import urlsplit

import requests

from pwanimate.web_search.exceptions import WebSearchProviderError
from pwanimate.web_search.types import WebSearchResponse, WebSearchResult

_RECENCY_TAVILY = {"day": "day", "week": "week", "month": "month", "year": "year"}
_RECENCY_BRAVE = {"day": "pd", "week": "pw", "month": "pm", "year": "py"}
_RECENCY_SERPER = {"day": "qdr:d", "week": "qdr:w", "month": "qdr:m", "year": "qdr:y"}


class BaseWebSearchProvider:
    provider_name = ""
    endpoint = ""

    def __init__(self, api_key: str = "", timeout: float = 10.0, session: requests.Session | None = None):
        self.api_key = (api_key or "").strip()
        self.timeout = timeout
        self.session = session or requests.Session()

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _send(self, method: str, *, headers: dict[str, str], params=None, json=None):
        if not self.is_available():
            raise WebSearchProviderError(self.provider_name, "not_configured")
        try:
            response = self.session.request(
                method,
                self.endpoint,
                headers=headers,
                params=params,
                json=json,
                timeout=self.timeout,
            )
        except requests.Timeout:
            raise WebSearchProviderError(self.provider_name, "timeout") from None
        except requests.RequestException:
            raise WebSearchProviderError(self.provider_name, "connection_error") from None

        status_code = getattr(response, "status_code", None)
        if not isinstance(status_code, int) or status_code < 200 or status_code >= 300:
            raise WebSearchProviderError(self.provider_name, "upstream_error", status_code)
        try:
            payload = response.json()
        except (ValueError, TypeError):
            raise WebSearchProviderError(self.provider_name, "invalid_json", status_code) from None
        if not isinstance(payload, dict):
            raise WebSearchProviderError(self.provider_name, "invalid_response", status_code)
        return payload

    def _normalize_results(self, values: Any, max_results: int) -> list[WebSearchResult]:
        if not isinstance(values, list):
            raise WebSearchProviderError(self.provider_name, "invalid_results")

        normalized = []
        for entry in values[:max_results]:
            if not isinstance(entry, dict):
                continue
            url = _safe_url(entry.get("url") or entry.get("link"))
            title = _clean_text(entry.get("title"), limit=500)
            snippet = _clean_text(
                entry.get("content") or entry.get("description") or entry.get("snippet"),
                limit=3000,
            )
            if not url or not title:
                continue
            hostname = urlsplit(url).hostname or ""
            score = _as_score(entry.get("score"))
            published_at = _clean_text(
                entry.get("published_date") or entry.get("published_at") or entry.get("page_age") or entry.get("date"),
                limit=120,
            ) or None
            normalized.append(WebSearchResult(
                title=title,
                url=url,
                snippet=snippet,
                source=hostname.lower(),
                published_at=published_at,
                score=score,
            ))
        if values and not normalized:
            raise WebSearchProviderError(self.provider_name, "invalid_results")
        return normalized


class TavilySearchProvider(BaseWebSearchProvider):
    provider_name = "tavily"
    endpoint = "https://api.tavily.com/search"

    def search(
        self,
        query: str,
        *,
        recency: str | None = None,
        domains: list[str] | None = None,
        max_results: int = 5,
    ) -> WebSearchResponse:
        payload: dict[str, Any] = {
            "query": query,
            "search_depth": "basic",
            "max_results": max_results,
            "include_answer": False,
            "include_raw_content": False,
            "include_published_date": True,
        }
        if recency in _RECENCY_TAVILY:
            payload["time_range"] = _RECENCY_TAVILY[recency]
        if domains:
            payload["include_domains"] = domains
        data = self._send(
            "POST",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=payload,
        )
        return WebSearchResponse(
            provider=self.provider_name,
            query=query,
            results=self._normalize_results(data.get("results"), max_results),
        )


class BraveSearchProvider(BaseWebSearchProvider):
    provider_name = "brave"
    endpoint = "https://api.search.brave.com/res/v1/web/search"

    def search(
        self,
        query: str,
        *,
        recency: str | None = None,
        domains: list[str] | None = None,
        max_results: int = 5,
    ) -> WebSearchResponse:
        search_query = _query_with_domains(query, domains)
        params: dict[str, Any] = {"q": search_query, "count": min(max_results, 20)}
        if recency in _RECENCY_BRAVE:
            params["freshness"] = _RECENCY_BRAVE[recency]
        data = self._send(
            "GET",
            headers={"Accept": "application/json", "X-Subscription-Token": self.api_key},
            params=params,
        )
        web = data.get("web")
        if not isinstance(web, dict):
            raise WebSearchProviderError(self.provider_name, "invalid_results")
        values = web.get("results")
        if isinstance(values, list):
            enriched_values = []
            for entry in values:
                if isinstance(entry, dict) and isinstance(entry.get("extra_snippets"), list):
                    extra = " ".join(
                        _clean_text(part, limit=700)
                        for part in entry["extra_snippets"]
                        if isinstance(part, str)
                    )
                    if extra:
                        entry = dict(entry)
                        description = _clean_text(entry.get("description"), 1800)
                        entry["description"] = " ".join(filter(None, [description, extra]))
                enriched_values.append(entry)
            values = enriched_values
        return WebSearchResponse(
            provider=self.provider_name,
            query=query,
            results=self._normalize_results(values, max_results),
        )


class SerperSearchProvider(BaseWebSearchProvider):
    provider_name = "serper"
    endpoint = "https://google.serper.dev/search"

    def search(
        self,
        query: str,
        *,
        recency: str | None = None,
        domains: list[str] | None = None,
        max_results: int = 5,
    ) -> WebSearchResponse:
        payload: dict[str, Any] = {"q": _query_with_domains(query, domains), "num": min(max_results, 20)}
        if recency in _RECENCY_SERPER:
            payload["tbs"] = _RECENCY_SERPER[recency]
        data = self._send(
            "POST",
            headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
            json=payload,
        )
        return WebSearchResponse(
            provider=self.provider_name,
            query=query,
            results=self._normalize_results(data.get("organic"), max_results),
        )


def _safe_url(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    value = value.strip()
    if len(value) > 2048:
        return ""
    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            return ""
        if parsed.username or parsed.password:
            return ""
    except ValueError:
        return ""
    return value


def _clean_text(value: Any, limit: int) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:limit]


def _as_score(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        return None
    score = float(value)
    return score if math.isfinite(score) else None


def _query_with_domains(query: str, domains: list[str] | None) -> str:
    if not domains:
        return query
    site_filter = " OR ".join(f"site:{domain}" for domain in domains)
    return f"{query} ({site_filter})"
