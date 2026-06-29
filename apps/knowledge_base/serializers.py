"""
知识库管理序列化器
"""
from rest_framework import serializers
from .models import KnowledgeBase, KnowledgeBaseShare, KnowledgeBaseTag, KnowledgeBaseSettings
from .permissions import can_write, get_user_role, is_owner


class KnowledgeBaseSerializer(serializers.ModelSerializer):
    """
    知识库序列化器
    """
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    tags = serializers.StringRelatedField(many=True, read_only=True)
    user_role = serializers.SerializerMethodField()
    can_write = serializers.SerializerMethodField()
    can_manage = serializers.SerializerMethodField()
    
    class Meta:
        model = KnowledgeBase
        fields = [
            'id', 'name', 'description', 'icon', 'status', 'is_public',
            'chunk_size', 'chunk_overlap', 'similarity_threshold', 'top_k',
            'documents_count', 'chunks_count', 'total_size',
            'created_by', 'created_by_name', 'created_at', 'updated_at',
            'tags', 'user_role', 'can_write', 'can_manage'
        ]
        read_only_fields = [
            'id', 'created_by', 'created_by_name', 'created_at', 'updated_at',
            'documents_count', 'chunks_count', 'total_size'
        ]

    def get_user_role(self, obj):
        """Return the current user's effective role on this knowledge base."""
        request = self.context.get('request')
        return get_user_role(request.user, obj) if request else 'none'

    def get_can_write(self, obj):
        """Return whether the current user can maintain data sources."""
        request = self.context.get('request')
        return can_write(request.user, obj) if request else False

    def get_can_manage(self, obj):
        """Return whether the current user can manage permissions/settings."""
        request = self.context.get('request')
        return is_owner(request.user, obj) if request else False
    
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
    user_role = serializers.SerializerMethodField()
    can_write = serializers.SerializerMethodField()
    can_manage = serializers.SerializerMethodField()
    
    class Meta:
        model = KnowledgeBase
        fields = [
            'id', 'name', 'description', 'icon', 'status', 'is_public',
            'documents_count', 'chunks_count', 'total_size',
            'created_by_name', 'created_at', 'updated_at',
            'user_role', 'can_write', 'can_manage'
        ]
        read_only_fields = [
            'id', 'created_by_name', 'created_at', 'updated_at',
            'documents_count', 'chunks_count', 'total_size'
        ]

    def get_user_role(self, obj):
        """Return the current user's effective role on this knowledge base."""
        request = self.context.get('request')
        return get_user_role(request.user, obj) if request else 'none'

    def get_can_write(self, obj):
        """Return whether the current user can maintain data sources."""
        request = self.context.get('request')
        return can_write(request.user, obj) if request else False

    def get_can_manage(self, obj):
        """Return whether the current user can manage permissions/settings."""
        request = self.context.get('request')
        return is_owner(request.user, obj) if request else False


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
