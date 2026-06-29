"""Models for exporting knowledge bases as hosted MCP servers."""

import hashlib
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel


class MCPProfile(BaseModel):
    """One externally exposed MCP endpoint profile for a knowledge base."""

    class Scope(models.TextChoices):
        SEARCH_ONLY = 'search_only', 'Search only'
        CITATIONS_ONLY = 'citations_only', 'Search with citations'
        READ_ONLY = 'read_only', 'Read-only tools'

    DEFAULT_TOOLS = ['search_knowledge', 'list_sources', 'get_document', 'get_paragraph']
    SCOPE_TOOL_LIMITS = {
        Scope.SEARCH_ONLY: {'search_knowledge'},
        Scope.CITATIONS_ONLY: {'search_knowledge', 'list_sources', 'answer_with_citations'},
        Scope.READ_ONLY: {'search_knowledge', 'list_sources', 'get_document', 'get_paragraph', 'answer_with_citations'},
    }

    knowledge_base = models.ForeignKey(
        'knowledge_base.KnowledgeBase',
        on_delete=models.CASCADE,
        related_name='mcp_profiles',
    )
    name = models.CharField(max_length=120)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mcp_profiles')
    token_hash = models.CharField(max_length=64, unique=True)
    permission_scope = models.CharField(max_length=40, choices=Scope.choices, default=Scope.READ_ONLY)
    allowed_tools = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    rate_limit_per_minute = models.PositiveIntegerField(default=60)
    max_top_k = models.PositiveIntegerField(default=5)
    include_source_content = models.BooleanField(default=True)
    include_metadata = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    usage_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'mcp_profiles'
        ordering = ['-created_at']

    def __str__(self) -> str:
        """Return a readable profile label."""
        return f'{self.knowledge_base_id}:{self.name}'

    @staticmethod
    def hash_token(token: str) -> str:
        """Return a stable hash for a raw bearer token."""
        return hashlib.sha256(token.encode('utf-8')).hexdigest()

    @classmethod
    def generate_token(cls) -> str:
        """Generate a one-time bearer token for MCP clients."""
        return f'mcp_{secrets.token_urlsafe(32)}'

    def set_token(self, raw_token: str) -> None:
        """Store a hash of the raw bearer token."""
        self.token_hash = self.hash_token(raw_token)

    def is_expired(self) -> bool:
        """Return True when the profile has passed its expiry time."""
        return bool(self.expires_at and self.expires_at <= timezone.now())

    def allowed_tool_names(self) -> list[str]:
        """Return configured tool names or the safe default set."""
        configured = self.allowed_tools or self.DEFAULT_TOOLS
        scope_tools = self.SCOPE_TOOL_LIMITS.get(self.permission_scope, self.SCOPE_TOOL_LIMITS[self.Scope.READ_ONLY])
        return [tool for tool in configured if tool in scope_tools]


class MCPAccessLog(BaseModel):
    """Audit log for hosted MCP tool/resource calls."""

    profile = models.ForeignKey(MCPProfile, on_delete=models.CASCADE, related_name='access_logs')
    method = models.CharField(max_length=100, blank=True, default='')
    tool_name = models.CharField(max_length=100, blank=True, default='')
    query = models.TextField(blank=True, default='')
    caller_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, default='ok')
    latency_ms = models.PositiveIntegerField(default=0)
    result_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'mcp_access_logs'
        ordering = ['-created_at']

    def __str__(self) -> str:
        """Return a compact log label."""
        return f'{self.profile_id}:{self.method}:{self.status}'
