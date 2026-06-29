"""Django app configuration for hosted MCP server profiles."""

from django.apps import AppConfig


class McpServerConfig(AppConfig):
    """Register the hosted MCP server app."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.mcp_server'
    verbose_name = 'MCP Server'
