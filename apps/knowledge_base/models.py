"""
知识库管理模型
"""
from django.db import models
from django.contrib.auth import get_user_model
from apps.core.models import BaseModel, UserRelatedModel, SoftDeleteModel, StatusChoices

User = get_user_model()


class KnowledgeBase(UserRelatedModel, SoftDeleteModel):
    """
    知识库模型
    """
    name = models.CharField(max_length=100, verbose_name='知识库名称')
    description = models.TextField(blank=True, null=True, verbose_name='描述')
    icon = models.CharField(max_length=200, blank=True, null=True, verbose_name='图标')
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.ACTIVE,
        verbose_name='状态'
    )
    is_public = models.BooleanField(default=False, verbose_name='是否公开')
    
    # 知识库配置
    chunk_size = models.IntegerField(default=1000, verbose_name='分块大小')
    chunk_overlap = models.IntegerField(default=200, verbose_name='分块重叠')
    similarity_threshold = models.FloatField(default=0.7, verbose_name='相似度阈值')
    top_k = models.IntegerField(default=5, verbose_name='返回数量')
    
    # 统计信息
    documents_count = models.IntegerField(default=0, verbose_name='文档数量')
    chunks_count = models.IntegerField(default=0, verbose_name='分块数量')
    total_size = models.BigIntegerField(default=0, verbose_name='总大小(字节)')
    
    class Meta:
        db_table = 'knowledge_bases'
        verbose_name = '知识库'
        verbose_name_plural = '知识库'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def update_stats(self):
        """更新统计信息"""
        from apps.document.models import Document
        documents = Document.objects.filter(knowledge_base=self, is_deleted=False)
        self.documents_count = documents.count()
        self.chunks_count = sum(doc.chunks_count for doc in documents)
        self.total_size = sum(doc.file_size for doc in documents)
        self.save()


class KnowledgeBaseShare(BaseModel):
    """
    知识库分享模型
    """
    knowledge_base = models.ForeignKey(
        KnowledgeBase,
        on_delete=models.CASCADE,
        related_name='shares',
        verbose_name='知识库'
    )
    shared_with = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shared_knowledge_bases',
        verbose_name='分享给'
    )
    permissions = models.JSONField(default=dict, verbose_name='权限')
    
    class PermissionChoices(models.TextChoices):
        READ = 'read', '只读'
        WRITE = 'write', '读写'
        ADMIN = 'admin', '管理'
    
    permission = models.CharField(
        max_length=20,
        choices=PermissionChoices.choices,
        default=PermissionChoices.READ,
        verbose_name='权限级别'
    )
    
    class Meta:
        db_table = 'knowledge_base_shares'
        unique_together = ['knowledge_base', 'shared_with']
        verbose_name = '知识库分享'
        verbose_name_plural = '知识库分享'
    
    def __str__(self):
        return f"{self.knowledge_base.name} -> {self.shared_with.email}"


class KnowledgeBaseTag(BaseModel):
    """
    知识库标签模型
    """
    knowledge_base = models.ForeignKey(
        KnowledgeBase,
        on_delete=models.CASCADE,
        related_name='tags',
        verbose_name='知识库'
    )
    name = models.CharField(max_length=50, verbose_name='标签名称')
    color = models.CharField(max_length=20, default='#1890ff', verbose_name='标签颜色')
    
    class Meta:
        db_table = 'knowledge_base_tags'
        unique_together = ['knowledge_base', 'name']
        verbose_name = '知识库标签'
        verbose_name_plural = '知识库标签'
    
    def __str__(self):
        return f"{self.knowledge_base.name} - {self.name}"


class KnowledgeBaseSettings(BaseModel):
    """
    知识库设置模型
    """
    knowledge_base = models.OneToOneField(
        KnowledgeBase,
        on_delete=models.CASCADE,
        related_name='settings',
        verbose_name='知识库'
    )
    
    # 索引设置
    auto_index = models.BooleanField(default=True, verbose_name='自动索引')
    index_schedule = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='索引计划'
    )
    
    # 检索设置
    search_mode = models.CharField(
        max_length=20,
        choices=[
            ('semantic', '语义检索'),
            ('keyword', '关键词检索'),
            ('hybrid', '混合检索')
        ],
        default='semantic',
        verbose_name='检索模式'
    )
    
    # 其他设置
    enable_rerank = models.BooleanField(default=False, verbose_name='启用重排序')
    rerank_model = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='重排序模型'
    )
    
    class Meta:
        db_table = 'knowledge_base_settings'
        verbose_name = '知识库设置'
        verbose_name_plural = '知识库设置'
    
    def __str__(self):
        return f"{self.knowledge_base.name} - Settings" 