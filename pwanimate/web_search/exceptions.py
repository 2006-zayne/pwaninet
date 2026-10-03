"""Safe, provider-neutral web search errors."""


class WebSearchError(Exception):
    """Base class for web search failures safe to handle above the provider layer."""


class WebSearchUnavailable(WebSearchError):
    """Raised when web search is disabled or no provider has credentials."""


class WebSearchProviderError(WebSearchError):
    """A provider could not return a valid search response.

    Error details deliberately exclude provider response bodies and request data,
    which may contain sensitive queries or credential-bearing request context.
    """

    def __init__(self, provider: str, code: str, status_code: int | None = None):
        super().__init__(f"{provider} search failed ({code}).")
        self.provider = provider
        self.code = code
        self.status_code = status_code
