"""DRF exception handler that records API errors into the central ErrorLog.

The handler marks `request._monitoring_logged` so the request-logging middleware
does not double-log the same event.
"""

from rest_framework import status as http_status
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    Throttled,
    ValidationError,
)
from rest_framework.views import exception_handler as drf_exception_handler

from apps.monitoring.alerting import fire_alert
from apps.monitoring.models import LogCategory, LogSeverity, LogSource
from apps.monitoring.services import LOG_FLAG, capture_error, mark_request_logged

_LOGGED = LOG_FLAG


def monitoring_exception_handler(exc, context):
    """Wrap DRF's default handler with centralized error capture."""
    request = context.get('request')
    response = drf_exception_handler(exc, context)

    if request is None:
        return response
    if response is not None:
        response['X-Correlation-ID'] = getattr(request, 'correlation_id', '')

    status_code = getattr(response, 'status_code', None) if response else 500

    category = LogCategory.SYSTEM
    severity = LogSeverity.ERROR
    log_it = True

    if isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
        category = LogCategory.AUTH
        severity = LogSeverity.WARNING
    elif isinstance(exc, PermissionDenied):
        category = LogCategory.PERMISSION
        severity = LogSeverity.WARNING
    elif isinstance(exc, Throttled):
        category = LogCategory.SECURITY
        severity = LogSeverity.WARNING
    elif isinstance(exc, ValidationError):
        log_it = False  # business validation is not an error event
    elif status_code and status_code < 500:
        log_it = False  # other 4xx (404/405/...): skip to avoid noise

    if log_it and not getattr(request, _LOGGED, False):
        log = capture_error(
            message=str(getattr(exc, 'detail', exc) or exc),
            severity=severity,
            category=category,
            module=_module_for(request),
            source=LogSource.BACKEND,
            request=request,
            exc=exc if status_code and status_code >= 500 else None,
            status_code=status_code,
        )
        mark_request_logged(request)
        if status_code and status_code >= 500:
            fire_alert(
                title=f'{severity}: {request.method} {request.path}',
                message=str(getattr(exc, 'detail', exc) or exc),
                severity=LogSeverity.ERROR if severity != LogSeverity.CRITICAL else severity,
                category=category,
                module=_module_for(request),
                correlation_id=getattr(request, 'correlation_id', ''),
                error=log,
            )

    return response


def _module_for(request) -> str:
    try:
        return request.resolver_match.view_name or 'api'
    except Exception:
        return 'api'
