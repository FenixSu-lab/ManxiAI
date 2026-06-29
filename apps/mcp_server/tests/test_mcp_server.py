"""Tests for hosted MCP profile management and JSON-RPC endpoint."""

from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from apps.document.models import Document, DocumentStatus, Paragraph
from apps.knowledge_base.models import KnowledgeBase
from apps.mcp_server.models import MCPAccessLog, MCPProfile
from apps.users.models import User


class MCPProfileAPITests(TestCase):
    """Verify owner profile management and hosted MCP calls."""

    def setUp(self):
        """Create a knowledge base owner and sample source."""
        self.owner = User.objects.create_user(email='mcp-owner@example.com', username='mcp-owner', password='secret123')
        self.other = User.objects.create_user(email='mcp-other@example.com', username='mcp-other', password='secret123')
        self.knowledge_base = KnowledgeBase.objects.create(name='MCP KB', created_by=self.owner)
        self.document = Document.objects.create(
            knowledge_base=self.knowledge_base,
            created_by=self.owner,
            name='MCP Source',
            status=DocumentStatus.COMPLETED,
        )
        self.paragraph = Paragraph.objects.create(
            document=self.document,
            knowledge_base=self.knowledge_base,
            title='MCP paragraph',
            content='MCP hosted server content.',
            position=0,
            status=DocumentStatus.COMPLETED,
        )
        self.client = APIClient(HTTP_HOST='localhost')

    def test_owner_can_create_profile_and_receives_one_time_token(self):
        """Owner profile creation should return endpoint URL and raw token once."""
        self.client.force_authenticate(self.owner)

        response = self.client.post(
            f'/api/v1/knowledge-bases/{self.knowledge_base.id}/mcp-profiles/',
            {'name': 'External Agent'},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertIn('token', response.data)
        self.assertTrue(response.data['token'].startswith('mcp_'))
        self.assertIn(f'/mcp/{response.data["id"]}/', response.data['endpoint_url'])
        self.assertEqual(MCPProfile.objects.count(), 1)

    def test_non_owner_cannot_create_profile(self):
        """Only the knowledge-base owner can export MCP profiles."""
        self.client.force_authenticate(self.other)

        response = self.client.post(
            f'/api/v1/knowledge-bases/{self.knowledge_base.id}/mcp-profiles/',
            {'name': 'Denied'},
            format='json',
        )

        self.assertEqual(response.status_code, 403)

    def test_create_profile_filters_tools_by_scope(self):
        """Profile management should persist only tools allowed by the selected scope."""
        self.client.force_authenticate(self.owner)

        response = self.client.post(
            f'/api/v1/knowledge-bases/{self.knowledge_base.id}/mcp-profiles/',
            {
                'name': 'Search Only',
                'permission_scope': 'search_only',
                'allowed_tools': ['search_knowledge'],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        profile = MCPProfile.objects.get(id=response.data['id'])
        self.assertEqual(profile.allowed_tools, ['search_knowledge'])

    def _create_profile_with_token(self):
        """Create a profile and return it with its raw token."""
        raw_token = MCPProfile.generate_token()
        profile = MCPProfile.objects.create(
            knowledge_base=self.knowledge_base,
            created_by=self.owner,
            name='MCP Runtime',
            token_hash=MCPProfile.hash_token(raw_token),
            allowed_tools=MCPProfile.DEFAULT_TOOLS,
        )
        return profile, raw_token

    def test_mcp_initialize_and_tools_list(self):
        """MCP endpoint should support initialize and tools/list JSON-RPC calls."""
        profile, token = self._create_profile_with_token()

        initialize = self.client.post(
            f'/mcp/{profile.id}/',
            {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
            HTTP_ACCEPT='application/json, text/event-stream',
        )
        tools = self.client.post(
            f'/mcp/{profile.id}/',
            {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list', 'params': {}},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
            HTTP_ACCEPT='application/json, text/event-stream',
        )

        self.assertEqual(initialize.status_code, 200)
        self.assertEqual(initialize.data['result']['protocolVersion'], '2025-06-18')
        self.assertEqual(tools.status_code, 200)
        self.assertIn('search_knowledge', [tool['name'] for tool in tools.data['result']['tools']])

    @patch('apps.mcp_server.services.VectorSearchService.search_paragraphs')
    def test_mcp_search_tool_returns_structured_content_and_logs(self, mock_search):
        """search_knowledge should call vector search and write an access log."""
        profile, token = self._create_profile_with_token()
        mock_search.return_value = [
            {
                'paragraph_id': self.paragraph.id,
                'document_id': self.document.id,
                'document_name': self.document.name,
                'title': self.paragraph.title,
                'content': self.paragraph.content,
                'score': 0.91,
            }
        ]

        response = self.client.post(
            f'/mcp/{profile.id}/',
            {
                'jsonrpc': '2.0',
                'id': 3,
                'method': 'tools/call',
                'params': {'name': 'search_knowledge', 'arguments': {'query': 'MCP', 'top_k': 3}},
            },
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
            HTTP_ACCEPT='application/json, text/event-stream',
        )

        self.assertEqual(response.status_code, 200)
        content = response.data['result']['structuredContent']
        self.assertEqual(content['query'], 'MCP')
        self.assertEqual(content['results'][0]['document_name'], self.document.name)
        mock_search.assert_called_once_with('MCP', str(self.knowledge_base.id), top_k=3)
        self.assertEqual(MCPAccessLog.objects.filter(profile=profile, method='tools/call', tool_name='search_knowledge').count(), 1)

    def test_mcp_endpoint_rejects_invalid_token(self):
        """MCP endpoint should reject missing or invalid bearer tokens."""
        profile, _token = self._create_profile_with_token()

        response = self.client.post(
            f'/mcp/{profile.id}/',
            {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list', 'params': {}},
            format='json',
            HTTP_AUTHORIZATION='Bearer wrong',
        )

        self.assertEqual(response.status_code, 403)

    def test_profile_scope_filters_disallowed_tools(self):
        """A search-only profile must not expose read tools even if configured."""
        raw_token = MCPProfile.generate_token()
        profile = MCPProfile.objects.create(
            knowledge_base=self.knowledge_base,
            created_by=self.owner,
            name='Search Only',
            token_hash=MCPProfile.hash_token(raw_token),
            permission_scope=MCPProfile.Scope.SEARCH_ONLY,
            allowed_tools=['search_knowledge', 'get_document'],
        )

        response = self.client.post(
            f'/mcp/{profile.id}/',
            {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list', 'params': {}},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {raw_token}',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([tool['name'] for tool in response.data['result']['tools']], ['search_knowledge'])

    def test_mcp_resources_list_and_read(self):
        """MCP endpoint should expose document resources for MCP clients."""
        profile, token = self._create_profile_with_token()
        resource_uri = f'manxiai://knowledge-bases/{self.knowledge_base.id}/documents/{self.document.id}'

        listed = self.client.post(
            f'/mcp/{profile.id}/',
            {'jsonrpc': '2.0', 'id': 4, 'method': 'resources/list', 'params': {}},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        read = self.client.post(
            f'/mcp/{profile.id}/',
            {'jsonrpc': '2.0', 'id': 5, 'method': 'resources/read', 'params': {'uri': resource_uri}},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )

        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.data['result']['resources'][0]['uri'], resource_uri)
        self.assertEqual(read.status_code, 200)
        self.assertIn('MCP hosted server content.', read.data['result']['contents'][0]['text'])
