"""Tests for runtime check management commands."""

from django.core.management.base import CommandError
from django.test import SimpleTestCase

from apps.core.management.commands.check_db_latency import Command as CheckDBLatencyCommand
from apps.core.management.commands.check_embedding_endpoint import Command as CheckEmbeddingEndpointCommand
from apps.core.management.commands.check_llm_stack import Command as CheckLLMStackCommand
from apps.core.management.commands.ensure_dev_admin import Command as EnsureDevAdminCommand
from apps.model_management.ai_service import LLMProviderConfig, OpenAICompatibleLLMService


class CheckLLMStackCommandTests(SimpleTestCase):
    """Verify LLM runtime checks fail fast on unsafe configuration."""

    def test_placeholder_key_is_rejected_for_real_provider(self):
        """Real LLM providers should not accept empty or placeholder API keys."""
        command = CheckLLMStackCommand()
        service = OpenAICompatibleLLMService(
            LLMProviderConfig(
                name='deepseek',
                api_key='your-deepseek-api-key-here',
                base_url='https://api.deepseek.com/v1',
                model='deepseek-chat',
            )
        )

        with self.assertRaises(CommandError):
            command._validate_service('deepseek', service)

    def test_valid_real_provider_config_is_accepted(self):
        """A real provider with non-placeholder settings should pass non-live validation."""
        command = CheckLLMStackCommand()
        service = OpenAICompatibleLLMService(
            LLMProviderConfig(
                name='deepseek',
                api_key='sk-test-value',
                base_url='https://api.deepseek.com/v1',
                model='deepseek-chat',
            )
        )

        command._validate_service('deepseek', service)


class CheckDBLatencyCommandTests(SimpleTestCase):
    """Verify database latency threshold handling."""

    def test_threshold_exceeded_raises_by_default(self):
        """High latency should fail checks unless warn-only mode is enabled."""
        command = CheckDBLatencyCommand()

        with self.assertRaises(CommandError):
            command._enforce_threshold(
                label='PostgreSQL connection',
                actual_ms=5000,
                max_ms=3000,
                warn_only=False,
            )

    def test_threshold_exceeded_can_warn_only(self):
        """Warn-only mode should not raise when latency is above threshold."""
        command = CheckDBLatencyCommand()

        command._enforce_threshold(
            label='PostgreSQL connection',
            actual_ms=5000,
            max_ms=3000,
            warn_only=True,
        )

    def test_postgres_connect_params_include_latency_options(self):
        """Django database OPTIONS should be forwarded to psycopg2 connections."""
        command = CheckDBLatencyCommand()
        params = command._postgres_connect_params(
            {
                'NAME': 'manxiai',
                'USER': 'postgres',
                'PASSWORD': 'secret',
                'HOST': '127.0.0.1',
                'PORT': '5432',
                'OPTIONS': {
                    'connect_timeout': 10,
                    'sslmode': 'disable',
                    'gssencmode': 'disable',
                    'application_name': 'manxiai-test',
                },
            }
        )

        self.assertEqual(params['connect_timeout'], 10)
        self.assertEqual(params['sslmode'], 'disable')
        self.assertEqual(params['gssencmode'], 'disable')
        self.assertEqual(params['application_name'], 'manxiai-test')


class CheckEmbeddingEndpointCommandTests(SimpleTestCase):
    """Verify embedding endpoint diagnostics helpers."""

    def test_build_health_url_uses_endpoint_origin(self):
        """Health checks should reuse the embedding endpoint scheme, host, and port."""
        command = CheckEmbeddingEndpointCommand()

        self.assertEqual(
            command._build_health_url('http://172.16.60.26:8884/v1/embeddings', '/health'),
            'http://172.16.60.26:8884/health',
        )

    def test_invalid_embedding_response_shape_raises(self):
        """OpenAI-compatible response validation should fail on malformed payloads."""
        command = CheckEmbeddingEndpointCommand()

        with self.assertRaises(CommandError):
            command._extract_vector({'items': []}, 'http://127.0.0.1:8884/v1/embeddings')


class EnsureDevAdminCommandTests(SimpleTestCase):
    """Verify safety checks for local admin bootstrapping."""

    def test_default_password_rejected_when_debug_false(self):
        """The built-in development password should not be allowed in production mode."""
        command = EnsureDevAdminCommand()

        with self.settings(DEBUG=False):
            with self.assertRaises(CommandError):
                command._validate_inputs(
                    email='admin@example.com',
                    username='admin',
                    password=command.DEFAULT_PASSWORD,
                    allow_default_password=False,
                )
