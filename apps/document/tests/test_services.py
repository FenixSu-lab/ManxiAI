"""Tests for document processing service helpers."""

from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.document.models import Document, DocumentProcessingTask, DocumentStatus
from apps.document.services import EmbeddingService
from apps.knowledge_base.models import KnowledgeBase
from apps.users.models import User


class DocumentEmbeddingServiceTests(TestCase):
    """Cover synchronous execution for deterministic smoke tests."""

    def setUp(self):
        """Create a document fixture for embedding workflow tests."""
        self.user = User.objects.create_user(
            email='document-service@example.com',
            username='document-service',
            password='secret123',
        )
        self.knowledge_base = KnowledgeBase.objects.create(
            name='Document Service KB',
            created_by=self.user,
        )
        self.document = Document.objects.create(
            knowledge_base=self.knowledge_base,
            created_by=self.user,
            name='Document Service Doc',
            type='qa',
            status=DocumentStatus.PENDING,
        )

    @override_settings(RUN_BACKGROUND_TASKS_SYNC=True)
    @patch('apps.document.services.ParagraphEmbeddingService.embed_document_paragraphs')
    def test_embed_paragraphs_async_can_run_synchronously(self, mock_embed):
        """The smoke-test setting should run embeddings before returning."""
        mock_embed.return_value = {'embedded_count': 0, 'dimensions': 0}

        EmbeddingService.embed_paragraphs_async(self.document)

        self.document.refresh_from_db()
        self.assertEqual(self.document.status, DocumentStatus.COMPLETED)
        mock_embed.assert_called_once_with(self.document)

    @override_settings(RUN_BACKGROUND_TASKS_SYNC=True)
    @patch('apps.document.services.ParagraphEmbeddingService.embed_document_paragraphs')
    def test_embed_failure_marks_document_and_task_failed(self, mock_embed):
        """Embedding provider failures should be persisted for UI diagnostics."""
        mock_embed.side_effect = RuntimeError('Embedding request failed. provider=http_openai_compatible')

        EmbeddingService.embed_paragraphs_async(self.document)

        self.document.refresh_from_db()
        task = DocumentProcessingTask.objects.get(document=self.document, task_type='embedding')
        self.assertEqual(self.document.status, DocumentStatus.FAILED)
        self.assertEqual(task.status, 'failed')
        self.assertIn('Embedding request failed', task.error_message)
