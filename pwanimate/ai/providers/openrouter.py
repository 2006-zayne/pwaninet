"""
OpenRouter LLM Provider for Pwanimate.

Implements generative LLM calls against OpenRouter's OpenAI-compatible
chat/completions REST API using direct HTTP requests.
"""

from typing import Any, Dict, List, Optional
import logging
import requests

from django.conf import settings

from pwanimate.ai.exceptions import (
    AIProviderAPIError,
    AIProviderAuthenticationError,
    AIProviderConfigurationError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
)
from pwanimate.ai.gateway.base import BaseLLMProvider
from pwanimate.ai.gateway.types import ChatMessage, LLMRequest, LLMResponse

logger = logging.getLogger(__name__)

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterLLMProvider(BaseLLMProvider):
    """
    Direct REST provider for OpenRouter API.
    """

    provider_name: str = "openrouter"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: Optional[float] = None,
        connect_timeout: Optional[float] = None,
        site_url: str = "https://pwaninet.local",
        site_name: str = "Pwanimate",
        session: Optional[requests.Session] = None,
    ):
        self.api_key = api_key if api_key is not None else getattr(settings, "PWANIMATE_OPENROUTER_API_KEY", "")
        self.model_name = model_name or getattr(settings, "PWANIMATE_OPENROUTER_MODEL", "google/gemini-3.6-flash")
        self.timeout = timeout if timeout is not None else getattr(settings, "PWANIMATE_LLM_TIMEOUT", 30.0)
        self.connect_timeout = (
            connect_timeout if connect_timeout is not None else getattr(settings, "PWANIMATE_LLM_CONNECT_TIMEOUT", 5.0)
        )
        self.site_url = site_url
        self.site_name = site_name
        self.session = session or requests.Session()

    def is_available(self) -> bool:
        """Available if API key is non-empty."""
        return bool(self.api_key and self.api_key.strip())

    def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Send generation request to OpenRouter REST API.
        """
        if not self.is_available():
            raise AIProviderConfigurationError(
                "OpenRouter API key is not configured.",
                provider=self.provider_name,
            )

        model = request.model or self.model_name
        payload = self._build_payload(request, model)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": self.site_url,
            "X-Title": self.site_name,
        }

        try:
            resp = self.session.post(
                OPENROUTER_CHAT_URL,
                json=payload,
                headers=headers,
                timeout=(self.connect_timeout, self.timeout),
            )
        except requests.exceptions.Timeout as exc:
            raise AIProviderTimeoutError(
                f"OpenRouter API request timed out after {self.timeout}s: {exc}",
                provider=self.provider_name,
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise AIProviderAPIError(
                f"OpenRouter HTTP connection error: {exc}",
                provider=self.provider_name,
            ) from exc

        # Handle HTTP status codes
        if resp.status_code == 401 or resp.status_code == 403:
            raise AIProviderAuthenticationError(
                "OpenRouter API authentication failed (invalid or forbidden key).",
                provider=self.provider_name,
                status_code=resp.status_code,
            )
        elif resp.status_code == 429:
            raise AIProviderRateLimitError(
                "OpenRouter API rate limit or quota exceeded.",
                provider=self.provider_name,
                status_code=resp.status_code,
            )
        elif resp.status_code != 200:
            err_msg = self._extract_error_message(resp)
            raise AIProviderAPIError(
                f"OpenRouter API error ({resp.status_code}): {err_msg}",
                provider=self.provider_name,
                status_code=resp.status_code,
            )

        try:
            data = resp.json()
        except Exception as exc:
            raise AIProviderAPIError(
                f"Malformed JSON in OpenRouter response: {exc}",
                provider=self.provider_name,
            ) from exc

        return self._parse_response(data, request, model)

    def _build_payload(self, request: LLMRequest, model: str) -> Dict[str, Any]:
        """Construct OpenAI-compatible chat completions payload."""
        messages: List[Dict[str, str]] = []

        if request.system_instruction:
            messages.append({"role": "system", "content": request.system_instruction})

        for msg in request.messages:
            messages.append({"role": msg.role, "content": msg.content})

        # Inject context into messages if present
        if request.context and request.context.items:
            context_text = request.context.format_context_text()
            if messages and messages[-1]["role"] == "user":
                messages[-1]["content"] = f"{context_text}\n\n{messages[-1]['content']}"
            else:
                messages.append({"role": "user", "content": context_text})

        if not messages:
            messages.append({"role": "user", "content": "Hello"})

        return {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens or 1500,
        }

    def _parse_response(self, data: Dict[str, Any], request: LLMRequest, model: str) -> LLMResponse:
        """Extract content, finish reason, and usage from OpenRouter response."""
        choices = data.get("choices", [])
        if not choices:
            raise AIProviderAPIError(
                "OpenRouter response contained no completion choices.",
                provider=self.provider_name,
                details=data,
            )

        choice = choices[0]
        content = choice.get("message", {}).get("content") or ""
        finish_reason = choice.get("finish_reason")

        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
        total_tokens = usage.get("total_tokens")

        citations = list(request.context.citations) if request.context else []

        return LLMResponse(
            content=content,
            provider=self.provider_name,
            model=model,
            finish_reason=finish_reason,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            citations=citations,
            metadata={"openrouter_id": data.get("id")},
        )

    def _extract_error_message(self, resp: requests.Response) -> str:
        """Extract readable error message without leaking sensitive parameters."""
        try:
            body = resp.json()
            err = body.get("error", {})
            return err.get("message", resp.text[:200])
        except Exception:
            return resp.text[:200]
