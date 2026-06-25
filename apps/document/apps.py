"""Django application configuration for document ingestion and QA records."""
from django.apps import AppConfig


class DocumentConfig(AppConfig):
    """Register the document application."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.document'
    verbose_name = 'Document'
