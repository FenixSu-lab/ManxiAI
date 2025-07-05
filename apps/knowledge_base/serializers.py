"""
知识库管理序列化器
"""
from rest_framework import serializers
from .models import KnowledgeBase, KnowledgeBaseShare, KnowledgeBaseTag, KnowledgeBaseSettings


class KnowledgeBaseSerializer(serializers.ModelSerializer):
    """
    知识库序列化器
    """
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    tags = serializers.StringRelatedField(many=True, read_only=True)
    
    class Meta:
        model = KnowledgeBase
        fields = [
            'id', 'name', 'description', 'icon', 'status', 'is_public',
            'chunk_size', 'chunk_overlap', 'similarity_threshold', 'top_k',
            'documents_count', 'chunks_count', 'total_size',
            'created_by', 'created_by_name', 'created_at', 'updated_at',
            'tags'
        ]
        read_only_fields = [
            'id', 'created_by', 'created_by_name', 'created_at', 'updated_at',
            'documents_count', 'chunks_count', 'total_size'
        ]
    
    def validate_name(self, value):
        """验证知识库名称唯一性"""
        user = self.context['request'].user
        if KnowledgeBase.objects.filter(
            name=value,
            created_by=user,
            is_deleted=False
        ).exclude(id=self.instance.id if self.instance else None).exists():
            raise serializers.ValidationError("知识库名称已存在")
        return value


class KnowledgeBaseShareSerializer(serializers.ModelSerializer):
    """
    知识库分享序列化器
    """
    shared_with_name = serializers.CharField(source='shared_with.username', read_only=True)
    shared_with_email = serializers.CharField(source='shared_with.email', read_only=True)
    knowledge_base_name = serializers.CharField(source='knowledge_base.name', read_only=True)
    
    class Meta:
        model = KnowledgeBaseShare
        fields = [
            'id', 'knowledge_base', 'knowledge_base_name',
            'shared_with', 'shared_with_name', 'shared_with_email',
            'permission', 'permissions', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'knowledge_base_name', 'shared_with_name', 'shared_with_email',
            'created_at', 'updated_at'
        ]


class KnowledgeBaseTagSerializer(serializers.ModelSerializer):
    """
    知识库标签序列化器
    """
    class Meta:
        model = KnowledgeBaseTag
        fields = ['id', 'name', 'color', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class KnowledgeBaseSettingsSerializer(serializers.ModelSerializer):
    """
    知识库设置序列化器
    """
    class Meta:
        model = KnowledgeBaseSettings
        fields = [
            'id', 'auto_index', 'index_schedule', 'search_mode',
            'enable_rerank', 'rerank_model', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class KnowledgeBaseListSerializer(serializers.ModelSerializer):
    """
    知识库列表序列化器（简化版）
    """
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = KnowledgeBase
        fields = [
            'id', 'name', 'description', 'icon', 'status', 'is_public',
            'documents_count', 'chunks_count', 'total_size',
            'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_by_name', 'created_at', 'updated_at',
            'documents_count', 'chunks_count', 'total_size'
        ]


class KnowledgeBaseCreateSerializer(serializers.ModelSerializer):
    """
    创建知识库序列化器
    """
    class Meta:
        model = KnowledgeBase
        fields = [
            'name', 'description', 'icon', 'is_public',
            'chunk_size', 'chunk_overlap', 'similarity_threshold', 'top_k'
        ]
    
    def validate_name(self, value):
        """验证知识库名称唯一性"""
        user = self.context['request'].user
        if KnowledgeBase.objects.filter(
            name=value,
            created_by=user,
            is_deleted=False
        ).exists():
            raise serializers.ValidationError("知识库名称已存在")
        return value 