"""Database models for LLM provider management."""

from django.db import models

from apps.core.models import BaseModel


class LLMProvider(BaseModel):
    """Store an OpenAI-compatible LLM provider configuration."""

    class ProviderType(models.TextChoices):
        """Supported provider presets."""

        DEEPSEEK = 'deepseek', 'DeepSeek'
        QWEN = 'qwen', 'Tongyi Qianwen'
        OPENAI = 'openai', 'OpenAI'
        CUSTOM = 'custom', 'Custom OpenAI Compatible'
        DEBUG = 'debug', 'Debug'

    name = models.CharField(max_length=100)
    provider_type = models.CharField(max_length=30, choices=ProviderType.choices, default=ProviderType.CUSTOM)
    base_url = models.URLField(max_length=500, blank=True)
    api_key = models.CharField(max_length=500, blank=True)
    model = models.CharField(max_length=100)
    timeout = models.PositiveIntegerField(default=60)
    is_active = models.BooleanField(default=False)
    is_enabled = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'llm_providers'
        ordering = ['-is_active', 'name']

    def __str__(self) -> str:
        """Return a concise provider label."""
        return f'{self.name} ({self.model})'

    def masked_api_key(self) -> str:
        """Return a safe display value for the provider API key."""
        if not self.api_key:
            return ''
        if len(self.api_key) <= 8:
            return '***'
        return f'{self.api_key[:4]}...{self.api_key[-4:]}'
