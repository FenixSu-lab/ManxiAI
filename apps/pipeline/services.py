"""RAG pipeline services for retrieval-augmented chat."""

import logging

from apps.embedding.services import VectorSearchService
from apps.model_management.ai_service import AIServiceFactory

logger = logging.getLogger(__name__)


class RetrievalAugmentedGenerationService:
    """Combine vector retrieval with LLM generation for chat replies."""

    @staticmethod
    def build_context(message: str, knowledge_base_id: str, top_k: int = 5) -> list[str]:
        """Retrieve relevant paragraph snippets for a knowledge base."""
        if not knowledge_base_id:
            return []

        results = VectorSearchService.search_paragraphs(message, knowledge_base_id, top_k=top_k)
        context = [item['content'] for item in results]
        logger.info(
            'rag_context_built knowledge_base_id=%s query_length=%s context_count=%s',
            knowledge_base_id,
            len(message),
            len(context),
        )
        return context

    @staticmethod
    def generate_chat_reply(message: str, history: list[dict], knowledge_base_id: str | None = None) -> str:
        """Generate an assistant reply with optional retrieval context."""
        context = RetrievalAugmentedGenerationService.build_context(message, knowledge_base_id) if knowledge_base_id else []
        llm_service = AIServiceFactory.get_service()
        reply = llm_service.chat_with_history(
            message=message,
            history=history,
            context=context,
        )
        logger.info(
            'rag_reply_generated knowledge_base_id=%s history_count=%s context_count=%s reply_length=%s',
            knowledge_base_id,
            len(history),
            len(context),
            len(reply),
        )
        return reply
