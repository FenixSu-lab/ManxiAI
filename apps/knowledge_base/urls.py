"""
知识库管理URL配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import KnowledgeBaseViewSet

router = DefaultRouter()
router.register(r'', KnowledgeBaseViewSet, basename='knowledge-base')

urlpatterns = [
    path('', include(router.urls)),
] 