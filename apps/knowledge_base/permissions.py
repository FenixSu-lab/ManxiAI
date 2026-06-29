"""Centralized knowledge-base access helpers.

These helpers keep owner/write/read/none behavior consistent across
knowledge-base, document, chat, and archive APIs.
"""

import logging

from django.db import models
from rest_framework.exceptions import PermissionDenied

from .models import KnowledgeBase, KnowledgeBaseShare

logger = logging.getLogger(__name__)


class KnowledgeBaseRole:
    """Role constants used by API serializers and permission checks."""

    OWNER = 'owner'
    WRITE = 'write'
    READ = 'read'
    NONE = 'none'


ROLE_LEVELS = {
    KnowledgeBaseRole.NONE: 0,
    KnowledgeBaseRole.READ: 1,
    KnowledgeBaseRole.WRITE: 2,
    KnowledgeBaseRole.OWNER: 3,
}


def get_user_role(user, knowledge_base: KnowledgeBase) -> str:
    """Return the effective role for a user on a knowledge base."""
    if not user or not user.is_authenticated:
        return KnowledgeBaseRole.NONE
    if knowledge_base.created_by_id == user.id:
        return KnowledgeBaseRole.OWNER

    share = KnowledgeBaseShare.objects.filter(
        knowledge_base=knowledge_base,
        shared_with=user,
    ).first()
    if share and share.permission in {KnowledgeBaseRole.READ, KnowledgeBaseRole.WRITE}:
        return share.permission
    if knowledge_base.is_public:
        return KnowledgeBaseRole.READ
    return KnowledgeBaseRole.NONE


def has_role(user, knowledge_base: KnowledgeBase, minimum_role: str) -> bool:
    """Return True when a user's effective role is at least the required role."""
    current_role = get_user_role(user, knowledge_base)
    return ROLE_LEVELS[current_role] >= ROLE_LEVELS[minimum_role]


def can_read(user, knowledge_base: KnowledgeBase) -> bool:
    """Return True when the user can view or chat with a knowledge base."""
    return has_role(user, knowledge_base, KnowledgeBaseRole.READ)


def can_write(user, knowledge_base: KnowledgeBase) -> bool:
    """Return True when the user can maintain data sources."""
    return has_role(user, knowledge_base, KnowledgeBaseRole.WRITE)


def is_owner(user, knowledge_base: KnowledgeBase) -> bool:
    """Return True when the user owns the knowledge base."""
    return has_role(user, knowledge_base, KnowledgeBaseRole.OWNER)


def require_role(user, knowledge_base: KnowledgeBase, minimum_role: str, action: str) -> None:
    """Raise a DRF permission error when a user lacks the required role."""
    if has_role(user, knowledge_base, minimum_role):
        return
    logger.info(
        'knowledge_base_permission_denied user_id=%s knowledge_base_id=%s required_role=%s action=%s',
        getattr(user, 'id', None),
        knowledge_base.id,
        minimum_role,
        action,
    )
    raise PermissionDenied(f'{minimum_role} permission is required for this knowledge base.')


def require_read(user, knowledge_base: KnowledgeBase, action: str) -> None:
    """Require read access for a knowledge-base operation."""
    require_role(user, knowledge_base, KnowledgeBaseRole.READ, action)


def require_write(user, knowledge_base: KnowledgeBase, action: str) -> None:
    """Require write access for a knowledge-base operation."""
    require_role(user, knowledge_base, KnowledgeBaseRole.WRITE, action)


def require_owner(user, knowledge_base: KnowledgeBase, action: str) -> None:
    """Require owner access for a knowledge-base operation."""
    require_role(user, knowledge_base, KnowledgeBaseRole.OWNER, action)


def filter_visible(queryset, user):
    """Filter a KnowledgeBase queryset to records readable by the user."""
    if not user or not user.is_authenticated:
        return queryset.none()
    return queryset.filter(
        models.Q(created_by=user)
        | models.Q(is_public=True)
        | models.Q(shares__shared_with=user)
    ).distinct()


def filter_writable(queryset, user):
    """Filter a KnowledgeBase queryset to records writable by the user."""
    if not user or not user.is_authenticated:
        return queryset.none()
    return queryset.filter(
        models.Q(created_by=user)
        | models.Q(shares__shared_with=user, shares__permission=KnowledgeBaseRole.WRITE)
    ).distinct()
