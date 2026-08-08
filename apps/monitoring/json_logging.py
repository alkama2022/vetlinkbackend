"""Structured JSON logging formatter (production logs)."""

import json
import logging
import traceback


class JsonFormatter(logging.Formatter):
    """Emit one JSON object per log line: machine-readable for log shippers."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            'timestamp': self.formatTime(record, self.datefmt or '%Y-%m-%dT%H:%M:%S%z'),
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
        }
        if record.exc_info:
            payload['exception'] = ''.join(
                traceback.format_exception(*record.exc_info))
        if hasattr(record, 'correlation_id'):
            payload['correlation_id'] = record.correlation_id
        try:
            return json.dumps(payload, ensure_ascii=False)
        except Exception:
            return super().format(record)
