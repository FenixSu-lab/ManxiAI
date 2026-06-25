"""Django application configuration for RAG pipeline services."""
from django.apps import AppConfig


class PipelineConfig(AppConfig):
    """Register the pipeline application."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.pipeline'
    verbose_name = 'RAG Pipeline'
