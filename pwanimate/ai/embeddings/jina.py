"""
Jina AI embedding provider using direct REST API.
Default Model: jina-embeddings-v3.
"""

import logging
import time
from typing import List, Optional
import requests
from django.conf import settings

from .base import (
    BaseEmbeddingProvider,
    EmbeddingProviderError,
    EmbeddingConfigurationError,
    EmbeddingAuthenticationError,
    EmbeddingDimensionMismatchError,
    EmbeddingQuotaExhaustedError,
    EmbeddingTimeoutError,
    EmbeddingInvalidRequestError,
    EmbeddingServerResponseError,
    EmbeddingMalformedResponseError,
)

logger = logging.getLogger(__name__)

JINA_API_ENDPOINT = "https://api.jina.ai/v1/embeddings"


class JinaEmbeddingProvider(BaseEmbeddingProvider):
    """
    Jina AI vector embedding provider.
    Connects to the official Jina AI REST API endpoint (https://api.jina.ai/v1/embeddings).
    Defaults to jina-embeddings-v3 with 768 dimensions (Matryoshka Representation Learning).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        dimensions: Optional[int] = None,
        timeout: int = 30
    ):
        configured_key = getattr(settings, 'PWANIMATE_JINA_API_KEY', '') or getattr(settings, 'JINA_API_KEY', '')
        self.api_key = api_key if api_key is not None else configured_key
        self.model_name = model_name or getattr(settings, 'PWANIMATE_JINA_MODEL', 'jina-embeddings-v3')
        
        # Default to 768 to remain compatible with Pwanimate's pgvector schema when using MRL models
        default_dim = getattr(settings, 'PWANIMATE_EMBEDDING_DIMENSIONS', 768)
        self.dimensions = dimensions if dimensions is not None else default_dim
        self.timeout = timeout

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def get_dimensions(self) -> int:
        return self.dimensions

    def get_model_name(self) -> str:
        return self.model_name

    def _map_task_type(self, task_type: str) -> str:
        """Map generic Pwanimate task type to Jina task parameter."""
        normalized = (task_type or "").upper()
        if normalized == "RETRIEVAL_QUERY":
            return "retrieval.query"
        elif normalized == "RETRIEVAL_DOCUMENT":
            return "retrieval.passage"
        elif normalized in ("TEXT_MATCHING", "MATCHING"):
            return "text-matching"
        elif normalized in ("CLASSIFICATION", "CLASSIFY"):
            return "classification"
        return "retrieval.passage"

    def embed_texts(self, texts: List[str], task_type: str = "RETRIEVAL_DOCUMENT") -> List[List[float]]:
        if not texts:
            return []

        if not self.is_configured():
            raise EmbeddingConfigurationError(
                "Jina AI API key is not configured. Set PWANIMATE_JINA_API_KEY or JINA_API_KEY in environment or settings.",
                provider="jina"
            )

        jina_task = self._map_task_type(task_type)
        payload = {
            "model": self.model_name,
            "task": jina_task,
            "normalized": True,
            "input": [t.strip() or " " for t in texts]
        }

        # jina-embeddings-v3 supports explicit Matryoshka output dimensionality
        if self.dimensions:
            payload["dimensions"] = self.dimensions

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key.strip()}",
        }

        logger.info(
            f"[JINA-EMBEDDINGS] Requesting embeddings for {len(texts)} texts "
            f"using model '{self.model_name}' (task: {jina_task}, dim: {self.dimensions})"
        )

        start_time = time.monotonic()
        try:
            response = requests.post(
                JINA_API_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
        except requests.exceptions.Timeout as e:
            err_msg = f"Jina embedding request timed out after {self.timeout}s: {e}"
            logger.error(f"[JINA-EMBEDDINGS] {err_msg}")
            raise EmbeddingTimeoutError(err_msg, provider="jina") from e
        except requests.exceptions.RequestException as e:
            err_msg = f"Jina embedding network connection error: {e}"
            logger.error(f"[JINA-EMBEDDINGS] {err_msg}")
            raise EmbeddingProviderError(err_msg, provider="jina") from e

        duration = time.monotonic() - start_time

        # Handle HTTP status codes
        if response.status_code in (401, 403):
            err_msg = f"Jina authentication failed (status {response.status_code}). Verify your API key."
            logger.error(f"[JINA-EMBEDDINGS] {err_msg}")
            raise EmbeddingAuthenticationError(err_msg, provider="jina", status_code=response.status_code)

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "not provided")
            err_msg = f"Jina quota/rate limit exhausted (429). Retry-After: {retry_after}."
            logger.warning(f"[JINA-EMBEDDINGS] {err_msg}")
            raise EmbeddingQuotaExhaustedError(
                err_msg,
                provider="jina",
                status_code=429,
                details={"retry_after": retry_after}
            )

        if response.status_code in (400, 422):
            err_msg = f"Jina invalid request error (status {response.status_code}): {response.text[:300]}"
            logger.error(f"[JINA-EMBEDDINGS] {err_msg}")
            raise EmbeddingInvalidRequestError(err_msg, provider="jina", status_code=response.status_code)

        if response.status_code >= 500:
            err_msg = f"Jina server error (status {response.status_code}): {response.text[:300]}"
            logger.error(f"[JINA-EMBEDDINGS] {err_msg}")
            raise EmbeddingServerResponseError(err_msg, provider="jina", status_code=response.status_code)

        if response.status_code != 200:
            err_msg = f"Jina API unexpected response status {response.status_code}: {response.text[:300]}"
            logger.error(f"[JINA-EMBEDDINGS] {err_msg}")
            raise EmbeddingProviderError(err_msg, provider="jina", status_code=response.status_code)

        try:
            data = response.json()
        except ValueError as e:
            err_msg = f"Jina returned malformed non-JSON payload: {e}"
            logger.error(f"[JINA-EMBEDDINGS] {err_msg}")
            raise EmbeddingMalformedResponseError(err_msg, provider="jina") from e

        items = data.get("data")
        if not isinstance(items, list):
            err_msg = f"Jina response missing 'data' list. Received: {list(data.keys()) if isinstance(data, dict) else type(data)}"
            logger.error(f"[JINA-EMBEDDINGS] {err_msg}")
            raise EmbeddingMalformedResponseError(err_msg, provider="jina")

        if len(items) != len(texts):
            err_msg = f"Jina returned {len(items)} embeddings for {len(texts)} input texts."
            logger.error(f"[JINA-EMBEDDINGS] {err_msg}")
            raise EmbeddingProviderError(err_msg, provider="jina")

        # Jina returns items with 'index' and 'embedding'
        try:
            sorted_items = sorted(items, key=lambda x: x.get("index", 0))
        except Exception:
            sorted_items = items

        vectors: List[List[float]] = []
        for idx, item in enumerate(sorted_items):
            vec = item.get("embedding")
            if not isinstance(vec, list):
                err_msg = f"Jina embedding item at index {idx} does not contain an 'embedding' list."
                logger.error(f"[JINA-EMBEDDINGS] {err_msg}")
                raise EmbeddingMalformedResponseError(err_msg, provider="jina")

            if len(vec) != self.dimensions:
                err_msg = (
                    f"Jina vector at index {idx} has {len(vec)} dimensions, "
                    f"expected {self.dimensions}."
                )
                logger.error(f"[JINA-EMBEDDINGS] {err_msg}")
                raise EmbeddingDimensionMismatchError(
                    err_msg,
                    provider="jina",
                    details={"actual": len(vec), "expected": self.dimensions}
                )

            vectors.append(vec)

        logger.info(
            f"[JINA-EMBEDDINGS] Successfully generated {len(vectors)} embeddings "
            f"in {duration:.2f}s (dim: {self.dimensions})"
        )
        return vectors

    def embed_query(self, text: str) -> List[float]:
        results = self.embed_texts([text], task_type="RETRIEVAL_QUERY")
        return results[0]
