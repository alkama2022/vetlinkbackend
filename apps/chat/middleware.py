"""
WebSocket authentication for the chat endpoint.

The frontend connects to ``/ws/chat/?token=<JWT access token>``. The token is
validated with djangorestframework-simplejwt and the resolved user is placed in
``scope['user']`` before the consumer runs.
"""

import json
from urllib.parse import parse_qs

from channels.db import database_sync_to_async


class JWTAuthMiddleware:
    """Wrap an ASGI websocket application with JWT query-string auth."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        scope_copy = dict(scope)
        query = parse_qs(scope['query_string'].decode('utf-8', errors='ignore'))
        token = (query.get('token') or [None])[0]
        scope_copy['user'] = await self.resolve_user(token)
        return await self.inner(scope_copy, receive, send)

    @database_sync_to_async
    def resolve_user(self, token):
        if not token:
            return None
        try:
            from rest_framework_simplejwt.tokens import AccessToken

            from apps.accounts.models import User

            access = AccessToken(token)
            return User.objects.filter(pk=access['user_id'], is_active=True).first()
        except Exception:
            return None


def parse_text(data: bytes):
    """Best-effort JSON parse of an incoming websocket frame."""
    try:
        return json.loads(data.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        return {}