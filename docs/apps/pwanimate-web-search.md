# Pwanimate web search

## Architecture

Pwanimate exposes one `web_search` tool. The tool calls `WebSearchRouter`, which tries enabled, credentialed providers in configured order and stops at the first valid response. The initial order is Tavily, Brave Search, then Serper. Each adapter normalizes provider results into `WebSearchResponse` and `WebSearchResult`, including title, original URL, snippet, source domain, publication date when available, and relevance score when supplied.

The search provider only retrieves results. The existing Pwanimate tool adapter turns those results into grounded context items for the selected answer model. The answer model receives citation labels and source URLs through the existing response source metadata. Search results are treated as untrusted external evidence, not instructions. Provider names and credentials are hidden from the model-facing tool schema.

The LLM-assisted selector only chooses web search for an explicit online lookup or information that may have changed. Stable concepts do not trigger a web request. PwaniNet documents, posts, groups, people, policies, and private account data continue through their existing tools and retrieval paths.

## Configuration

All values are optional. With empty provider keys, the Django application starts normally and Pwanimate reports that web search is unavailable only when a web lookup is requested.

```env
WEB_SEARCH_ENABLED=true
WEB_SEARCH_PROVIDER_ORDER=tavily,brave,serper
TAVILY_API_KEY=
BRAVE_SEARCH_API_KEY=
SERPER_API_KEY=
WEB_SEARCH_TIMEOUT_SECONDS=10
WEB_SEARCH_MAX_RESULTS=5
```

Set one or more keys in the local environment or secret manager. Keep credentials server-side; `.env` is ignored by Git and `.env.example` contains blank values only. Set `WEB_SEARCH_ENABLED=false` to disable the feature without removing provider keys.

Supported recency values are `day`, `week`, `month`, and `year`. Optional domains must be host names, such as `example.org`; the tool rejects URLs and paths.

## Fallback and provider maintenance

Providers are attempted in `WEB_SEARCH_PROVIDER_ORDER`; unknown names are ignored and duplicates are removed. If no recognized names remain, the default order is used. Providers without keys are skipped. Timeouts, malformed responses, authentication/upstream errors, and quota/rate-limit responses fall through to the next configured provider. A successful empty result set is returned as empty and does not trigger another paid search. If no providers have keys, the router raises `WebSearchUnavailable`. If all configured providers fail, it raises a clean `WebSearchError` without response bodies or credentials.

To add a provider, implement the `WebSearchProvider` interface, normalize its response to `WebSearchResponse`, add its key and order name to centralized config/settings, and cover request, normalization, error, and fallback behavior with mocked HTTP tests. Do not add provider-specific tools to the model-facing registry.

Operational logs include provider, result count, query length, outcome, status code where available, and latency. They omit full queries, headers, secrets, and upstream response bodies.

## Verification

Run the isolated mocked suite with:

```bash
./venv/bin/python manage.py test pwanimate.tests.test_web_search
```

The suite mocks HTTP responses and does not contact search providers.
