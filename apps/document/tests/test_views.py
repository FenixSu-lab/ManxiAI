"""Regression tests for document creation endpoints."""

from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.document.models import (
    Document,
    DocumentProcessingTask,
    DocumentStatus,
    Paragraph,
    Problem,
    ProblemParagraphMapping,
)
from apps.document.serializers import DocumentDetailSerializer, DocumentListSerializer
from apps.document.views import DocumentViewSet
from apps.knowledge_base.models import KnowledgeBase
from apps.users.models import User


class DocumentViewSetTests(TestCase):
    """Verify document API flows that feed the retrieval pipeline."""

    def setUp(self):
        """Create a user, a knowledge base, and a request factory."""
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            email='owner@example.com',
            username='owner',
            password='secret123',
        )
        self.knowledge_base = KnowledgeBase.objects.create(
            name='QA KB',
            created_by=self.user,
        )

    @patch('apps.document.views.EmbeddingService.embed_paragraphs_async')
    def test_create_qa_triggers_embedding_workflow(self, mock_embed):
        """QA document creation should enqueue embeddings for the generated paragraphs."""
        view = DocumentViewSet.as_view({'post': 'create_qa'})
        request = self.factory.post(
            f'/api/v1/documents/knowledge-bases/{self.knowledge_base.id}/documents/create-qa/',
            {
                'name': 'Common Questions',
                'qa_pairs': [
                    {'question': 'What is ManxiAI?', 'answer': 'A knowledge workflow system.'},
                    {'question': 'What database is used?', 'answer': 'PostgreSQL with pgvector.'},
                ],
            },
            format='json',
        )
        force_authenticate(request, user=self.user)

        response = view(request, knowledge_base_id=self.knowledge_base.id)

        self.assertEqual(response.status_code, 201)
        document = Document.objects.get(name='Common Questions')
        self.assertEqual(document.type, 'qa')
        self.assertEqual(document.status, DocumentStatus.EMBEDDING)
        self.assertEqual(Paragraph.objects.filter(document=document).count(), 2)
        self.assertEqual(Problem.objects.filter(knowledge_base=self.knowledge_base).count(), 2)
        self.assertEqual(ProblemParagraphMapping.objects.filter(document=document).count(), 2)
        mock_embed.assert_called_once_with(document)

    def test_create_qa_rejects_empty_pairs(self):
        """QA document creation should expose serializer errors for invalid payloads."""
        view = DocumentViewSet.as_view({'post': 'create_qa'})
        request = self.factory.post(
            f'/api/v1/documents/knowledge-bases/{self.knowledge_base.id}/documents/create-qa/',
            {
                'name': 'Invalid QA',
                'qa_pairs': [],
            },
            format='json',
        )
        force_authenticate(request, user=self.user)

        response = view(request, knowledge_base_id=self.knowledge_base.id)

        self.assertEqual(response.status_code, 400)
        self.assertIn('qa_pairs', response.data)

    @patch('apps.document.views.DocumentProcessingService.process_document_async')
    def test_reprocess_resets_document_and_clears_paragraphs(self, mock_process):
        """Reprocess should reset status, clear old paragraphs, and enqueue processing."""
        document = Document.objects.create(
            knowledge_base=self.knowledge_base,
            created_by=self.user,
            name='Uploaded Doc',
            status=DocumentStatus.COMPLETED,
        )
        Paragraph.objects.create(
            document=document,
            knowledge_base=self.knowledge_base,
            content='Old paragraph',
            position=0,
        )
        view = DocumentViewSet.as_view({'post': 'reprocess'})
        request = self.factory.post(
            f'/api/v1/documents/knowledge-bases/{self.knowledge_base.id}/documents/{document.id}/reprocess/',
            {},
            format='json',
        )
        force_authenticate(request, user=self.user)

        response = view(request, knowledge_base_id=self.knowledge_base.id, pk=document.id)

        document.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(document.status, DocumentStatus.PROCESSING)
        self.assertEqual(Paragraph.objects.filter(document=document).count(), 0)
        mock_process.assert_called_once_with(document)

    def test_document_serializers_include_latest_failed_task_error(self):
        """Document list/detail payloads should expose failed embedding diagnostics."""
        document = Document.objects.create(
            knowledge_base=self.knowledge_base,
            created_by=self.user,
            name='Failed Doc',
            status=DocumentStatus.FAILED,
        )
        DocumentProcessingTask.objects.create(
            document=document,
            task_type='embedding',
            status='failed',
            error_message='Embedding request failed.',
        )

        list_payload = DocumentListSerializer(document).data
        detail_payload = DocumentDetailSerializer(document).data

        self.assertEqual(list_payload['latest_error'], 'Embedding request failed.')
        self.assertEqual(detail_payload['latest_error'], 'Embedding request failed.')
