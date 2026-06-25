"""ViewSets for authentication, profile, team, and API-key management."""

import logging
import secrets

from django.db import models
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import ApiKey, Team, TeamMember, User, UserProfile
from .serializers import (
    ApiKeySerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    TeamMemberSerializer,
    TeamSerializer,
    UserProfileSerializer,
    UserSerializer,
)

logger = logging.getLogger(__name__)


class UserViewSet(viewsets.ModelViewSet):
    """Expose registration, login, and current-user profile endpoints."""

    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        """Return action-specific permissions for account operations."""
        if self.action in ['create', 'login']:
            permission_classes = [permissions.AllowAny]
        elif self.action in ['me', 'change_password', 'logout']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        """Create a user and log the registration output identifier."""
        user = serializer.save()
        logger.info('user_registered user_id=%s email=%s', user.id, user.email)

    @action(detail=False, methods=['get', 'put'])
    def me(self, request):
        """Read or update the authenticated user's account fields."""
        if request.method == 'GET':
            logger.info('user_profile_read user_id=%s', request.user.id)
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)

        serializer = self.get_serializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            user = serializer.save()
            logger.info('user_profile_updated user_id=%s changed_fields=%s', user.id, sorted(request.data.keys()))
            return Response(serializer.data)
        logger.info('user_profile_update_rejected user_id=%s errors=%s', request.user.id, serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def login(self, request):
        """Authenticate a user and return a DRF token plus user profile."""
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token, _created = Token.objects.get_or_create(user=user)
            logger.info('user_login_success user_id=%s email=%s', user.id, user.email)
            return Response(
                {
                    'token': token.key,
                    'user': UserSerializer(user).data,
                }
            )

        logger.info('user_login_failed email=%s errors=%s', request.data.get('email'), serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def logout(self, request):
        """Revoke the current DRF token."""
        user_id = request.user.id
        Token.objects.filter(user=request.user).delete()
        logger.info('user_logout user_id=%s', user_id)
        return Response({'message': 'Logged out successfully.'})

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """Change the authenticated user's password after validating the old password."""
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save(update_fields=['password'])
            logger.info('user_password_changed user_id=%s', user.id)
            return Response({'message': 'Password changed successfully.'})

        logger.info('user_password_change_rejected user_id=%s errors=%s', request.user.id, serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileViewSet(viewsets.ModelViewSet):
    """Manage extended profile rows owned by the authenticated user."""

    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Restrict profile queries to the authenticated user."""
        return UserProfile.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Create the profile row for the authenticated user."""
        profile = serializer.save(user=self.request.user)
        logger.info('user_profile_detail_created user_id=%s profile_id=%s', self.request.user.id, profile.id)


class TeamViewSet(viewsets.ModelViewSet):
    """Manage teams owned by or shared with the authenticated user."""

    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return teams owned by or joined by the authenticated user."""
        return Team.objects.filter(
            models.Q(owner=self.request.user) | models.Q(members=self.request.user)
        ).distinct()

    def perform_create(self, serializer):
        """Create a team with the authenticated user as owner."""
        team = serializer.save(owner=self.request.user)
        TeamMember.objects.create(
            team=team,
            user=self.request.user,
            role=TeamMember.RoleChoices.OWNER,
        )
        logger.info('team_created user_id=%s team_id=%s', self.request.user.id, team.id)

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """Join the selected team as a member."""
        team = self.get_object()
        member, created = TeamMember.objects.get_or_create(
            team=team,
            user=request.user,
            defaults={'role': 'member'},
        )
        if created:
            logger.info('team_joined user_id=%s team_id=%s member_id=%s', request.user.id, team.id, member.id)
            return Response({'message': 'Joined team successfully.'})
        return Response({'message': 'You are already a team member.'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def add_member(self, request, pk=None):
        """Add a user to the selected team."""
        team = self.get_object()
        user_id = request.data.get('user_id')
        role = request.data.get('role', TeamMember.RoleChoices.MEMBER)

        if not user_id:
            return Response({'error': 'User ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        user = get_object_or_404(User, id=user_id)
        if TeamMember.objects.filter(team=team, user=user).exists():
            return Response({'error': 'User is already a team member.'}, status=status.HTTP_400_BAD_REQUEST)

        member = TeamMember.objects.create(team=team, user=user, role=role)
        logger.info(
            'team_member_added actor_user_id=%s team_id=%s member_user_id=%s role=%s',
            request.user.id,
            team.id,
            user.id,
            role,
        )
        return Response(TeamMemberSerializer(member).data)

    @action(detail=True, methods=['delete'])
    def remove_member(self, request, pk=None):
        """Remove a user from the selected team."""
        team = self.get_object()
        user_id = request.data.get('user_id')

        if not user_id:
            return Response({'error': 'User ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        member = get_object_or_404(TeamMember, team=team, user_id=user_id)
        member.delete()
        logger.info('team_member_removed actor_user_id=%s team_id=%s member_user_id=%s', request.user.id, team.id, user_id)
        return Response({'message': 'Team member removed successfully.'})

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """Leave the selected team if the authenticated user is a member."""
        team = self.get_object()
        try:
            member = TeamMember.objects.get(team=team, user=request.user)
        except TeamMember.DoesNotExist:
            return Response({'message': 'You are not a team member.'}, status=status.HTTP_400_BAD_REQUEST)

        member.delete()
        logger.info('team_left user_id=%s team_id=%s', request.user.id, team.id)
        return Response({'message': 'Left team successfully.'})


class ApiKeyViewSet(viewsets.ModelViewSet):
    """Manage API keys scoped to the authenticated user."""

    queryset = ApiKey.objects.all()
    serializer_class = ApiKeySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Restrict API-key queries to the authenticated user."""
        return ApiKey.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Create an API key for the authenticated user."""
        api_key = serializer.save(user=self.request.user)
        logger.info('api_key_created user_id=%s api_key_id=%s name=%s', self.request.user.id, api_key.id, api_key.name)

    @action(detail=True, methods=['post'])
    def regenerate(self, request, pk=None):
        """Regenerate the selected API key and return the new secret once."""
        api_key = self.get_object()
        api_key.key = secrets.token_urlsafe(32)
        api_key.save(update_fields=['key', 'updated_at'])
        logger.info('api_key_regenerated user_id=%s api_key_id=%s', request.user.id, api_key.id)
        return Response({'message': 'API key regenerated successfully.', 'key': api_key.key})
