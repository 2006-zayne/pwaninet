"""Mocked tests for Pwanimate's provider-neutral web search."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import requests
from django.test import SimpleTestCase, override_settings

from pwanimate.orchestrator.service import PwanimateOrchestrator
from pwanimate.orchestrator.types import OrchestrationRequest
from pwanimate.ai.gateway.types import LLMResponse
from pwanimate.tools.adapter import build_tool_context_package, tool_result_to_context_items
from pwanimate.tools.base import ToolResult
from pwanimate.tools.domain.web_search import WebSearchTool
from pwanimate.tools.registry import get_default_tool_registry
from pwanimate.tools.selector import LLMToolSelector
from pwanimate.web_search.config import WebSearchConfig
from pwanimate.web_search.exceptions import WebSearchError, WebSearchProviderError, WebSearchUnavailable
from pwanimate.web_search.providers import BraveSearchProvider, SerperSearchProvider, TavilySearchProvider
from pwanimate.web_search.router import WebSearchRouter
from pwanimate.web_search.types import WebSearchResponse, WebSearchResult


class FakeResponse:
    def __init__(self, data, status_code=200):
        self.data = data
        self.status_code = status_code

    def json(self):
        if isinstance(self.data, Exception):
            raise self.data
        return self.data


class FakeProvider:
    def __init__(self, name, response=None, error=None, available=True):
        self.provider_name = name
        self.response = response or WebSearchResponse(name, "query", [])
        self.error = error
        self.available = available
        self.calls = []

    def is_available(self):
        return self.available

    def search(self, query, **kwargs):
        self.calls.append((query, kwargs))
        if self.error:
            raise self.error
        return self.response


class WebSearchConfigTests(SimpleTestCase):
    def test_settings_read_order_and_bounds(self):
        source = SimpleNamespace(
            WEB_SEARCH_ENABLED="yes",
            WEB_SEARCH_PROVIDER_ORDER="serper, tavily,serper,unknown",
            TAVILY_API_KEY=" tavily-secret ",
            BRAVE_SEARCH_API_KEY="",
            SERPER_API_KEY="serper-secret",
            WEB_SEARCH_TIMEOUT_SECONDS="12.5",
            WEB_SEARCH_MAX_RESULTS="7",
        )
        config = WebSearchConfig.from_django_settings(source)
        self.assertTrue(config.enabled)
        self.assertEqual(config.provider_order, ("serper", "tavily"))
        self.assertEqual(config.tavily_api_key, "tavily-secret")
        self.assertEqual(config.timeout_seconds, 12.5)
        self.assertEqual(config.max_results, 7)

    def test_empty_keys_make_search_unavailable_without_http(self):
        config = WebSearchConfig(tavily_api_key="", brave_search_api_key="", serper_api_key="")
        router = WebSearchRouter(config=config)
        with self.assertRaises(WebSearchUnavailable):
            router.search("latest public information")

    @override_settings(
        WEB_SEARCH_ENABLED=True,
        TAVILY_API_KEY="",
        BRAVE_SEARCH_API_KEY="",
        SERPER_API_KEY="",
    )
    def test_tool_returns_safe_unavailable_result_without_api_keys(self):
        result = WebSearchTool().execute(user=None, query="latest public information")
        self.assertFalse(result.success)
        self.assertEqual(result.metadata["error_type"], "web_search_unavailable")
        self.assertIn("not configured", result.error)
        self.assertNotIn("API", result.to_dict())


class ProviderAdapterTests(SimpleTestCase):
    def test_tavily_success_normalizes_fields_and_uses_expected_request(self):
        session = Mock()
        session.request.return_value = FakeResponse({"results": [{
            "title": "A result", "url": "https://example.com/article", "content": " Useful snippet ",
            "published_date": "2026-09-30", "score": 0.91,
        }]})
        provider = TavilySearchProvider("tavily-secret", timeout=8, session=session)

        response = provider.search("a query", recency="week", domains=["example.com"], max_results=4)

        self.assertEqual(response.provider, "tavily")
        self.assertEqual(response.results[0].source, "example.com")
        self.assertEqual(response.results[0].snippet, "Useful snippet")
        self.assertEqual(response.results[0].published_at, "2026-09-30")
        self.assertEqual(response.results[0].score, 0.91)
        request = session.request.call_args.kwargs
        self.assertEqual(request["timeout"], 8)
        self.assertEqual(request["headers"]["Authorization"], "Bearer tavily-secret")
        self.assertEqual(request["json"]["time_range"], "week")
        self.assertEqual(request["json"]["include_domains"], ["example.com"])

    def test_brave_success_normalizes_results_and_maps_recency_domains(self):
        session = Mock()
        session.request.return_value = FakeResponse({"web": {"results": [{
            "title": "Brave result", "url": "https://news.example.org/story", "description": "A snippet",
            "extra_snippets": ["More context"], "page_age": "2 days ago",
        }]}})
        provider = BraveSearchProvider("brave-secret", session=session)

        response = provider.search("a query", recency="day", domains=["example.org"])

        self.assertEqual(response.results[0].published_at, "2 days ago")
        self.assertIn("More context", response.results[0].snippet)
        request = session.request.call_args.kwargs
        self.assertEqual(request["headers"]["X-Subscription-Token"], "brave-secret")
        self.assertEqual(request["params"]["freshness"], "pd")
        self.assertIn("site:example.org", request["params"]["q"])

    def test_serper_success_normalizes_results_and_maps_recency(self):
        session = Mock()
        session.request.return_value = FakeResponse({"organic": [{
            "title": "Serper result", "link": "https://example.net/page", "snippet": "A result", "date": "Sep 2026",
        }]})
        provider = SerperSearchProvider("serper-secret", session=session)

        response = provider.search("a query", recency="month", max_results=3)

        self.assertEqual(response.results[0].title, "Serper result")
        self.assertEqual(response.results[0].url, "https://example.net/page")
        self.assertEqual(response.results[0].published_at, "Sep 2026")
        request = session.request.call_args.kwargs
        self.assertEqual(request["headers"]["X-API-KEY"], "serper-secret")
        self.assertEqual(request["json"]["tbs"], "qdr:m")
        self.assertEqual(request["json"]["num"], 3)

    def test_missing_key_skips_provider_before_http_call(self):
        session = Mock()
        provider = TavilySearchProvider("", session=session)
        self.assertFalse(provider.is_available())
        with self.assertRaises(WebSearchProviderError):
            provider.search("query")
        self.assertFalse(session.request.called)

    def test_malformed_provider_response_is_rejected(self):
        session = Mock()
        session.request.return_value = FakeResponse({"unexpected": []})
        with self.assertRaises(WebSearchProviderError):
            TavilySearchProvider("key", session=session).search("query")

    def test_http_error_is_cleanly_classified(self):
        session = Mock()
        session.request.return_value = FakeResponse({"error": "private upstream response"}, status_code=429)
        with self.assertRaises(WebSearchProviderError) as caught:
            TavilySearchProvider("key", session=session).search("query")
        self.assertEqual(caught.exception.status_code, 429)
        self.assertNotIn("private upstream response", str(caught.exception))

    def test_timeout_is_cleanly_classified(self):
        session = Mock()
        session.request.side_effect = requests.Timeout("sensitive request details")
        with self.assertRaises(WebSearchProviderError) as caught:
            BraveSearchProvider("key", session=session).search("query")
        self.assertEqual(caught.exception.code, "timeout")
        self.assertNotIn("sensitive request details", str(caught.exception))

    def test_empty_results_are_a_valid_empty_response(self):
        session = Mock()
        session.request.return_value = FakeResponse({"results": []})
        response = TavilySearchProvider("key", session=session).search("query")
        self.assertEqual(response.results, [])


class WebSearchRouterTests(SimpleTestCase):
    def _config(self):
        return WebSearchConfig(provider_order=("tavily", "brave", "serper"))

    def test_first_success_stops_fallback(self):
        result = WebSearchResult("Title", "https://example.com", "Snippet", "example.com")
        tavily = FakeProvider("tavily", WebSearchResponse("tavily", "query", [result]))
        brave = FakeProvider("brave")
        serper = FakeProvider("serper")

        response = WebSearchRouter(self._config(), {"tavily": tavily, "brave": brave, "serper": serper}).search("query")

        self.assertEqual(response.provider, "tavily")
        self.assertEqual(len(tavily.calls), 1)
        self.assertEqual(brave.calls, [])
        self.assertEqual(serper.calls, [])

    def test_falls_back_after_provider_failure_and_stops_at_first_success(self):
        tavily = FakeProvider("tavily", error=WebSearchProviderError("tavily", "upstream_error", 503))
        result = WebSearchResult("Title", "https://example.com", "Snippet", "example.com")
        brave = FakeProvider("brave", WebSearchResponse("brave", "query", [result]))
        serper = FakeProvider("serper")

        response = WebSearchRouter(self._config(), {"tavily": tavily, "brave": brave, "serper": serper}).search("query")

        self.assertEqual(response.provider, "brave")
        self.assertEqual(len(tavily.calls), 1)
        self.assertEqual(len(brave.calls), 1)
        self.assertEqual(serper.calls, [])

    def test_tries_all_providers_in_priority_order(self):
        calls = []

        class OrderedProvider(FakeProvider):
            def search(self, query, **kwargs):
                calls.append(self.provider_name)
                return super().search(query, **kwargs)

        providers = {
            name: OrderedProvider(name, error=RuntimeError("provider failure"))
            for name in ("tavily", "brave")
        }
        result = WebSearchResult("Title", "https://example.com", "Snippet", "example.com")
        providers["serper"] = OrderedProvider("serper", WebSearchResponse("serper", "query", [result]))

        response = WebSearchRouter(self._config(), providers).search("query")

        self.assertEqual(calls, ["tavily", "brave", "serper"])
        self.assertEqual(response.provider, "serper")

    def test_all_failures_return_clean_error_and_do_not_log_query_or_key(self):
        secret_query = "private student research query"
        providers = {
            name: FakeProvider(name, error=RuntimeError("Bearer top-secret-key " + secret_query))
            for name in ("tavily", "brave", "serper")
        }
        router = WebSearchRouter(self._config(), providers)

        with self.assertLogs("pwanimate.web_search.router", level="WARNING") as captured:
            with self.assertRaises(WebSearchError) as caught:
                router.search(secret_query)

        logs = "\n".join(captured.output)
        self.assertNotIn(secret_query, logs)
        self.assertNotIn("top-secret-key", logs)
        self.assertNotIn("top-secret-key", str(caught.exception))
        self.assertIn("temporarily unavailable", str(caught.exception))

    def test_invalid_domains_are_rejected_before_provider_call(self):
        provider = FakeProvider("tavily")
        router = WebSearchRouter(self._config(), {"tavily": provider})
        with self.assertRaises(WebSearchError):
            router.search("query", domains=["https://example.com/private"])
        self.assertEqual(provider.calls, [])


class WebSearchIntegrationTests(SimpleTestCase):
    def test_default_registry_has_one_provider_neutral_web_tool(self):
        names = {tool.name for tool in get_default_tool_registry().list_tools()}
        self.assertIn("web_search", names)
        self.assertNotIn("tavily_search", names)
        self.assertNotIn("brave_search", names)
        self.assertNotIn("serper_search", names)

    def test_selector_gates_public_web_search_but_skips_stable_concepts(self):
        self.assertTrue(LLMToolSelector.might_need_tool("Please search the internet for this"))
        self.assertTrue(LLMToolSelector.might_need_tool("What is the latest release?"))
        self.assertTrue(LLMToolSelector.might_need_tool("Research the new public policy"))
        self.assertTrue(LLMToolSelector.might_need_tool("What were they discussing at the recent meeting?"))
        self.assertFalse(LLMToolSelector.might_need_tool("Explain photosynthesis simply"))
        self.assertIn("does not need to explicitly ask for web search", LLMToolSelector.SYSTEM_INSTRUCTION)
        self.assertIn("recent events, news", LLMToolSelector.SYSTEM_INSTRUCTION)

    def test_recent_event_and_its_follow_up_require_web_search_without_model_choice(self):
        first_question = "What did the AI companies discuss at the recent Trump meeting?"
        self.assertEqual(LLMToolSelector.required_web_query(first_question), first_question)

        history = [
            SimpleNamespace(role="user", content="What did the AI companies discuss at the recent Trump meeting?"),
            SimpleNamespace(role="assistant", content="They signed an accord at the White House meeting."),
        ]
        self.assertIn("Was Sam Altman present?", LLMToolSelector.required_web_query(
            "Was Sam Altman present?", history
        ))

    def test_web_results_keep_urls_and_published_dates_in_grounding_sources(self):
        result = ToolResult.ok([{
            "title": "A public result",
            "url": "https://example.com/story",
            "snippet": "A useful web snippet.",
            "source": "example.com",
            "published_at": "2026-09-30",
            "score": 0.8,
        }])

        items = tool_result_to_context_items("web_search", result)
        package = build_tool_context_package("current public fact", items)
        source_summary = PwanimateOrchestrator._build_sources_summary(None, package.items)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].url, "https://example.com/story")
        self.assertIn("2026-09-30", items[0].content)
        self.assertIn("[Web 1: example.com]", package.citations)
        self.assertEqual(source_summary[0]["url"], "https://example.com/story")
        self.assertEqual(source_summary[0]["published_at"], "2026-09-30")

    def test_unavailable_tool_result_becomes_notice_without_fake_sources(self):
        items = tool_result_to_context_items(
            "web_search",
            ToolResult.fail("Web search is not configured.", error_type="web_search_unavailable"),
        )
        self.assertEqual(len(items), 1)
        self.assertIsNone(items[0].citation)
        self.assertEqual(items[0].url, "")
        self.assertIn("not configured", items[0].content)

    def test_model_selected_web_search_flows_into_answer_context_and_sources(self):
        search_response = WebSearchResponse("tavily", "latest test news", [
            WebSearchResult(
                "A current story",
                "https://example.com/story",
                "The current story snippet.",
                "example.com",
                published_at="2026-10-01",
                score=0.95,
            )
        ])
        search_router = Mock()
        search_router.search.return_value = search_response
        gateway = Mock()
        gateway.generate.side_effect = [
            LLMResponse(
                content='{"tool":"web_search","arguments":{"query":"latest test news"},"sources":[]}',
                provider="mock",
                model="selector",
            ),
            LLMResponse(
                content="The latest report says this. [Web 1: example.com]",
                provider="openrouter",
                model="answer-model",
            ),
        ]

        with patch("pwanimate.tools.domain.web_search.WebSearchRouter", return_value=search_router):
            orchestrator = PwanimateOrchestrator(gateway=gateway)
            response = orchestrator.run(OrchestrationRequest(
                query="Search the internet for the latest test news",
                provider="openrouter",
                model="answer-model",
            ))

        self.assertEqual(gateway.generate.call_count, 2)
        self.assertEqual(search_router.search.call_args.args[0], "latest test news")
        self.assertEqual(response.provider, "openrouter")
        self.assertEqual(response.sources[0]["url"], "https://example.com/story")
        answer_request = gateway.generate.call_args_list[1].args[0]
        self.assertIn("GROUNDING MODE: OPTIONAL", answer_request.system_instruction)
        self.assertIn("https://example.com/story", answer_request.context.format_context_text())
