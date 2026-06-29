"""Hosted MCP JSON-RPC services for knowledge-base profiles."""

import json
import logging
import time
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.db import models
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.document.models import Document, Paragraph
from apps.embedding.services import VectorSearchService
from apps.model_management.ai_service import AIServiceFactory

from .models import MCPAccessLog, MCPProfile

logger = logging.getLogger(__name__)

MCP_PROTOCOL_VERSION = '2025-06-18'


@dataclass
class MCPResult:
    """Structured outcome for a JSON-RPC request."""

    payload: dict[str, Any] | None
    status_code: int = 200


class MCPError(Exception):
    """Protocol-aware JSON-RPC error."""

    def __init__(self, code: int, message: str):
        """Create a JSON-RPC error with a numeric code and message."""
        self.code = code
        self.message = message
        super().__init__(message)


class MCPProfileAuthenticator:
    """Authenticate bearer tokens for hosted MCP profiles."""

    @staticmethod
    def authenticate(profile_id, authorization_header: str) -> MCPProfile:
        """Return an active profile when the bearer token is valid."""
        if not authorization_header.startswith('Bearer '):
            raise PermissionDenied('Bearer token is required.')
        raw_token = authorization_header.removeprefix('Bearer ').strip()
        token_hash = MCPProfile.hash_token(raw_token)
        try:
            profile = MCPProfile.objects.select_related('knowledge_base').get(id=profile_id, token_hash=token_hash)
        except MCPProfile.DoesNotExist as exc:
            raise PermissionDenied('Invalid MCP token.') from exc
        if not profile.is_active:
            raise PermissionDenied('MCP profile is disabled.')
        if profile.is_expired():
            raise PermissionDenied('MCP profile has expired.')
        return profile


class MCPRateLimiter:
    """Simple per-profile request limiter backed by access logs."""

    @staticmethod
    def check(profile: MCPProfile) -> None:
        """Reject requests over the profile's minute limit."""
        if profile.rate_limit_per_minute <= 0:
            return
        since = timezone.now() - timedelta(minutes=1)
        recent_count = MCPAccessLog.objects.filter(profile=profile, created_at__gte=since).count()
        if recent_count >= profile.rate_limit_per_minute:
            raise PermissionDenied('MCP rate limit exceeded.')


class MCPToolRegistry:
    """Expose safe read-only knowledge-base tools."""

    @staticmethod
    def list_tools(profile: MCPProfile) -> list[dict[str, Any]]:
        """Return tool descriptors filtered by profile configuration."""
        tools = {
            'search_knowledge': {
                'name': 'search_knowledge',
                'description': 'Search this ManxiAI knowledge base and return cited paragraph snippets.',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'query': {'type': 'string', 'description': 'Natural-language search query.'},
                        'top_k': {'type': 'integer', 'minimum': 1, 'maximum': profile.max_top_k},
                    },
                    'required': ['query'],
                },
            },
            'list_sources': {
                'name': 'list_sources',
                'description': 'List visible data sources exported by this knowledge base.',
                'inputSchema': {'type': 'object', 'properties': {}},
            },
            'get_document': {
                'name': 'get_document',
                'description': 'Read one data source summary and paragraphs by document_id.',
                'inputSchema': {
                    'type': 'object',
                    'properties': {'document_id': {'type': 'string'}},
                    'required': ['document_id'],
                },
            },
            'get_paragraph': {
                'name': 'get_paragraph',
                'description': 'Read one paragraph by paragraph_id.',
                'inputSchema': {
                    'type': 'object',
                    'properties': {'paragraph_id': {'type': 'string'}},
                    'required': ['paragraph_id'],
                },
            },
            'answer_with_citations': {
                'name': 'answer_with_citations',
                'description': 'Generate an answer using retrieved context and include citations.',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'question': {'type': 'string'},
                        'top_k': {'type': 'integer', 'minimum': 1, 'maximum': profile.max_top_k},
                    },
                    'required': ['question'],
                },
            },
        }
        return [tools[name] for name in profile.allowed_tool_names() if name in tools]

    @staticmethod
    def call_tool(profile: MCPProfile, name: str, arguments: dict[str, Any]) -> tuple[dict[str, Any], int, str]:
        """Call one configured tool and return payload, result count, query text."""
        if name not in profile.allowed_tool_names():
            raise MCPError(-32601, f'Tool is not enabled for this MCP profile: {name}')
        handlers = {
            'search_knowledge': MCPToolRegistry.search_knowledge,
            'list_sources': MCPToolRegistry.list_sources,
            'get_document': MCPToolRegistry.get_document,
            'get_paragraph': MCPToolRegistry.get_paragraph,
            'answer_with_citations': MCPToolRegistry.answer_with_citations,
        }
        if name not in handlers:
            raise MCPError(-32601, f'Unknown tool: {name}')
        return handlers[name](profile, arguments or {})

    @staticmethod
    def search_knowledge(profile: MCPProfile, arguments: dict[str, Any]) -> tuple[dict[str, Any], int, str]:
        """Run vector search against the profile knowledge base."""
        query = str(arguments.get('query', '')).strip()
        if not query:
            raise MCPError(-32602, 'query is required.')
        top_k = min(int(arguments.get('top_k') or profile.max_top_k), profile.max_top_k)
        results = VectorSearchService.search_paragraphs(query, str(profile.knowledge_base_id), top_k=top_k)
        payload = {
            'query': query,
            'results': [MCPToolRegistry._format_search_result(item, profile) for item in results],
        }
        return payload, len(results), query

    @staticmethod
    def list_sources(profile: MCPProfile, _arguments: dict[str, Any]) -> tuple[dict[str, Any], int, str]:
        """List non-deleted data sources in this profile's knowledge base."""
        documents = Document.objects.filter(knowledge_base=profile.knowledge_base, is_deleted=False).order_by('-updated_at')
        payload = {
            'knowledge_base_id': str(profile.knowledge_base_id),
            'sources': [
                {
                    'document_id': str(document.id),
                    'name': document.name,
                    'type': document.type,
                    'status': document.status,
                    'paragraph_count': document.paragraph_count,
                    'updated_at': document.updated_at.isoformat(),
                }
                for document in documents
            ],
        }
        return payload, documents.count(), ''

    @staticmethod
    def get_document(profile: MCPProfile, arguments: dict[str, Any]) -> tuple[dict[str, Any], int, str]:
        """Read one document and optionally include paragraph content."""
        document_id = arguments.get('document_id')
        if not document_id:
            raise MCPError(-32602, 'document_id is required.')
        document = Document.objects.get(id=document_id, knowledge_base=profile.knowledge_base, is_deleted=False)
        paragraphs = document.paragraphs.filter(is_active=True).order_by('position')
        payload = {
            'document_id': str(document.id),
            'name': document.name,
            'type': document.type,
            'status': document.status,
            'paragraph_count': document.paragraph_count,
            'paragraphs': [
                {
                    'paragraph_id': str(paragraph.id),
                    'title': paragraph.title,
                    'content': paragraph.content if profile.include_source_content else '',
                    'position': paragraph.position,
                }
                for paragraph in paragraphs
            ],
        }
        return payload, paragraphs.count(), ''

    @staticmethod
    def get_paragraph(profile: MCPProfile, arguments: dict[str, Any]) -> tuple[dict[str, Any], int, str]:
        """Read one active paragraph from this profile's knowledge base."""
        paragraph_id = arguments.get('paragraph_id')
        if not paragraph_id:
            raise MCPError(-32602, 'paragraph_id is required.')
        paragraph = Paragraph.objects.select_related('document').get(
            id=paragraph_id,
            knowledge_base=profile.knowledge_base,
            is_active=True,
        )
        payload = {
            'paragraph_id': str(paragraph.id),
            'document_id': str(paragraph.document_id),
            'document_name': paragraph.document.name,
            'title': paragraph.title,
            'content': paragraph.content if profile.include_source_content else '',
            'position': paragraph.position,
        }
        return payload, 1, ''

    @staticmethod
    def answer_with_citations(profile: MCPProfile, arguments: dict[str, Any]) -> tuple[dict[str, Any], int, str]:
        """Generate an answer with retrieved citations."""
        question = str(arguments.get('question', '')).strip()
        if not question:
            raise MCPError(-32602, 'question is required.')
        top_k = min(int(arguments.get('top_k') or profile.max_top_k), profile.max_top_k)
        results = VectorSearchService.search_paragraphs(question, str(profile.knowledge_base_id), top_k=top_k)
        context = [item['content'] for item in results]
        answer = AIServiceFactory.get_service().chat_with_history(message=question, history=[], context=context)
        payload = {
            'question': question,
            'answer': answer,
            'citations': [MCPToolRegistry._format_search_result(item, profile) for item in results],
        }
        return payload, len(results), question

    @staticmethod
    def _format_search_result(item: dict[str, Any], profile: MCPProfile) -> dict[str, Any]:
        """Format vector search results for MCP clients."""
        payload = {
            'paragraph_id': str(item['paragraph_id']),
            'document_id': str(item['document_id']),
            'document_name': item['document_name'],
            'title': item.get('title') or '',
            'score': item.get('score'),
            'citation': f"{item['document_name']} / {item.get('title') or item['paragraph_id']}",
        }
        if profile.include_source_content:
            payload['content'] = item.get('content') or ''
        return payload


class MCPResourceRegistry:
    """Expose knowledge-base resources through MCP."""

    @staticmethod
    def list_resources(profile: MCPProfile) -> list[dict[str, Any]]:
        """List document resources for this profile."""
        documents = Document.objects.filter(knowledge_base=profile.knowledge_base, is_deleted=False).order_by('-updated_at')
        return [
            {
                'uri': f'manxiai://knowledge-bases/{profile.knowledge_base_id}/documents/{document.id}',
                'name': document.name,
                'description': f'{document.type} source with {document.paragraph_count} paragraphs',
                'mimeType': 'application/json',
            }
            for document in documents
        ]

    @staticmethod
    def read_resource(profile: MCPProfile, uri: str) -> dict[str, Any]:
        """Read a supported ManxiAI resource URI."""
        marker = f'manxiai://knowledge-bases/{profile.knowledge_base_id}/documents/'
        if not uri.startswith(marker):
            raise MCPError(-32602, 'Unsupported resource URI.')
        document_id = uri.removeprefix(marker).strip('/')
        payload, _count, _query = MCPToolRegistry.get_document(profile, {'document_id': document_id})
        return {
            'contents': [
                {
                    'uri': uri,
                    'mimeType': 'application/json',
                    'text': json.dumps(payload, ensure_ascii=False),
                }
            ]
        }


class MCPJSONRPCService:
    """Handle MCP JSON-RPC requests."""

    @staticmethod
    def handle(profile: MCPProfile, message: dict[str, Any], request_meta: dict[str, Any]) -> MCPResult:
        """Dispatch one JSON-RPC request or notification."""
        started_at = time.perf_counter()
        request_id = message.get('id')
        method = message.get('method', '')
        params = message.get('params') or {}
        tool_name = ''
        query = ''
        result_count = 0
        try:
            if message.get('jsonrpc') != '2.0':
                raise MCPError(-32600, 'jsonrpc must be "2.0".')
            if request_id is None:
                return MCPResult(None, status_code=202)
            result, tool_name, result_count, query = MCPJSONRPCService._dispatch(profile, method, params)
            MCPJSONRPCService._record_success(profile, method, tool_name, query, result_count, started_at, request_meta)
            return MCPResult({'jsonrpc': '2.0', 'id': request_id, 'result': result})
        except MCPError as exc:
            MCPJSONRPCService._record_error(profile, method, tool_name, query, started_at, request_meta, exc.message)
            return MCPResult({'jsonrpc': '2.0', 'id': request_id, 'error': {'code': exc.code, 'message': exc.message}})
        except (Document.DoesNotExist, Paragraph.DoesNotExist):
            message_text = 'Requested knowledge resource was not found.'
            MCPJSONRPCService._record_error(profile, method, tool_name, query, started_at, request_meta, message_text)
            return MCPResult({'jsonrpc': '2.0', 'id': request_id, 'error': {'code': -32004, 'message': message_text}})
        except Exception as exc:
            logger.exception('mcp_request_failed profile_id=%s method=%s', profile.id, method)
            MCPJSONRPCService._record_error(profile, method, tool_name, query, started_at, request_meta, str(exc))
            return MCPResult({'jsonrpc': '2.0', 'id': request_id, 'error': {'code': -32603, 'message': 'Internal MCP server error.'}})

    @staticmethod
    def _dispatch(profile: MCPProfile, method: str, params: dict[str, Any]) -> tuple[dict[str, Any], str, int, str]:
        """Dispatch JSON-RPC methods supported by this server."""
        if method == 'initialize':
            return MCPJSONRPCService._initialize(profile), '', 0, ''
        if method == 'tools/list':
            return {'tools': MCPToolRegistry.list_tools(profile)}, '', 0, ''
        if method == 'tools/call':
            tool_name = params.get('name', '')
            arguments = params.get('arguments') or {}
            payload, result_count, query = MCPToolRegistry.call_tool(profile, tool_name, arguments)
            return MCPJSONRPCService._tool_result(payload), tool_name, result_count, query
        if method == 'resources/list':
            return {'resources': MCPResourceRegistry.list_resources(profile)}, '', 0, ''
        if method == 'resources/read':
            return MCPResourceRegistry.read_resource(profile, params.get('uri', '')), '', 1, ''
        raise MCPError(-32601, f'Unsupported MCP method: {method}')

    @staticmethod
    def _initialize(profile: MCPProfile) -> dict[str, Any]:
        """Return server capabilities for MCP initialization."""
        return {
            'protocolVersion': MCP_PROTOCOL_VERSION,
            'capabilities': {
                'tools': {},
                'resources': {},
            },
            'serverInfo': {
                'name': f'ManxiAI Knowledge Base - {profile.knowledge_base.name}',
                'version': '1.0.0',
            },
        }

    @staticmethod
    def _tool_result(payload: dict[str, Any]) -> dict[str, Any]:
        """Return an MCP tool result with text and structured content."""
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        return {
            'content': [{'type': 'text', 'text': text}],
            'structuredContent': payload,
            'isError': False,
        }

    @staticmethod
    def _record_success(profile, method, tool_name, query, result_count, started_at, request_meta):
        """Persist success audit data and profile usage counters."""
        MCPJSONRPCService._create_log(profile, method, tool_name, query, 'ok', result_count, '', started_at, request_meta)
        MCPProfile.objects.filter(id=profile.id).update(
            last_used_at=timezone.now(),
            usage_count=models.F('usage_count') + 1,
        )

    @staticmethod
    def _record_error(profile, method, tool_name, query, started_at, request_meta, error_message):
        """Persist failure audit data."""
        MCPJSONRPCService._create_log(profile, method, tool_name, query, 'error', 0, error_message, started_at, request_meta)

    @staticmethod
    def _create_log(profile, method, tool_name, query, status, result_count, error_message, started_at, request_meta):
        """Create one access log row."""
        MCPAccessLog.objects.create(
            profile=profile,
            method=method or '',
            tool_name=tool_name or '',
            query=(query or '')[:2000],
            caller_ip=request_meta.get('ip'),
            user_agent=request_meta.get('user_agent', '')[:2000],
            status=status,
            latency_ms=max(int((time.perf_counter() - started_at) * 1000), 0),
            result_count=result_count,
            error_message=(error_message or '')[:4000],
        )
