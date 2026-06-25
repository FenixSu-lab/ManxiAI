"""HTTP embedding provider for OpenAI-compatible endpoints."""

import logging
import time

import requests
from django.conf import settings
from requests import RequestException

from .base import BaseEmbeddingProvider

logger = logging.getLogger(__name__)


class HttpOpenAICompatibleEmbeddingProvider(BaseEmbeddingProvider):
    """Call an OpenAI-compatible `/embeddings` endpoint over HTTP."""

    def __init__(self) -> None:
        """Load provider configuration from Django settings."""
        configured_provider = settings.EMBEDDING_PROVIDER.strip().lower()
        self.provider_name = configured_provider or 'http_openai_compatible'
        self.model_name = settings.EMBEDDING_MODEL
        self.timeout = settings.EMBEDDING_REQUEST_TIMEOUT

        if self.provider_name == 'openai':
            base_url = settings.OPENAI_BASE_URL.rstrip('/')
            self.api_url = settings.EMBEDDING_API_URL or f'{base_url}/embeddings'
            self.api_key = settings.EMBEDDING_API_KEY or settings.OPENAI_API_KEY
        else:
            self.api_url = settings.EMBEDDING_API_URL or 'http://127.0.0.1:8884/v1/embeddings'
            self.api_key = getattr(settings, 'EMBEDDING_API_KEY', '')

    def embed_text(self, text: str) -> list[float]:
        """Embed a single text by delegating to the batch interface."""
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts and preserve the original item order."""
        if not texts:
            return []

        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'

        payload = {
            'input': texts,
            'model': self.model_name,
        }
        started_at = time.perf_counter()
        logger.info(
            'embedding_request_start provider=%s model=%s input_count=%s',
            self.get_provider_name(),
            self.model_name,
            len(texts),
        )

        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except RequestException as exc:
            elapsed_ms = int((time.perf_counter() - started_at) * 1000)
            logger.error(
                'embedding_request_failed provider=%s model=%s api_url=%s input_count=%s latency_ms=%s error=%s',
                self.get_provider_name(),
                self.model_name,
                self.api_url,
                len(texts),
                elapsed_ms,
                exc,
            )
            raise RuntimeError(
                'Embedding request failed. '
                f'provider={self.get_provider_name()} model={self.model_name} api_url={self.api_url} '
                f'input_count={len(texts)} latency_ms={elapsed_ms}. '
                'Verify the embedding service is running and accepts OpenAI-compatible POST /embeddings JSON.'
            ) from exc

        data = response.json()
        vectors = self._parse_embedding_response(data, expected_count=len(texts))

        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        logger.info(
            'embedding_request_success provider=%s model=%s input_count=%s dimensions=%s latency_ms=%s',
            self.get_provider_name(),
            self.model_name,
            len(texts),
            len(vectors[0]) if vectors else 0,
            elapsed_ms,
        )
        return vectors

    def _parse_embedding_response(self, data: dict, expected_count: int) -> list[list[float]]:
        """Validate and extract vectors from an OpenAI-compatible embedding response."""
        try:
            items = sorted(data['data'], key=lambda item: item['index'])
            vectors = [item['embedding'] for item in items]
        except (KeyError, TypeError) as exc:
            logger.error(
                'embedding_response_invalid provider=%s model=%s api_url=%s response_keys=%s',
                self.get_provider_name(),
                self.model_name,
                self.api_url,
                sorted(data.keys()) if isinstance(data, dict) else '<non-dict>',
            )
            raise RuntimeError(
                'Embedding response is not OpenAI-compatible. Expected JSON with data[].index and data[].embedding.'
            ) from exc

        if len(vectors) != expected_count:
            raise RuntimeError(
                f'Embedding response count mismatch. expected={expected_count} actual={len(vectors)} '
                f'provider={self.get_provider_name()} model={self.model_name}'
            )
        if any(not vector for vector in vectors):
            raise RuntimeError(f'Embedding response contains empty vectors. provider={self.get_provider_name()}')
        return vectors

    def get_provider_name(self) -> str:
        """Return the stable provider identifier."""
        return self.provider_name

    def get_model_name(self) -> str:
        """Return the configured model name."""
        return self.model_name
