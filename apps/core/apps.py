"""Django application configuration for shared core utilities."""
from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Register the core application."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = 'Core'
