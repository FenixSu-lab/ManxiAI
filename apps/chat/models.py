"""Chat models for persistent sessions and messages."""
from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class ChatSession(BaseModel):
    """Persist one user-owned chat session."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_sessions',
    )
    knowledge_base = models.ForeignKey(
        'knowledge_base.KnowledgeBase',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='chat_sessions',
    )
    title = models.CharField(max_length=200, blank=True, default='')

    class Meta:
        db_table = 'chat_sessions'
        ordering = ['-updated_at']

    def __str__(self):
        """Return a readable session label."""
        return self.title or f'Chat {self.pk}'


class ChatMessage(BaseModel):
    """Persist one message inside a chat session."""

    class RoleChoices(models.TextChoices):
        USER = 'user', 'User'
        ASSISTANT = 'assistant', 'Assistant'
        SYSTEM = 'system', 'System'

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    role = models.CharField(
        max_length=20,
        choices=RoleChoices.choices,
        default=RoleChoices.USER,
    )
    content = models.TextField()

    class Meta:
        db_table = 'chat_messages'
        ordering = ['created_at']

    def __str__(self):
        """Return a compact preview string."""
        return f'{self.role}: {self.content[:30]}'
