"""Check the database, pgvector extension, and embedding provider configuration."""

import logging
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from apps.embedding.models import ParagraphEmbedding
from apps.embedding.services import EmbeddingProviderFactory

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Validate the minimum runtime dependencies for RAG retrieval."""

    help = 'Check PostgreSQL, pgvector, and embedding provider configuration.'

    PLACEHOLDER_VALUES = {
        '',
        'your-openai-api-key-here',
        'your-deepseek-api-key-here',
        'your-api-key',
        'changeme',
    }

    def add_arguments(self, parser):
        """Register optional live dependency checks."""
        parser.add_argument(
            '--live',
            action='store_true',
            help='Make a real embedding request to verify the configured endpoint and key.',
        )

    def handle(self, *args, **options):
        """Run RAG stack checks and print a compact diagnostic report."""
        logger.info('rag_stack_check_start database_engine=%s', settings.DATABASES['default']['ENGINE'])
        self._check_database_connection()
        self._check_vector_extension()
        self._check_embedding_provider(live=options['live'])
        embedding_count = ParagraphEmbedding.objects.count()
        self.stdout.write(self.style.SUCCESS(f'Paragraph embeddings table reachable. rows={embedding_count}'))
        logger.info('rag_stack_check_success paragraph_embedding_count=%s', embedding_count)

    def _check_database_connection(self) -> None:
        """Verify that Django can connect to the configured database."""
        with connection.cursor() as cursor:
            cursor.execute('SELECT current_database()')
            database_name = cursor.fetchone()[0]
        self.stdout.write(self.style.SUCCESS(f'Database connection OK. database={database_name}'))
        logger.info('rag_stack_database_ok database=%s', database_name)

    def _check_vector_extension(self) -> None:
        """Verify pgvector is installed when using PostgreSQL."""
        engine = settings.DATABASES['default']['ENGINE']
        if 'postgresql' not in engine:
            self.stdout.write(self.style.WARNING(f'Skipping pgvector check for non-PostgreSQL engine: {engine}'))
            logger.warning('rag_stack_vector_check_skipped database_engine=%s', engine)
            return

        with connection.cursor() as cursor:
            cursor.execute("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
            has_vector = cursor.fetchone()[0]

        if not has_vector:
            logger.error('rag_stack_vector_missing')
            raise CommandError('pgvector extension is not installed. Run: CREATE EXTENSION vector;')

        self.stdout.write(self.style.SUCCESS('pgvector extension OK.'))
        logger.info('rag_stack_vector_ok')

    def _check_embedding_provider(self, live: bool = False) -> None:
        """Validate configured embedding provider values and optionally call it."""
        try:
            provider = EmbeddingProviderFactory.create_provider()
        except Exception as exc:
            logger.exception('rag_stack_embedding_provider_failed error=%s', exc)
            raise CommandError(f'Embedding provider configuration failed: {exc}') from exc

        api_url = getattr(provider, 'api_url', '<not exposed>')
        api_key = getattr(provider, 'api_key', '')
        model_name = provider.get_model_name()
        provider_name = provider.get_provider_name()
        self._validate_embedding_provider_config(provider_name, model_name, api_url, api_key)

        if live:
            self._check_embedding_provider_live(provider)

        self.stdout.write(
            self.style.SUCCESS(
                f'Embedding provider OK. provider={provider_name} model={model_name} api_url={api_url}'
            )
        )
        logger.info(
            'rag_stack_embedding_provider_ok provider=%s model=%s api_url=%s',
            provider_name,
            model_name,
            api_url,
        )

    def _validate_embedding_provider_config(
        self,
        provider_name: str,
        model_name: str,
        api_url: str,
        api_key: str,
    ) -> None:
        """Fail fast on placeholder or incomplete embedding configuration."""
        if not model_name:
            raise CommandError('EMBEDDING_MODEL is empty. Set it to the model served by your embedding provider.')

        if provider_name == 'openai':
            if self._is_placeholder(api_key):
                raise CommandError(
                    'EMBEDDING_PROVIDER=openai requires a real OPENAI_API_KEY or EMBEDDING_API_KEY. '
                    'Current value is empty or a placeholder.'
                )
            return

        if provider_name == 'http_openai_compatible':
            if not api_url or api_url == '<not exposed>':
                raise CommandError('EMBEDDING_API_URL is required for http_openai_compatible embedding provider.')
            return

        if provider_name == 'hash_debug':
            self.stdout.write(self.style.WARNING('Using hash_debug embeddings. This is for diagnostics, not production RAG.'))
            return

    def _check_embedding_provider_live(self, provider) -> None:
        """Make a small embedding request to verify endpoint reachability and response shape."""
        started_at = time.perf_counter()
        try:
            vector = provider.embed_text('RAG runtime check')
        except Exception as exc:
            logger.error('rag_stack_embedding_live_failed error=%s', exc)
            raise CommandError(
                f'Live embedding request failed: {exc} '
                'Run manage.py check_embedding_endpoint for TCP/health/POST diagnostics.'
            ) from exc

        if not vector:
            raise CommandError('Live embedding request returned an empty vector.')
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        self.stdout.write(
            self.style.SUCCESS(f'Live embedding request OK. dimensions={len(vector)} latency_ms={elapsed_ms}')
        )
        logger.info('rag_stack_embedding_live_ok dimensions=%s latency_ms=%s', len(vector), elapsed_ms)

    def _is_placeholder(self, value: str) -> bool:
        """Return whether a secret-like setting is empty or a known placeholder."""
        return (value or '').strip().lower() in self.PLACEHOLDER_VALUES
