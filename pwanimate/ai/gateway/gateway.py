"""
AI Gateway Facade for Pwanimate.

Serves as the unified, provider-agnostic entrypoint for LLM generation.
Delegates to LLMRouter, enforces validation, measures latency, and produces
normalized LLMResponse objects.
"""

from typing import Optional
import logging
import time

from pwanimate.ai.exceptions import (
    AIGatewayError,
    AIProviderAPIError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
)
from pwanimate.ai.gateway.base import BaseLLMProvider
from pwanimate.ai.gateway.router import LLMRouter
from pwanimate.ai.gateway.types import LLMRequest, LLMResponse

logger = logging.getLogger(__name__)


class AIGateway:
    """
    Unified AI Gateway facade for Pwanimate LLM operations.
    """

    def __init__(self, router: Optional[LLMRouter] = None, quota_tracker: Optional['QuotaTracker'] = None):
        self.router = router or LLMRouter()
        if quota_tracker is not None:
            self.quota_tracker = quota_tracker
        else:
            from pwanimate.ai.gateway.quota_tracker import get_quota_tracker
            self.quota_tracker = get_quota_tracker()

    def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Validate request, resolve provider chain, and execute LLM generation
        with automatic fallback on rate-limit errors.

        Args:
            request: Validated LLMRequest.

        Returns:
            Normalized LLMResponse with fallback metadata if applicable.

        Raises:
            ValueError: On invalid request structure.
            AIGatewayError: On provider configuration, authentication, timeout,
                            or API errors. Rate-limit errors are raised only
                            when all fallback providers are exhausted.
        """
        self._validate_request(request)

        fallback_chain = self.router.resolve_fallback_chain(request, quota_tracker=self.quota_tracker)
        original_candidate = fallback_chain[0]
        original_provider = original_candidate["provider"]
        original_model = original_candidate["model"]

        attempted_candidates = []
        skipped_candidates = []
        last_rate_limit_exc = None
        last_error_exc = None

        for candidate in fallback_chain:
            provider_name = candidate["provider"]
            model_name = candidate["model"]
            candidate_label = f"{provider_name}:{model_name}" if model_name else provider_name

            # Skip models/providers currently in rate-limit cooldown
            if self.quota_tracker.is_rate_limited(provider_name, model_name):
                logger.info(
                    "AI Gateway skipping rate-limited candidate: %s",
                    candidate_label,
                )
                skipped_candidates.append({
                    "provider": provider_name,
                    "model": model_name,
                    "reason": "cooldown",
                })
                continue

            attempted_candidates.append(candidate)
            provider: BaseLLMProvider = self.router.get_provider(provider_name)

            t_start = time.perf_counter()
            logger.info(
                "AI Gateway starting generation: provider=%s task=%s model=%s",
                provider.provider_name,
                request.task,
                model_name or getattr(provider, "model_name", "default"),
            )

            try:
                gen_request = LLMRequest(
                    task=request.task,
                    messages=request.messages,
                    context=request.context,
                    system_instruction=request.system_instruction,
                    provider=provider_name,
                    model=model_name,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    metadata=request.metadata,
                )

                response = provider.generate(gen_request)

                # Defensive check: if candidate generated empty content, treat as failure and trigger fallback
                if not response.content or not response.content.strip():
                    raise AIProviderAPIError(
                        f"Candidate '{candidate_label}' generated empty content (finish_reason={response.finish_reason}).",
                        provider=provider_name,
                    )
            except AIProviderRateLimitError as exc:
                duration_ms = round((time.perf_counter() - t_start) * 1000, 2)
                logger.warning(
                    "AI Gateway rate limited: candidate=%s duration_ms=%.2f, trying fallback",
                    candidate_label,
                    duration_ms,
                )
                self.quota_tracker.record_rate_limit(provider_name, model_name)
                last_rate_limit_exc = exc
                last_error_exc = exc
                skipped_candidates.append({
                    "provider": provider_name,
                    "model": model_name,
                    "reason": "rate_limit",
                })
                continue
            except (AIProviderAPIError, AIProviderTimeoutError) as exc:
                duration_ms = round((time.perf_counter() - t_start) * 1000, 2)
                logger.warning(
                    "AI Gateway candidate failed: candidate=%s error=%s duration_ms=%.2f, trying fallback",
                    candidate_label,
                    exc,
                    duration_ms,
                )
                last_error_exc = exc
                skipped_candidates.append({
                    "provider": provider_name,
                    "model": model_name,
                    "reason": f"error: {type(exc).__name__}",
                })
                continue
            except AIGatewayError as exc:
                duration_ms = round((time.perf_counter() - t_start) * 1000, 2)
                logger.warning(
                    "AI Gateway generation failed: provider=%s error=%s duration_ms=%.2f",
                    provider.provider_name,
                    type(exc).__name__,
                    duration_ms,
                )
                raise
            except Exception as exc:
                duration_ms = round((time.perf_counter() - t_start) * 1000, 2)
                logger.error(
                    "AI Gateway unexpected error: provider=%s error=%s duration_ms=%.2f",
                    provider.provider_name,
                    exc,
                    duration_ms,
                )
                raise AIGatewayError(
                    f"Unexpected error during {provider.provider_name} generation: {exc}",
                    provider=provider.provider_name,
                ) from exc

            # Success path
            duration_ms = round((time.perf_counter() - t_start) * 1000, 2)
            response.metadata["latency_ms"] = duration_ms

            is_switched = (
                provider_name != original_provider
                or (model_name and original_model and model_name.strip().lower() != original_model.strip().lower())
            )

            quota_info = {
                "active_provider": response.provider,
                "active_model": response.model,
                "primary_provider": original_provider,
                "primary_model": original_model,
                "switched": is_switched,
                "skipped": skipped_candidates,
                "cooldown_remaining": self.quota_tracker.get_cooldown_remaining(original_provider, original_model),
            }
            response.metadata["quota_info"] = quota_info
            response.metadata["fallback_used"] = is_switched

            if is_switched:
                response.metadata["original_provider"] = original_provider
                response.metadata["original_model"] = original_model
                response.metadata["attempted_candidates"] = attempted_candidates
                logger.info(
                    "AI Gateway model switch succeeded: original=%s:%s actual=%s:%s",
                    original_provider,
                    original_model,
                    response.provider,
                    response.model,
                )

            response.metadata.setdefault("max_output_tokens", request.max_tokens)

            extra_tokens = ""
            if response.metadata.get("thoughts_tokens") is not None:
                extra_tokens = (
                    f" prompt={response.prompt_tokens} completion={response.completion_tokens} "
                    f"thoughts={response.metadata['thoughts_tokens']} "
                    f"total_out={response.metadata.get('total_output_tokens')} "
                    f"max_out={response.metadata.get('max_output_tokens')}"
                )

            logger.info(
                "AI Gateway generation completed: provider=%s model=%s tokens=%s finish=%s duration_ms=%.2f%s",
                response.provider,
                response.model,
                response.total_tokens,
                response.finish_reason,
                duration_ms,
                extra_tokens,
            )

            return response

        # All candidates exhausted
        attempted_labels = [
            f"{c['provider']}:{c['model']}" if c.get("model") else c["provider"]
            for c in attempted_candidates
        ]
        if last_rate_limit_exc is not None:
            exhausted_msg = (
                f"All available AI models/providers are temporarily rate-limited or quota exhausted. "
                f"Attempted: {', '.join(attempted_labels) or 'none (all in cooldown)'}. "
                f"Please try again in about {int(self.quota_tracker.cooldown)}s."
            )
            logger.warning("AI Gateway all candidates exhausted: %s", exhausted_msg)
            raise AIProviderRateLimitError(
                exhausted_msg,
                provider="all",
                details={"attempted": attempted_labels, "skipped": skipped_candidates},
            )
        elif last_error_exc is not None:
            raise last_error_exc
        else:
            exhausted_msg = (
                f"All available AI models/providers failed or in cooldown. "
                f"Attempted: {', '.join(attempted_labels) or 'none'}. "
            )
            logger.warning("AI Gateway all candidates exhausted: %s", exhausted_msg)
            raise AIProviderRateLimitError(
                exhausted_msg,
                provider="all",
                details={"attempted": attempted_labels, "skipped": skipped_candidates},
            )

    def _validate_request(self, request: LLMRequest) -> None:
        """Validate that the request has sufficient content to execute."""
        if not isinstance(request, LLMRequest):
            raise TypeError(f"Expected LLMRequest instance, got {type(request).__name__}")

        has_messages = bool(request.messages and any(m.content.strip() for m in request.messages))
        has_context = bool(request.context and request.context.items)

        if not has_messages and not has_context:
            raise ValueError("LLMRequest must contain at least one non-empty ChatMessage or ContextPackage.")
