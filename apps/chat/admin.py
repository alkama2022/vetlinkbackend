from django.contrib import admin

from apps.chat.models import (
    ChatBlock,
    Conversation,
    ConversationParticipant,
    Message,
    MessageAttachment,
    MessageReadReceipt,
    UserPresence,
)


class ParticipantInline(admin.TabularInline):
    model = ConversationParticipant
    extra = 0


class AttachmentInline(admin.TabularInline):
    model = MessageAttachment
    extra = 0


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation_type', 'title', 'last_message_at', 'created_at']
    inlines = [ParticipantInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'sender', 'message_type', 'created_at', 'is_deleted']
    list_filter = ['message_type', 'is_deleted', 'created_at']
    search_fields = ['content']
    inlines = [AttachmentInline]


@admin.register(ConversationParticipant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'user', 'role', 'last_read_at']


@admin.register(MessageReadReceipt)
class ReadReceiptAdmin(admin.ModelAdmin):
    list_display = ['id', 'message', 'user', 'created_at']


@admin.register(UserPresence)
class PresenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'online_count', 'last_seen_at']


@admin.register(ChatBlock)
class ChatBlockAdmin(admin.ModelAdmin):
    list_display = ['blocker', 'blocked', 'reason', 'created_at']