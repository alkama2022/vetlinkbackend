"""Channel-layer helpers used by both REST views and the WebSocket consumer."""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

PRESENCE_GROUP = 'presence_broadcast'


def user_group(user_id):
    return f'user_{user_id}'


async def abroadcast_to_users(user_ids, event):
    """Send an event dict to each user's personal channel group (async)."""
    layer = get_channel_layer()
    for uid in user_ids:
        await layer.group_send(user_group(uid), event)


def broadcast_to_users(user_ids, event):
    async_to_sync(abroadcast_to_users)(user_ids, event)


async def abroadcast_presence(event):
    layer = get_channel_layer()
    await layer.group_send(PRESENCE_GROUP, event)


def broadcast_presence(event):
    async_to_sync(abroadcast_presence)(event)