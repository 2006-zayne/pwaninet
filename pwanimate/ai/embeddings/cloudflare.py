"""
Cloudflare Workers AI embedding provider using direct REST API.
Default Model: @cf/baai/bge-base-en-v1.5 (768 dimensions).
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

CLOUDFLARE_API_BASE = "https://api.cloudflare.com/client/v4/accounts"


class CloudflareEmbeddingProvider(BaseEmbeddingProvider):
    """
    Cloudflare Workers AI vector embedding provider.
    Connects to the Cloudflare Workers AI REST API endpoint:
      https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}
    Defaults to @cf/baai/bge-base-en-v1.5 with 768 dimensions.
    """

    def __init__(
        self,
        api_token: Optional[str] = None,
        account_id: Optional[str] = None,
        model_name: Optional[str] = None,
        dimensions: Optional[int] = None,
        timeout: int = 30
    ):
        configured_token = (
            getattr(settings, 'PWANIMATE_CLOUDFLARE_API_TOKEN', '')
            or getattr(settings, 'CLOUDFLARE_API_TOKEN', '')
        )
        configured_account = (
            getattr(settings, 'PWANIMATE_CLOUDFLARE_ACCOUNT_ID', '')
            or getattr(settings, 'CLOUDFLARE_ACCOUNT_ID', '')
        )
        self.api_token = api_token if api_token is not None else configured_token
        self.account_id = account_id if account_id is not None else configured_account
        
        # Model defaults to @cf/baai/bge-base-en-v1.5 (768 dimensions)
        self.model_name = (
            model_name
            or getattr(settings, 'PWANIMATE_CLOUDFLARE_MODEL', '')
            or getattr(settings, 'CLOUDFLARE_EMBEDDING_MODEL', '')
            or '@cf/baai/bge-base-en-v1.5'
        )
        
        # Dimensions default to 768 for bge-base-en-v1.5
        default_dim = getattr(settings, 'PWANIMATE_EMBEDDING_DIMENSIONS', 768)
        self.dimensions = dimensions if dimensions is not None else default_dim
        self.timeout = timeout

    def is_configured(self) -> bool:
        return bool(
            self.api_token and self.api_token.strip()
            and self.account_id and self.account_id.strip()
        )

    def get_dimensions(self) -> int:
        return self.dimensions

    def get_model_name(self) -> str:
        return self.model_name

    def _build_endpoint_url(self) -> str:
        """Construct the Cloudflare Workers AI execution URL."""
        clean_account = self.account_id.strip()
        clean_model = self.model_name.strip()
        # Strip leading slash if present
        if clean_model.startswith('/'):
            clean_model = clean_model[1:]
        return f"{CLOUDFLARE_API_BASE}/{clean_account}/ai/run/{clean_model}"

    def embed_texts(self, texts: List[str], task_type: str = "RETRIEVAL_DOCUMENT") -> List[List[float]]:
        if not texts:
            return []

        if not self.is_configured():
            missing = []
            if not (self.api_token and self.api_token.strip()):
                missing.append("PWANIMATE_CLOUDFLARE_API_TOKEN (or CLOUDFLARE_API_TOKEN)")
            if not (self.account_id and self.account_id.strip()):
                missing.append("PWANIMATE_CLOUDFLARE_ACCOUNT_ID (or CLOUDFLARE_ACCOUNT_ID)")
            raise EmbeddingConfigurationError(
                f"Cloudflare Workers AI provider is not fully configured. Missing: {', '.join(missing)}.",
                provider="cloudflare"
            )

        endpoint = self._build_endpoint_url()
        cleaned_texts = [t.strip() or " " for t in texts]

        # Cloudflare Workers AI expects {"text": [...]} for batch embedding
        payload = {"text": cleaned_texts}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_token.strip()}",
        }

        logger.info(
            f"[CLOUDFLARE-EMBEDDINGS] Requesting embeddings for {len(texts)} texts "
            f"using model '{self.model_name}' (dim: {self.dimensions})"
        )

        start_time = time.monotonic()
        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
        except requests.exceptions.Timeout as e:
            err_msg = f"Cloudflare embedding request timed out after {self.timeout}s: {e}"
            logger.error(f"[CLOUDFLARE-EMBEDDINGS] {err_msg}")
            raise EmbeddingTimeoutError(err_msg, provider="cloudflare") from e
        except requests.exceptions.RequestException as e:
            err_msg = f"Cloudflare embedding network connection error: {e}"
            logger.error(f"[CLOUDFLARE-EMBEDDINGS] {err_msg}")
            raise EmbeddingProviderError(err_msg, provider="cloudflare") from e

        duration = time.monotonic() - start_time

        # Handle HTTP status codes
        if response.status_code in (401, 403):
            err_msg = f"Cloudflare authentication failed (status {response.status_code}). Verify your API token and Account ID."
            logger.error(f"[CLOUDFLARE-EMBEDDINGS] {err_msg}")
            raise EmbeddingAuthenticationError(err_msg, provider="cloudflare", status_code=response.status_code)

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "not provided")
            err_msg = f"Cloudflare quota/rate limit exhausted (429). Retry-After: {retry_after}."
            logger.warning(f"[CLOUDFLARE-EMBEDDINGS] {err_msg}")
            raise EmbeddingQuotaExhaustedError(
                err_msg,
                provider="cloudflare",
                status_code=429,
                details={"retry_after": retry_after}
            )

        if response.status_code in (400, 422):
            err_msg = f"Cloudflare invalid request error (status {response.status_code}): {response.text[:300]}"
            logger.error(f"[CLOUDFLARE-EMBEDDINGS] {err_msg}")
            raise EmbeddingInvalidRequestError(err_msg, provider="cloudflare", status_code=response.status_code)

        if response.status_code >= 500:
            err_msg = f"Cloudflare server error (status {response.status_code}): {response.text[:300]}"
            logger.error(f"[CLOUDFLARE-EMBEDDINGS] {err_msg}")
            raise EmbeddingServerResponseError(err_msg, provider="cloudflare", status_code=response.status_code)

        if response.status_code != 200:
            err_msg = f"Cloudflare API unexpected response status {response.status_code}: {response.text[:300]}"
            logger.error(f"[CLOUDFLARE-EMBEDDINGS] {err_msg}")
            raise EmbeddingProviderError(err_msg, provider="cloudflare", status_code=response.status_code)

        try:
            data = response.json()
        except ValueError as e:
            err_msg = f"Cloudflare returned malformed non-JSON payload: {e}"
            logger.error(f"[CLOUDFLARE-EMBEDDINGS] {err_msg}")
            raise EmbeddingMalformedResponseError(err_msg, provider="cloudflare") from e

        # Check Cloudflare success envelope
        if not data.get("success", False):
            errors = data.get("errors", [])
            err_details = "; ".join(f"[{e.get('code', '?')}] {e.get('message', '')}" for e in errors) or response.text[:300]
            err_msg = f"Cloudflare Workers AI returned success=false: {err_details}"
            logger.error(f"[CLOUDFLARE-EMBEDDINGS] {err_msg}")
            raise EmbeddingServerResponseError(err_msg, provider="cloudflare", details={"errors": errors})

        result = data.get("result")
        if not isinstance(result, dict):
            err_msg = f"Cloudflare response missing 'result' dictionary. Received: {list(data.keys()) if isinstance(data, dict) else type(data)}"
            logger.error(f"[CLOUDFLARE-EMBEDDINGS] {err_msg}")
            raise EmbeddingMalformedResponseError(err_msg, provider="cloudflare")

        raw_vectors = result.get("data")
        if not isinstance(raw_vectors, list):
            err_msg = f"Cloudflare result missing 'data' list. Received: {list(result.keys())}"
            logger.error(f"[CLOUDFLARE-EMBEDDINGS] {err_msg}")
            raise EmbeddingMalformedResponseError(err_msg, provider="cloudflare")

        # Cloudflare data handling:
        # If single text was passed, Cloudflare might return [[...]] or [...]
        # If multiple texts were passed, Cloudflare returns [[...], [...]]
        if len(texts) == 1 and raw_vectors and isinstance(raw_vectors[0], (int, float)):
            vectors = [raw_vectors]
        else:
            vectors = raw_vectors

        if len(vectors) != len(texts):
            err_msg = f"Cloudflare returned {len(vectors)} embeddings for {len(texts)} input texts."
            logger.error(f"[CLOUDFLARE-EMBEDDINGS] {err_msg}")
            raise EmbeddingProviderError(err_msg, provider="cloudflare")

        validated_vectors: List[List[float]] = []
        for idx, vec in enumerate(vectors):
            if not isinstance(vec, list):
                err_msg = f"Cloudflare embedding item at index {idx} is not a list of floats."
                logger.error(f"[CLOUDFLARE-EMBEDDINGS] {err_msg}")
                raise EmbeddingMalformedResponseError(err_msg, provider="cloudflare")

            if len(vec) != self.dimensions:
                err_msg = (
                    f"Cloudflare vector at index {idx} has {len(vec)} dimensions, "
                    f"expected {self.dimensions}."
                )
                logger.error(f"[CLOUDFLARE-EMBEDDINGS] {err_msg}")
                raise EmbeddingDimensionMismatchError(
                    err_msg,
                    provider="cloudflare",
                    details={"actual": len(vec), "expected": self.dimensions}
                )

            validated_vectors.append(vec)

        logger.info(
            f"[CLOUDFLARE-EMBEDDINGS] Successfully generated {len(validated_vectors)} embeddings "
            f"in {duration:.2f}s (dim: {self.dimensions})"
        )
        return validated_vectors

    def embed_query(self, text: str) -> List[float]:
        results = self.embed_texts([text], task_type="RETRIEVAL_QUERY")
        return results[0]
