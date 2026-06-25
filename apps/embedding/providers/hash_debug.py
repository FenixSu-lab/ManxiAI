"""Deterministic debug embedding provider for local smoke tests."""

import hashlib
import logging
import math
import re

from django.conf import settings

from .base import BaseEmbeddingProvider

logger = logging.getLogger(__name__)


class HashDebugEmbeddingProvider(BaseEmbeddingProvider):
    """Generate deterministic vectors without network calls for diagnostics."""

    def __init__(self) -> None:
        """Load debug embedding dimensions from Django settings."""
        self.model_name = settings.EMBEDDING_MODEL or 'hash-debug'
        self.dimensions = settings.EMBEDDING_DIMENSIONS

    def embed_text(self, text: str) -> list[float]:
        """Embed a single text by delegating to the batch interface."""
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts using stable hashed token buckets."""
        vectors = [self._embed_text(text) for text in texts]
        logger.info(
            'hash_debug_embedding_generated input_count=%s dimensions=%s',
            len(texts),
            self.dimensions,
        )
        return vectors

    def get_provider_name(self) -> str:
        """Return the stable provider identifier."""
        return 'hash_debug'

    def get_model_name(self) -> str:
        """Return the configured model name."""
        return self.model_name

    def _embed_text(self, text: str) -> list[float]:
        """Convert text into a normalized sparse hash vector."""
        vector = [0.0] * self.dimensions
        tokens = self._tokenize(text)
        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.sha256(token.encode('utf-8')).digest()
            index = int.from_bytes(digest[:4], 'big') % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if not norm:
            return vector
        return [value / norm for value in vector]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Split English and CJK text into stable tokens."""
        normalized = text.lower()
        word_tokens = re.findall(r'[a-z0-9_]+', normalized)
        cjk_tokens = re.findall(r'[\u4e00-\u9fff]', normalized)
        return word_tokens + cjk_tokens
