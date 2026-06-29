"""API regression tests for chat session and message workflows."""

from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.chat.models import ChatMessage, ChatSession
from apps.chat.views import ChatSessionViewSet
from apps.document.models import Document, DocumentType, Paragraph, ProblemParagraphMapping
from apps.knowledge_base.models import KnowledgeBase, KnowledgeBaseShare
from apps.users.models import User


class ChatSessionViewSetTests(TestCase):
    """Cover chat API behavior that connects sessions to the RAG pipeline."""

    def setUp(self):
        """Create a user, knowledge base, and request factory for API calls."""
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            email='chat-owner@example.com',
            username='chat-owner',
            password='secret123',
        )
        self.knowledge_base = KnowledgeBase.objects.create(
            name='Chat KB',
            created_by=self.user,
        )

    def test_create_session_auto_binds_single_user_knowledge_base(self):
        """Creating a session should bind the user's only knowledge base by default."""
        view = ChatSessionViewSet.as_view({'post': 'create'})
        request = self.factory.post('/api/v1/chat/sessions/', {'title': 'KB chat'}, format='json')
        force_authenticate(request, user=self.user)

        response = view(request)

        self.assertEqual(response.status_code, 201)
        session = ChatSession.objects.get(id=response.data['id'])
        self.assertEqual(session.knowledge_base_id, self.knowledge_base.id)
        self.assertEqual(response.data['knowledge_base_id'], str(self.knowledge_base.id))

    @patch('apps.chat.views.RetrievalAugmentedGenerationService.generate_chat_reply')
    def test_post_message_calls_rag_pipeline_with_bound_knowledge_base(self, mock_generate):
        """Posting a user message should persist both turns and pass the KB into RAG."""
        mock_generate.return_value = 'assistant answer'
        session = ChatSession.objects.create(
            user=self.user,
            title='KB chat',
            knowledge_base=self.knowledge_base,
        )
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.RoleChoices.USER,
            content='previous question',
        )
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.RoleChoices.ASSISTANT,
            content='previous answer',
        )
        view = ChatSessionViewSet.as_view({'post': 'messages'})
        request = self.factory.post(
            f'/api/v1/chat/sessions/{session.id}/messages/',
            {'role': 'user', 'content': 'What does this KB contain?'},
            format='json',
        )
        force_authenticate(request, user=self.user)

        response = view(request, pk=session.id)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(ChatMessage.objects.filter(session=session).count(), 4)
        self.assertEqual(response.data['assistant_message']['content'], 'assistant answer')
        mock_generate.assert_called_once_with(
            message='What does this KB contain?',
            history=[
                {'role': 'user', 'content': 'previous question'},
                {'role': 'assistant', 'content': 'previous answer'},
            ],
            knowledge_base_id=str(self.knowledge_base.id),
        )

    @patch('apps.chat.views.RetrievalAugmentedGenerationService.generate_chat_reply')
    def test_post_message_rejects_non_user_role(self, mock_generate):
        """Only user-authored messages should be accepted by the public API."""
        session = ChatSession.objects.create(
            user=self.user,
            title='KB chat',
            knowledge_base=self.knowledge_base,
        )
        view = ChatSessionViewSet.as_view({'post': 'messages'})
        request = self.factory.post(
            f'/api/v1/chat/sessions/{session.id}/messages/',
            {'role': 'assistant', 'content': 'invalid assistant message'},
            format='json',
        )
        force_authenticate(request, user=self.user)

        response = view(request, pk=session.id)

        self.assertEqual(response.status_code, 400)
        self.assertIn('role', response.data)
        mock_generate.assert_not_called()

    @patch('apps.chat.views.RetrievalAugmentedGenerationService.generate_chat_reply')
    def test_post_message_rejects_blank_content(self, mock_generate):
        """Blank message content should return a content field error."""
        session = ChatSession.objects.create(
            user=self.user,
            title='KB chat',
            knowledge_base=self.knowledge_base,
        )
        view = ChatSessionViewSet.as_view({'post': 'messages'})
        request = self.factory.post(
            f'/api/v1/chat/sessions/{session.id}/messages/',
            {'role': 'user', 'content': '   '},
            format='json',
        )
        force_authenticate(request, user=self.user)

        response = view(request, pk=session.id)

        self.assertEqual(response.status_code, 400)
        self.assertIn('content', response.data)
        mock_generate.assert_not_called()

    def test_archive_preview_returns_pairs_without_creating_document(self):
        """Archive preview should show generated QA items without writing a data source."""
        session = ChatSession.objects.create(user=self.user, title='Archive chat', knowledge_base=self.knowledge_base)
        ChatMessage.objects.create(session=session, role=ChatMessage.RoleChoices.USER, content='What is A?')
        ChatMessage.objects.create(session=session, role=ChatMessage.RoleChoices.ASSISTANT, content='A is alpha.')
        view = ChatSessionViewSet.as_view({'post': 'archive'})
        request = self.factory.post(
            f'/api/v1/chat/sessions/{session.id}/archive/',
            {'knowledge_base_id': str(self.knowledge_base.id), 'preview': True},
            format='json',
        )
        force_authenticate(request, user=self.user)

        response = view(request, pk=session.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['estimated_count'], 1)
        self.assertEqual(Document.objects.count(), 0)

    @patch('apps.chat.services.EmbeddingService.embed_paragraphs_async')
    def test_archive_creates_managed_chat_archive_document(self, mock_embed):
        """Archiving a chat should create a visible data source that can be managed."""
        session = ChatSession.objects.create(user=self.user, title='Archive chat', knowledge_base=self.knowledge_base)
        ChatMessage.objects.create(session=session, role=ChatMessage.RoleChoices.USER, content='What is A?')
        ChatMessage.objects.create(session=session, role=ChatMessage.RoleChoices.ASSISTANT, content='A is alpha.')
        view = ChatSessionViewSet.as_view({'post': 'archive'})
        request = self.factory.post(
            f'/api/v1/chat/sessions/{session.id}/archive/',
            {'knowledge_base_id': str(self.knowledge_base.id), 'name': 'Archived Chat'},
            format='json',
        )
        force_authenticate(request, user=self.user)

        response = view(request, pk=session.id)

        self.assertEqual(response.status_code, 201)
        document = Document.objects.get(id=response.data['document_id'])
        self.assertEqual(document.type, DocumentType.CHAT_ARCHIVE)
        self.assertEqual(document.name, 'Archived Chat')
        self.assertEqual(document.meta['source'], 'chat_archive')
        self.assertEqual(Paragraph.objects.filter(document=document).count(), 1)
        self.assertEqual(ProblemParagraphMapping.objects.filter(document=document).count(), 1)
        mock_embed.assert_called_once_with(document)

    def test_read_share_cannot_archive_chat_to_knowledge_base(self):
        """Read users can chat with shared knowledge but cannot archive new data sources."""
        reader = User.objects.create_user(email='chat-reader@example.com', username='chat-reader', password='secret123')
        KnowledgeBaseShare.objects.create(knowledge_base=self.knowledge_base, shared_with=reader, permission='read')
        session = ChatSession.objects.create(user=reader, title='Reader chat', knowledge_base=self.knowledge_base)
        ChatMessage.objects.create(session=session, role=ChatMessage.RoleChoices.USER, content='What is A?')
        ChatMessage.objects.create(session=session, role=ChatMessage.RoleChoices.ASSISTANT, content='A is alpha.')
        view = ChatSessionViewSet.as_view({'post': 'archive'})
        request = self.factory.post(
            f'/api/v1/chat/sessions/{session.id}/archive/',
            {'knowledge_base_id': str(self.knowledge_base.id), 'name': 'Denied Archive'},
            format='json',
        )
        force_authenticate(request, user=reader)

        response = view(request, pk=session.id)

        self.assertEqual(response.status_code, 403)
