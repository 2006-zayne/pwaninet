"""
Google Gemini LLM Provider for Pwanimate.

Implements generative LLM calls against the Google Generative Language
generateContent REST API using direct HTTP requests.
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

GEMINI_GENERATE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiLLMProvider(BaseLLMProvider):
    """
    Direct REST provider for Google Gemini models (e.g., gemini-3.6-flash).
    """

    provider_name: str = "gemini"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: Optional[float] = None,
        connect_timeout: Optional[float] = None,
        session: Optional[requests.Session] = None,
    ):
        self.api_key = api_key if api_key is not None else getattr(settings, "PWANIMATE_GEMINI_API_KEY", "")
        self.model_name = model_name or getattr(settings, "PWANIMATE_GEMINI_MODEL", "gemini-3.6-flash")
        self.timeout = timeout if timeout is not None else getattr(settings, "PWANIMATE_LLM_TIMEOUT", 30.0)
        self.connect_timeout = (
            connect_timeout if connect_timeout is not None else getattr(settings, "PWANIMATE_LLM_CONNECT_TIMEOUT", 5.0)
        )
        self.session = session or requests.Session()

    def is_available(self) -> bool:
        """Available if API key is non-empty."""
        return bool(self.api_key and self.api_key.strip())

    def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Send generation request to Gemini REST API.
        """
        if not self.is_available():
            raise AIProviderConfigurationError(
                "Gemini API key is not configured.",
                provider=self.provider_name,
            )

        model = request.model or self.model_name
        url = GEMINI_GENERATE_URL.format(model=model)

        # Build payload
        payload = self._build_payload(request)
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }

        try:
            resp = self.session.post(
                url,
                json=payload,
                headers=headers,
                timeout=(self.connect_timeout, self.timeout),
            )
        except requests.exceptions.Timeout as exc:
            raise AIProviderTimeoutError(
                f"Gemini API request timed out after {self.timeout}s: {exc}",
                provider=self.provider_name,
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise AIProviderAPIError(
                f"Gemini HTTP connection error: {exc}",
                provider=self.provider_name,
            ) from exc

        # Handle HTTP status codes
        if resp.status_code == 401 or resp.status_code == 403:
            raise AIProviderAuthenticationError(
                "Gemini API authentication failed (invalid or forbidden key).",
                provider=self.provider_name,
                status_code=resp.status_code,
            )
        elif resp.status_code == 429:
            err_msg = self._extract_error_message(resp)
            raise AIProviderRateLimitError(
                f"Gemini API rate limit or quota exceeded: {err_msg}",
                provider=self.provider_name,
                status_code=resp.status_code,
            )
        elif resp.status_code != 200:
            err_msg = self._extract_error_message(resp)
            raise AIProviderAPIError(
                f"Gemini API error ({resp.status_code}): {err_msg}",
                provider=self.provider_name,
                status_code=resp.status_code,
            )

        try:
            data = resp.json()
        except Exception as exc:
            raise AIProviderAPIError(
                f"Malformed JSON in Gemini response: {exc}",
                provider=self.provider_name,
            ) from exc

        return self._parse_response(data, request, model)

    def _build_payload(self, request: LLMRequest) -> Dict[str, Any]:
        """Construct Gemini generateContent JSON payload."""
        system_instruction_text = request.system_instruction or ""
        contents: List[Dict[str, Any]] = []

        # Process messages
        for msg in request.messages:
            if msg.role == "system":
                # System message in turn list gets appended to system instructions
                if system_instruction_text:
                    system_instruction_text += "\n" + msg.content
                else:
                    system_instruction_text = msg.content
            elif msg.role == "assistant":
                contents.append({
                    "role": "model",
                    "parts": [{"text": msg.content}],
                })
            else:  # user
                contents.append({
                    "role": "user",
                    "parts": [{"text": msg.content}],
                })

        # Inject context into contents if present
        if request.context and (request.context.items or getattr(request.context, "user_context", None)):
            context_text = request.context.format_context_text()
            if context_text:
                # If there's a last user message, prepend context parts
                if contents and contents[-1]["role"] == "user":
                    contents[-1]["parts"].insert(0, {"text": context_text})
                else:
                    # Add context as a user part
                    contents.append({
                        "role": "user",
                        "parts": [{"text": context_text}],
                    })

        # Fallback if no messages were provided
        if not contents:
            contents.append({
                "role": "user",
                "parts": [{"text": "Hello"}],
            })

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
            },
        }

        if system_instruction_text:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction_text}]
            }

        return payload

    def _parse_response(self, data: Dict[str, Any], request: LLMRequest, model: str) -> LLMResponse:
        """Extract text, finish reason, and usage from response JSON."""
        candidates = data.get("candidates", [])
        if not candidates:
            raise AIProviderAPIError(
                "Gemini response contained no candidate outputs.",
                provider=self.provider_name,
                details=data,
            )

        candidate = candidates[0]
        content_parts = candidate.get("content", {}).get("parts", [])
        text = "".join(part.get("text", "") for part in content_parts)
        finish_reason = candidate.get("finishReason", "stop").lower()

        usage = data.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount")
        completion_tokens = usage.get("candidatesTokenCount")
        total_tokens = usage.get("totalTokenCount")

        citations = list(request.context.citations) if request.context else []

        return LLMResponse(
            content=text,
            provider=self.provider_name,
            model=model,
            finish_reason=finish_reason,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            citations=citations,
            metadata={"gemini_finish_reason": candidate.get("finishReason")},
        )

    def _extract_error_message(self, resp: requests.Response) -> str:
        """Extract readable error message without leaking sensitive parameters."""
        try:
            body = resp.json()
            err = body.get("error", {})
            return err.get("message", resp.text[:200])
        except Exception:
            return resp.text[:200]
