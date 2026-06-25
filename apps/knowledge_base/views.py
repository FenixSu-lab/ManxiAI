"""ViewSets for knowledge base management APIs."""

import logging

from django.contrib.auth import get_user_model
from django.db import models
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import KnowledgeBase, KnowledgeBaseSettings, KnowledgeBaseShare, KnowledgeBaseTag
from .serializers import (
    KnowledgeBaseCreateSerializer,
    KnowledgeBaseListSerializer,
    KnowledgeBaseSerializer,
    KnowledgeBaseSettingsSerializer,
    KnowledgeBaseShareSerializer,
    KnowledgeBaseTagSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()


class KnowledgeBaseViewSet(viewsets.ModelViewSet):
    """Manage knowledge bases and related settings for the current user."""

    queryset = KnowledgeBase.objects.filter(is_deleted=False)
    serializer_class = KnowledgeBaseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return knowledge bases owned by or shared with the current user."""
        user = self.request.user
        return self.queryset.filter(
            models.Q(created_by=user) | models.Q(shares__shared_with=user)
        ).distinct()

    def get_serializer_class(self):
        """Select a serializer for list/create/detail operations."""
        if self.action == 'list':
            return KnowledgeBaseListSerializer
        if self.action == 'create':
            return KnowledgeBaseCreateSerializer
        return KnowledgeBaseSerializer

    def create(self, request, *args, **kwargs):
        """Create a knowledge base and return the full resource payload."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        response_serializer = KnowledgeBaseSerializer(serializer.instance, context=self.get_serializer_context())
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        """Attach ownership and create default settings."""
        knowledge_base = serializer.save(created_by=self.request.user)
        KnowledgeBaseSettings.objects.get_or_create(knowledge_base=knowledge_base)
        logger.info(
            'knowledge_base_created user_id=%s knowledge_base_id=%s name=%s',
            self.request.user.id,
            knowledge_base.id,
            knowledge_base.name,
        )

    def perform_destroy(self, instance):
        """Soft-delete a knowledge base."""
        instance.soft_delete()
        logger.info('knowledge_base_deleted user_id=%s knowledge_base_id=%s', self.request.user.id, instance.id)

    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        """Share a knowledge base with another user by email."""
        knowledge_base = self.get_object()
        user_email = request.data.get('user_email')
        permission = request.data.get('permission', 'read')

        if not user_email:
            return Response({'error': 'user_email is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            shared_user = User.objects.get(email=user_email)
        except User.DoesNotExist:
            return Response({'error': 'user not found'}, status=status.HTTP_404_NOT_FOUND)

        share, _ = KnowledgeBaseShare.objects.get_or_create(
            knowledge_base=knowledge_base,
            shared_with=shared_user,
            defaults={'permission': permission},
        )
        if share.permission != permission:
            share.permission = permission
            share.save(update_fields=['permission', 'updated_at'])

        logger.info(
            'knowledge_base_shared owner_id=%s knowledge_base_id=%s shared_with_id=%s permission=%s',
            request.user.id,
            knowledge_base.id,
            shared_user.id,
            permission,
        )
        return Response(KnowledgeBaseShareSerializer(share).data)

    @action(detail=True, methods=['delete'])
    def unshare(self, request, pk=None):
        """Remove sharing for a user email."""
        knowledge_base = self.get_object()
        user_email = request.data.get('user_email')
        if not user_email:
            return Response({'error': 'user_email is required'}, status=status.HTTP_400_BAD_REQUEST)

        deleted_count, _ = KnowledgeBaseShare.objects.filter(
            knowledge_base=knowledge_base,
            shared_with__email=user_email,
        ).delete()
        if deleted_count == 0:
            return Response({'error': 'share not found'}, status=status.HTTP_404_NOT_FOUND)

        logger.info(
            'knowledge_base_unshared owner_id=%s knowledge_base_id=%s user_email=%s',
            request.user.id,
            knowledge_base.id,
            user_email,
        )
        return Response({'message': 'share removed'})

    @action(detail=True, methods=['get'])
    def shares(self, request, pk=None):
        """List sharing records for a knowledge base."""
        knowledge_base = self.get_object()
        shares = KnowledgeBaseShare.objects.filter(knowledge_base=knowledge_base).select_related('shared_with')
        return Response(KnowledgeBaseShareSerializer(shares, many=True).data)

    @action(detail=True, methods=['post'])
    def add_tag(self, request, pk=None):
        """Add a tag to a knowledge base."""
        knowledge_base = self.get_object()
        tag_name = request.data.get('name')
        tag_color = request.data.get('color', '#1890ff')
        if not tag_name:
            return Response({'error': 'name is required'}, status=status.HTTP_400_BAD_REQUEST)

        tag, created = KnowledgeBaseTag.objects.get_or_create(
            knowledge_base=knowledge_base,
            name=tag_name,
            defaults={'color': tag_color},
        )
        if not created:
            return Response({'error': 'tag already exists'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(KnowledgeBaseTagSerializer(tag).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'])
    def remove_tag(self, request, pk=None):
        """Remove a tag from a knowledge base."""
        knowledge_base = self.get_object()
        tag_name = request.data.get('name')
        if not tag_name:
            return Response({'error': 'name is required'}, status=status.HTTP_400_BAD_REQUEST)

        deleted_count, _ = KnowledgeBaseTag.objects.filter(knowledge_base=knowledge_base, name=tag_name).delete()
        if deleted_count == 0:
            return Response({'error': 'tag not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'message': 'tag removed'})

    @action(detail=True, methods=['get', 'put'])
    def kb_settings(self, request, pk=None):
        """Get or update retrieval settings for a knowledge base."""
        knowledge_base = self.get_object()
        settings_obj, _ = KnowledgeBaseSettings.objects.get_or_create(knowledge_base=knowledge_base)

        if request.method == 'GET':
            return Response(KnowledgeBaseSettingsSerializer(settings_obj).data)

        serializer = KnowledgeBaseSettingsSerializer(settings_obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logger.info('knowledge_base_settings_updated knowledge_base_id=%s', knowledge_base.id)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def update_stats(self, request, pk=None):
        """Recalculate document and chunk counters for a knowledge base."""
        knowledge_base = self.get_object()
        knowledge_base.update_stats()
        serializer = KnowledgeBaseSerializer(knowledge_base, context=self.get_serializer_context())
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def public(self, request):
        """List public knowledge bases."""
        public_kbs = KnowledgeBase.objects.filter(is_public=True, is_deleted=False)
        serializer = KnowledgeBaseListSerializer(public_kbs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def shared_with_me(self, request):
        """List knowledge bases shared with the current user."""
        shared_kbs = KnowledgeBase.objects.filter(shares__shared_with=request.user, is_deleted=False).distinct()
        serializer = KnowledgeBaseListSerializer(shared_kbs, many=True)
        return Response(serializer.data)
