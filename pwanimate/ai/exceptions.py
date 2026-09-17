"""
AI Gateway and Provider Exception Hierarchy for Pwanimate.

Defines normalized, provider-neutral exceptions for all downstream
AI operations. Never exposes API secrets or raw credentials in messages.
"""


class AIGatewayError(Exception):
    """Base exception for all AI Gateway and provider operations."""
    def __init__(self, message: str, provider: str = "", status_code: int = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.status_code = status_code
        self.details = details or {}

    def __str__(self):
        prefix = f"[{self.provider}] " if self.provider else ""
        code = f" (status {self.status_code})" if self.status_code else ""
        return f"{prefix}{self.message}{code}"


class AIProviderConfigurationError(AIGatewayError):
    """Raised when an AI provider is misconfigured or missing credentials."""
    pass


class AIProviderAuthenticationError(AIGatewayError):
    """Raised when external provider returns 401 or 403 authentication failure."""
    pass


class AIProviderRateLimitError(AIGatewayError):
    """Raised when external provider returns 429 rate limit or quota exhausted."""
    pass


class AIProviderTimeoutError(AIGatewayError):
    """Raised when connection or read timeout occurs during provider call."""
    pass


class AIProviderAPIError(AIGatewayError):
    """Raised when external provider returns 4xx or 5xx server or request error."""
    pass
