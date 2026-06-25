"""Unit tests for HTTP embedding provider configuration."""

from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from requests import ConnectionError

from apps.embedding.providers.http_openai_compatible import HttpOpenAICompatibleEmbeddingProvider


class HttpOpenAICompatibleEmbeddingProviderTests(SimpleTestCase):
    """Verify provider-specific endpoint and credential selection."""

    @override_settings(
        EMBEDDING_PROVIDER='openai',
        EMBEDDING_MODEL='text-embedding-3-small',
        EMBEDDING_API_URL='',
        EMBEDDING_API_KEY='',
        EMBEDDING_REQUEST_TIMEOUT=30,
        OPENAI_BASE_URL='https://api.openai.com/v1',
        OPENAI_API_KEY='openai-key',
    )
    def test_openai_provider_uses_openai_embeddings_endpoint(self):
        """OpenAI mode should derive endpoint and key from OpenAI settings."""
        provider = HttpOpenAICompatibleEmbeddingProvider()

        self.assertEqual(provider.api_url, 'https://api.openai.com/v1/embeddings')
        self.assertEqual(provider.api_key, 'openai-key')
        self.assertEqual(provider.get_provider_name(), 'openai')

    @override_settings(
        EMBEDDING_PROVIDER='http_openai_compatible',
        EMBEDDING_MODEL='bge-large-zh-v1.5',
        EMBEDDING_API_URL='http://127.0.0.1:8884/v1/embeddings',
        EMBEDDING_API_KEY='local-key',
        EMBEDDING_REQUEST_TIMEOUT=30,
        OPENAI_BASE_URL='https://api.openai.com/v1',
        OPENAI_API_KEY='openai-key',
    )
    def test_compatible_provider_uses_embedding_settings(self):
        """Compatible mode should use the explicit embedding endpoint and key."""
        provider = HttpOpenAICompatibleEmbeddingProvider()

        self.assertEqual(provider.api_url, 'http://127.0.0.1:8884/v1/embeddings')
        self.assertEqual(provider.api_key, 'local-key')
        self.assertEqual(provider.get_provider_name(), 'http_openai_compatible')

    @override_settings(
        EMBEDDING_PROVIDER='http_openai_compatible',
        EMBEDDING_MODEL='bge-large-zh-v1.5',
        EMBEDDING_API_URL='http://127.0.0.1:8884/v1/embeddings',
        EMBEDDING_API_KEY='',
        EMBEDDING_REQUEST_TIMEOUT=30,
    )
    def test_request_failure_raises_actionable_error(self):
        """Network failures should include provider, model, and endpoint context."""
        provider = HttpOpenAICompatibleEmbeddingProvider()

        with patch(
            'apps.embedding.providers.http_openai_compatible.requests.post',
            side_effect=ConnectionError('empty reply'),
        ):
            with self.assertRaisesRegex(RuntimeError, 'Embedding request failed'):
                provider.embed_text('hello')

    @override_settings(
        EMBEDDING_PROVIDER='http_openai_compatible',
        EMBEDDING_MODEL='bge-large-zh-v1.5',
        EMBEDDING_API_URL='http://127.0.0.1:8884/v1/embeddings',
        EMBEDDING_API_KEY='',
        EMBEDDING_REQUEST_TIMEOUT=30,
    )
    def test_invalid_response_shape_raises_actionable_error(self):
        """Malformed responses should fail before vector persistence."""
        provider = HttpOpenAICompatibleEmbeddingProvider()

        with self.assertRaisesRegex(RuntimeError, 'not OpenAI-compatible'):
            provider._parse_embedding_response({'items': []}, expected_count=1)
