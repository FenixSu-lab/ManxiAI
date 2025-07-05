"""
用户管理视图
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import login, logout
from django.shortcuts import get_object_or_404
from .models import User, UserProfile, Team, TeamMember, ApiKey
from .serializers import (
    UserSerializer, UserProfileSerializer, LoginSerializer, 
    ChangePasswordSerializer, TeamSerializer, TeamMemberSerializer, 
    ApiKeySerializer
)


class UserViewSet(viewsets.ModelViewSet):
    """
    用户管理视图集
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        """
        根据action设置权限
        """
        if self.action == 'create':
            permission_classes = [permissions.AllowAny]
        elif self.action in ['me', 'change_password']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]
    
    @action(detail=False, methods=['get', 'put'])
    def me(self, request):
        """
        获取或更新当前用户信息
        """
        if request.method == 'GET':
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)
        elif request.method == 'PUT':
            serializer = self.get_serializer(request.user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def login(self, request):
        """
        用户登录
        """
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            login(request, user)
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user': UserSerializer(user).data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def logout(self, request):
        """
        用户登出
        """
        logout(request)
        return Response({'message': '登出成功'})
    
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """
        修改密码
        """
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({'message': '密码修改成功'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileViewSet(viewsets.ModelViewSet):
    """
    用户详情视图集
    """
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """
        只返回当前用户的详情
        """
        return self.queryset.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """
        创建时设置用户
        """
        serializer.save(user=self.request.user)


class TeamViewSet(viewsets.ModelViewSet):
    """
    团队管理视图集
    """
    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """
        只返回用户参与的团队
        """
        return self.queryset.filter(members=self.request.user)
    
    def perform_create(self, serializer):
        """
        创建时设置拥有者
        """
        team = serializer.save(owner=self.request.user)
        # 创建者自动成为成员
        TeamMember.objects.create(
            team=team,
            user=self.request.user,
            role=TeamMember.RoleChoices.OWNER
        )
    
    @action(detail=True, methods=['post'])
    def add_member(self, request, pk=None):
        """
        添加团队成员
        """
        team = self.get_object()
        user_id = request.data.get('user_id')
        role = request.data.get('role', TeamMember.RoleChoices.MEMBER)
        
        if not user_id:
            return Response({'error': '用户ID不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        
        user = get_object_or_404(User, id=user_id)
        
        # 检查是否已经是成员
        if TeamMember.objects.filter(team=team, user=user).exists():
            return Response({'error': '用户已经是团队成员'}, status=status.HTTP_400_BAD_REQUEST)
        
        member = TeamMember.objects.create(team=team, user=user, role=role)
        serializer = TeamMemberSerializer(member)
        return Response(serializer.data)
    
    @action(detail=True, methods=['delete'])
    def remove_member(self, request, pk=None):
        """
        移除团队成员
        """
        team = self.get_object()
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response({'error': '用户ID不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        
        member = get_object_or_404(TeamMember, team=team, user_id=user_id)
        member.delete()
        return Response({'message': '成员移除成功'})


class ApiKeyViewSet(viewsets.ModelViewSet):
    """
    API密钥管理视图集
    """
    queryset = ApiKey.objects.all()
    serializer_class = ApiKeySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """
        只返回当前用户的API密钥
        """
        return self.queryset.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """
        创建时设置用户
        """
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def regenerate(self, request, pk=None):
        """
        重新生成API密钥
        """
        api_key = self.get_object()
        import secrets
        api_key.key = secrets.token_urlsafe(32)
        api_key.save()
        serializer = self.get_serializer(api_key)
        return Response(serializer.data) 