"""Run an API-level smoke test for the knowledge-base RAG chat workflow."""

import logging
import time
import uuid

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.test.utils import override_settings
from rest_framework.test import APIClient

from apps.document.models import Document
from apps.embedding.models import ParagraphEmbedding

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Exercise the same API URLs used by the frontend RAG workflow."""

    help = 'Smoke test auth settings, KB creation, QA document creation, embedding, chat session, and message APIs.'

    def add_arguments(self, parser):
        """Register command-line options."""
        parser.add_argument(
            '--keep',
            action='store_true',
            help='Keep generated smoke-test rows for inspection.',
        )
        parser.add_argument(
            '--timeout',
            type=float,
            default=10.0,
            help='Maximum seconds to wait for background embedding.',
        )
        parser.add_argument(
            '--real-embedding',
            action='store_true',
            help='Use the configured embedding provider instead of hash_debug; the LLM still uses debug.',
        )

    def handle(self, *args, **options):
        """Run the API-level smoke test."""
        keep = options['keep']
        timeout = options['timeout']
        real_embedding = options['real_embedding']
        user = self._create_user()
        client = APIClient()
        client.force_authenticate(user=user)
        logger.info(
            'api_smoke_start user_id=%s keep=%s timeout=%s real_embedding=%s',
            user.id,
            keep,
            timeout,
            real_embedding,
        )

        try:
            override_values = {
                'DEFAULT_LLM_PROVIDER': 'debug',
                'RUN_BACKGROUND_TASKS_SYNC': True,
                'ALLOWED_HOSTS': list({*settings.ALLOWED_HOSTS, 'testserver'}),
            }
            if not real_embedding:
                override_values.update(
                    {
                        'EMBEDDING_PROVIDER': 'hash_debug',
                        'EMBEDDING_MODEL': 'hash-debug',
                        'EMBEDDING_DIMENSIONS': 64,
                        'EMBEDDING_BATCH_SIZE': 8,
                    }
                )

            with override_settings(**override_values):
                self._exercise_account_settings(client, user)
                self._exercise_team_management(client)
                knowledge_base_id = self._create_knowledge_base(client)
                document_id = self._create_qa_document(client, knowledge_base_id)
                self._wait_for_embeddings(document_id, timeout)
                session_id = self._create_chat_session(client, knowledge_base_id)
                reply = self._post_chat_message(client, session_id)

            if 'Context count:' not in reply:
                raise CommandError(f'Debug LLM reply did not include context metadata: {reply}')

            self.stdout.write(
                self.style.SUCCESS(
                    'API smoke OK. '
                    f'knowledge_base_id={knowledge_base_id} document_id={document_id} session_id={session_id}'
                )
            )
            logger.info(
                'api_smoke_success user_id=%s knowledge_base_id=%s document_id=%s session_id=%s real_embedding=%s',
                user.id,
                knowledge_base_id,
                document_id,
                session_id,
                real_embedding,
            )
        finally:
            if not keep:
                user.delete()
                logger.info('api_smoke_cleanup user_id=%s', user.id)

    def _create_user(self):
        """Create a temporary authenticated API user."""
        suffix = uuid.uuid4().hex[:12]
        return get_user_model().objects.create_user(
            email=f'api-smoke-{suffix}@example.com',
            username=f'api-smoke-{suffix}',
            password='not-used',
        )

    def _create_knowledge_base(self, client: APIClient) -> str:
        """Create a knowledge base through the public API route."""
        response = client.post(
            '/api/v1/knowledge-bases/',
            {
                'name': f'API Smoke KB {uuid.uuid4().hex[:8]}',
                'description': 'Temporary knowledge base created by smoke_api_stack.',
            },
            format='json',
        )
        self._ensure_success(response, expected_status=201, step='create knowledge base')
        knowledge_base_id = str(response.data['id'])
        logger.info('api_smoke_kb_created knowledge_base_id=%s', knowledge_base_id)
        return knowledge_base_id

    def _exercise_account_settings(self, client: APIClient, user) -> None:
        """Exercise the profile and API-key routes used by the settings page."""
        expected_username = f'{user.username}-settings'
        profile_response = client.put(
            '/api/v1/auth/users/me/',
            {
                'email': user.email,
                'username': expected_username,
                'first_name': 'Smoke',
                'last_name': 'User',
            },
            format='json',
        )
        self._ensure_success(profile_response, expected_status=200, step='update account profile')
        if profile_response.data['username'] != expected_username:
            raise CommandError(f'Profile update returned unexpected username: {profile_response.data}')

        key_response = client.post(
            '/api/v1/auth/api-keys/',
            {'name': 'Smoke API Key'},
            format='json',
        )
        self._ensure_success(key_response, expected_status=201, step='create API key')
        api_key_id = str(key_response.data['id'])
        if not key_response.data.get('key'):
            raise CommandError('API key creation did not return a key value.')

        regenerate_response = client.post(f'/api/v1/auth/api-keys/{api_key_id}/regenerate/', format='json')
        self._ensure_success(regenerate_response, expected_status=200, step='regenerate API key')
        if not regenerate_response.data.get('key'):
            raise CommandError('API key regeneration did not return a key value.')

        delete_response = client.delete(f'/api/v1/auth/api-keys/{api_key_id}/')
        self._ensure_success(delete_response, expected_status=204, step='delete API key')
        logger.info('api_smoke_account_settings_ok user_id=%s api_key_id=%s', user.id, api_key_id)

    def _exercise_team_management(self, client: APIClient) -> None:
        """Exercise team create, add-member, and remove-member routes."""
        member_user = self._create_user()
        try:
            team_response = client.post(
                '/api/v1/auth/teams/',
                {
                    'name': f'API Smoke Team {uuid.uuid4().hex[:8]}',
                    'description': 'Temporary team created by smoke_api_stack.',
                },
                format='json',
            )
            self._ensure_success(team_response, expected_status=201, step='create team')
            team_id = str(team_response.data['id'])

            add_response = client.post(
                f'/api/v1/auth/teams/{team_id}/add_member/',
                {
                    'user_id': str(member_user.id),
                    'role': 'member',
                },
                format='json',
            )
            self._ensure_success(add_response, expected_status=200, step='add team member')

            remove_response = client.delete(
                f'/api/v1/auth/teams/{team_id}/remove_member/',
                {'user_id': str(member_user.id)},
                format='json',
            )
            self._ensure_success(remove_response, expected_status=200, step='remove team member')
            logger.info('api_smoke_team_management_ok team_id=%s member_user_id=%s', team_id, member_user.id)
        finally:
            member_user.delete()

    def _create_qa_document(self, client: APIClient, knowledge_base_id: str) -> str:
        """Create a QA document through the public API route."""
        response = client.post(
            f'/api/v1/knowledge-bases/{knowledge_base_id}/documents/create-qa/',
            {
                'name': 'API Smoke QA',
                'qa_pairs': [
                    {
                        'question': 'How does pgvector support RAG?',
                        'answer': 'pgvector stores paragraph embeddings and supports similarity search.',
                    },
                    {
                        'question': 'How does chat use a knowledge base?',
                        'answer': 'The chat endpoint retrieves relevant paragraph context before generating a reply.',
                    },
                ],
            },
            format='json',
        )
        self._ensure_success(response, expected_status=201, step='create QA document')
        document_id = str(response.data['id'])
        logger.info('api_smoke_qa_created knowledge_base_id=%s document_id=%s', knowledge_base_id, document_id)
        return document_id

    def _wait_for_embeddings(self, document_id: str, timeout: float) -> None:
        """Wait for async QA embedding to write vectors for the generated document."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            embedding_count = ParagraphEmbedding.objects.filter(paragraph__document_id=document_id).count()
            if embedding_count >= 2:
                logger.info('api_smoke_embeddings_ready document_id=%s embedding_count=%s', document_id, embedding_count)
                return
            time.sleep(0.1)

        document = Document.objects.filter(id=document_id).first()
        status = getattr(document, 'status', '<missing>')
        raise CommandError(f'Embedding did not complete for document_id={document_id}; status={status}')

    def _create_chat_session(self, client: APIClient, knowledge_base_id: str) -> str:
        """Create a chat session through the public API route."""
        response = client.post(
            '/api/v1/chat/sessions/',
            {
                'title': 'API Smoke Chat',
                'knowledge_base_id': knowledge_base_id,
            },
            format='json',
        )
        self._ensure_success(response, expected_status=201, step='create chat session')
        session_id = str(response.data['id'])
        logger.info('api_smoke_session_created knowledge_base_id=%s session_id=%s', knowledge_base_id, session_id)
        return session_id

    def _post_chat_message(self, client: APIClient, session_id: str) -> str:
        """Post a chat message through the public API route and return assistant content."""
        response = client.post(
            f'/api/v1/chat/sessions/{session_id}/messages/',
            {
                'role': 'user',
                'content': 'How does pgvector support RAG chat?',
            },
            format='json',
        )
        self._ensure_success(response, expected_status=201, step='post chat message')
        assistant_content = response.data['assistant_message']['content']
        logger.info(
            'api_smoke_message_posted session_id=%s assistant_reply_length=%s',
            session_id,
            len(assistant_content),
        )
        return assistant_content

    @staticmethod
    def _ensure_success(response, expected_status: int, step: str) -> None:
        """Raise a useful command error when an API call fails."""
        if response.status_code != expected_status:
            data = getattr(response, 'data', None)
            if data is None:
                data = response.content.decode('utf-8', errors='replace')[:500]
            raise CommandError(
                f'API smoke failed during {step}: status={response.status_code} data={data}'
            )
