"""
Deterministic Mock Embedding Provider for tests and offline development.
Generates reproducible, normalized 768-dimensional float vectors from text hashes.
"""

import hashlib
import math
from typing import List
from .base import BaseEmbeddingProvider


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """
    Deterministic mock provider producing 768-dimensional unit vectors.
    Does not require an external network connection or API keys.
    """

    def __init__(self, model_name: str = "mock-embedding-768", dimensions: int = 768):
        self.model_name = model_name
        self.dimensions = dimensions

    def is_configured(self) -> bool:
        return True

    def get_dimensions(self) -> int:
        return self.dimensions

    def get_model_name(self) -> str:
        return self.model_name

    def _generate_vector(self, text: str) -> List[float]:
        """Generate a deterministic normalized unit vector for the given text."""
        seed_bytes = hashlib.sha256(text.encode('utf-8')).digest()
        vector = []
        for i in range(self.dimensions):
            # Compute a pseudo-random float in [-1.0, 1.0] from cyclic digest bytes
            b1 = seed_bytes[i % len(seed_bytes)]
            b2 = seed_bytes[(i + 7) % len(seed_bytes)]
            val = ((b1 * 256 + b2) / 65535.0) * 2.0 - 1.0
            vector.append(round(val, 6))

        # Normalize to unit sphere (L2 norm = 1.0)
        norm = math.sqrt(sum(x * x for x in vector)) or 1.0
        return [round(x / norm, 6) for x in vector]

    def embed_texts(self, texts: List[str], task_type: str = "RETRIEVAL_DOCUMENT") -> List[List[float]]:
        return [self._generate_vector(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._generate_vector(text)
