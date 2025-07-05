"""
用户管理URL配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, UserProfileViewSet, TeamViewSet, ApiKeyViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'profiles', UserProfileViewSet, basename='profile')
router.register(r'teams', TeamViewSet, basename='team')
router.register(r'api-keys', ApiKeyViewSet, basename='apikey')

urlpatterns = [
    path('', include(router.urls)),
] 