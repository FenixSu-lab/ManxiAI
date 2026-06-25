"""Unit tests for RAG pipeline services."""

from unittest.mock import patch

from django.test import SimpleTestCase

from apps.pipeline.services import RetrievalAugmentedGenerationService


class RetrievalAugmentedGenerationServiceTests(SimpleTestCase):
    """Verify retrieval context is passed into response generation."""

    @patch('apps.pipeline.services.VectorSearchService.search_paragraphs')
    def test_build_context_extracts_content(self, mock_search):
        """Context building should keep only paragraph content strings."""
        mock_search.return_value = [
            {'content': 'first paragraph'},
            {'content': 'second paragraph'},
        ]

        context = RetrievalAugmentedGenerationService.build_context('question', 'kb-1', top_k=2)

        self.assertEqual(context, ['first paragraph', 'second paragraph'])

    @patch('apps.pipeline.services.AIServiceFactory.get_service')
    @patch('apps.pipeline.services.VectorSearchService.search_paragraphs')
    def test_generate_chat_reply_passes_retrieved_context(self, mock_search, mock_get_service):
        """The generated reply should use the retrieved knowledge base context."""
        mock_search.return_value = [{'content': 'retrieved paragraph'}]
        mock_llm = mock_get_service.return_value
        mock_llm.chat_with_history.return_value = 'assistant reply'

        reply = RetrievalAugmentedGenerationService.generate_chat_reply(
            message='question',
            history=[{'role': 'user', 'content': 'history'}],
            knowledge_base_id='kb-1',
        )

        self.assertEqual(reply, 'assistant reply')
        mock_llm.chat_with_history.assert_called_once_with(
            message='question',
            history=[{'role': 'user', 'content': 'history'}],
            context=['retrieved paragraph'],
        )
