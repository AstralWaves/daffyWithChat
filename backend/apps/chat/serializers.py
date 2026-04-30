from rest_framework import serializers
from .models import Conversation, Message, TypingStatus
from apps.accounts.serializers import UserSerializer

class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.ReadOnlyField(source='sender.full_name')
    sender_id = serializers.ReadOnlyField(source='sender.id')

    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender_id', 'sender_name', 'content', 'message_type', 'media_url', 'media_metadata', 'reply_to', 'is_edited', 'is_deleted', 'created_at', 'updated_at']

class ConversationSerializer(serializers.ModelSerializer):
    participants = UserSerializer(many=True, read_only=True)
    last_message_content = serializers.SerializerMethodField()
    last_message_time = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'participants', 'is_group', 'group_name', 'group_avatar', 'group_description', 'created_by', 'last_message', 'last_message_content', 'last_message_time', 'created_at', 'updated_at']

    def get_last_message_content(self, obj):
        return obj.last_message.content if obj.last_message else None

    def get_last_message_time(self, obj):
        return obj.last_message.created_at if obj.last_message else None
