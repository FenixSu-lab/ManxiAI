"""Serializers for user, team, and API-key endpoints."""

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import ApiKey, Team, TeamMember, User, UserProfile


class UserSerializer(serializers.ModelSerializer):
    """Serialize user account data and handle local account creation."""

    password = serializers.CharField(write_only=True, required=False, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'phone',
            'avatar',
            'is_email_verified',
            'is_phone_verified',
            'created_at',
            'password',
            'confirm_password',
        ]
        read_only_fields = ['id', 'created_at', 'is_email_verified', 'is_phone_verified']

    def validate(self, attrs):
        """Ensure password confirmation is present and matches when creating a user."""
        if self.instance is None:
            if not attrs.get('password'):
                raise serializers.ValidationError({'password': 'Password is required.'})
            if not attrs.get('confirm_password'):
                raise serializers.ValidationError({'confirm_password': 'Password confirmation is required.'})

        if attrs.get('password') or attrs.get('confirm_password'):
            if attrs.get('password') != attrs.get('confirm_password'):
                raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        """Create a user through Django's password-aware user manager."""
        validated_data.pop('confirm_password', None)
        return User.objects.create_user(**validated_data)

    def update(self, instance, validated_data):
        """Update non-password account fields from profile settings."""
        validated_data.pop('password', None)
        validated_data.pop('confirm_password', None)
        return super().update(instance, validated_data)


class UserOptionSerializer(serializers.ModelSerializer):
    """Serialize compact user options for permission pickers."""

    label = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'label']
        read_only_fields = fields

    def get_label(self, obj):
        """Return a readable dropdown label."""
        return f'{obj.username} <{obj.email}>' if obj.username else obj.email


class UserProfileSerializer(serializers.ModelSerializer):
    """Serialize extended profile metadata for the current user."""

    user = UserSerializer(read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            'id',
            'user',
            'nickname',
            'bio',
            'company',
            'department',
            'position',
            'language',
            'timezone',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class LoginSerializer(serializers.Serializer):
    """Validate account/password login credentials."""

    email = serializers.CharField()
    password = serializers.CharField()

    def validate(self, attrs):
        """Authenticate the user and return it in validated data."""
        account = attrs.get('email')
        password = attrs.get('password')

        if not account or not password:
            raise serializers.ValidationError('Account and password are required.')

        user = self._authenticate_by_account(account, password)
        if not user:
            raise serializers.ValidationError('Invalid account or password.')
        if not user.is_active:
            raise serializers.ValidationError('This account is disabled.')

        attrs['user'] = user
        return attrs

    def _authenticate_by_account(self, account, password):
        """Authenticate by email first, then map a username to its email."""
        user = authenticate(username=account, password=password)
        if user:
            return user

        matched_user = User.objects.filter(username=account).first()
        if not matched_user:
            return None
        return authenticate(username=matched_user.email, password=password)


class ChangePasswordSerializer(serializers.Serializer):
    """Validate password change payloads."""

    old_password = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])
    confirm_password = serializers.CharField()

    def validate(self, attrs):
        """Ensure the new password confirmation matches."""
        if attrs.get('new_password') != attrs.get('confirm_password'):
            raise serializers.ValidationError({'confirm_password': 'New passwords do not match.'})
        return attrs

    def validate_old_password(self, value):
        """Verify the old password against the authenticated user."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value


class TeamSerializer(serializers.ModelSerializer):
    """Serialize team metadata and member counts."""

    owner = UserSerializer(read_only=True)
    members_count = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ['id', 'name', 'description', 'owner', 'members_count', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']

    def get_members_count(self, obj):
        """Return the number of users attached to this team."""
        return obj.members.count()


class TeamMemberSerializer(serializers.ModelSerializer):
    """Serialize team membership rows."""

    user = UserSerializer(read_only=True)
    team = TeamSerializer(read_only=True)

    class Meta:
        model = TeamMember
        fields = ['id', 'team', 'user', 'role', 'joined_at', 'created_at']
        read_only_fields = ['id', 'joined_at', 'created_at']


class ApiKeySerializer(serializers.ModelSerializer):
    """Serialize API keys owned by the authenticated user."""

    key = serializers.CharField(read_only=True)

    class Meta:
        model = ApiKey
        fields = ['id', 'name', 'key', 'is_active', 'last_used_at', 'expires_at', 'created_at', 'updated_at']
        read_only_fields = ['id', 'key', 'last_used_at', 'created_at', 'updated_at']
