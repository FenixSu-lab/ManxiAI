#!/usr/bin/env python
"""
创建测试数据脚本
"""
import os
import sys
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.knowledge_base.models import KnowledgeBase
from apps.document.models import Document, Paragraph

User = get_user_model()

def create_test_data():
    """创建测试数据"""
    print("开始创建测试数据...")
    
    # 创建测试用户
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'test@example.com',
            'first_name': '测试',
            'last_name': '用户'
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()
        print(f"创建用户: {user.username}")
    else:
        print(f"用户已存在: {user.username}")
    
    # 创建测试知识库
    kb1, created = KnowledgeBase.objects.get_or_create(
        name='产品文档知识库',
        defaults={
            'description': '包含产品相关的所有文档和说明',
            'created_by': user,
            'is_public': False
        }
    )
    if created:
        print(f"创建知识库: {kb1.name}")
    else:
        print(f"知识库已存在: {kb1.name}")
    
    kb2, created = KnowledgeBase.objects.get_or_create(
        name='技术文档知识库',
        defaults={
            'description': '技术开发相关的文档和API说明',
            'created_by': user,
            'is_public': True
        }
    )
    if created:
        print(f"创建知识库: {kb2.name}")
    else:
        print(f"知识库已存在: {kb2.name}")
    
    # 创建测试文档
    doc1, created = Document.objects.get_or_create(
        name='用户手册.pdf',
        knowledge_base=kb1,
        defaults={
            'type': 'base',
            'status': 'completed',
            'created_by': user,
            'file_size': 1024000,
            'char_length': 5000,
            'paragraph_count': 10
        }
    )
    if created:
        print(f"创建文档: {doc1.name}")
        # 创建段落
        for i in range(5):
            Paragraph.objects.create(
                document=doc1,
                knowledge_base=kb1,
                title=f'第{i+1}章 用户指南',
                content=f'这是第{i+1}章的内容，介绍了如何使用产品的各种功能。包含详细的操作步骤和注意事项。',
                position=i,
                char_length=100
            )
    
    doc2, created = Document.objects.get_or_create(
        name='API文档',
        knowledge_base=kb2,
        defaults={
            'type': 'web',
            'status': 'completed',
            'created_by': user,
            'char_length': 8000,
            'paragraph_count': 15
        }
    )
    if created:
        print(f"创建文档: {doc2.name}")
        # 创建段落
        for i in range(8):
            Paragraph.objects.create(
                document=doc2,
                knowledge_base=kb2,
                title=f'API接口{i+1}',
                content=f'这是API接口{i+1}的说明文档，包含请求参数、响应格式和示例代码。',
                position=i,
                char_length=150
            )
    
    # 更新知识库统计
    kb1.update_stats()
    kb2.update_stats()
    
    print("测试数据创建完成！")
    print(f"知识库数量: {KnowledgeBase.objects.count()}")
    print(f"文档数量: {Document.objects.count()}")
    print(f"段落数量: {Paragraph.objects.count()}")

if __name__ == '__main__':
    create_test_data() 