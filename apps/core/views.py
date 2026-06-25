"""Public health-check endpoints for local and deployment diagnostics."""

import logging
import time

from django.conf import settings
from django.db import connection
from django.db import models
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.chat.models import ChatSession
from apps.document.models import Document
from apps.knowledge_base.models import KnowledgeBase
from apps.users.models import User

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Return backend process status and database query latency."""
    started_at = time.perf_counter()
    database_result = _check_database()
    total_latency_ms = _elapsed_ms(started_at)
    is_healthy = database_result['ok']
    response_status = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    payload = {
        'status': 'ok' if is_healthy else 'degraded',
        'debug': settings.DEBUG,
        'database': database_result,
        'latency_ms': total_latency_ms,
    }
    logger.info(
        'health_check status=%s db_ok=%s db_latency_ms=%s total_latency_ms=%s',
        payload['status'],
        database_result['ok'],
        database_result.get('latency_ms'),
        total_latency_ms,
    )
    return Response(payload, status=response_status)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_summary(request):
    """Return summary counters for the authenticated user's dashboard."""
    started_at = time.perf_counter()
    visible_knowledge_bases = KnowledgeBase.objects.filter(
        models.Q(created_by=request.user) | models.Q(shares__shared_with=request.user),
        is_deleted=False,
    ).distinct()
    knowledge_base_ids = visible_knowledge_bases.values_list('id', flat=True)
    payload = {
        'knowledge_base_count': visible_knowledge_bases.count(),
        'document_count': Document.objects.filter(knowledge_base_id__in=knowledge_base_ids, is_deleted=False).count(),
        'chat_count': ChatSession.objects.filter(user=request.user).count(),
        'user_count': User.objects.count(),
    }
    elapsed_ms = _elapsed_ms(started_at)
    logger.info(
        'dashboard_summary user_id=%s knowledge_base_count=%s document_count=%s chat_count=%s user_count=%s latency_ms=%s',
        request.user.id,
        payload['knowledge_base_count'],
        payload['document_count'],
        payload['chat_count'],
        payload['user_count'],
        elapsed_ms,
    )
    return Response({**payload, 'latency_ms': elapsed_ms})


def _check_database() -> dict:
    """Run a minimal database query and return a structured result."""
    started_at = time.perf_counter()
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except Exception as exc:
        latency_ms = _elapsed_ms(started_at)
        logger.exception('health_check_database_failed latency_ms=%s error=%s', latency_ms, exc)
        return {
            'ok': False,
            'engine': settings.DATABASES['default']['ENGINE'],
            'latency_ms': latency_ms,
            'error': str(exc),
        }

    return {
        'ok': True,
        'engine': settings.DATABASES['default']['ENGINE'],
        'latency_ms': _elapsed_ms(started_at),
    }


def _elapsed_ms(started_at: float) -> int:
    """Return elapsed milliseconds since a monotonic timestamp."""
    return int((time.perf_counter() - started_at) * 1000)
