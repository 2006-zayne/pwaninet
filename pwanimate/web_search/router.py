"""Provider selection, fallback, and safe operational logging."""

import logging
import re
import time
from pwanimate.web_search.config import WebSearchConfig
from pwanimate.web_search.exceptions import WebSearchError, WebSearchProviderError, WebSearchUnavailable
from pwanimate.web_search.providers import BraveSearchProvider, SerperSearchProvider, TavilySearchProvider
from pwanimate.web_search.types import WebSearchProvider, WebSearchResponse

logger = logging.getLogger(__name__)

_DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"
    r"[a-zA-Z]{2,63}$"
)
_VALID_RECENCY = {"day", "week", "month", "year"}


class WebSearchRouter:
    """Search through configured providers in priority order, falling back on failure."""

    def __init__(
        self,
        config: WebSearchConfig | None = None,
        providers: dict[str, WebSearchProvider] | None = None,
    ):
        self.config = config or WebSearchConfig.from_django_settings()
        if providers is None:
            providers = {
                "tavily": TavilySearchProvider(self.config.tavily_api_key, self.config.timeout_seconds),
                "brave": BraveSearchProvider(self.config.brave_search_api_key, self.config.timeout_seconds),
                "serper": SerperSearchProvider(self.config.serper_api_key, self.config.timeout_seconds),
            }
        self.providers = providers

    def search(
        self,
        query: str,
        *,
        recency: str | None = None,
        domains: list[str] | None = None,
        max_results: int | None = None,
    ) -> WebSearchResponse:
        if not self.config.enabled:
            raise WebSearchUnavailable("Web search is disabled.")

        if not isinstance(query, str):
            raise WebSearchError("A search query must be text.")
        clean_query = " ".join(query.split())
        if not clean_query:
            raise WebSearchError("A search query is required.")
        if len(clean_query) > 600:
            raise WebSearchError("Search queries must be 600 characters or fewer.")
        clean_recency = str(recency).strip().lower() if recency else None
        if clean_recency and clean_recency not in _VALID_RECENCY:
            raise WebSearchError("Unsupported search recency value.")
        clean_domains = _validate_domains(domains)
        if max_results is None:
            result_limit = self.config.max_results
        else:
            try:
                result_limit = min(max(int(max_results), 1), 20)
            except (TypeError, ValueError) as exc:
                raise WebSearchError("Result limit must be a number.") from exc
        logger.info(
            "Pwanimate web search requested query_length=%d result_limit=%d",
            len(clean_query),
            result_limit,
        )

        available = [
            (name, self.providers.get(name))
            for name in self.config.provider_order
            if self.providers.get(name) is not None and self.providers[name].is_available()
        ]
        if not available:
            logger.info(
                "Pwanimate web search unavailable reason=no_configured_provider query_length=%d",
                len(clean_query),
            )
            raise WebSearchUnavailable("No web search provider is configured.")

        started = time.perf_counter()
        for provider_index, (name, provider) in enumerate(available):
            provider_started = time.perf_counter()
            try:
                response = provider.search(
                    clean_query,
                    recency=clean_recency,
                    domains=clean_domains,
                    max_results=result_limit,
                )
                elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
                logger.info(
                    "Pwanimate web search completed provider=%s result_count=%d latency_ms=%.2f query_length=%d",
                    name,
                    len(response.results),
                    elapsed_ms,
                    len(clean_query),
                )
                return response
            except WebSearchProviderError as exc:
                logger.warning(
                    "Pwanimate web search provider failed provider=%s failure=%s "
                    "status_code=%s latency_ms=%.2f query_length=%d",
                    name,
                    exc.code,
                    exc.status_code,
                    round((time.perf_counter() - provider_started) * 1000, 2),
                    len(clean_query),
                )
                if provider_index + 1 < len(available):
                    next_provider = available[provider_index + 1][0]
                    logger.info(
                        "Pwanimate web search fallback from_provider=%s to_provider=%s query_length=%d",
                        name,
                        next_provider,
                        len(clean_query),
                    )
            except Exception as exc:
                logger.warning(
                    "Pwanimate web search provider failed provider=%s failure=%s latency_ms=%.2f query_length=%d",
                    name,
                    type(exc).__name__,
                    round((time.perf_counter() - provider_started) * 1000, 2),
                    len(clean_query),
                )
                if provider_index + 1 < len(available):
                    next_provider = available[provider_index + 1][0]
                    logger.info(
                        "Pwanimate web search fallback from_provider=%s to_provider=%s query_length=%d",
                        name,
                        next_provider,
                        len(clean_query),
                    )

        logger.error(
            "Pwanimate web search exhausted providers attempted=%d latency_ms=%.2f query_length=%d",
            len(available),
            round((time.perf_counter() - started) * 1000, 2),
            len(clean_query),
        )
        raise WebSearchError("All configured web search providers are temporarily unavailable.") from None


def _validate_domains(domains: list[str] | None) -> list[str] | None:
    if domains is None:
        return None
    if not isinstance(domains, list) or len(domains) > 10:
        raise WebSearchError("Provide at most 10 valid search domains.")
    cleaned = []
    for value in domains:
        if not isinstance(value, str):
            raise WebSearchError("Search domains must be host names.")
        domain = value.strip().lower().rstrip(".")
        if not _DOMAIN_RE.fullmatch(domain):
            raise WebSearchError("Search domains must be host names without paths or URLs.")
        if domain not in cleaned:
            cleaned.append(domain)
    return cleaned or None
