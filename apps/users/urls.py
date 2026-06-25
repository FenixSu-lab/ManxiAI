"""URL routes for user, team, and API-key endpoints."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ApiKeyViewSet, TeamViewSet, UserProfileViewSet, UserViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'profiles', UserProfileViewSet, basename='profile')
router.register(r'teams', TeamViewSet, basename='team')
router.register(r'api-keys', ApiKeyViewSet, basename='apikey')

urlpatterns = [
    path('', include(router.urls)),
]
