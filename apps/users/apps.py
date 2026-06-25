"""Django application configuration for user accounts."""
from django.apps import AppConfig


class UsersConfig(AppConfig):
    """Register the users application."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.users'
    verbose_name = 'Users'
