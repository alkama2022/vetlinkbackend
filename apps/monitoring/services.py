"""Centralized logging services.

All backend error/audit/performance capture goes through this module so that
business code never needs to know how logs are stored.

Key helpers:
    capture_error(...)          - store one ErrorLog row
    capture_exception(...)      - convenience wrapper around capture_error for a Python exception
    capture_performance(...)    - record a slow operation (API/query/task)
    record_event(...)           - store one audit SystemEvent row
    sanitize_dict(...)          - strip secrets before persistence
"""

import logging
import re
import traceback as tb
from typing import Any, Dict, Optional

from django.conf import settings

from apps.monitoring.models import (
    ErrorLog,
    LogCategory,
    LogResolutionStatus,
    LogSeverity,
    LogSource,
    SystemEvent,
)

logger = logging.getLogger('monitoring')

LOG_FLAG = '_monitoring_logged'


def mark_request_logged(request) -> None:
    """Mark a request as already captured so middleware does not double-log.

    DRF's Request wrapper forwards attribute reads to the underlying
    HttpRequest but NOT writes, so the flag must be set on both objects.
    """
    setattr(request, LOG_FLAG, True)
    inner = getattr(request, '_request', None)
    if inner is not None and inner is not request:
        setattr(inner, LOG_FLAG, True)

_SECRET_KEY_RE = re.compile(
    r'(password|passwd|pwd|token|refresh|access_token|secret|api[_-]?key|authorization'
    r'|credit_card|card_number|cvv|client_secret|private_key|auth|bearer)',
    re.IGNORECASE,
)


def environment() -> str:
    return getattr(settings, 'ENVIRONMENT', 'development')


def truncate(value: str, max_length: int) -> str:
    if not value:
        return ''
    return value if len(value) <= max_length else value[:max_length]


def sanitize_dict(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Recursively remove secret-looking keys/values before persistence."""
    if not isinstance(data, dict):
        return {}
    result: Dict[str, Any] = {}
    for key, value in data.items():
        if _SECRET_KEY_RE.search(str(key)):
            result[key] = '[REDACTED]'
            continue
        if isinstance(value, dict):
            result[key] = sanitize_dict(value)
        elif isinstance(value, (list, tuple)):
            result[key] = [
                sanitize_dict(item) if isinstance(item, dict) else item for item in value
            ]
        elif isinstance(value, str) and len(value) > 2000:
            result[key] = truncate(value, 2000)
        else:
            result[key] = value
    return result


def sanitize_message(message: str) -> str:
    """Sanitize free-text messages (e.g. stack traces) for obvious secrets."""
    message = re.sub(r'(Bearer\s+)[A-Za-z0-9._\-]+', r'\1[REDACTED]', message)
    message = re.sub(r'https?://\S+:(\S+)@', r'https://[REDACTED]@', message)
    return message


def _config(name: str, default):
    return getattr(settings, 'MONITORING_SETTINGS', {}).get(name, default)


def capture_error(
    *,
    message: str,
    severity: str = LogSeverity.ERROR,
    category: str = LogCategory.SYSTEM,
    module: str = '',
    source: str = LogSource.BACKEND,
    request=None,
    exc: Optional[BaseException] = None,
    user=None,
    endpoint: str = '',
    method: str = '',
    status_code: Optional[int] = None,
    exception_type: str = '',
    stack_trace: str = '',
    correlation_id: str = '',
    duration_ms: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: str = '',
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[ErrorLog]:
    """Persist one ErrorLog row. Never raises; logs to the Python logger on failure."""
    try:
        if request is not None:
            user = user or getattr(request, 'user', None)
            if user and getattr(user, 'is_authenticated', False):
                pass  # keep user
            else:
                user = None
            endpoint = endpoint or request.path
            method = method or request.method
            correlation_id = correlation_id or getattr(request, 'correlation_id', '')
            ip_address = ip_address or _client_ip(request)
            user_agent = user_agent or request.META.get('HTTP_USER_AGENT', '')[:512]
            user_role = getattr(user, 'user_type', '') if user else ''
        else:
            user_role = getattr(user, 'user_type', '') if user else ''

        if exc is not None:
            exception_type = exception_type or f'{type(exc).__module__}.{type(exc).__name__}'
            if not stack_trace:
                stack_trace = ''.join(
                    tb.format_exception(type(exc), exc, exc.__traceback__))

        max_message = _config('MAX_MESSAGE_LENGTH', 4000)
        max_trace = _config('MAX_STACKTRACE_LENGTH', 8000)

        log = ErrorLog.objects.create(
            severity=severity,
            category=category,
            source=source,
            module=truncate(module, 255),
            endpoint=truncate(endpoint, 500),
            method=method,
            status_code=status_code,
            user=user if (user and getattr(user, 'is_authenticated', False)) else None,
            user_role=user_role,
            correlation_id=truncate(correlation_id, 64),
            exception_type=truncate(exception_type, 255),
            message=truncate(sanitize_message(str(message)), max_message),
            stack_trace=truncate(sanitize_message(stack_trace), max_trace),
            environment=environment(),
            duration_ms=duration_ms,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=sanitize_dict(metadata or {}),
        )
        logger.log(logging.DEBUG if severity == LogSeverity.DEBUG else logging.INFO,
                   'error captured: %s [%s] %s', log.error_id, severity, message[:120])
        return log
    except Exception as exc_log:  # pragma: no cover - defensive
        logger.exception('failed to capture error: %s', exc_log)
        return None


def capture_exception(request, exc: BaseException, *, category: str = LogCategory.SYSTEM,
                      severity: str = LogSeverity.ERROR, module: str = '',
                      status_code: Optional[int] = None) -> Optional[ErrorLog]:
    return capture_error(
        message=str(exc),
        severity=severity,
        category=category,
        module=module,
        source=LogSource.BACKEND,
        request=request,
        exc=exc,
        status_code=status_code,
    )


def capture_performance(
    *, module: str, endpoint: str = '', method: str = '', duration_ms: int,
    severity: str = LogSeverity.WARNING, category: str = LogCategory.PERFORMANCE,
    correlation_id: str = '', request=None, metadata: Optional[Dict[str, Any]] = None,
) -> Optional[ErrorLog]:
    return capture_error(
        message=f'{module} took {duration_ms}ms',
        severity=severity,
        category=category,
        module=module,
        source=LogSource.BACKEND,
        request=request,
        endpoint=endpoint,
        method=method,
        duration_ms=duration_ms,
        correlation_id=correlation_id,
        metadata=metadata,
    )


def record_event(
    *, category: str, action: str, actor=None, actor_role: str = '',
    target_type: str = '', target_id: str = '',
    details: Optional[Dict[str, Any]] = None,
    request=None, ip_address: Optional[str] = None, correlation_id: str = '',
) -> Optional[SystemEvent]:
    """Persist one audit SystemEvent row. Never raises."""
    try:
        if request is not None:
            correlation_id = correlation_id or getattr(request, 'correlation_id', '')
            ip_address = ip_address or _client_ip(request)
            actor = actor or getattr(request, 'user', None)
        actor_role = actor_role or (getattr(actor, 'user_type', '') if actor else '')
        event = SystemEvent.objects.create(
            category=category,
            action=truncate(action, 120),
            actor=actor if (actor and getattr(actor, 'is_authenticated', False)) else None,
            actor_role=actor_role,
            target_type=truncate(target_type, 100),
            target_id=truncate(str(target_id), 64),
            details=sanitize_dict(details or {}),
            ip_address=ip_address,
            correlation_id=truncate(correlation_id, 64),
        )
        logger.debug('event recorded: %s:%s', category, action)
        return event
    except Exception as exc_log:  # pragma: no cover - defensive
        logger.exception('failed to record event: %s', exc_log)
        return None


def _client_ip(request) -> Optional[str]:
    if request is None:
        return None
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')
