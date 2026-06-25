"""Tests for user registration and login API behavior."""

import pytest
from rest_framework.test import APIClient

from apps.users.models import User


pytestmark = pytest.mark.django_db


def test_login_accepts_email_credentials():
    """Email login returns a token and the matching user payload."""
    user = User.objects.create_user(
        email='login-email@example.com',
        username='emailuser',
        password='StrongPass123!',
    )
    client = APIClient()

    response = client.post(
        '/api/v1/auth/users/login/',
        {'email': user.email, 'password': 'StrongPass123!'},
        format='json',
    )

    assert response.status_code == 200
    assert response.data['token']
    assert response.data['user']['email'] == user.email


def test_login_accepts_username_credentials():
    """Username login maps the username to the custom email credential."""
    user = User.objects.create_user(
        email='login-username@example.com',
        username='usernameuser',
        password='StrongPass123!',
    )
    client = APIClient()

    response = client.post(
        '/api/v1/auth/users/login/',
        {'email': user.username, 'password': 'StrongPass123!'},
        format='json',
    )

    assert response.status_code == 200
    assert response.data['token']
    assert response.data['user']['email'] == user.email


def test_login_does_not_require_csrf_token_from_frontend_origin():
    """Token login accepts SPA requests without requiring a CSRF cookie."""
    user = User.objects.create_user(
        email='csrf-login@example.com',
        username='csrfuser',
        password='StrongPass123!',
    )
    client = APIClient(enforce_csrf_checks=True)

    response = client.post(
        '/api/v1/auth/users/login/',
        {'email': user.email, 'password': 'StrongPass123!'},
        format='json',
        HTTP_ORIGIN='http://localhost:3000',
    )

    assert response.status_code == 200
    assert response.data['token']


def test_register_returns_password_validation_errors():
    """Weak registration passwords return field-level DRF validation details."""
    client = APIClient()

    response = client.post(
        '/api/v1/auth/users/',
        {
            'email': 'weak-password@example.com',
            'username': 'weakpassword',
            'password': '123456',
            'confirm_password': '123456',
        },
        format='json',
    )

    assert response.status_code == 400
    assert 'password' in response.data
