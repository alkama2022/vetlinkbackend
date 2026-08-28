import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class Conversation(TimeStampedModel):
    """
    A private chat conversation between exactly two users.

    Messages belong to one conversation; only the participants may read or write
    to it, which is the backbone of conversation privacy.
    """

    class TypeChoices(models.TextChoices):
        DIRECT = 'direct', 'Direct'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation_type = models.CharField(
        max_length=20, choices=TypeChoices.choices, default=TypeChoices.DIRECT
    )
    title = models.CharField(max_length=255, blank=True, default='')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_conversations_created',
    )
    last_message_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['-last_message_at']

    @property
    def last_message(self):
        """Latest non-deleted message (cached on the instance)."""
        if not hasattr(self, '_last_message_obj'):
            self._last_message_obj = self.messages.filter(is_deleted=False).order_by('-id').first()
        return self._last_message_obj

    def __str__(self):
        return f'Conversation {self.id} ({self.conversation_type})'


class ConversationParticipant(TimeStampedModel):
    class RoleChoices(models.TextChoices):
        OWNER = 'owner', 'Owner'
        MEMBER = 'member', 'Member'

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='participants'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_participants'
    )
    role = models.CharField(
        max_length=20, choices=RoleChoices.choices, default=RoleChoices.MEMBER
    )
    last_read_at = models.DateTimeField(null=True, blank=True, db_index=True)
    muted_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [('conversation', 'user')]
        ordering = ['created_at']

    def __str__(self):
        return f'{self.user.full_name} in {self.conversation_id}'


class Message(models.Model):
    """
    A single chat message. Uses a BigAuto primary key so cursor pagination is
    always exact and cheap, independent of timestamps.
    """

    class TypeChoices(models.TextChoices):
        MESSAGE = 'message', 'Text'
        IMAGE = 'image', 'Image'
        VIDEO = 'video', 'Video'
        VOICE = 'voice', 'Voice note'
        AUDIO = 'audio', 'Audio'
        DOCUMENT = 'document', 'Document'
        ANIMAL = 'animal', 'Animal photo/info'
        LAB_RECORD = 'lab_record', 'Laboratory record'
        DISEASE_REPORT = 'disease_report', 'Disease report'
        PRESCRIPTION = 'prescription', 'Prescription'
        LOCATION = 'location', 'Location'
        SYSTEM = 'system', 'System'

    id = models.BigAutoField(primary_key=True)
    external_id = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_messages'
    )
    message_type = models.CharField(
        max_length=30, choices=TypeChoices.choices, default=TypeChoices.MESSAGE, db_index=True
    )
    content = models.TextField(blank=True, default='')

    # Medical/domain context attachment — a thin link to a platform record
    # (animal, disease report, appointment, prescription) so the recipient can
    # open supporting context without leaving the chat.
    context = models.CharField(max_length=40, blank=True, default='', db_index=True)
    context_id = models.CharField(max_length=255, blank=True, default='')
    context_title = models.CharField(max_length=255, blank=True, default='')

    # Client-generated id for safe retries (deduplication)
    client_message_id = models.CharField(max_length=120, blank=True, default='', db_index=True)
    reply_to = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies'
    )

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['id']
        indexes = [
            models.Index(fields=['conversation', '-id']),
            models.Index(fields=['conversation', 'sender', 'id']),
        ]

    def read_by(self):
        return list(self.read_receipts.values_list('user_id', flat=True))

    def __str__(self):
        return f'Message {self.id} in {self.conversation_id} from {self.sender_id}'

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])


class MessageAttachment(TimeStampedModel):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='chat/%Y/%m/%d/')
    filename = models.CharField(max_length=255, blank=True, default='')
    mime_type = models.CharField(max_length=120, blank=True, default='')
    size = models.PositiveIntegerField(default=0)
    kind = models.CharField(max_length=30, default='document', db_index=True)

    def __str__(self):
        return self.filename or self.file.name


class MessageReadReceipt(TimeStampedModel):
    """Read status per message per user."""

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='read_receipts')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_read_receipts'
    )

    class Meta:
        unique_together = [('message', 'user')]
        indexes = [models.Index(fields=['message', 'user'])]

    def __str__(self):
        return f'read {self.message_id} by user {self.user_id}'


class UserPresence(models.Model):
    """
    Runtime presence. The online counter is incremented per connected socket so
    multiple tabs work correctly; last_seen_at persists the offline marker.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_presence'
    )
    online_count = models.PositiveIntegerField(default=0)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    def is_online(self):
        return self.online_count > 0

    def __str__(self):
        return f'{self.user.username}: online={self.is_online()}'


class ChatBlock(models.Model):
    """Block abuse / spam. A block stops either party creating messages."""

    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_blocks'
    )
    blocked = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_blocked'
    )
    reason = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [('blocker', 'blocked')]

    def __str__(self):
        return f'{self.blocker_id} blocked {self.blocked_id}'


def is_blocked(user_a, user_b):
    return (
        ChatBlock.objects.filter(blocker=user_a, blocked=user_b).exists()
        or ChatBlock.objects.filter(blocker=user_b, blocked=user_a).exists()
    )


def get_presence(user):
    presence, _ = UserPresence.objects.get_or_create(user=user)
    return presence