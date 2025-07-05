"""
用户管理模型
"""
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from apps.core.models import BaseModel


class User(AbstractUser):
    """
    自定义用户模型
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_('email address'), unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='手机号')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='头像')
    is_email_verified = models.BooleanField(default=False, verbose_name='邮箱是否验证')
    is_phone_verified = models.BooleanField(default=False, verbose_name='手机是否验证')
    last_login_ip = models.GenericIPAddressField(blank=True, null=True, verbose_name='最后登录IP')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    # 使用邮箱作为用户名
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'users'
        verbose_name = '用户'
        verbose_name_plural = '用户'
    
    def __str__(self):
        return self.email or self.username


class UserProfile(BaseModel):
    """
    用户详细信息
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    nickname = models.CharField(max_length=50, blank=True, null=True, verbose_name='昵称')
    bio = models.TextField(blank=True, null=True, verbose_name='个人简介')
    company = models.CharField(max_length=100, blank=True, null=True, verbose_name='公司')
    department = models.CharField(max_length=100, blank=True, null=True, verbose_name='部门')
    position = models.CharField(max_length=100, blank=True, null=True, verbose_name='职位')
    language = models.CharField(max_length=10, default='zh-hans', verbose_name='语言偏好')
    timezone = models.CharField(max_length=50, default='Asia/Shanghai', verbose_name='时区')
    
    class Meta:
        db_table = 'user_profiles'
        verbose_name = '用户详情'
        verbose_name_plural = '用户详情'
    
    def __str__(self):
        return f"{self.user.email} - Profile"


class Team(BaseModel):
    """
    团队模型
    """
    name = models.CharField(max_length=100, verbose_name='团队名称')
    description = models.TextField(blank=True, null=True, verbose_name='团队描述')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_teams', verbose_name='创建者')
    members = models.ManyToManyField(User, through='TeamMember', related_name='teams', verbose_name='成员')
    is_active = models.BooleanField(default=True, verbose_name='是否激活')
    
    class Meta:
        db_table = 'teams'
        verbose_name = '团队'
        verbose_name_plural = '团队'
    
    def __str__(self):
        return self.name


class TeamMember(BaseModel):
    """
    团队成员关系
    """
    class RoleChoices(models.TextChoices):
        OWNER = 'owner', '拥有者'
        ADMIN = 'admin', '管理员'
        MEMBER = 'member', '成员'
        VIEWER = 'viewer', '查看者'
    
    team = models.ForeignKey(Team, on_delete=models.CASCADE, verbose_name='团队')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    role = models.CharField(max_length=20, choices=RoleChoices.choices, default=RoleChoices.MEMBER, verbose_name='角色')
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name='加入时间')
    
    class Meta:
        db_table = 'team_members'
        unique_together = ['team', 'user']
        verbose_name = '团队成员'
        verbose_name_plural = '团队成员'
    
    def __str__(self):
        return f"{self.user.email} - {self.team.name} ({self.role})"


class ApiKey(BaseModel):
    """
    API密钥模型
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_keys', verbose_name='用户')
    name = models.CharField(max_length=100, verbose_name='密钥名称')
    key = models.CharField(max_length=64, unique=True, verbose_name='密钥')
    is_active = models.BooleanField(default=True, verbose_name='是否激活')
    last_used_at = models.DateTimeField(null=True, blank=True, verbose_name='最后使用时间')
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name='过期时间')
    
    class Meta:
        db_table = 'api_keys'
        verbose_name = 'API密钥'
        verbose_name_plural = 'API密钥'
    
    def __str__(self):
        return f"{self.user.email} - {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.key:
            import secrets
            self.key = secrets.token_urlsafe(32)
        super().save(*args, **kwargs) 