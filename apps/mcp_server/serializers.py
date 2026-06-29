"""Serializers for hosted MCP profile management."""

from django.conf import settings
from rest_framework import serializers

from .models import MCPAccessLog, MCPProfile


class MCPProfileSerializer(serializers.ModelSerializer):
    """Serialize MCP profile configuration without exposing token hashes."""

    endpoint_url = serializers.SerializerMethodField()
    knowledge_base_name = serializers.CharField(source='knowledge_base.name', read_only=True)

    class Meta:
        model = MCPProfile
        fields = [
            'id',
            'name',
            'knowledge_base',
            'knowledge_base_name',
            'permission_scope',
            'allowed_tools',
            'is_active',
            'expires_at',
            'rate_limit_per_minute',
            'max_top_k',
            'include_source_content',
            'include_metadata',
            'last_used_at',
            'usage_count',
            'endpoint_url',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'knowledge_base',
            'knowledge_base_name',
            'last_used_at',
            'usage_count',
            'endpoint_url',
            'created_at',
            'updated_at',
        ]

    def get_endpoint_url(self, obj):
        """Return an absolute MCP endpoint URL when request context exists."""
        request = self.context.get('request')
        path = f'/mcp/{obj.id}/'
        public_base_url = settings.MCP_PUBLIC_BASE_URL.rstrip('/')
        if public_base_url:
            return f'{public_base_url}{path}'
        return request.build_absolute_uri(path) if request else path

    def validate_allowed_tools(self, value):
        """Ensure only known safe tools can be exposed."""
        allowed = {
            'search_knowledge',
            'list_sources',
            'get_document',
            'get_paragraph',
            'answer_with_citations',
        }
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise serializers.ValidationError(f'Unknown MCP tools: {", ".join(unknown)}')
        return value

    def validate(self, attrs):
        """Ensure selected tools fit within the selected permission scope."""
        scope = attrs.get('permission_scope') or getattr(self.instance, 'permission_scope', MCPProfile.Scope.READ_ONLY)
        tools = attrs.get('allowed_tools')
        if tools is None:
            return attrs
        scope_tools = MCPProfile.SCOPE_TOOL_LIMITS.get(scope, MCPProfile.SCOPE_TOOL_LIMITS[MCPProfile.Scope.READ_ONLY])
        disallowed = sorted(set(tools) - scope_tools)
        if disallowed:
            raise serializers.ValidationError({'allowed_tools': f'Tools not allowed for {scope}: {", ".join(disallowed)}'})
        return attrs


class MCPProfileCreateSerializer(MCPProfileSerializer):
    """Create serializer that returns a raw bearer token once."""

    token = serializers.CharField(read_only=True)

    class Meta(MCPProfileSerializer.Meta):
        fields = MCPProfileSerializer.Meta.fields + ['token']


class MCPAccessLogSerializer(serializers.ModelSerializer):
    """Serialize recent MCP audit log rows."""

    class Meta:
        model = MCPAccessLog
        fields = [
            'id',
            'method',
            'tool_name',
            'query',
            'caller_ip',
            'user_agent',
            'status',
            'latency_ms',
            'result_count',
            'error_message',
            'created_at',
        ]
        read_only_fields = fields
