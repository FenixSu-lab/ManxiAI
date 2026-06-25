"""Tests for public core health-check endpoints."""

import pytest
from rest_framework.test import APIClient


pytestmark = pytest.mark.django_db


def test_health_check_is_public_and_reports_database_status():
    """The health endpoint should be anonymous and include database diagnostics."""
    client = APIClient()

    response = client.get('/api/v1/health/')

    assert response.status_code == 200
    assert response.data['status'] == 'ok'
    assert response.data['database']['ok'] is True
    assert 'latency_ms' in response.data['database']
    assert 'latency_ms' in response.data
