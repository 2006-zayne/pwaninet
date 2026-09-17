"""
Static LLM Router for Pwanimate.

Resolves the appropriate BaseLLMProvider instance based on explicit request
overrides or Django settings. Supports automatic fallback chain for rate-limit
recovery while maintaining strict validation of individual providers.
"""

from typing import Any, Dict, List, Optional
import logging

from django.conf import settings

from pwanimate.ai.exceptions import AIProviderConfigurationError
from pwanimate.ai.gateway.base import BaseLLMProvider
from pwanimate.ai.gateway.types import LLMRequest

logger = logging.getLogger(__name__)

SUPPORTED_PROVIDERS = {"gemini", "groq", "openrouter", "mock"}


class LLMRouter:
    """
    Static router mapping LLM requests to provider implementations.
    """

    def __init__(
        self,
        providers: Optional[Dict[str, BaseLLMProvider]] = None,
        default_provider: Optional[str] = None,
    ):
        self._explicit_providers: Optional[Dict[str, BaseLLMProvider]] = dict(providers) if providers is not None else None
        self._providers: Dict[str, BaseLLMProvider] = dict(providers) if providers else {}
        self._default_provider_name = default_provider

    @property
    def default_provider_name(self) -> str:
        if self._default_provider_name:
            return self._default_provider_name.lower()
        return getattr(settings, "PWANIMATE_DEFAULT_LLM_PROVIDER", "gemini").lower()

    def get_provider(self, name: str) -> BaseLLMProvider:
        """
        Retrieve or lazily instantiate the requested provider.
        """
        normalized_name = name.strip().lower()
        if normalized_name in self._providers:
            return self._providers[normalized_name]

        if normalized_name == "gemini":
            from pwanimate.ai.providers.gemini import GeminiLLMProvider
            provider = GeminiLLMProvider()
        elif normalized_name == "groq":
            from pwanimate.ai.providers.groq import GroqLLMProvider
            provider = GroqLLMProvider()
        elif normalized_name == "openrouter":
            from pwanimate.ai.providers.openrouter import OpenRouterLLMProvider
            provider = OpenRouterLLMProvider()
        elif normalized_name == "mock":
            from pwanimate.ai.providers.mock import MockLLMProvider
            provider = MockLLMProvider()
        else:
            raise AIProviderConfigurationError(
                f"Unknown LLM provider '{name}'. Supported providers: {sorted(SUPPORTED_PROVIDERS)}",
                provider=name,
            )

        self._providers[normalized_name] = provider
        return provider

    def resolve_provider(self, request: LLMRequest) -> BaseLLMProvider:
        """
        Resolve the provider instance for the given request.

        1. Respects explicit request.provider override if specified.
        2. Otherwise resolves configured default provider.
        3. Enforces that provider is configured/available.
        4. Strictly does NOT perform cross-provider fallback.
        """
        target_name = (request.provider or self.default_provider_name).strip().lower()

        provider = self.get_provider(target_name)

        if not provider.is_available():
            raise AIProviderConfigurationError(
                f"Requested LLM provider '{target_name}' is not configured or missing required API credentials. "
                "Automatic cross-provider fallback is prohibited.",
                provider=target_name,
            )

        return provider

    def resolve_fallback_chain(
        self,
        request: LLMRequest,
        quota_tracker: Optional[Any] = None,
    ) -> List[Dict[str, str]]:
        """
        Build an ordered list of (provider, model) candidates for fallback.

        1. Starts with the explicitly requested (or default) provider and model.
        2. Appends remaining entries from configured PWANIMATE_LLM_FALLBACK_CHAIN.
        3. Scopes to self._providers if router was instantiated with an explicit provider dict.
        4. Filters out providers that are not available (missing API keys).
        5. Deduplicates candidates preserving precedence.
        6. Dynamically sorts candidates by real-time health / availability using quota_tracker.

        Returns:
            List of dicts: [{'provider': str, 'model': str}, ...]
        """
        configured_chain = getattr(
            settings,
            "PWANIMATE_LLM_FALLBACK_CHAIN",
            None,
        )
        if configured_chain is None:
            # Backwards compatibility or default fallback chain
            provider_order = getattr(
                settings,
                "PWANIMATE_PROVIDER_FALLBACK_ORDER",
                ["gemini", "groq", "openrouter"],
            )
            configured_chain = []
            for p in provider_order:
                if p == "gemini":
                    configured_chain.append(
                        {"provider": "gemini", "model": getattr(settings, "PWANIMATE_GEMINI_MODEL", "gemini-3.6-flash")}
                    )
                elif p == "groq":
                    configured_chain.extend([
                        {"provider": "groq", "model": getattr(settings, "PWANIMATE_GROQ_MODEL", "openai/gpt-oss-120b")},
                        {"provider": "groq", "model": "openai/gpt-oss-20b"},
                    ])
                elif p == "openrouter":
                    configured_chain.append(
                        {"provider": "openrouter", "model": getattr(settings, "PWANIMATE_OPENROUTER_MODEL", "google/gemini-2.5-flash")}
                    )
                else:
                    configured_chain.append({"provider": p, "model": None})

        primary_provider = (request.provider or self.default_provider_name).strip().lower()
        primary_model = request.model
        if not primary_model and primary_provider in SUPPORTED_PROVIDERS:
            try:
                prov_instance = self.get_provider(primary_provider)
                primary_model = getattr(prov_instance, "model_name", None)
            except Exception:
                primary_model = None

        raw_candidates = [{"provider": primary_provider, "model": primary_model}]
        for item in configured_chain:
            if isinstance(item, dict):
                p_name = item.get("provider", "").strip().lower()
                m_name = item.get("model")
            else:
                p_name = str(item).strip().lower()
                m_name = None
            raw_candidates.append({"provider": p_name, "model": m_name})

        # Deduplicate while preserving order & filter by availability and scope
        available: List[Dict[str, str]] = []
        seen = set()

        for cand in raw_candidates:
            p_name = cand["provider"]
            m_name = cand["model"]
            if not p_name or p_name not in SUPPORTED_PROVIDERS:
                continue

            # If router was given an explicit providers map (e.g. in tests with mock),
            # restrict fallback strictly to providers present in that map
            if self._explicit_providers is not None and p_name not in self._explicit_providers:
                continue

            key = (p_name, (m_name or "").strip().lower())
            if key in seen:
                continue
            seen.add(key)

            try:
                prov = self.get_provider(p_name)
                if prov.is_available():
                    available.append({
                        "provider": p_name,
                        "model": m_name or getattr(prov, "model_name", None),
                    })
            except AIProviderConfigurationError:
                continue

        if not available:
            raise AIProviderConfigurationError(
                "No LLM providers are configured with valid API credentials.",
                provider="none",
            )

        # Dynamically prioritize un-throttled, healthy candidates based on live quota status
        if quota_tracker is not None and len(available) > 1:
            has_user_override = bool(request.provider or request.model)
            if has_user_override:
                # Preserve user's explicitly selected model as first attempt
                user_cand = available[0]
                remaining = available[1:]
                healthy = [c for c in remaining if not quota_tracker.is_rate_limited(c["provider"], c["model"])]
                throttled = [c for c in remaining if quota_tracker.is_rate_limited(c["provider"], c["model"])]
                available = [user_cand] + healthy + throttled
            else:
                # Auto mode: route to the best available healthy candidate without failing over
                healthy = [c for c in available if not quota_tracker.is_rate_limited(c["provider"], c["model"])]
                throttled = [c for c in available if quota_tracker.is_rate_limited(c["provider"], c["model"])]
                if healthy:
                    available = healthy + throttled

        return available
