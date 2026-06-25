"""Root URL configuration for ManxiAI."""

import warnings

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework import permissions

warnings.filterwarnings(
    'ignore',
    message='pkg_resources is deprecated as an API.*',
    category=UserWarning,
)
from drf_yasg import openapi  # noqa: E402
from drf_yasg.views import get_schema_view  # noqa: E402

schema_view = get_schema_view(
    openapi.Info(
        title='ManxiAI API',
        default_version='v1',
        description='ManxiAI knowledge-base and RAG chat API.',
        terms_of_service='https://www.manxiai.com/terms/',
        contact=openapi.Contact(email='contact@manxiai.com'),
        license=openapi.License(name='MIT License'),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('api/v1/', include('apps.core.urls')),
    path('api/v1/auth/', include('apps.users.urls')),
    path('api/v1/', include('apps.knowledge_base.urls')),
    path('api/v1/', include('apps.document.urls')),
    path('api/v1/', include('apps.chat.urls')),
    path('api/v1/', include('apps.model_management.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
