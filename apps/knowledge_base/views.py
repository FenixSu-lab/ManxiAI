"""
知识库管理视图
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db import models
from .models import KnowledgeBase, KnowledgeBaseShare, KnowledgeBaseTag, KnowledgeBaseSettings
from .serializers import (
    KnowledgeBaseSerializer, KnowledgeBaseListSerializer, KnowledgeBaseCreateSerializer,
    KnowledgeBaseShareSerializer, KnowledgeBaseTagSerializer, KnowledgeBaseSettingsSerializer
)

User = get_user_model()


class KnowledgeBaseViewSet(viewsets.ModelViewSet):
    """
    知识库管理视图集
    """
    queryset = KnowledgeBase.objects.filter(is_deleted=False)
    serializer_class = KnowledgeBaseSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """
        获取用户有权限访问的知识库
        """
        user = self.request.user
        # 用户创建的知识库 + 分享给用户的知识库
        return self.queryset.filter(
            models.Q(created_by=user) | 
            models.Q(shares__shared_with=user)
        ).distinct()
    
    def get_serializer_class(self):
        """
        根据action选择序列化器
        """
        if self.action == 'list':
            return KnowledgeBaseListSerializer
        elif self.action == 'create':
            return KnowledgeBaseCreateSerializer
        return KnowledgeBaseSerializer
    
    def perform_create(self, serializer):
        """
        创建知识库时设置创建者
        """
        kb = serializer.save(created_by=self.request.user)
        # 创建默认设置
        KnowledgeBaseSettings.objects.create(knowledge_base=kb)
    
    def perform_destroy(self, instance):
        """
        软删除知识库
        """
        instance.soft_delete()
    
    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        """
        分享知识库
        """
        kb = self.get_object()
        user_email = request.data.get('user_email')
        permission = request.data.get('permission', 'read')
        
        if not user_email:
            return Response({'error': '用户邮箱不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=user_email)
        except User.DoesNotExist:
            return Response({'error': '用户不存在'}, status=status.HTTP_404_NOT_FOUND)
        
        # 检查是否已经分享
        share, created = KnowledgeBaseShare.objects.get_or_create(
            knowledge_base=kb,
            shared_with=user,
            defaults={'permission': permission}
        )
        
        if not created:
            share.permission = permission
            share.save()
        
        serializer = KnowledgeBaseShareSerializer(share)
        return Response(serializer.data)
    
    @action(detail=True, methods=['delete'])
    def unshare(self, request, pk=None):
        """
        取消分享知识库
        """
        kb = self.get_object()
        user_email = request.data.get('user_email')
        
        if not user_email:
            return Response({'error': '用户邮箱不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=user_email)
            share = KnowledgeBaseShare.objects.get(knowledge_base=kb, shared_with=user)
            share.delete()
            return Response({'message': '取消分享成功'})
        except (User.DoesNotExist, KnowledgeBaseShare.DoesNotExist):
            return Response({'error': '分享记录不存在'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['get'])
    def shares(self, request, pk=None):
        """
        获取知识库分享列表
        """
        kb = self.get_object()
        shares = KnowledgeBaseShare.objects.filter(knowledge_base=kb)
        serializer = KnowledgeBaseShareSerializer(shares, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_tag(self, request, pk=None):
        """
        添加标签
        """
        kb = self.get_object()
        tag_name = request.data.get('name')
        tag_color = request.data.get('color', '#1890ff')
        
        if not tag_name:
            return Response({'error': '标签名称不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        
        tag, created = KnowledgeBaseTag.objects.get_or_create(
            knowledge_base=kb,
            name=tag_name,
            defaults={'color': tag_color}
        )
        
        if not created:
            return Response({'error': '标签已存在'}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = KnowledgeBaseTagSerializer(tag)
        return Response(serializer.data)
    
    @action(detail=True, methods=['delete'])
    def remove_tag(self, request, pk=None):
        """
        移除标签
        """
        kb = self.get_object()
        tag_name = request.data.get('name')
        
        if not tag_name:
            return Response({'error': '标签名称不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            tag = KnowledgeBaseTag.objects.get(knowledge_base=kb, name=tag_name)
            tag.delete()
            return Response({'message': '标签删除成功'})
        except KnowledgeBaseTag.DoesNotExist:
            return Response({'error': '标签不存在'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['get', 'put'])
    def settings(self, request, pk=None):
        """
        获取或更新知识库设置
        """
        kb = self.get_object()
        settings, created = KnowledgeBaseSettings.objects.get_or_create(knowledge_base=kb)
        
        if request.method == 'GET':
            serializer = KnowledgeBaseSettingsSerializer(settings)
            return Response(serializer.data)
        elif request.method == 'PUT':
            serializer = KnowledgeBaseSettingsSerializer(settings, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def update_stats(self, request, pk=None):
        """
        更新知识库统计信息
        """
        kb = self.get_object()
        kb.update_stats()
        serializer = self.get_serializer(kb)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def public(self, request):
        """
        获取公开的知识库
        """
        public_kbs = KnowledgeBase.objects.filter(is_public=True, is_deleted=False)
        serializer = KnowledgeBaseListSerializer(public_kbs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def shared_with_me(self, request):
        """
        获取分享给我的知识库
        """
        shares = KnowledgeBaseShare.objects.filter(shared_with=request.user)
        kbs = [share.knowledge_base for share in shares]
        serializer = KnowledgeBaseListSerializer(kbs, many=True)
        return Response(serializer.data) 