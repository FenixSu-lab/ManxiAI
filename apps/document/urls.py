"""
文档管理URL配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DocumentViewSet, ParagraphViewSet, ProblemViewSet

# 创建路由器
router = DefaultRouter()

app_name = 'document'

urlpatterns = [
    # 知识库下的文档管理
    path('knowledge-bases/<uuid:knowledge_base_id>/documents/', DocumentViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='document-list'),
    
    path('knowledge-bases/<uuid:knowledge_base_id>/documents/<uuid:pk>/', DocumentViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='document-detail'),
    
    # 文档上传
    path('knowledge-bases/<uuid:knowledge_base_id>/documents/upload/', 
         DocumentViewSet.as_view({'post': 'upload'}), 
         name='document-upload'),
    
    # 创建Web文档
    path('knowledge-bases/<uuid:knowledge_base_id>/documents/create-web/', 
         DocumentViewSet.as_view({'post': 'create_web'}), 
         name='document-create-web'),
    
    # 创建问答文档
    path('knowledge-bases/<uuid:knowledge_base_id>/documents/create-qa/', 
         DocumentViewSet.as_view({'post': 'create_qa'}), 
         name='document-create-qa'),
    
    # 文档搜索
    path('knowledge-bases/<uuid:knowledge_base_id>/documents/search/', 
         DocumentViewSet.as_view({'get': 'search'}), 
         name='document-search'),
    
    # 文档统计
    path('knowledge-bases/<uuid:knowledge_base_id>/documents/stats/', 
         DocumentViewSet.as_view({'get': 'stats'}), 
         name='document-stats'),
    
    # 批量操作
    path('knowledge-bases/<uuid:knowledge_base_id>/documents/batch/', 
         DocumentViewSet.as_view({'post': 'batch_operation'}), 
         name='document-batch'),
    
    # 重新处理文档
    path('knowledge-bases/<uuid:knowledge_base_id>/documents/<uuid:pk>/reprocess/', 
         DocumentViewSet.as_view({'post': 'reprocess'}), 
         name='document-reprocess'),
    
    # 获取文档段落
    path('knowledge-bases/<uuid:knowledge_base_id>/documents/<uuid:pk>/paragraphs/', 
         DocumentViewSet.as_view({'get': 'paragraphs'}), 
         name='document-paragraphs'),
    
    # 获取文档处理任务
    path('knowledge-bases/<uuid:knowledge_base_id>/documents/<uuid:pk>/tasks/', 
         DocumentViewSet.as_view({'get': 'processing_tasks'}), 
         name='document-tasks'),
    
    # 段落管理
    path('documents/<uuid:document_id>/paragraphs/', ParagraphViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='paragraph-list'),
    
    path('documents/<uuid:document_id>/paragraphs/<uuid:pk>/', ParagraphViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='paragraph-detail'),
    
    # 切换段落激活状态
    path('documents/<uuid:document_id>/paragraphs/<uuid:pk>/toggle-active/', 
         ParagraphViewSet.as_view({'post': 'toggle_active'}), 
         name='paragraph-toggle-active'),
    
    # 问题管理
    path('knowledge-bases/<uuid:knowledge_base_id>/problems/', ProblemViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='problem-list'),
    
    path('knowledge-bases/<uuid:knowledge_base_id>/problems/<uuid:pk>/', ProblemViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='problem-detail'),
    
    # 问题搜索
    path('knowledge-bases/<uuid:knowledge_base_id>/problems/search/', 
         ProblemViewSet.as_view({'get': 'search'}), 
         name='problem-search'),
] 