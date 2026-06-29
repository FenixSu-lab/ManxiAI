"""URL routes for hosted MCP profiles and endpoints."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MCPProfileViewSet, mcp_endpoint

router = DefaultRouter()
router.register(
    r'knowledge-bases/(?P<knowledge_base_id>[^/.]+)/mcp-profiles',
    MCPProfileViewSet,
    basename='mcp-profile',
)

urlpatterns = [
    path('', include(router.urls)),
    path('mcp/<uuid:profile_id>/', mcp_endpoint, name='mcp-endpoint'),
]
