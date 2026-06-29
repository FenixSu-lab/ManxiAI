"""URL configuration for chat APIs."""
from django.urls import path

from .views import ChatSessionViewSet, public_chat_share

app_name = 'chat'

urlpatterns = [
    path('chat/sessions/', ChatSessionViewSet.as_view({
        'get': 'list',
        'post': 'create',
    }), name='chat-session-list'),
    path('chat/sessions/<uuid:pk>/', ChatSessionViewSet.as_view({
        'get': 'retrieve',
        'patch': 'partial_update',
        'put': 'update',
        'delete': 'destroy',
    }), name='chat-session-detail'),
    path('chat/sessions/<uuid:pk>/messages/', ChatSessionViewSet.as_view({
        'get': 'messages',
        'post': 'messages',
        'delete': 'messages',
    }), name='chat-session-messages'),
    path('chat/sessions/<uuid:pk>/archive/', ChatSessionViewSet.as_view({
        'post': 'archive',
    }), name='chat-session-archive'),
    path('chat/sessions/<uuid:pk>/share/', ChatSessionViewSet.as_view({
        'get': 'share',
        'post': 'share',
        'delete': 'share',
    }), name='chat-session-share'),
    path('chat/shares/<str:token>/', public_chat_share, name='public-chat-share'),
]
