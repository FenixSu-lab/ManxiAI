"""Serializers for chat APIs."""
from rest_framework import serializers

from .models import ChatMessage, ChatSession


class ChatMessageSerializer(serializers.ModelSerializer):
    """Serialize persisted chat messages."""

    class Meta:
        model = ChatMessage
        fields = ['id', 'role', 'content', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ChatSessionSerializer(serializers.ModelSerializer):
    """Serialize chat sessions with preview data."""

    last_message = serializers.SerializerMethodField()
    knowledge_base_id = serializers.UUIDField(source='knowledge_base.id', read_only=True)
    knowledge_base_name = serializers.CharField(source='knowledge_base.name', read_only=True, default='')

    class Meta:
        model = ChatSession
        fields = [
            'id',
            'title',
            'last_message',
            'knowledge_base_id',
            'knowledge_base_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_last_message(self, obj):
        """Return the newest message content for session preview."""
        message = obj.messages.order_by('-created_at').first()
        return message.content if message else ''


class ChatSessionCreateSerializer(serializers.ModelSerializer):
    """Validate session creation and update payloads."""

    knowledge_base_id = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = ChatSession
        fields = ['id', 'title', 'knowledge_base_id']
        read_only_fields = ['id']

    def validate(self, attrs):
        """Keep helper fields out of model persistence payloads."""
        attrs.setdefault('title', '')
        return attrs

    def create(self, validated_data):
        """Create a chat session after stripping helper fields."""
        validated_data.pop('knowledge_base_id', None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Update a chat session after stripping helper fields."""
        validated_data.pop('knowledge_base_id', None)
        return super().update(instance, validated_data)


class ChatMessageCreateSerializer(serializers.Serializer):
    """Validate inbound chat message payloads."""

    role = serializers.ChoiceField(choices=ChatMessage.RoleChoices.choices, default=ChatMessage.RoleChoices.USER)
    content = serializers.CharField(allow_blank=False, trim_whitespace=True)

    def validate_role(self, value: str) -> str:
        """Only accept user-authored messages from API callers."""
        if value != ChatMessage.RoleChoices.USER:
            raise serializers.ValidationError('Only user messages can be created through this endpoint.')
        return value
