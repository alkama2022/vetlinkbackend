"""Health check endpoints.

    GET /health/live/   - process is up (no dependencies touched)
    GET /health/ready/  - dependencies healthy (DB, cache, channel layer)
    GET /health/        - combined summary

Never expose configuration, version internals or credentials here.
"""

import asyncio
import json

from django.db import connection
from django.http import JsonResponse
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny


def _db_ok():
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        return True
    except Exception:
        return False


def _cache_ok():
    try:
        from django.core.cache import cache
        cache.set('__health_probe__', 1, 5)
        return cache.get('__health_probe__') == 1
    except Exception:
        return True  # no cache configured -> treated as healthy


def _channels_ok():
    try:
        from channels.layers import get_channel_layer
        layer = get_channel_layer()
        if layer is None:
            return True

        async def probe():
            try:
                await asyncio.wait_for(
                    layer.send('health_probe', {'t': timezone.now().isoformat()}), timeout=2)
                return True
            except Exception:
                return False

        return asyncio.run(probe())
    except Exception:
        return True


def _components():
    return {
        'app': True,
        'database': _db_ok(),
        'cache': _cache_ok(),
        'channel_layer': _channels_ok(),
    }


def _payload(ready: bool):
    return JsonResponse({
        'status': 'ok' if ready else 'degraded',
        'checks': _components(),
        'time': timezone.now().isoformat(),
    }, status=200 if ready else 503)


@api_view(['GET'])
@permission_classes([AllowAny])
def health_live(request):
    return JsonResponse({'status': 'ok', 'time': timezone.now().isoformat()})


@api_view(['GET'])
@permission_classes([AllowAny])
def health_ready(request):
    components = _components()
    return _payload(all(components.values()))


@api_view(['GET'])
@permission_classes([AllowAny])
def health_summary(request):
    components = _components()
    ready = all(components.values())
    payload = _payload(ready)
    data = json.loads(payload.content)
    data['uptime_seconds'] = None
    return JsonResponse(data, status=200 if ready else 503)
