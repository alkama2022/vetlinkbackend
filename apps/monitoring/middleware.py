"""Middleware for correlation IDs, request error capture and performance tracking."""

import logging
import time
import uuid

from django.conf import settings

from apps.monitoring.alerting import fire_alert
from apps.monitoring.models import LogCategory, LogSeverity, LogSource
from apps.monitoring.services import capture_error

logger = logging.getLogger('monitoring')

_SKIPPED_PREFIXES = ('/static/', '/media/', '/admin/', '/health', '/api/schema')

_MONITORING_FLAG = '_monitoring_logged'


class CorrelationIdMiddleware:
    """Attach a correlation ID to every request.

    Accepts an upstream X-Correlation-ID header (e.g. from the frontend),
    generates one otherwise, and echoes it back on the response so errors can
    be traced across systems.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.headers.get('X-Correlation-ID', '').strip()
        request.correlation_id = (incoming[:64] or uuid.uuid4().hex[:16].upper())
        response = self.get_response(request)
        response['X-Correlation-ID'] = request.correlation_id
        return response


class RequestLoggingMiddleware:
    """Capture unhandled exceptions, HTTP errors and slow requests.

    DRF-handled API errors are captured by the DRF exception handler
    (apps.monitoring.exception_handler) which marks the request with
    `_monitoring_logged`; this middleware only logs what that handler did not:
      * unhandled exceptions (non-DRF views / middleware errors),
      * slow API requests (configurable thresholds),
      * 401 / 403 / 429 responses that escaped the handler (e.g. session auth).
    """

    def __init__(self, get_response):
        self.get_response = get_response
        mon = getattr(settings, 'MONITORING_SETTINGS', {})
        self.slow_warning_ms = mon.get('API_SLOW_WARNING_MS', 2000)
        self.slow_error_ms = mon.get('API_SLOW_ERROR_MS', 5000)

    def _skip(self, path: str) -> bool:
        return any(path.startswith(p) for p in _SKIPPED_PREFIXES)

    def __call__(self, request):
        start = time.perf_counter()
        response = None
        try:
            response = self.get_response(request)
        except Exception as exc:
            if not self._skip(request.path):
                capture_error(
                    message=f'Unhandled exception: {exc}',
                    severity=LogSeverity.ERROR,
                    category=LogCategory.SYSTEM,
                    module='django.middleware',
                    source=LogSource.BACKEND,
                    request=request,
                    exc=exc,
                    status_code=500,
                )
            raise
        finally:
            duration_ms = int((time.perf_counter() - start) * 1000)

        path = request.path
        if self._skip(path):
            return response

        already_logged = getattr(request, _MONITORING_FLAG, False)
        status = getattr(response, 'status_code', 0)
        request.user  # ensure user is resolved so middleware never reads lazy proxies

        # Slow request detection (configurable thresholds).
        if duration_ms >= self.slow_error_ms:
            log = capture_error(
                message=f'API request {request.method} {path} took {duration_ms}ms '
                        f'(threshold {self.slow_error_ms}ms)',
                severity=LogSeverity.ERROR,
                category=LogCategory.PERFORMANCE,
                module='django.http',
                source=LogSource.BACKEND,
                request=request,
                method=request.method,
                endpoint=path,
                status_code=status,
                duration_ms=duration_ms,
            )
            if log:
                fire_alert(
                    title=f'Slow API request: {request.method} {path} ({duration_ms}ms)',
                    severity=LogSeverity.ERROR,
                    category=LogCategory.PERFORMANCE,
                    module='django.http',
                    correlation_id=getattr(request, 'correlation_id', ''),
                    error=log,
                )
        elif duration_ms >= self.slow_warning_ms:
            capture_error(
                message=f'API request {request.method} {path} took {duration_ms}ms '
                        f'(threshold {self.slow_warning_ms}ms)',
                severity=LogSeverity.WARNING,
                category=LogCategory.PERFORMANCE,
                module='django.http',
                source=LogSource.BACKEND,
                request=request,
                method=request.method,
                endpoint=path,
                status_code=status,
                duration_ms=duration_ms,
            )

        # Unhandled 5xx that escaped DRF's exception handler (plain views,
        # middleware errors, response-phase failures).
        if not already_logged and status >= 500:
            capture_error(
                message=f'Unhandled exception: {request.method} {path} returned {status}',
                severity=LogSeverity.ERROR,
                category=LogCategory.SYSTEM,
                module='django.middleware',
                source=LogSource.BACKEND,
                request=request,
                method=request.method,
                endpoint=path,
                status_code=status,
            )

        # Auth / permission / rate-limit events not already handled by DRF.
        if not already_logged and status in (401, 403, 429):
            category = LogCategory.PERMISSION if status == 403 else (
                LogCategory.SECURITY if status == 429 else LogCategory.AUTH)
            capture_error(
                message=f'{request.method} {path} returned {status}',
                severity=LogSeverity.WARNING,
                category=category,
                module='django.http',
                source=LogSource.BACKEND,
                request=request,
                method=request.method,
                endpoint=path,
                status_code=status,
            )

        return response
