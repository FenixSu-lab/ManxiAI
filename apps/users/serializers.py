"""
用户管理序列化器
"""
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, UserProfile, Team, TeamMember, ApiKey


class UserSerializer(serializers.ModelSerializer):
    """
    用户序列化器
    """
    password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'phone', 
                 'avatar', 'is_email_verified', 'is_phone_verified', 'created_at', 
                 'password', 'confirm_password']
        read_only_fields = ['id', 'created_at', 'is_email_verified', 'is_phone_verified']
    
    def validate(self, attrs):
        if attrs.get('password') != attrs.get('confirm_password'):
            raise serializers.ValidationError("密码不匹配")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = User.objects.create_user(**validated_data)
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """
    用户详情序列化器
    """
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'nickname', 'bio', 'company', 'department', 
                 'position', 'language', 'timezone', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class LoginSerializer(serializers.Serializer):
    """
    登录序列化器
    """
    email = serializers.EmailField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(username=email, password=password)
            if not user:
                raise serializers.ValidationError('邮箱或密码错误')
            if not user.is_active:
                raise serializers.ValidationError('账户已被禁用')
            attrs['user'] = user
        else:
            raise serializers.ValidationError('请提供邮箱和密码')
        
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """
    修改密码序列化器
    """
    old_password = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])
    confirm_password = serializers.CharField()
    
    def validate(self, attrs):
        if attrs.get('new_password') != attrs.get('confirm_password'):
            raise serializers.ValidationError("新密码不匹配")
        return attrs
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("原密码错误")
        return value


class TeamSerializer(serializers.ModelSerializer):
    """
    团队序列化器
    """
    owner = UserSerializer(read_only=True)
    members_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Team
        fields = ['id', 'name', 'description', 'owner', 'members_count', 
                 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']
    
    def get_members_count(self, obj):
        return obj.members.count()


class TeamMemberSerializer(serializers.ModelSerializer):
    """
    团队成员序列化器
    """
    user = UserSerializer(read_only=True)
    team = TeamSerializer(read_only=True)
    
    class Meta:
        model = TeamMember
        fields = ['id', 'team', 'user', 'role', 'joined_at', 'created_at']
        read_only_fields = ['id', 'joined_at', 'created_at']


class ApiKeySerializer(serializers.ModelSerializer):
    """
    API密钥序列化器
    """
    key = serializers.CharField(read_only=True)
    
    class Meta:
        model = ApiKey
        fields = ['id', 'name', 'key', 'is_active', 'last_used_at', 
                 'expires_at', 'created_at', 'updated_at']
        read_only_fields = ['id', 'key', 'last_used_at', 'created_at', 'updated_at'] 