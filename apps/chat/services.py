"""Services for converting managed chat content into knowledge data sources."""

import logging
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.document.models import Document, DocumentStatus, DocumentType, Paragraph, Problem, ProblemParagraphMapping
from apps.document.services import EmbeddingService
from apps.knowledge_base.permissions import require_write

from .models import ChatMessage, ChatSession

logger = logging.getLogger(__name__)


@dataclass
class ArchiveItem:
    """One question-answer item extracted from a chat session."""

    question: str
    answer: str
    question_message_id: str
    answer_message_id: str


class ChatArchiveService:
    """Build preview data and managed document records from chat messages."""

    @staticmethod
    def build_archive_items(session: ChatSession, message_ids: list[str] | None = None) -> list[ArchiveItem]:
        """Extract user/assistant pairs from a chat session."""
        messages = session.messages.exclude(role=ChatMessage.RoleChoices.SYSTEM).order_by('created_at')
        if message_ids:
            messages = messages.filter(id__in=message_ids)
        ordered_messages = list(messages)
        items: list[ArchiveItem] = []
        pending_user: ChatMessage | None = None

        for message in ordered_messages:
            if message.role == ChatMessage.RoleChoices.USER:
                pending_user = message
                continue
            if message.role == ChatMessage.RoleChoices.ASSISTANT and pending_user:
                items.append(
                    ArchiveItem(
                        question=pending_user.content.strip(),
                        answer=message.content.strip(),
                        question_message_id=str(pending_user.id),
                        answer_message_id=str(message.id),
                    )
                )
                pending_user = None

        if not items:
            raise ValidationError({'messages': 'No user/assistant pairs are available to archive.'})
        return items

    @staticmethod
    def preview(session: ChatSession, message_ids: list[str] | None = None) -> dict:
        """Return the archive payload without writing a document."""
        items = ChatArchiveService.build_archive_items(session, message_ids)
        logger.info('chat_archive_preview session_id=%s item_count=%s', session.id, len(items))
        return {
            'items': [
                {
                    'question': item.question,
                    'answer': item.answer,
                    'question_message_id': item.question_message_id,
                    'answer_message_id': item.answer_message_id,
                }
                for item in items
            ],
            'estimated_count': len(items),
        }

    @staticmethod
    def archive(session: ChatSession, knowledge_base, user, name: str, message_ids: list[str] | None = None) -> dict:
        """Create a managed chat archive document and enqueue embedding."""
        require_write(user, knowledge_base, 'archive_chat_to_knowledge_base')
        items = ChatArchiveService.build_archive_items(session, message_ids)
        document_name = name or f'Chat archive-{timezone.now().strftime("%Y%m%d%H%M%S")}'

        with transaction.atomic():
            document = Document.objects.create(
                knowledge_base=knowledge_base,
                created_by=user,
                name=document_name,
                type=DocumentType.CHAT_ARCHIVE,
                status=DocumentStatus.EMBEDDING,
                meta={
                    'source': 'chat_archive',
                    'chat_session_id': str(session.id),
                    'archived_by': str(user.id),
                    'message_ids': [item.question_message_id for item in items] + [item.answer_message_id for item in items],
                    'archive_mode': 'qa',
                },
            )

            for position, item in enumerate(items):
                problem = Problem.objects.create(
                    knowledge_base=knowledge_base,
                    content=item.question,
                )
                paragraph = Paragraph.objects.create(
                    document=document,
                    knowledge_base=knowledge_base,
                    title=item.question,
                    content=item.answer,
                    position=position,
                    status=DocumentStatus.PENDING,
                )
                ProblemParagraphMapping.objects.create(
                    knowledge_base=knowledge_base,
                    document=document,
                    problem=problem,
                    paragraph=paragraph,
                )

            document.update_stats()
            document.save(update_fields=['status', 'paragraph_count', 'char_length', 'updated_at'])

        logger.info(
            'chat_archived user_id=%s session_id=%s knowledge_base_id=%s document_id=%s item_count=%s',
            user.id,
            session.id,
            knowledge_base.id,
            document.id,
            len(items),
        )
        EmbeddingService.embed_paragraphs_async(document)
        return {
            'document_id': str(document.id),
            'document_type': document.type,
            'status': document.status,
            'item_count': len(items),
        }
