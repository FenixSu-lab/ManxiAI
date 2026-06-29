"""ViewSets for managing LLM provider configuration."""

import logging

from django.conf import settings
from django.db import transaction
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .ai_service import AIServiceFactory, OpenAICompatibleLLMService
from .models import LLMProvider
from .serializers import LLMProviderSerializer

logger = logging.getLogger(__name__)


class LLMProviderViewSet(viewsets.ModelViewSet):
    """Manage OpenAI-compatible LLM providers and active model selection."""

    queryset = LLMProvider.objects.all()
    serializer_class = LLMProviderSerializer
    permission_classes = [permissions.IsAdminUser]

    def perform_create(self, serializer):
        """Create a provider configuration and log its identifier."""
        provider = serializer.save()
        logger.info(
            'llm_provider_created user_id=%s provider_id=%s provider_type=%s model=%s',
            self.request.user.id,
            provider.id,
            provider.provider_type,
            provider.model,
        )

    def perform_update(self, serializer):
        """Update a provider configuration and log its identifier."""
        provider = serializer.save()
        logger.info(
            'llm_provider_updated user_id=%s provider_id=%s provider_type=%s model=%s',
            self.request.user.id,
            provider.id,
            provider.provider_type,
            provider.model,
        )

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate one provider as the default runtime LLM."""
        provider = self.get_object()
        if not provider.is_enabled:
            return Response({'detail': 'Cannot activate a disabled provider.'}, status=status.HTTP_400_BAD_REQUEST)
        readiness_error = self._get_activation_error(provider)
        if readiness_error:
            return Response({'detail': readiness_error}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            LLMProvider.objects.exclude(id=provider.id).update(is_active=False)
            provider.is_active = True
            provider.save(update_fields=['is_active', 'updated_at'])
        logger.info('llm_provider_activated user_id=%s provider_id=%s model=%s', request.user.id, provider.id, provider.model)
        return Response(self.get_serializer(provider).data)

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Return the active provider, or the environment fallback when none is active."""
        provider = LLMProvider.objects.filter(is_active=True, is_enabled=True).first()
        if provider:
            return Response({'source': 'database', 'provider': self.get_serializer(provider).data})
        return Response(
            {
                'source': 'environment',
                'fallback': {
                    'provider_type': getattr(settings, 'DEFAULT_LLM_PROVIDER', 'deepseek'),
                    'model': getattr(settings, 'DEFAULT_LLM_MODEL', ''),
                    'base_url': getattr(settings, 'DEEPSEEK_BASE_URL', ''),
                },
            }
        )

    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """Send a minimal live request through the selected provider configuration."""
        provider = self.get_object()
        try:
            service = AIServiceFactory.get_service_from_provider(provider)
            reply = service.generate_response('Reply with exactly: ok', temperature=0, max_tokens=8)
        except Exception as exc:
            logger.error('llm_provider_test_failed provider_id=%s error=%s', provider.id, exc)
            return Response({'ok': False, 'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        logger.info('llm_provider_test_ok provider_id=%s reply_length=%s', provider.id, len(reply))
        return Response({'ok': True, 'reply_length': len(reply), 'reply_preview': reply[:80]})

    @action(detail=False, methods=['post'])
    def seed_defaults(self, request):
        """Create common Chinese provider presets for quick local setup."""
        presets = [
            {
                'name': 'DeepSeek',
                'provider_type': LLMProvider.ProviderType.DEEPSEEK,
                'base_url': 'https://api.deepseek.com/v1',
                'model': 'deepseek-chat',
                'description': 'DeepSeek OpenAI-compatible chat endpoint.',
            },
            {
                'name': '通义千问 Qwen',
                'provider_type': LLMProvider.ProviderType.QWEN,
                'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
                'model': 'qwen-plus',
                'description': 'Alibaba Cloud DashScope OpenAI-compatible endpoint.',
            },
        ]
        created = 0
        for preset in presets:
            _provider, was_created = LLMProvider.objects.get_or_create(
                provider_type=preset['provider_type'],
                name=preset['name'],
                defaults=preset,
            )
            created += int(was_created)
        logger.info('llm_provider_presets_seeded user_id=%s created=%s', request.user.id, created)
        return Response({'created': created})

    def _get_activation_error(self, provider):
        """Return a user-facing validation error when a provider cannot be activated."""
        if provider.provider_type == LLMProvider.ProviderType.DEBUG:
            return ''
        if not provider.base_url:
            return 'Base URL is required before activating this provider.'
        if not provider.model:
            return 'Model name is required before activating this provider.'
        if not provider.api_key:
            return 'API key is required before activating this provider.'
        return ''
