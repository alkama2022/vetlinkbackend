from __future__ import annotations

import threading
from typing import Optional

_thread_locals = threading.local()


def get_current_request() -> Optional[object]:
    return getattr(_thread_locals, 'request', None)


def get_current_user() -> Optional[object]:
    req = get_current_request()
    if not req:
        return None
    return getattr(req, 'user', None)


class ThreadLocalMiddleware:
    """Middleware that stores the current request in thread local storage.

    This allows signal handlers and model save hooks to access the requesting
    user and IP address when creating audit entries.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.request = request
        try:
            response = self.get_response(request)
            return response
        finally:
            # Avoid leaking request objects between requests
            try:
                del _thread_locals.request
            except Exception:
                pass