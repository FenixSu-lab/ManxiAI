"""Run a local PostgreSQL/pgvector smoke test for the RAG retrieval path."""

import logging
import uuid

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.test.utils import override_settings

from apps.document.models import Document, DocumentStatus, Paragraph
from apps.embedding.models import ParagraphEmbedding
from apps.embedding.services import EmbeddingService, VectorSearchService
from apps.knowledge_base.models import KnowledgeBase

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Create temporary data, embed it, search it, and optionally clean it up."""

    help = 'Smoke test RAG retrieval using PostgreSQL, pgvector, and hash_debug embeddings.'

    def add_arguments(self, parser):
        """Register command-line options."""
        parser.add_argument(
            '--keep',
            action='store_true',
            help='Keep the generated smoke-test user, knowledge base, document, and embeddings.',
        )

    def handle(self, *args, **options):
        """Run a self-contained retrieval smoke test."""
        keep = options['keep']
        created_user = None
        logger.info('rag_smoke_start keep=%s', keep)

        try:
            with override_settings(
                EMBEDDING_PROVIDER='hash_debug',
                EMBEDDING_MODEL='hash-debug',
                EMBEDDING_DIMENSIONS=64,
                EMBEDDING_BATCH_SIZE=8,
            ):
                created_user, knowledge_base, document = self._create_fixture()
                embedding_result = EmbeddingService.embed_document_paragraphs(document)
                results = VectorSearchService.search_paragraphs(
                    query='PostgreSQL pgvector search',
                    knowledge_base_id=str(knowledge_base.id),
                    top_k=2,
                )

            if not results:
                raise CommandError('Vector search returned no results.')

            top_result = results[0]
            if top_result['document_id'] != document.id:
                raise CommandError(f'Unexpected top result document_id={top_result["document_id"]}.')

            embedding_count = ParagraphEmbedding.objects.filter(paragraph__document=document).count()
            self.stdout.write(
                self.style.SUCCESS(
                    'RAG smoke OK. '
                    f'document_id={document.id} embeddings={embedding_count} '
                    f'embedded_count={embedding_result["embedded_count"]} top_score={top_result["score"]:.4f}'
                )
            )
            logger.info(
                'rag_smoke_success document_id=%s embedding_count=%s top_score=%s',
                document.id,
                embedding_count,
                top_result['score'],
            )
        finally:
            if created_user and not keep:
                created_user.delete()
                logger.info('rag_smoke_cleanup user_id=%s', created_user.id)

    def _create_fixture(self):
        """Create a temporary user, knowledge base, document, and paragraphs."""
        user_model = get_user_model()
        suffix = uuid.uuid4().hex[:12]
        user = user_model.objects.create_user(
            email=f'rag-smoke-{suffix}@example.com',
            username=f'rag-smoke-{suffix}',
            password='not-used',
        )
        knowledge_base = KnowledgeBase.objects.create(
            name='RAG Smoke Knowledge Base',
            description='Temporary data created by smoke_rag_stack.',
            created_by=user,
        )
        document = Document.objects.create(
            knowledge_base=knowledge_base,
            created_by=user,
            name='RAG Smoke Document',
            type='qa',
            status=DocumentStatus.PENDING,
        )
        Paragraph.objects.create(
            document=document,
            knowledge_base=knowledge_base,
            title='PostgreSQL pgvector',
            content='PostgreSQL with pgvector stores embeddings and supports vector similarity search.',
            position=0,
        )
        Paragraph.objects.create(
            document=document,
            knowledge_base=knowledge_base,
            title='Unrelated note',
            content='This paragraph is about application menus, user settings, and screen layout.',
            position=1,
        )
        document.update_stats()
        logger.info(
            'rag_smoke_fixture_created user_id=%s knowledge_base_id=%s document_id=%s',
            user.id,
            knowledge_base.id,
            document.id,
        )
        return user, knowledge_base, document
