"""URL routes for model provider management."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import LLMProviderViewSet

router = DefaultRouter()
router.register(r'model-providers', LLMProviderViewSet, basename='model-provider')

urlpatterns = [
    path('', include(router.urls)),
]
