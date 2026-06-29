"""Views for chat APIs."""

import logging

from django.db import models
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from apps.knowledge_base.models import KnowledgeBase
from apps.knowledge_base.permissions import filter_visible, require_read
from apps.pipeline.services import RetrievalAugmentedGenerationService

from .models import ChatMessage, ChatSession, ChatShare
from .serializers import (
    ChatArchiveSerializer,
    ChatMessageCreateSerializer,
    ChatMessageSerializer,
    ChatShareSerializer,
    PublicChatShareSerializer,
    ChatSessionCreateSerializer,
    ChatSessionSerializer,
)
from .services import ChatArchiveService

logger = logging.getLogger(__name__)


class ChatSessionViewSet(viewsets.ModelViewSet):
    """Manage chat sessions and message exchange."""

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return the current user's chat sessions."""
        return ChatSession.objects.filter(user=self.request.user).select_related('knowledge_base').prefetch_related('messages')

    def get_serializer_class(self):
        """Select serializers for create versus read operations."""
        if self.action in {'create', 'update', 'partial_update'}:
            return ChatSessionCreateSerializer
        return ChatSessionSerializer

    def create(self, request, *args, **kwargs):
        """Create a session and return the full session payload."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        session = ChatSession.objects.select_related('knowledge_base').get(id=serializer.instance.id)
        return Response(ChatSessionSerializer(session).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        """Partially update a session and return the full session payload."""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        session = ChatSession.objects.select_related('knowledge_base').get(id=instance.id)
        return Response(ChatSessionSerializer(session).data)

    def perform_create(self, serializer):
        """Create a session and optionally attach a knowledge base."""
        knowledge_base = self._resolve_knowledge_base(serializer.validated_data.get('knowledge_base_id'))
        if knowledge_base is None:
            user_knowledge_bases = filter_visible(KnowledgeBase.objects.filter(is_deleted=False), self.request.user)
            if user_knowledge_bases.count() == 1:
                knowledge_base = user_knowledge_bases.first()
        title = serializer.validated_data.get('title') or 'New Chat'
        serializer.save(user=self.request.user, title=title, knowledge_base=knowledge_base)
        logger.info(
            'chat_session_created user_id=%s session_title=%s knowledge_base_id=%s',
            self.request.user.id,
            title,
            getattr(knowledge_base, 'id', None),
        )

    def perform_update(self, serializer):
        """Update session title or knowledge base association."""
        knowledge_base_id = serializer.validated_data.get('knowledge_base_id')
        knowledge_base = self._resolve_knowledge_base(knowledge_base_id) if 'knowledge_base_id' in serializer.validated_data else serializer.instance.knowledge_base
        serializer.save(knowledge_base=knowledge_base)
        logger.info(
            'chat_session_updated session_id=%s knowledge_base_id=%s',
            serializer.instance.id,
            getattr(knowledge_base, 'id', None),
        )

    def _resolve_knowledge_base(self, knowledge_base_id):
        """Resolve a knowledge base readable by the current user."""
        if not knowledge_base_id:
            return None
        knowledge_base = get_object_or_404(KnowledgeBase, id=knowledge_base_id, is_deleted=False)
        require_read(self.request.user, knowledge_base, 'attach_chat_knowledge_base')
        return knowledge_base

    @action(detail=True, methods=['get', 'post', 'delete'], url_path='messages')
    def messages(self, request, pk=None):
        """List, create, or clear messages within a session."""
        session = self.get_object()
        if session.knowledge_base:
            require_read(request.user, session.knowledge_base, 'chat_messages')

        if request.method == 'GET':
            queryset = session.messages.all()
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = ChatMessageSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = ChatMessageSerializer(queryset, many=True)
            return Response(serializer.data)

        if request.method == 'DELETE':
            deleted_count, _ = session.messages.all().delete()
            session.save(update_fields=['updated_at'])
            logger.info('chat_messages_cleared session_id=%s deleted_count=%s', session.id, deleted_count)
            return Response(status=status.HTTP_204_NO_CONTENT, data={'deleted': deleted_count})

        serializer = ChatMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            user_message = ChatMessage.objects.create(
                session=session,
                role=serializer.validated_data['role'],
                content=serializer.validated_data['content'],
            )
            history = [
                {'role': item.role, 'content': item.content}
                for item in session.messages.exclude(id=user_message.id).order_by('created_at')
            ]
            assistant_reply = RetrievalAugmentedGenerationService.generate_chat_reply(
                message=user_message.content,
                history=history,
                knowledge_base_id=str(session.knowledge_base_id) if session.knowledge_base_id else None,
            )
            assistant_message = ChatMessage.objects.create(
                session=session,
                role=ChatMessage.RoleChoices.ASSISTANT,
                content=assistant_reply,
            )
            session.save(update_fields=['updated_at'])

        logger.info(
            'chat_message_processed session_id=%s knowledge_base_id=%s user_message_length=%s assistant_message_length=%s',
            session.id,
            session.knowledge_base_id,
            len(user_message.content),
            len(assistant_message.content),
        )
        return Response(
            {
                'user_message': ChatMessageSerializer(user_message).data,
                'assistant_message': ChatMessageSerializer(assistant_message).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Preview or archive a chat session as a managed knowledge data source."""
        session = self.get_object()
        serializer = ChatArchiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        knowledge_base = self._resolve_knowledge_base(serializer.validated_data['knowledge_base_id'])
        message_ids = [str(item) for item in serializer.validated_data.get('message_ids', [])]
        if serializer.validated_data.get('preview'):
            payload = ChatArchiveService.preview(session, message_ids or None)
            return Response(payload)

        payload = ChatArchiveService.archive(
            session=session,
            knowledge_base=knowledge_base,
            user=request.user,
            name=serializer.validated_data.get('name', ''),
            message_ids=message_ids or None,
        )
        return Response(payload, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get', 'post', 'delete'])
    def share(self, request, pk=None):
        """Get, create, or revoke a public read-only share link."""
        session = self.get_object()

        if request.method == 'GET':
            share = getattr(session, 'share', None)
            if not share:
                return Response({'is_active': False})
            return Response(ChatShareSerializer(share).data)

        if request.method == 'DELETE':
            share = getattr(session, 'share', None)
            if not share:
                return Response(status=status.HTTP_204_NO_CONTENT)
            share.is_active = False
            share.save(update_fields=['is_active', 'updated_at'])
            logger.info('chat_share_revoked user_id=%s session_id=%s share_id=%s', request.user.id, session.id, share.id)
            return Response(status=status.HTTP_204_NO_CONTENT)

        share, created = ChatShare.objects.get_or_create(
            session=session,
            defaults={
                'token': ChatShare.generate_token(),
                'created_by': request.user,
                'is_active': True,
            },
        )
        if not created and not share.is_active:
            share.is_active = True
            share.save(update_fields=['is_active', 'updated_at'])
        logger.info('chat_share_enabled user_id=%s session_id=%s share_id=%s created=%s', request.user.id, session.id, share.id, created)
        return Response(ChatShareSerializer(share).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def public_chat_share(request, token):
    """Return a public read-only chat share by token."""
    share = get_object_or_404(
        ChatShare.objects.select_related('session', 'session__knowledge_base').prefetch_related('session__messages'),
        token=token,
        is_active=True,
    )
    ChatShare.objects.filter(id=share.id).update(
        view_count=models.F('view_count') + 1,
        last_viewed_at=timezone.now(),
    )
    logger.info('chat_share_viewed share_id=%s session_id=%s', share.id, share.session_id)
    return Response(PublicChatShareSerializer(share).data)
