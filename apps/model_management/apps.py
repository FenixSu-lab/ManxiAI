"""Django application configuration for model provider management."""
from django.apps import AppConfig


class ModelManagementConfig(AppConfig):
    """Register the model management application."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.model_management'
    verbose_name = 'Model Management'
