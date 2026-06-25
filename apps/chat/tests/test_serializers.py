"""Serializer regression tests for chat APIs."""

from django.test import SimpleTestCase

from apps.chat.serializers import ChatMessageCreateSerializer


class ChatMessageCreateSerializerTests(SimpleTestCase):
    """Cover validation rules for inbound chat messages."""

    def test_accepts_user_role(self):
        """The API should allow user-authored messages."""
        serializer = ChatMessageCreateSerializer(data={'role': 'user', 'content': 'hello'})

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_rejects_assistant_role(self):
        """The API should reject assistant-authored payloads from callers."""
        serializer = ChatMessageCreateSerializer(data={'role': 'assistant', 'content': 'hello'})

        self.assertFalse(serializer.is_valid())
        self.assertIn('role', serializer.errors)
