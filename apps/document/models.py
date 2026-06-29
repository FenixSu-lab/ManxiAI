"""
文档管理模型
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from apps.core.models import BaseModel, UserRelatedModel, SoftDeleteModel, StatusChoices

User = get_user_model()


class DocumentType(models.TextChoices):
    """文档类型"""
    BASE = 'base', '通用类型'
    WEB = 'web', 'Web站点'
    QA = 'qa', '问答对'
    CHAT_ARCHIVE = 'chat_archive', '对话归档'
    TABLE = 'table', '表格'
    MARKDOWN = 'markdown', 'Markdown'
    TEXT = 'text', '纯文本'


class DocumentStatus(models.TextChoices):
    """文档状态"""
    PENDING = 'pending', '待处理'
    PROCESSING = 'processing', '处理中'
    COMPLETED = 'completed', '已完成'
    FAILED = 'failed', '处理失败'
    EMBEDDING = 'embedding', '向量化中'


class HitHandlingMethod(models.TextChoices):
    """命中处理方式"""
    OPTIMIZATION = 'optimization', '优化'
    DIRECTLY_RETURN = 'directly_return', '直接返回'


class Document(UserRelatedModel, SoftDeleteModel):
    """
    文档模型
    """
    knowledge_base = models.ForeignKey(
        'knowledge_base.KnowledgeBase',
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name='知识库'
    )
    name = models.CharField(max_length=255, verbose_name='文档名称')
    type = models.CharField(
        max_length=20,
        choices=DocumentType.choices,
        default=DocumentType.BASE,
        verbose_name='文档类型'
    )
    status = models.CharField(
        max_length=20,
        choices=DocumentStatus.choices,
        default=DocumentStatus.PENDING,
        verbose_name='文档状态'
    )
    file_path = models.CharField(max_length=500, blank=True, null=True, verbose_name='文件路径')
    file_size = models.BigIntegerField(default=0, verbose_name='文件大小(字节)')
    char_length = models.IntegerField(default=0, verbose_name='字符数')
    paragraph_count = models.IntegerField(default=0, verbose_name='段落数')
    
    # 处理设置
    hit_handling_method = models.CharField(
        max_length=20,
        choices=HitHandlingMethod.choices,
        default=HitHandlingMethod.OPTIMIZATION,
        verbose_name='命中处理方式'
    )
    directly_return_similarity = models.FloatField(
        default=0.9,
        verbose_name='直接返回相似度阈值'
    )
    
    # 元数据
    meta = models.JSONField(default=dict, verbose_name='元数据')
    
    # 统计信息
    hit_count = models.IntegerField(default=0, verbose_name='命中次数')
    last_hit_time = models.DateTimeField(null=True, blank=True, verbose_name='最后命中时间')
    
    class Meta:
        db_table = 'documents'
        verbose_name = '文档'
        verbose_name_plural = '文档'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.knowledge_base.name} - {self.name}"
    
    def update_stats(self):
        """更新统计信息"""
        from .models import Paragraph
        stats = Paragraph.objects.filter(document=self).aggregate(
            paragraph_count=models.Count('id'),
            char_length=models.Sum('char_length') or 0
        )
        self.paragraph_count = stats['paragraph_count']
        self.char_length = stats['char_length']
        self.save(update_fields=['paragraph_count', 'char_length'])


class Paragraph(BaseModel):
    """
    段落模型
    """
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='paragraphs',
        verbose_name='文档'
    )
    knowledge_base = models.ForeignKey(
        'knowledge_base.KnowledgeBase',
        on_delete=models.CASCADE,
        related_name='paragraphs',
        verbose_name='知识库'
    )
    title = models.CharField(max_length=255, blank=True, default='', verbose_name='标题')
    content = models.TextField(verbose_name='内容')
    char_length = models.IntegerField(default=0, verbose_name='字符数')
    
    # 状态
    status = models.CharField(
        max_length=20,
        choices=DocumentStatus.choices,
        default=DocumentStatus.PENDING,
        verbose_name='状态'
    )
    is_active = models.BooleanField(default=True, verbose_name='是否激活')
    
    # 向量化信息
    embedding_id = models.CharField(max_length=100, blank=True, null=True, verbose_name='向量ID')
    
    # 统计信息
    hit_count = models.IntegerField(default=0, verbose_name='命中次数')
    last_hit_time = models.DateTimeField(null=True, blank=True, verbose_name='最后命中时间')
    
    # 位置信息
    position = models.IntegerField(default=0, verbose_name='在文档中的位置')
    
    class Meta:
        db_table = 'paragraphs'
        verbose_name = '段落'
        verbose_name_plural = '段落'
        ordering = ['document', 'position']
    
    def __str__(self):
        return f"{self.document.name} - {self.title or self.content[:50]}"
    
    def save(self, *args, **kwargs):
        if not self.char_length:
            self.char_length = len(self.content)
        super().save(*args, **kwargs)


class Problem(BaseModel):
    """
    问题模型 - 用于QA类型的知识库
    """
    knowledge_base = models.ForeignKey(
        'knowledge_base.KnowledgeBase',
        on_delete=models.CASCADE,
        related_name='problems',
        verbose_name='知识库'
    )
    content = models.TextField(verbose_name='问题内容')
    
    # 统计信息
    hit_count = models.IntegerField(default=0, verbose_name='命中次数')
    last_hit_time = models.DateTimeField(null=True, blank=True, verbose_name='最后命中时间')
    
    class Meta:
        db_table = 'problems'
        verbose_name = '问题'
        verbose_name_plural = '问题'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.knowledge_base.name} - {self.content[:50]}"


class ProblemParagraphMapping(BaseModel):
    """
    问题段落映射模型
    """
    knowledge_base = models.ForeignKey(
        'knowledge_base.KnowledgeBase',
        on_delete=models.CASCADE,
        verbose_name='知识库'
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        verbose_name='文档'
    )
    problem = models.ForeignKey(
        Problem,
        on_delete=models.CASCADE,
        verbose_name='问题'
    )
    paragraph = models.ForeignKey(
        Paragraph,
        on_delete=models.CASCADE,
        verbose_name='段落'
    )
    
    class Meta:
        db_table = 'problem_paragraph_mappings'
        verbose_name = '问题段落映射'
        verbose_name_plural = '问题段落映射'
        unique_together = ['problem', 'paragraph']
    
    def __str__(self):
        return f"{self.problem.content[:30]} -> {self.paragraph.content[:30]}"


class DocumentProcessingTask(BaseModel):
    """
    文档处理任务模型
    """
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='processing_tasks',
        verbose_name='文档'
    )
    task_type = models.CharField(max_length=50, verbose_name='任务类型')
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
        verbose_name='任务状态'
    )
    progress = models.IntegerField(default=0, verbose_name='进度百分比')
    error_message = models.TextField(blank=True, null=True, verbose_name='错误信息')
    result = models.JSONField(default=dict, verbose_name='处理结果')
    
    class Meta:
        db_table = 'document_processing_tasks'
        verbose_name = '文档处理任务'
        verbose_name_plural = '文档处理任务'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.document.name} - {self.task_type}" 
