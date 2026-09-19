"""
Voyage AI embedding provider using direct REST API.
Default Model: voyage-3.
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

VOYAGE_API_ENDPOINT = "https://api.voyageai.com/v1/embeddings"


class VoyageEmbeddingProvider(BaseEmbeddingProvider):
    """
    Voyage AI vector embedding provider.
    Connects to the official Voyage AI REST API (https://api.voyageai.com/v1/embeddings).
    Defaults to voyage-3 with 1024 dimensions (or configurable).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        dimensions: Optional[int] = None,
        timeout: int = 30
    ):
        configured_key = getattr(settings, 'PWANIMATE_VOYAGE_API_KEY', '') or getattr(settings, 'VOYAGE_API_KEY', '')
        self.api_key = api_key if api_key is not None else configured_key
        self.model_name = model_name or getattr(settings, 'PWANIMATE_VOYAGE_MODEL', 'voyage-3')
        
        # voyage-3 defaults to 1024 dimensions. Supports 256, 512, 1024, 2048.
        # Note: Voyage does not natively produce 768 dimensions.
        self.dimensions = dimensions if dimensions is not None else 1024
        self.timeout = timeout

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def get_dimensions(self) -> int:
        return self.dimensions

    def get_model_name(self) -> str:
        return self.model_name

    def _map_input_type(self, task_type: str) -> Optional[str]:
        """Map generic Pwanimate task type to Voyage input_type parameter."""
        normalized = (task_type or "").upper()
        if normalized == "RETRIEVAL_QUERY":
            return "query"
        elif normalized == "RETRIEVAL_DOCUMENT":
            return "document"
        return None

    def embed_texts(self, texts: List[str], task_type: str = "RETRIEVAL_DOCUMENT") -> List[List[float]]:
        if not texts:
            return []

        if not self.is_configured():
            raise EmbeddingConfigurationError(
                "Voyage AI API key is not configured. Set PWANIMATE_VOYAGE_API_KEY or VOYAGE_API_KEY in environment or settings.",
                provider="voyage"
            )

        input_type = self._map_input_type(task_type)
        payload = {
            "model": self.model_name,
            "input": [t.strip() or " " for t in texts],
        }
        if input_type:
            payload["input_type"] = input_type

        # Many modern Voyage models support output_dimension (e.g. 256, 512, 1024, 2048)
        if self.dimensions:
            payload["output_dimension"] = self.dimensions

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key.strip()}",
        }

        logger.info(
            f"[VOYAGE-EMBEDDINGS] Requesting embeddings for {len(texts)} texts "
            f"using model '{self.model_name}' (input_type: {input_type}, dim: {self.dimensions})"
        )

        start_time = time.monotonic()
        try:
            response = requests.post(
                VOYAGE_API_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
        except requests.exceptions.Timeout as e:
            err_msg = f"Voyage embedding request timed out after {self.timeout}s: {e}"
            logger.error(f"[VOYAGE-EMBEDDINGS] {err_msg}")
            raise EmbeddingTimeoutError(err_msg, provider="voyage") from e
        except requests.exceptions.RequestException as e:
            err_msg = f"Voyage embedding network connection error: {e}"
            logger.error(f"[VOYAGE-EMBEDDINGS] {err_msg}")
            raise EmbeddingProviderError(err_msg, provider="voyage") from e

        duration = time.monotonic() - start_time

        # Handle HTTP status codes
        if response.status_code in (401, 403):
            err_msg = f"Voyage authentication failed (status {response.status_code}). Verify your API key."
            logger.error(f"[VOYAGE-EMBEDDINGS] {err_msg}")
            raise EmbeddingAuthenticationError(err_msg, provider="voyage", status_code=response.status_code)

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "not provided")
            err_msg = f"Voyage quota/rate limit exhausted (429). Retry-After: {retry_after}."
            logger.warning(f"[VOYAGE-EMBEDDINGS] {err_msg}")
            raise EmbeddingQuotaExhaustedError(
                err_msg,
                provider="voyage",
                status_code=429,
                details={"retry_after": retry_after}
            )

        if response.status_code in (400, 422):
            err_msg = f"Voyage invalid request error (status {response.status_code}): {response.text[:300]}"
            logger.error(f"[VOYAGE-EMBEDDINGS] {err_msg}")
            raise EmbeddingInvalidRequestError(err_msg, provider="voyage", status_code=response.status_code)

        if response.status_code >= 500:
            err_msg = f"Voyage server error (status {response.status_code}): {response.text[:300]}"
            logger.error(f"[VOYAGE-EMBEDDINGS] {err_msg}")
            raise EmbeddingServerResponseError(err_msg, provider="voyage", status_code=response.status_code)

        if response.status_code != 200:
            err_msg = f"Voyage API unexpected response status {response.status_code}: {response.text[:300]}"
            logger.error(f"[VOYAGE-EMBEDDINGS] {err_msg}")
            raise EmbeddingProviderError(err_msg, provider="voyage", status_code=response.status_code)

        try:
            data = response.json()
        except ValueError as e:
            err_msg = f"Voyage returned malformed non-JSON payload: {e}"
            logger.error(f"[VOYAGE-EMBEDDINGS] {err_msg}")
            raise EmbeddingMalformedResponseError(err_msg, provider="voyage") from e

        items = data.get("data")
        if not isinstance(items, list):
            err_msg = f"Voyage response missing 'data' list. Received: {list(data.keys()) if isinstance(data, dict) else type(data)}"
            logger.error(f"[VOYAGE-EMBEDDINGS] {err_msg}")
            raise EmbeddingMalformedResponseError(err_msg, provider="voyage")

        if len(items) != len(texts):
            err_msg = f"Voyage returned {len(items)} embeddings for {len(texts)} input texts."
            logger.error(f"[VOYAGE-EMBEDDINGS] {err_msg}")
            raise EmbeddingProviderError(err_msg, provider="voyage")

        # Voyage returns items with 'index' and 'embedding'
        try:
            sorted_items = sorted(items, key=lambda x: x.get("index", 0))
        except Exception:
            sorted_items = items

        vectors: List[List[float]] = []
        for idx, item in enumerate(sorted_items):
            vec = item.get("embedding")
            if not isinstance(vec, list):
                err_msg = f"Voyage embedding item at index {idx} does not contain an 'embedding' list."
                logger.error(f"[VOYAGE-EMBEDDINGS] {err_msg}")
                raise EmbeddingMalformedResponseError(err_msg, provider="voyage")

            if len(vec) != self.dimensions:
                err_msg = (
                    f"Voyage vector at index {idx} has {len(vec)} dimensions, "
                    f"expected {self.dimensions}."
                )
                logger.error(f"[VOYAGE-EMBEDDINGS] {err_msg}")
                raise EmbeddingDimensionMismatchError(
                    err_msg,
                    provider="voyage",
                    details={"actual": len(vec), "expected": self.dimensions}
                )

            vectors.append(vec)

        logger.info(
            f"[VOYAGE-EMBEDDINGS] Successfully generated {len(vectors)} embeddings "
            f"in {duration:.2f}s (dim: {self.dimensions})"
        )
        return vectors

    def embed_query(self, text: str) -> List[float]:
        results = self.embed_texts([text], task_type="RETRIEVAL_QUERY")
        return results[0]
