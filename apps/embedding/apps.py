"""Embedding app configuration."""
from django.apps import AppConfig


class EmbeddingConfig(AppConfig):
    """Register the embedding application."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.embedding'
    verbose_name = 'Embedding'
