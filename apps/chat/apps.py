"""Django application configuration for chat sessions and messages."""
from django.apps import AppConfig


class ChatConfig(AppConfig):
    """Register the chat application."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.chat'
    verbose_name = 'Chat'
