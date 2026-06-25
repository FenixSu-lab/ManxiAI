"""Django application configuration for knowledge bases."""
from django.apps import AppConfig


class KnowledgeBaseConfig(AppConfig):
    """Register the knowledge base application."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.knowledge_base'
    verbose_name = 'Knowledge Base'
