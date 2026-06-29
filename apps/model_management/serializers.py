"""Serializers for model provider management APIs."""

from rest_framework import serializers

from .models import LLMProvider


class LLMProviderSerializer(serializers.ModelSerializer):
    """Serialize LLM provider configuration with masked secrets."""

    masked_api_key = serializers.CharField(read_only=True)
    api_key = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = LLMProvider
        fields = [
            'id',
            'name',
            'provider_type',
            'base_url',
            'api_key',
            'masked_api_key',
            'model',
            'timeout',
            'is_active',
            'is_enabled',
            'description',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'is_active', 'created_at', 'updated_at']

    def validate(self, attrs):
        """Validate required fields for enabled real providers."""
        provider_type = attrs.get('provider_type') or getattr(self.instance, 'provider_type', '')
        if provider_type == LLMProvider.ProviderType.DEBUG:
            return attrs

        base_url = attrs.get('base_url') if 'base_url' in attrs else getattr(self.instance, 'base_url', '')
        model = attrs.get('model') if 'model' in attrs else getattr(self.instance, 'model', '')
        api_key = attrs.get('api_key') if 'api_key' in attrs else getattr(self.instance, 'api_key', '')
        if not base_url:
            raise serializers.ValidationError({'base_url': 'Base URL is required for real providers.'})
        if not model:
            raise serializers.ValidationError({'model': 'Model name is required.'})
        if not api_key:
            raise serializers.ValidationError({'api_key': 'API key is required for real providers.'})
        return attrs

    def update(self, instance, validated_data):
        """Keep the existing API key when an update omits the write-only field."""
        if 'api_key' not in validated_data:
            validated_data.pop('api_key', None)
        return super().update(instance, validated_data)


class ActiveLLMProviderSerializer(serializers.Serializer):
    """Serialize the active LLM provider summary."""

    source = serializers.CharField()
    provider = LLMProviderSerializer(required=False)
    fallback = serializers.DictField(required=False)
