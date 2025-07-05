"""
核心模型基础类
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model


class BaseModel(models.Model):
    """
    基础抽象模型，提供通用字段
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        abstract = True


class UserRelatedModel(BaseModel):
    """
    与用户相关的模型基类
    """
    created_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name='%(class)s_created',
        verbose_name='创建者'
    )
    
    class Meta:
        abstract = True


class SoftDeleteModel(BaseModel):
    """
    软删除模型基类
    """
    is_deleted = models.BooleanField(default=False, verbose_name='是否删除')
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='删除时间')
    
    class Meta:
        abstract = True
    
    def soft_delete(self):
        """软删除"""
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()
    
    def restore(self):
        """恢复"""
        self.is_deleted = False
        self.deleted_at = None
        self.save()


class StatusChoices(models.TextChoices):
    """通用状态选择"""
    ACTIVE = 'active', '活跃'
    INACTIVE = 'inactive', '非活跃'
    PENDING = 'pending', '待处理'
    PROCESSING = 'processing', '处理中'
    COMPLETED = 'completed', '已完成'
    FAILED = 'failed', '失败'
    CANCELLED = 'cancelled', '已取消' 