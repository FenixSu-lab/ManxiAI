"""Views for hosted MCP profile management and JSON-RPC transport."""

import json
import logging

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.knowledge_base.models import KnowledgeBase
from apps.knowledge_base.permissions import require_owner

from .models import MCPProfile
from .serializers import MCPAccessLogSerializer, MCPProfileCreateSerializer, MCPProfileSerializer
from .services import MCPJSONRPCService, MCPProfileAuthenticator, MCPRateLimiter

logger = logging.getLogger(__name__)


class MCPProfileViewSet(viewsets.ModelViewSet):
    """Owner-only management for hosted knowledge-base MCP profiles."""

    serializer_class = MCPProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_knowledge_base(self):
        """Return the route knowledge base after owner validation."""
        knowledge_base = get_object_or_404(
            KnowledgeBase,
            id=self.kwargs['knowledge_base_id'],
            is_deleted=False,
        )
        require_owner(self.request.user, knowledge_base, 'manage_mcp_profiles')
        return knowledge_base

    def get_queryset(self):
        """Return MCP profiles for an owned knowledge base."""
        return MCPProfile.objects.filter(knowledge_base=self.get_knowledge_base()).select_related('knowledge_base')

    def get_serializer_class(self):
        """Use create serializer when returning one-time tokens."""
        if self.action in {'create', 'rotate_token'}:
            return MCPProfileCreateSerializer
        return MCPProfileSerializer

    def perform_create(self, serializer):
        """Create a profile and attach a one-time raw token to the instance."""
        knowledge_base = self.get_knowledge_base()
        raw_token = MCPProfile.generate_token()
        allowed_tools = self._filter_tools_for_scope(
            serializer.validated_data.get('permission_scope', MCPProfile.Scope.READ_ONLY),
            serializer.validated_data.get('allowed_tools') or MCPProfile.DEFAULT_TOOLS,
        )
        profile = serializer.save(
            knowledge_base=knowledge_base,
            created_by=self.request.user,
            allowed_tools=allowed_tools,
        )
        profile.set_token(raw_token)
        profile.save(update_fields=['token_hash', 'updated_at'])
        profile.token = raw_token
        logger.info('mcp_profile_created user_id=%s profile_id=%s knowledge_base_id=%s', self.request.user.id, profile.id, knowledge_base.id)

    def perform_update(self, serializer):
        """Persist profile updates after normalizing tools for the selected scope."""
        scope = serializer.validated_data.get('permission_scope', serializer.instance.permission_scope)
        tools = serializer.validated_data.get('allowed_tools', serializer.instance.allowed_tools)
        profile = serializer.save(allowed_tools=self._filter_tools_for_scope(scope, tools))
        logger.info('mcp_profile_updated user_id=%s profile_id=%s', self.request.user.id, profile.id)

    def _filter_tools_for_scope(self, scope, tools):
        """Return tools allowed by the selected profile scope."""
        allowed = MCPProfile.SCOPE_TOOL_LIMITS.get(scope, MCPProfile.SCOPE_TOOL_LIMITS[MCPProfile.Scope.READ_ONLY])
        return [tool for tool in tools if tool in allowed]

    @action(detail=True, methods=['post'])
    def rotate_token(self, request, knowledge_base_id=None, pk=None):
        """Rotate a profile bearer token and return it once."""
        profile = self.get_object()
        raw_token = MCPProfile.generate_token()
        profile.set_token(raw_token)
        profile.save(update_fields=['token_hash', 'updated_at'])
        profile.token = raw_token
        logger.info('mcp_profile_token_rotated user_id=%s profile_id=%s', request.user.id, profile.id)
        serializer = self.get_serializer(profile)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def logs(self, request, knowledge_base_id=None, pk=None):
        """Return recent access logs for one profile."""
        profile = self.get_object()
        logs = profile.access_logs.all()[:100]
        return Response(MCPAccessLogSerializer(logs, many=True).data)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def mcp_endpoint(request, profile_id):
    """Handle one Streamable HTTP MCP JSON-RPC POST request."""
    origin_error = _validate_origin(request)
    if origin_error:
        return origin_error
    try:
        profile = MCPProfileAuthenticator.authenticate(profile_id, request.headers.get('Authorization', ''))
        MCPRateLimiter.check(profile)
    except PermissionDenied as exc:
        return Response({'error': str(exc.detail if hasattr(exc, 'detail') else exc)}, status=status.HTTP_403_FORBIDDEN)

    try:
        message = request.data if isinstance(request.data, dict) else json.loads(request.body.decode('utf-8'))
    except Exception:
        return Response({'jsonrpc': '2.0', 'error': {'code': -32700, 'message': 'Invalid JSON body.'}}, status=status.HTTP_400_BAD_REQUEST)

    result = MCPJSONRPCService.handle(profile, message, _request_meta(request))
    if result.status_code == 202:
        return Response(status=status.HTTP_202_ACCEPTED)
    return Response(result.payload, status=result.status_code, content_type='application/json')


def _validate_origin(request):
    """Validate browser Origin headers when configured."""
    origin = request.headers.get('Origin')
    if not origin:
        return None
    allowed = [
        item.strip()
        for item in getattr(settings, 'MCP_ALLOWED_ORIGINS', '').split(',')
        if item.strip()
    ]
    if '*' in allowed or origin in allowed or origin in getattr(settings, 'CSRF_TRUSTED_ORIGINS', []):
        return None
    return Response({'error': 'Origin is not allowed for this MCP endpoint.'}, status=status.HTTP_403_FORBIDDEN)


def _request_meta(request) -> dict:
    """Collect request metadata for MCP access logs."""
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    ip = forwarded_for.split(',')[0].strip() if forwarded_for else request.META.get('REMOTE_ADDR')
    return {
        'ip': ip,
        'user_agent': request.headers.get('User-Agent', ''),
    }
