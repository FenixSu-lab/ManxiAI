"""Tests for knowledge-base API behavior used by the frontend."""

import pytest
from rest_framework.test import APIClient

from apps.knowledge_base.models import KnowledgeBase, KnowledgeBaseShare
from apps.users.models import User


pytestmark = pytest.mark.django_db


def test_create_knowledge_base_returns_full_payload():
    """Creating a knowledge base should attach ownership and return list-card fields."""
    user = User.objects.create_user(
        email='kb-owner@example.com',
        username='kbowner',
        password='StrongPass123!',
    )
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        '/api/v1/knowledge-bases/',
        {
            'name': 'Frontend KB',
            'description': 'Created from the frontend form.',
            'is_public': False,
            'chunk_size': 1000,
            'top_k': 5,
        },
        format='json',
    )

    assert response.status_code == 201
    assert response.data['name'] == 'Frontend KB'
    assert response.data['created_by'] == user.id
    assert response.data['documents_count'] == 0
    assert response.data['chunks_count'] == 0


def test_duplicate_knowledge_base_name_returns_field_error():
    """Duplicate names for the same owner should return a name field error."""
    user = User.objects.create_user(
        email='kb-duplicate@example.com',
        username='kbduplicate',
        password='StrongPass123!',
    )
    KnowledgeBase.objects.create(name='Duplicate KB', created_by=user)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        '/api/v1/knowledge-bases/',
        {'name': 'Duplicate KB', 'description': ''},
        format='json',
    )

    assert response.status_code == 400
    assert 'name' in response.data


def test_knowledge_base_list_only_returns_visible_rows():
    """The list endpoint should only include owned or shared visible knowledge bases."""
    user = User.objects.create_user(
        email='kb-list@example.com',
        username='kblist',
        password='StrongPass123!',
    )
    other_user = User.objects.create_user(
        email='kb-list-other@example.com',
        username='kblistother',
        password='StrongPass123!',
    )
    visible = KnowledgeBase.objects.create(name='Visible KB', created_by=user)
    KnowledgeBase.objects.create(name='Hidden KB', created_by=other_user)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get('/api/v1/knowledge-bases/')

    assert response.status_code == 200
    names = [item['name'] for item in response.data['results']]
    assert names == [visible.name]


def test_public_knowledge_base_is_visible_as_read_only():
    """Public knowledge bases should be readable without explicit shares."""
    owner = User.objects.create_user(email='kb-public-owner@example.com', username='kbpublicowner', password='StrongPass123!')
    reader = User.objects.create_user(email='kb-public-reader@example.com', username='kbpublicreader', password='StrongPass123!')
    public_kb = KnowledgeBase.objects.create(name='Open KB', created_by=owner, is_public=True)
    client = APIClient()
    client.force_authenticate(user=reader)

    response = client.get('/api/v1/knowledge-bases/')

    assert response.status_code == 200
    payload = response.data['results'][0]
    assert payload['id'] == str(public_kb.id)
    assert payload['user_role'] == 'read'
    assert payload['can_write'] is False
    assert payload['can_manage'] is False


def test_only_owner_can_manage_knowledge_base_shares():
    """Write users can maintain data sources but cannot assign permissions."""
    owner = User.objects.create_user(email='kb-share-owner@example.com', username='kbshareowner', password='StrongPass123!')
    writer = User.objects.create_user(email='kb-share-writer@example.com', username='kbsharewriter', password='StrongPass123!')
    target = User.objects.create_user(email='kb-share-target@example.com', username='kbsharetarget', password='StrongPass123!')
    knowledge_base = KnowledgeBase.objects.create(name='Permission KB', created_by=owner)
    KnowledgeBaseShare.objects.create(knowledge_base=knowledge_base, shared_with=writer, permission='write')
    client = APIClient()
    client.force_authenticate(user=writer)

    response = client.post(
        f'/api/v1/knowledge-bases/{knowledge_base.id}/share/',
        {'user_email': target.email, 'permission': 'read'},
        format='json',
    )

    assert response.status_code == 403
