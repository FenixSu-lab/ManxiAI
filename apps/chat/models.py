"""Chat models for persistent sessions and messages."""
import secrets

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


class ChatShare(BaseModel):
    """Public read-only share link for a chat session."""

    session = models.OneToOneField(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='share',
    )
    token = models.CharField(max_length=80, unique=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_shares',
    )
    is_active = models.BooleanField(default=True)
    view_count = models.PositiveIntegerField(default=0)
    last_viewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'chat_shares'
        ordering = ['-created_at']

    def __str__(self):
        """Return a readable share label."""
        return f'Share {self.session_id}'

    @staticmethod
    def generate_token() -> str:
        """Generate a URL-safe public share token."""
        return secrets.token_urlsafe(32)
