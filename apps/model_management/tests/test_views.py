"""API tests for model provider management."""

from django.test import TestCase
from rest_framework.test import APIClient

from apps.model_management.models import LLMProvider
from apps.users.models import User


class LLMProviderViewSetTests(TestCase):
    """Verify admin model provider management workflows."""

    def setUp(self):
        """Create an admin user and authenticated API client."""
        self.admin = User.objects.create_user(
            email='model-admin@example.com',
            username='model-admin',
            password='secret123',
            is_staff=True,
            is_superuser=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_create_and_activate_provider(self):
        """Admins should be able to create and activate a model provider."""
        response = self.client.post(
            '/api/v1/model-providers/',
            {
                'name': 'Qwen',
                'provider_type': 'qwen',
                'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
                'api_key': 'qwen-key',
                'model': 'qwen-plus',
                'timeout': 60,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        provider_id = response.data['id']
        self.assertNotIn('api_key', response.data)
        self.assertEqual(response.data['masked_api_key'], '***')

        activate_response = self.client.post(f'/api/v1/model-providers/{provider_id}/activate/')

        self.assertEqual(activate_response.status_code, 200)
        self.assertTrue(LLMProvider.objects.get(id=provider_id).is_active)

    def test_activate_rejects_real_provider_without_api_key(self):
        """Real providers should not become active until credentials are complete."""
        provider = LLMProvider.objects.create(
            name='Qwen preset',
            provider_type=LLMProvider.ProviderType.QWEN,
            base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',
            model='qwen-plus',
        )

        response = self.client.post(f'/api/v1/model-providers/{provider.id}/activate/')

        self.assertEqual(response.status_code, 400)
        self.assertFalse(LLMProvider.objects.get(id=provider.id).is_active)

    def test_active_endpoint_returns_environment_fallback_without_database_provider(self):
        """The active endpoint should expose .env fallback when no provider is active."""
        response = self.client.get('/api/v1/model-providers/active/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['source'], 'environment')
