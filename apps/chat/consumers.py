"""WebSocket consumer for the chat system.

Every authenticated user joins a personal channel group (``user_<id>``) and the
``presence_broadcast`` group. Messages, read receipts and read state are pushed
by the REST views to the participants' personal groups; the consumer handles
typing indicators, presence, and heartbeat pings in real time.
"""

import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

from apps.chat.models import (
    Conversation,
    ConversationParticipant,
    UserPresence,
    is_blocked,
)
from apps.chat.ws import PRESENCE_GROUP, user_group

UNAUTHENTICATED = 4001
MALFORMED = 4400


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get('user')
        if self.user is None or not getattr(self.user, 'is_authenticated', False):
            await self.close(code=UNAUTHENTICATED)
            return

        self.user_group = user_group(self.user.id)
        await self.channel_layer.group_add(self.user_group, self.channel_name)
        await self.channel_layer.group_add(PRESENCE_GROUP, self.channel_name)

        await self.go_online()
        await self.accept()
        await self.send_json({'type': 'ready', 'payload': {'user_id': str(self.user.id)}})

    async def disconnect(self, code):
        if not hasattr(self, 'user_group'):
            return
        await self.go_offline()
        await self.channel_layer.group_discard(self.user_group, self.channel_name)
        await self.channel_layer.group_discard(PRESENCE_GROUP, self.channel_name)

    # ── Inbound handlers ─────────────────────────────────────────────────────

    async def receive(self, text_data=None, bytes_data=None):
        try:
            payload = json.loads(text_data or '{}')
        except (ValueError, TypeError):
            await self.send_json({'type': 'error', 'payload': MALFORMED})
            return

        kind = payload.get('type')
        data = payload.get('payload') or {}

        if kind == 'ping':
            await self.send_json({'type': 'pong'})
        elif kind == 'typing':
            await self.handle_typing(data)
        elif kind == 'read.conversation':
            await self.handle_read(data)

    async def handle_typing(self, data):
        conversation_id = data.get('conversation_id')
        if not conversation_id:
            return
        if not await sync_to_async(self.is_participant)(conversation_id):
            return
        peers = await sync_to_async(self.peer_ids)(conversation_id)
        await self.broadcast_to(peers, 'typing', {
            'conversation_id': str(conversation_id),
            'user': {'id': str(self.user.id), 'full_name': self.user.full_name},
            'is_typing': bool(data.get('is_typing')),
        })

    async def handle_read(self, data):
        conversation_id = data.get('conversation_id')
        if not conversation_id or not await sync_to_async(self.is_participant)(conversation_id):
            return
        peers = await sync_to_async(self.peer_ids)(conversation_id)
        await self.broadcast_to(peers, 'conversation.read', {
            'conversation_id': str(conversation_id),
            'reader_id': str(self.user.id),
        })

    # ── Presence ─────────────────────────────────────────────────────────────

    async def go_online(self):
        await sync_to_async(self._set_online)(True)

    async def go_offline(self):
        await sync_to_async(self._set_online)(False)

    def _set_online(self, online):
        presence, _ = UserPresence.objects.get_or_create(user=self.user)
        if online:
            presence.online_count += 1
        else:
            presence.online_count = max(0, presence.online_count - 1)
        update_fields = {'online_count'}
        if not online and presence.online_count == 0:
            presence.last_seen_at = timezone.now()
            update_fields.add('last_seen_at')
        presence.save(update_fields=list(update_fields))
        return presence

    # ── DB helpers ───────────────────────────────────────────────────────────

    def is_participant(self, conversation_id):
        try:
            conv = Conversation.objects.get(id=conversation_id)
        except (Conversation.DoesNotExist, ValueError, TypeError):
            return False
        if not ConversationParticipant.objects.filter(conversation=conv, user=self.user).exists():
            return False
        other = (
            ConversationParticipant.objects.filter(conversation=conv)
            .exclude(user=self.user)
            .first()
        )
        if other and is_blocked(self.user, other.user):
            return False
        return True

    def peer_ids(self, conversation_id):
        ids = list(
            ConversationParticipant.objects.filter(conversation_id=conversation_id)
            .values_list('user_id', flat=True)
        )
        return [uid for uid in ids if uid != self.user.id]

    async def broadcast_to(self, user_ids, event_type, payload):
        from apps.chat.ws import abroadcast_to_users

        await abroadcast_to_users(user_ids, {'type': event_type, 'payload': payload})

    # ── Relay of groups going out over this socket ──────────────────────────

    async def message_new(self, event):
        await self.send_json({'type': 'message.new', 'payload': event['payload']})

    async def message_updated(self, event):
        await self.send_json({'type': 'message.updated', 'payload': event['payload']})

    async def message_deleted(self, event):
        await self.send_json({'type': 'message.deleted', 'payload': event['payload']})

    async def conversation_read(self, event):
        await self.send_json({'type': 'conversation.read', 'payload': event['payload']})

    async def conversation_updated(self, event):
        await self.send_json({'type': 'conversation.updated', 'payload': event['payload']})

    async def typing(self, event):
        await self.send_json({'type': 'typing', 'payload': event['payload']})

    async def presence(self, event):
        await self.send_json({'type': 'presence', 'payload': event['payload']})

    async def send_json(self, data):
        await self.send(text_data=json.dumps(data))