from typing import Any, Dict, List, Optional

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from apps.chat.models import (
    Conversation,
    ConversationParticipant,
    Message,
    MessageAttachment,
)

User = get_user_model()


def _initials(full_name):
    parts = (full_name or '').strip().split()
    if not parts:
        return '??'
    return ''.join(p[0] for p in parts[:2]).upper()


class ChatUserBriefSerializer(serializers.ModelSerializer):
    initials = serializers.SerializerMethodField()
    user_type_label = serializers.SerializerMethodField()
    online = serializers.SerializerMethodField()
    last_seen = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'full_name', 'user_type', 'user_type_label',
            'lga', 'avatar', 'initials', 'online', 'last_seen',
        ]

    def get_initials(self, obj) -> str:
        return _initials(obj.full_name)

    def get_user_type_label(self, obj) -> str:
        return obj.get_user_type_display() if hasattr(obj, 'get_user_type_display') else obj.user_type

    def get_online(self, obj) -> bool:
        try:
            return obj.chat_presence.online_count > 0
        except Exception:
            return False

    def get_last_seen(self, obj) -> Optional[str]:
        try:
            if obj.chat_presence.last_seen_at:
                return obj.chat_presence.last_seen_at.isoformat()
        except Exception:
            pass
        return None


class MessageAttachmentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    file_type = serializers.SerializerMethodField()

    class Meta:
        model = MessageAttachment
        fields = ['id', 'url', 'filename', 'mime_type', 'size', 'kind', 'file_type']

    def get_url(self, obj) -> str:
        request = self.context.get('request')
        if obj.file:
            return request.build_absolute_uri(obj.file.url) if request else obj.file.url
        return ''

    def get_file_type(self, obj) -> str:
        return obj.kind or 'file'


class MessageSerializer(serializers.ModelSerializer):
    sender = ChatUserBriefSerializer(read_only=True)
    attachments = MessageAttachmentSerializer(many=True, read_only=True)
    read_by = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id', 'external_id', 'conversation', 'sender', 'message_type',
            'content', 'context', 'context_id', 'context_title',
            'client_message_id', 'reply_to', 'created_at', 'is_deleted',
            'attachments', 'read_by',
        ]

    def get_read_by(self, obj) -> List[str]:
        return [str(rid) for rid in obj.read_receipts.values_list('user_id', flat=True)]


def last_read_message_id(conversation, last_read_at):
    """Highest message id in the conversation at the read timestamp."""
    if not last_read_at:
        return 0
    last = (
        Message.objects.filter(conversation=conversation, created_at__lte=last_read_at)
        .order_by('-id')
        .first()
    )
    return last.id if last else 0


class ConversationSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    peers = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'type', 'title', 'created_by', 'last_message_at',
            'last_message', 'peers', 'unread_count',
        ]

    def get_type(self, obj) -> str:
        return obj.conversation_type

    def get_peers(self, obj) -> List[Dict[str, Any]]:
        user = self.context['request'].user
        peers = [
            p.user
            for p in obj.participants.select_related('user', 'user__chat_presence').all()
            if p.user_id != user.id
        ]
        return ChatUserBriefSerializer(peers, many=True, context=self.context).data

    def get_last_message(self, obj) -> Optional[Dict[str, Any]]:
        msg = obj.last_message
        if msg is None:
            return None
        return {
            'id': msg.id,
            'external_id': str(msg.external_id),
            'content_type': msg.message_type,
            'sender_id': str(msg.sender_id),
            'content': (msg.content or '')[:180],
            'created_at': msg.created_at.isoformat(),
            'has_attachment': msg.attachments.exists(),
        }

    def get_unread_count(self, obj) -> int:
        user = self.context['request'].user
        participant = next(
            (p for p in obj.participants.all() if p.user_id == user.id), None
        )
        pointer = last_read_message_id(obj, participant.last_read_at) if participant else 0
        return (
            obj.messages.filter(is_deleted=False).exclude(sender=user)
            .filter(id__gt=pointer).count()
        )


class ConversationCreateSerializer(serializers.Serializer):
    user_id = serializers.CharField(required=True)
    title = serializers.CharField(required=False, allow_blank=True)

    def validate_user_id(self, value):
        try:
            return User.objects.get(pk=value)
        except (User.DoesNotExist, ValueError):
            raise serializers.ValidationError('No user found with that id.')


class MessageCreateSerializer(serializers.Serializer):
    conversation_id = serializers.CharField(required=False, allow_blank=True)
    content = serializers.CharField(required=False, allow_blank=True)
    message_type = serializers.CharField(required=False, default='message')
    context = serializers.CharField(required=False, allow_blank=True, default='')
    context_id = serializers.CharField(required=False, allow_blank=True, default='')
    context_title = serializers.CharField(required=False, allow_blank=True, default='')
    client_message_id = serializers.CharField(required=False, allow_blank=True, default='')
    reply_to = serializers.IntegerField(required=False, default=None)
    file_kinds = serializers.JSONField(required=False, default=list)
    attachments = serializers.ListField(
        required=False, allow_empty=True, default=list, child=serializers.FileField()
    )


def get_or_create_direct_conversation(user_a, user_b):
    """Return or create a direct conversation between two users."""
    if user_a.id == user_b.id:
        raise serializers.ValidationError('You cannot open a conversation with yourself.')

    existing = Conversation.objects.filter(conversation_type='direct').filter(
        participants__user=user_a
    ).filter(participants__user=user_b).first()
    if existing:
        return existing

    with transaction.atomic():
        conv = Conversation.objects.create(conversation_type='direct', created_by=user_a)
        ConversationParticipant.objects.create(conversation=conv, user=user_a, role='owner')
        ConversationParticipant.objects.create(conversation=conv, user=user_b)
    return conv