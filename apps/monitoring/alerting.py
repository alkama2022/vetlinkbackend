"""Pluggable alerting service.

Handlers are registered at runtime (e.g. in settings or app ready()) and receive
an `Alert` model instance. No external service is hardcoded here; future
integrations (Email, Slack, Discord, PagerDuty, OpsGenie, Datadog...) simply
register a handler.

Default handler logs the alert to the 'monitoring.alerts' logger (ERROR level),
which the configured logging setup routes to the production JSON sink.
"""

import logging
from typing import Callable, List

from django.conf import settings

from apps.monitoring.models import Alert, ErrorLog, LogSeverity

alert_logger = logging.getLogger('monitoring.alerts')

_handlers: List[Callable[[Alert], None]] = []


def register_alert_handler(fn: Callable[[Alert], None]) -> None:
    """Register a callable that receives every fired Alert."""
    _handlers.append(fn)


def _default_handler(alert: Alert) -> None:
    alert_logger.error(
        'ALERT [%s] %s: %s (module=%s, correlation=%s)',
        alert.alert_id, alert.severity, alert.title, alert.module, alert.correlation_id,
    )


register_alert_handler(_default_handler)


def _min_severity() -> str:
    return getattr(settings, 'MONITORING_SETTINGS', {}).get(
        'ALERT_MIN_SEVERITY', LogSeverity.ERROR)


_SEVERITY_RANK = {
    LogSeverity.DEBUG: 0,
    LogSeverity.INFO: 1,
    LogSeverity.WARNING: 2,
    LogSeverity.ERROR: 3,
    LogSeverity.CRITICAL: 4,
}


def fire_alert(
    *, title: str, message: str = '', severity: str = LogSeverity.ERROR,
    category: str = 'SYSTEM', module: str = '', correlation_id: str = '',
    error: ErrorLog = None,
) -> Alert:
    """Create an Alert and fan it out to all registered handlers."""
    if _SEVERITY_RANK.get(severity, 3) < _SEVERITY_RANK.get(_min_severity(), 3):
        raise ValueError(f'severity {severity} below alert threshold {_min_severity()}')
    alert = Alert.objects.create(
        title=truncate_(title, 255),
        message=truncate_(message, 4000),
        severity=severity,
        category=category,
        module=truncate_(module, 255),
        correlation_id=truncate_(correlation_id, 64),
        error=error,
    )
    for handler in _handlers:
        try:
            handler(alert)
        except Exception:  # pragma: no cover - defensive
            alert_logger.exception('alert handler failed for %s', alert.alert_id)
    return alert


def truncate_(value, length):
    return value if not value or len(value) <= length else value[:length]
