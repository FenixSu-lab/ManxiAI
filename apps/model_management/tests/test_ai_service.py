"""Unit tests for the LLM provider service layer."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from apps.model_management.ai_service import AIServiceFactory, DebugLLMService, LLMProviderConfig, OpenAICompatibleLLMService


class OpenAICompatibleLLMServiceTests(SimpleTestCase):
    """Verify request shaping and response parsing for the LLM adapter."""

    def setUp(self):
        """Create a reusable provider instance for tests."""
        self.service = OpenAICompatibleLLMService(
            LLMProviderConfig(
                name='test-provider',
                api_key='test-key',
                base_url='https://example.com/v1',
                model='test-model',
                timeout=30,
            )
        )

    def test_build_messages_includes_context_and_history(self):
        """Prompt construction should preserve context and prior turns."""
        messages = self.service._build_messages(
            prompt='current question',
            history=[
                {'role': 'user', 'content': 'earlier user'},
                {'role': 'assistant', 'content': 'earlier assistant'},
            ],
            context=['context one', 'context two'],
        )

        self.assertEqual(messages[0]['role'], 'system')
        self.assertIn('Relevant knowledge base context', messages[1]['content'])
        self.assertEqual(messages[-1], {'role': 'user', 'content': 'current question'})

    @patch('apps.model_management.ai_service.requests.post')
    def test_chat_completion_returns_message_content(self, mock_post):
        """The service should parse the provider response payload."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'choices': [
                {'message': {'content': 'generated answer'}}
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = self.service.generate_response('hello world', context=['ctx'])

        self.assertEqual(result, 'generated answer')
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['model'], 'test-model')
        self.assertEqual(kwargs['timeout'], 30)


class AIServiceFactoryTests(SimpleTestCase):
    """Verify LLM provider selection from settings."""

    @override_settings(DEFAULT_LLM_PROVIDER='debug')
    def test_debug_provider_is_available_for_smoke_tests(self):
        """Debug mode should return a deterministic local LLM service."""
        service = AIServiceFactory.get_service()

        self.assertIsInstance(service, DebugLLMService)
        self.assertIn('Context count: 1', service.chat_with_history('hello', context=['ctx']))
