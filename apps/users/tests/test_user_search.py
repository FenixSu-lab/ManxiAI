"""Tests for user lookup endpoints used by permission assignment UI."""

from django.test import TestCase
from rest_framework.test import APIClient

from apps.users.models import User


class UserSearchTests(TestCase):
    """Verify authenticated user search behavior."""

    def test_authenticated_user_can_search_other_active_users(self):
        """Search should return system users except the requester."""
        requester = User.objects.create_user(email='requester@example.com', username='requester', password='secret123')
        target = User.objects.create_user(email='target@example.com', username='target-user', password='secret123')
        User.objects.create_user(email='other@example.com', username='other-user', password='secret123')
        client = APIClient()
        client.force_authenticate(requester)

        response = client.get('/api/v1/auth/users/search/', {'q': 'target'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], str(target.id))
        self.assertEqual(response.data[0]['email'], target.email)
