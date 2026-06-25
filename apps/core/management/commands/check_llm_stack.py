"""Check LLM provider configuration and optionally make a live chat request."""

import logging
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.model_management.ai_service import AIServiceFactory, OpenAICompatibleLLMService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Validate the configured LLM provider used by RAG chat."""

    help = 'Check LLM provider configuration; use --live to make a real minimal chat request.'

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
            help='Send a minimal live request to the configured LLM provider.',
        )

    def handle(self, *args, **options):
        """Run LLM configuration checks and optionally verify provider reachability."""
        provider_name = settings.DEFAULT_LLM_PROVIDER.strip().lower()
        logger.info('llm_stack_check_start provider=%s model=%s', provider_name, settings.DEFAULT_LLM_MODEL)

        try:
            service = AIServiceFactory.get_service()
        except Exception as exc:
            logger.exception('llm_stack_provider_create_failed error=%s', exc)
            raise CommandError(f'LLM provider configuration failed: {exc}') from exc

        self._validate_service(provider_name, service)

        if options['live']:
            self._check_live(service)

        self.stdout.write(self.style.SUCCESS(f'LLM provider OK. provider={provider_name}'))
        logger.info('llm_stack_check_success provider=%s live=%s', provider_name, options['live'])

    def _validate_service(self, provider_name: str, service) -> None:
        """Validate required provider settings without making a network request."""
        if provider_name == 'debug':
            self.stdout.write(self.style.WARNING('Using debug LLM. This is for diagnostics, not production answers.'))
            return

        if not isinstance(service, OpenAICompatibleLLMService):
            raise CommandError(f'Unsupported LLM service type for provider={provider_name}: {type(service).__name__}')

        config = service.config
        if self._is_placeholder(config.api_key):
            raise CommandError(
                f'DEFAULT_LLM_PROVIDER={provider_name} requires a real API key. '
                'Current value is empty or a known placeholder.'
            )
        if not config.base_url:
            raise CommandError(f'DEFAULT_LLM_PROVIDER={provider_name} requires a non-empty base URL.')
        if not config.model:
            raise CommandError(f'DEFAULT_LLM_PROVIDER={provider_name} requires a non-empty model name.')

        self.stdout.write(
            self.style.SUCCESS(
                f'LLM config OK. provider={config.name} model={config.model} base_url={config.base_url}'
            )
        )

    def _check_live(self, service) -> None:
        """Send one short request and verify a non-empty assistant reply."""
        started_at = time.perf_counter()
        try:
            reply = service.generate_response(
                'Reply with exactly: ok',
                temperature=0,
                max_tokens=8,
            )
        except Exception as exc:
            logger.exception('llm_stack_live_failed error=%s', exc)
            raise CommandError(f'Live LLM request failed: {exc}') from exc

        if not reply or not reply.strip():
            raise CommandError('Live LLM request returned an empty reply.')

        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        self.stdout.write(
            self.style.SUCCESS(f'Live LLM request OK. reply_length={len(reply)} latency_ms={elapsed_ms}')
        )
        logger.info('llm_stack_live_ok reply_length=%s latency_ms=%s', len(reply), elapsed_ms)

    def _is_placeholder(self, value: str) -> bool:
        """Return whether a secret-like setting is empty or a known placeholder."""
        return (value or '').strip().lower() in self.PLACEHOLDER_VALUES
