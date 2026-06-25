"""
文档管理序列化器
"""
from rest_framework import serializers
from django.db import transaction
from .models import Document, Paragraph, Problem, ProblemParagraphMapping, DocumentProcessingTask, DocumentType, DocumentStatus, HitHandlingMethod
from django.db import models


class ParagraphSerializer(serializers.ModelSerializer):
    """段落序列化器"""
    
    class Meta:
        model = Paragraph
        fields = [
            'id', 'title', 'content', 'char_length', 'status', 'is_active',
            'hit_count', 'last_hit_time', 'position', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'char_length', 'hit_count', 'last_hit_time', 'created_at', 'updated_at']


class ProblemSerializer(serializers.ModelSerializer):
    """问题序列化器"""
    
    class Meta:
        model = Problem
        fields = [
            'id', 'content', 'hit_count', 'last_hit_time', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'hit_count', 'last_hit_time', 'created_at', 'updated_at']


class DocumentListSerializer(serializers.ModelSerializer):
    """文档列表序列化器"""
    knowledge_base_id = serializers.UUIDField(source='knowledge_base.id', read_only=True)
    knowledge_base_name = serializers.CharField(source='knowledge_base.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    latest_error = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = [
            'id', 'name', 'type', 'type_display', 'status', 'status_display',
            'file_size', 'char_length', 'paragraph_count', 'hit_count',
            'knowledge_base_id', 'knowledge_base_name', 'latest_error', 'created_at', 'updated_at'
        ]

    def get_latest_error(self, obj):
        """Return the latest processing error for failed documents."""
        if obj.status != DocumentStatus.FAILED:
            return ''
        task = obj.processing_tasks.filter(status='failed').order_by('-updated_at').first()
        return task.error_message if task else ''


class DocumentDetailSerializer(serializers.ModelSerializer):
    """文档详情序列化器"""
    knowledge_base_name = serializers.CharField(source='knowledge_base.name', read_only=True)
    paragraphs = ParagraphSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    latest_error = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = [
            'id', 'name', 'type', 'type_display', 'status', 'status_display',
            'file_path', 'file_size', 'char_length', 'paragraph_count',
            'hit_handling_method', 'directly_return_similarity', 'meta',
            'hit_count', 'last_hit_time', 'knowledge_base_id', 'knowledge_base_name', 'paragraphs',
            'latest_error', 'created_at', 'updated_at'
        ]

    def get_latest_error(self, obj):
        """Return the latest processing error for failed documents."""
        if obj.status != DocumentStatus.FAILED:
            return ''
        task = obj.processing_tasks.filter(status='failed').order_by('-updated_at').first()
        return task.error_message if task else ''


class DocumentCreateSerializer(serializers.ModelSerializer):
    """文档创建序列化器"""
    paragraphs = ParagraphSerializer(many=True, required=False)
    
    class Meta:
        model = Document
        fields = [
            'name', 'type', 'file_path', 'file_size', 'hit_handling_method',
            'directly_return_similarity', 'meta', 'paragraphs'
        ]
    
    def create(self, validated_data):
        paragraphs_data = validated_data.pop('paragraphs', [])
        knowledge_base = self.context['knowledge_base']
        created_by = self.context['request'].user
        
        with transaction.atomic():
            # 创建文档
            document = Document.objects.create(
                knowledge_base=knowledge_base,
                created_by=created_by,
                **validated_data
            )
            
            # 创建段落
            for i, paragraph_data in enumerate(paragraphs_data):
                Paragraph.objects.create(
                    document=document,
                    knowledge_base=knowledge_base,
                    position=i,
                    **paragraph_data
                )
            
            # 更新统计信息
            document.update_stats()
            
        return document


class DocumentUpdateSerializer(serializers.ModelSerializer):
    """文档更新序列化器"""
    
    class Meta:
        model = Document
        fields = [
            'name', 'hit_handling_method', 'directly_return_similarity', 'meta'
        ]


class DocumentUploadSerializer(serializers.Serializer):
    """文档上传序列化器"""
    file = serializers.FileField()
    name = serializers.CharField(max_length=255, required=False)
    type = serializers.ChoiceField(choices=DocumentType.choices, required=False)
    hit_handling_method = serializers.ChoiceField(
        choices=HitHandlingMethod.choices,
        default=HitHandlingMethod.OPTIMIZATION
    )
    directly_return_similarity = serializers.FloatField(default=0.9, min_value=0.0, max_value=1.0)
    
    def validate_file(self, value):
        """验证文件"""
        # 检查文件大小 (50MB)
        if value.size > 50 * 1024 * 1024:
            raise serializers.ValidationError("文件大小不能超过50MB")
        
        # 检查文件类型
        allowed_types = [
            'application/pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/msword',
            'text/plain',
            'text/markdown',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        ]
        
        if value.content_type not in allowed_types:
            raise serializers.ValidationError("不支持的文件类型")
        
        return value


class DocumentProcessingTaskSerializer(serializers.ModelSerializer):
    """文档处理任务序列化器"""
    
    class Meta:
        model = DocumentProcessingTask
        fields = [
            'id', 'task_type', 'status', 'progress', 'error_message',
            'result', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DocumentBatchSerializer(serializers.Serializer):
    """文档批量操作序列化器"""
    document_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=100
    )
    action = serializers.ChoiceField(choices=[
        ('delete', '删除'),
        ('activate', '激活'),
        ('deactivate', '停用'),
        ('reprocess', '重新处理'),
    ])
    
    def validate_document_ids(self, value):
        """验证文档ID"""
        knowledge_base = self.context['knowledge_base']
        existing_ids = Document.objects.filter(
            knowledge_base=knowledge_base,
            id__in=value,
            is_deleted=False
        ).values_list('id', flat=True)
        
        if len(existing_ids) != len(value):
            raise serializers.ValidationError("部分文档不存在或已删除")
        
        return value


class WebDocumentSerializer(serializers.Serializer):
    """Web文档序列化器"""
    url = serializers.URLField()
    name = serializers.CharField(max_length=255, required=False)
    selector = serializers.CharField(max_length=500, required=False)
    depth = serializers.IntegerField(default=1, min_value=1, max_value=3)
    
    def validate_url(self, value):
        """验证URL"""
        if not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("URL必须以http://或https://开头")
        return value


class QADocumentSerializer(serializers.Serializer):
    """问答文档序列化器"""
    qa_pairs = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField()),
        min_length=1,
        max_length=1000
    )
    name = serializers.CharField(max_length=255, required=False)
    
    def validate_qa_pairs(self, value):
        """验证问答对"""
        for i, pair in enumerate(value):
            if 'question' not in pair or 'answer' not in pair:
                raise serializers.ValidationError(f"第{i+1}个问答对缺少question或answer字段")
            
            if not pair['question'].strip() or not pair['answer'].strip():
                raise serializers.ValidationError(f"第{i+1}个问答对的问题或答案不能为空")
        
        return value


class DocumentSearchSerializer(serializers.Serializer):
    """文档搜索序列化器"""
    query = serializers.CharField(max_length=500)
    type = serializers.ChoiceField(choices=DocumentType.choices, required=False)
    status = serializers.ChoiceField(choices=DocumentStatus.choices, required=False)
    page = serializers.IntegerField(default=1, min_value=1)
    page_size = serializers.IntegerField(default=20, min_value=1, max_value=100)
    
    def validate_query(self, value):
        """验证查询条件"""
        if len(value.strip()) < 2:
            raise serializers.ValidationError("查询条件至少需要2个字符")
        return value.strip()


class DocumentStatsSerializer(serializers.Serializer):
    """文档统计序列化器"""
    total_documents = serializers.IntegerField()
    total_paragraphs = serializers.IntegerField()
    total_characters = serializers.IntegerField()
    by_type = serializers.DictField()
    by_status = serializers.DictField()
    recent_uploads = serializers.ListField()
    
    def to_representation(self, instance):
        """自定义序列化"""
        knowledge_base = instance
        
        # 基础统计
        documents = Document.objects.filter(knowledge_base=knowledge_base, is_deleted=False)
        paragraphs = Paragraph.objects.filter(knowledge_base=knowledge_base)
        
        stats = {
            'total_documents': documents.count(),
            'total_paragraphs': paragraphs.count(),
            'total_characters': documents.aggregate(
                total=models.Sum('char_length')
            )['total'] or 0,
        }
        
        # 按类型统计
        stats['by_type'] = dict(
            documents.values('type').annotate(
                count=models.Count('id')
            ).values_list('type', 'count')
        )
        
        # 按状态统计
        stats['by_status'] = dict(
            documents.values('status').annotate(
                count=models.Count('id')
            ).values_list('status', 'count')
        )
        
        # 最近上传
        stats['recent_uploads'] = DocumentListSerializer(
            documents.order_by('-created_at')[:10],
            many=True
        ).data
        
        return stats 
