"""Application services for embedding generation and vector search."""

import logging
from itertools import islice

from django.conf import settings
from django.db import transaction
from pgvector.django import CosineDistance

from apps.document.models import Document, Paragraph

from .models import ParagraphEmbedding
from .providers.base import BaseEmbeddingProvider
from .providers.hash_debug import HashDebugEmbeddingProvider
from .providers.http_openai_compatible import HttpOpenAICompatibleEmbeddingProvider

logger = logging.getLogger(__name__)


def chunked(items: list[Paragraph], batch_size: int):
    """Yield fixed-size batches from a list."""
    iterator = iter(items)
    while True:
        batch = list(islice(iterator, batch_size))
        if not batch:
            return
        yield batch


class EmbeddingProviderFactory:
    """Build the configured embedding provider."""

    @staticmethod
    def create_provider() -> BaseEmbeddingProvider:
        """Create an embedding provider from project settings."""
        provider_name = settings.EMBEDDING_PROVIDER.strip().lower()
        if provider_name in {'http_openai_compatible', 'openai'}:
            return HttpOpenAICompatibleEmbeddingProvider()
        if provider_name == 'hash_debug':
            return HashDebugEmbeddingProvider()
        raise ValueError(f'Unsupported embedding provider: {provider_name}')


class EmbeddingService:
    """Coordinate embedding generation and persistence."""

    @staticmethod
    def embed_document_paragraphs(document: Document) -> dict[str, int]:
        """Embed all active paragraphs for a document and persist vectors."""
        paragraphs = list(document.paragraphs.filter(is_active=True).order_by('position'))
        provider = EmbeddingProviderFactory.create_provider()
        batch_size = settings.EMBEDDING_BATCH_SIZE
        total_count = len(paragraphs)
        embedded_count = 0
        dimensions = 0

        logger.info(
            'embed_document_start document_id=%s knowledge_base_id=%s paragraph_count=%s provider=%s model=%s',
            document.id,
            document.knowledge_base_id,
            total_count,
            provider.get_provider_name(),
            provider.get_model_name(),
        )

        for batch in chunked(paragraphs, batch_size):
            texts = [paragraph.content for paragraph in batch]
            vectors = provider.embed_texts(texts)
            dimensions = len(vectors[0]) if vectors else dimensions

            with transaction.atomic():
                for paragraph, vector in zip(batch, vectors, strict=True):
                    ParagraphEmbedding.objects.update_or_create(
                        paragraph=paragraph,
                        defaults={
                            'provider': provider.get_provider_name(),
                            'model': provider.get_model_name(),
                            'dimensions': len(vector),
                            'vector': vector,
                            'meta': {
                                'document_id': str(document.id),
                                'knowledge_base_id': str(document.knowledge_base_id),
                            },
                        },
                    )
                    paragraph.embedding_id = str(paragraph.id)
                    paragraph.status = 'completed'
                    paragraph.save(update_fields=['embedding_id', 'status', 'updated_at'])

            embedded_count += len(batch)
            logger.info(
                'embed_document_batch_success document_id=%s batch_count=%s embedded_count=%s',
                document.id,
                len(batch),
                embedded_count,
            )

        logger.info(
            'embed_document_success document_id=%s embedded_count=%s dimensions=%s',
            document.id,
            embedded_count,
            dimensions,
        )
        return {
            'embedded_count': embedded_count,
            'dimensions': dimensions,
        }


class VectorSearchService:
    """Run pgvector-based similarity search over paragraph embeddings."""

    @staticmethod
    def search_paragraphs(query: str, knowledge_base_id: str, top_k: int = 10) -> list[dict]:
        """Embed a query and return the nearest paragraphs for a knowledge base."""
        provider = EmbeddingProviderFactory.create_provider()
        query_vector = provider.embed_text(query)

        logger.info(
            'vector_search_start knowledge_base_id=%s top_k=%s provider=%s model=%s',
            knowledge_base_id,
            top_k,
            provider.get_provider_name(),
            provider.get_model_name(),
        )

        results = (
            ParagraphEmbedding.objects.select_related('paragraph', 'paragraph__document')
            .filter(
                paragraph__knowledge_base_id=knowledge_base_id,
                paragraph__is_active=True,
            )
            .annotate(distance=CosineDistance('vector', query_vector))
            .order_by('distance')[:top_k]
        )

        payload = [
            {
                'paragraph_id': item.paragraph_id,
                'document_id': item.paragraph.document_id,
                'document_name': item.paragraph.document.name,
                'title': item.paragraph.title,
                'content': item.paragraph.content,
                'score': 1 - float(item.distance),
            }
            for item in results
        ]
        logger.info(
            'vector_search_success knowledge_base_id=%s result_count=%s',
            knowledge_base_id,
            len(payload),
        )
        return payload
