"""Tests for authenticated dashboard summary endpoints."""

import pytest
from rest_framework.test import APIClient

from apps.chat.models import ChatSession
from apps.document.models import Document
from apps.knowledge_base.models import KnowledgeBase
from apps.users.models import User


pytestmark = pytest.mark.django_db


def test_dashboard_summary_requires_authentication():
    """Anonymous callers should not access user dashboard counters."""
    response = APIClient().get('/api/v1/dashboard/summary/')

    assert response.status_code == 401


def test_dashboard_summary_returns_user_visible_counts():
    """Summary counters should reflect resources visible to the current user."""
    user = User.objects.create_user(
        email='dashboard@example.com',
        username='dashboard',
        password='StrongPass123!',
    )
    other_user = User.objects.create_user(
        email='other-dashboard@example.com',
        username='otherdashboard',
        password='StrongPass123!',
    )
    knowledge_base = KnowledgeBase.objects.create(
        name='Dashboard KB',
        description='Dashboard summary test.',
        created_by=user,
    )
    KnowledgeBase.objects.create(
        name='Other KB',
        description='Should not be counted.',
        created_by=other_user,
    )
    Document.objects.create(
        knowledge_base=knowledge_base,
        created_by=user,
        name='Dashboard Doc',
    )
    ChatSession.objects.create(user=user, title='Dashboard Chat')
    ChatSession.objects.create(user=other_user, title='Other Chat')
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get('/api/v1/dashboard/summary/')

    assert response.status_code == 200
    assert response.data['knowledge_base_count'] == 1
    assert response.data['document_count'] == 1
    assert response.data['chat_count'] == 1
    assert response.data['user_count'] == 2
    assert 'latency_ms' in response.data
