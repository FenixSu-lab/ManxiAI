"""Unit tests for the deterministic debug embedding provider."""

from django.test import SimpleTestCase, override_settings

from apps.embedding.providers.hash_debug import HashDebugEmbeddingProvider
from apps.embedding.services import EmbeddingProviderFactory


class HashDebugEmbeddingProviderTests(SimpleTestCase):
    """Verify local debug embeddings are stable and factory-selectable."""

    @override_settings(EMBEDDING_MODEL='hash-debug', EMBEDDING_DIMENSIONS=16)
    def test_hash_debug_embeddings_are_deterministic(self):
        """The same text should always produce the same normalized vector."""
        provider = HashDebugEmbeddingProvider()

        first = provider.embed_text('PostgreSQL pgvector knowledge base')
        second = provider.embed_text('PostgreSQL pgvector knowledge base')

        self.assertEqual(first, second)
        self.assertEqual(len(first), 16)

    @override_settings(EMBEDDING_PROVIDER='hash_debug', EMBEDDING_MODEL='hash-debug', EMBEDDING_DIMENSIONS=16)
    def test_factory_creates_hash_debug_provider(self):
        """The provider factory should support the local diagnostic provider."""
        provider = EmbeddingProviderFactory.create_provider()

        self.assertIsInstance(provider, HashDebugEmbeddingProvider)
        self.assertEqual(provider.get_provider_name(), 'hash_debug')
