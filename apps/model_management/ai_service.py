"""LLM provider services for text generation and chat completion."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LLMProviderConfig:
    """Store the connection details for an LLM provider."""

    name: str
    api_key: str
    base_url: str
    model: str
    timeout: int = 60


class BaseLLMService(ABC):
    """Define the interface used by chat and RAG flows."""

    @abstractmethod
    def generate_response(
        self,
        prompt: str,
        context: list[str] | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        """Generate a completion for a prompt."""

    @abstractmethod
    def chat_with_history(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
        context: list[str] | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        """Generate a reply for a chat turn with optional context."""


class OpenAICompatibleLLMService(BaseLLMService):
    """Call an OpenAI-compatible chat completion endpoint over HTTP."""

    def __init__(self, config: LLMProviderConfig) -> None:
        """Store provider configuration for later requests."""
        self.config = config

    def generate_response(
        self,
        prompt: str,
        context: list[str] | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        """Generate a response for a standalone prompt."""
        messages = self._build_messages(prompt=prompt, history=None, context=context)
        return self._chat_completion(
            messages=messages,
            model=model or self.config.model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def chat_with_history(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
        context: list[str] | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        """Generate a reply for a chat turn with retrieval context."""
        messages = self._build_messages(prompt=message, history=history or [], context=context)
        return self._chat_completion(
            messages=messages,
            model=model or self.config.model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def _build_messages(
        self,
        prompt: str,
        history: list[dict[str, str]] | None,
        context: list[str] | None,
    ) -> list[dict[str, str]]:
        """Build a provider-compatible chat message list."""
        messages = [
            {
                'role': 'system',
                'content': 'You are a helpful AI assistant. Answer clearly and use the supplied context when it is relevant.',
            }
        ]
        if context:
            messages.append(
                {
                    'role': 'system',
                    'content': 'Relevant knowledge base context:\n' + '\n\n'.join(context),
                }
            )
        for item in history or []:
            role = item.get('role')
            content = item.get('content', '')
            if role in {'user', 'assistant', 'system'} and content:
                messages.append({'role': role, 'content': content})
        messages.append({'role': 'user', 'content': prompt})
        return messages

    def _chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Send a chat completion request and return the generated text."""
        headers = {
            'Authorization': f'Bearer {self.config.api_key}',
            'Content-Type': 'application/json',
        }
        payload: dict[str, Any] = {
            'model': model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens,
        }
        endpoint = self.config.base_url.rstrip('/') + '/chat/completions'
        logger.info(
            'llm_request_start provider=%s model=%s message_count=%s max_tokens=%s',
            self.config.name,
            model,
            len(messages),
            max_tokens,
        )
        response = requests.post(endpoint, json=payload, headers=headers, timeout=self.config.timeout)
        response.raise_for_status()
        data = response.json()
        content = data['choices'][0]['message']['content']
        logger.info(
            'llm_request_success provider=%s model=%s reply_length=%s',
            self.config.name,
            model,
            len(content),
        )
        return content


class DebugLLMService(BaseLLMService):
    """Return deterministic local replies for smoke tests and diagnostics."""

    def generate_response(
        self,
        prompt: str,
        context: list[str] | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        """Generate a deterministic response for a standalone prompt."""
        return self.chat_with_history(prompt, history=[], context=context, model=model, temperature=temperature, max_tokens=max_tokens)

    def chat_with_history(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
        context: list[str] | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        """Generate a deterministic chat reply without network calls."""
        context = context or []
        history = history or []
        reply = (
            f'Debug reply for: {message}\n'
            f'Context count: {len(context)}\n'
            f'History count: {len(history)}'
        )
        if context:
            reply += f'\nTop context: {context[0][:200]}'
        logger.info(
            'debug_llm_reply_generated message_length=%s history_count=%s context_count=%s',
            len(message),
            len(history),
            len(context),
        )
        return reply


class AIServiceFactory:
    """Create an LLM service from configured provider settings."""

    @staticmethod
    def get_service(provider: str | None = None) -> BaseLLMService:
        """Return the configured LLM service instance."""
        if provider is None:
            database_service = AIServiceFactory._get_active_database_service()
            if database_service:
                return database_service

        provider_name = (provider or getattr(settings, 'DEFAULT_LLM_PROVIDER', 'deepseek')).strip().lower()
        if provider_name == 'debug':
            return DebugLLMService()
        if provider_name == 'deepseek':
            return OpenAICompatibleLLMService(
                LLMProviderConfig(
                    name='deepseek',
                    api_key=settings.DEEPSEEK_API_KEY,
                    base_url=settings.DEEPSEEK_BASE_URL.rstrip('/') + '/v1' if not settings.DEEPSEEK_BASE_URL.rstrip('/').endswith('/v1') else settings.DEEPSEEK_BASE_URL,
                    model=settings.DEFAULT_LLM_MODEL,
                )
            )
        if provider_name == 'openai':
            return OpenAICompatibleLLMService(
                LLMProviderConfig(
                    name='openai',
                    api_key=settings.OPENAI_API_KEY,
                    base_url=settings.OPENAI_BASE_URL,
                    model=getattr(settings, 'OPENAI_DEFAULT_MODEL', 'gpt-4o-mini'),
                )
            )
        raise ValueError(f'Unsupported LLM provider: {provider_name}')

    @staticmethod
    def get_service_from_provider(provider_obj) -> BaseLLMService:
        """Build a service from an LLMProvider model instance."""
        provider_type = provider_obj.provider_type.strip().lower()
        if provider_type == 'debug':
            return DebugLLMService()
        return OpenAICompatibleLLMService(
            LLMProviderConfig(
                name=provider_type,
                api_key=provider_obj.api_key,
                base_url=AIServiceFactory._normalize_base_url(provider_obj.base_url),
                model=provider_obj.model,
                timeout=provider_obj.timeout,
            )
        )

    @staticmethod
    def _get_active_database_service() -> BaseLLMService | None:
        """Return the active DB-backed provider service when model management is configured."""
        try:
            from .models import LLMProvider

            provider_obj = LLMProvider.objects.filter(is_active=True, is_enabled=True).first()
        except Exception as exc:
            logger.warning('llm_database_provider_lookup_failed error=%s', exc)
            return None
        if not provider_obj:
            return None
        logger.info('llm_database_provider_selected provider_id=%s model=%s', provider_obj.id, provider_obj.model)
        return AIServiceFactory.get_service_from_provider(provider_obj)

    @staticmethod
    def _normalize_base_url(base_url: str) -> str:
        """Ensure an OpenAI-compatible base URL points at a `/v1` root."""
        stripped = base_url.rstrip('/')
        if stripped.endswith('/v1'):
            return stripped
        return f'{stripped}/v1'

