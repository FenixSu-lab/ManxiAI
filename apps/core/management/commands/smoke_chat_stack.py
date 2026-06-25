"""Run a local smoke test for the chat API, RAG retrieval, and debug LLM path."""

import logging
import uuid

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.test.utils import override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.chat.models import ChatMessage, ChatSession
from apps.chat.views import ChatSessionViewSet
from apps.document.models import Document, DocumentStatus, Paragraph
from apps.embedding.services import EmbeddingService
from apps.knowledge_base.models import KnowledgeBase

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Create temporary RAG data and post a chat message through the API."""

    help = 'Smoke test chat API with local hash_debug embeddings and debug LLM.'

    def add_arguments(self, parser):
        """Register command-line options."""
        parser.add_argument(
            '--keep',
            action='store_true',
            help='Keep generated smoke-test rows for inspection.',
        )

    def handle(self, *args, **options):
        """Run the chat API smoke test."""
        keep = options['keep']
        created_user = None
        logger.info('chat_smoke_start keep=%s', keep)

        try:
            with override_settings(
                EMBEDDING_PROVIDER='hash_debug',
                EMBEDDING_MODEL='hash-debug',
                EMBEDDING_DIMENSIONS=64,
                EMBEDDING_BATCH_SIZE=8,
                DEFAULT_LLM_PROVIDER='debug',
            ):
                created_user, knowledge_base, session = self._create_fixture()
                response = self._post_chat_message(created_user, session)

            if response.status_code != 201:
                raise CommandError(f'Chat API returned status_code={response.status_code} data={response.data}')

            assistant_payload = response.data['assistant_message']
            assistant_content = assistant_payload['content']
            if 'Context count: 2' not in assistant_content:
                raise CommandError(f'Debug LLM did not receive retrieval context: {assistant_content}')

            message_count = ChatMessage.objects.filter(session=session).count()
            self.stdout.write(
                self.style.SUCCESS(
                    'Chat smoke OK. '
                    f'knowledge_base_id={knowledge_base.id} session_id={session.id} '
                    f'message_count={message_count}'
                )
            )
            logger.info(
                'chat_smoke_success knowledge_base_id=%s session_id=%s message_count=%s',
                knowledge_base.id,
                session.id,
                message_count,
            )
        finally:
            if created_user and not keep:
                created_user.delete()
                logger.info('chat_smoke_cleanup user_id=%s', created_user.id)

    def _create_fixture(self):
        """Create a temporary user, knowledge base, embedded document, and chat session."""
        suffix = uuid.uuid4().hex[:12]
        user = get_user_model().objects.create_user(
            email=f'chat-smoke-{suffix}@example.com',
            username=f'chat-smoke-{suffix}',
            password='not-used',
        )
        knowledge_base = KnowledgeBase.objects.create(
            name='Chat Smoke Knowledge Base',
            description='Temporary data created by smoke_chat_stack.',
            created_by=user,
        )
        document = Document.objects.create(
            knowledge_base=knowledge_base,
            created_by=user,
            name='Chat Smoke Document',
            type='qa',
            status=DocumentStatus.PENDING,
        )
        Paragraph.objects.create(
            document=document,
            knowledge_base=knowledge_base,
            title='PostgreSQL pgvector',
            content='PostgreSQL with pgvector stores embeddings for semantic knowledge-base chat.',
            position=0,
        )
        Paragraph.objects.create(
            document=document,
            knowledge_base=knowledge_base,
            title='RAG chat',
            content='The chat endpoint retrieves paragraph context before generating an assistant answer.',
            position=1,
        )
        document.update_stats()
        EmbeddingService.embed_document_paragraphs(document)
        session = ChatSession.objects.create(
            user=user,
            title='Chat Smoke Session',
            knowledge_base=knowledge_base,
        )
        logger.info(
            'chat_smoke_fixture_created user_id=%s knowledge_base_id=%s document_id=%s session_id=%s',
            user.id,
            knowledge_base.id,
            document.id,
            session.id,
        )
        return user, knowledge_base, session

    def _post_chat_message(self, user, session):
        """Post a user message through the DRF ViewSet action."""
        view = ChatSessionViewSet.as_view({'post': 'messages'})
        request = APIRequestFactory().post(
            f'/api/v1/chat/sessions/{session.id}/messages/',
            {'role': 'user', 'content': 'How does PostgreSQL pgvector support chat retrieval?'},
            format='json',
        )
        force_authenticate(request, user=user)
        return view(request, pk=session.id)
