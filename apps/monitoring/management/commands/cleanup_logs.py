"""Retention policy for monitoring data.

Workflow:
  1. `archive`  - mark old logs/events as archived (soft retention).
  2. `purge`    - hard-delete archived rows older than the retention window.

Defaults come from settings.MONITORING_SETTINGS:
  LOG_RETENTION_DAYS    (default 180)
  EVENT_RETENTION_DAYS  (default 365)

Future work: stream archived rows to object storage / external monitoring
before purging (see docs on retention).
"""

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.monitoring.models import ErrorLog, Incident, SystemEvent


def _cfg(name, default):
    return getattr(settings, 'MONITORING_SETTINGS', {}).get(name, default)


class Command(BaseCommand):
    help = 'Archive and purge old monitoring logs per the retention policy.'

    def add_arguments(self, parser):
        parser.add_argument('--archive', action='store_true',
                            help='Mark rows older than retention as archived.')
        parser.add_argument('--purge', action='store_true',
                            help='Delete archived rows older than retention.')
        parser.add_argument('--log-days', type=int, default=None,
                            help='Override log retention window (days).')
        parser.add_argument('--event-days', type=int, default=None,
                            help='Override event retention window (days).')

    def handle(self, *args, **options):
        log_days = options['log_days'] or _cfg('LOG_RETENTION_DAYS', 180)
        event_days = options['event_days'] or _cfg('EVENT_RETENTION_DAYS', 365)

        log_cutoff = timezone.now() - timedelta(days=log_days)
        event_cutoff = timezone.now() - timedelta(days=event_days)

        if options['archive']:
            n_logs = ErrorLog.objects.filter(timestamp__lt=log_cutoff,
                                             archived=False).update(archived=True)
            n_events = SystemEvent.objects.filter(timestamp__lt=event_cutoff,
                                                  archived=False).update(archived=True)
            self.stdout.write(self.style.SUCCESS(
                f'Archived {n_logs} error logs, {n_events} system events.'))

        if options['purge']:
            n_logs, _ = ErrorLog.objects.filter(archived=True,
                                                timestamp__lt=log_cutoff).delete()
            n_events, _ = SystemEvent.objects.filter(archived=True,
                                                     timestamp__lt=event_cutoff).delete()
            n_incidents, _ = Incident.objects.filter(
                created_at__lt=timezone.now() - timedelta(days=730)).delete()
            self.stdout.write(self.style.SUCCESS(
                f'Purged {n_logs} logs, {n_events} events, {n_incidents} incidents.'))

        if not options['archive'] and not options['purge']:
            self.stdout.write(
                'No action requested. Use --archive and/or --purge. '
                f'(log retention: {log_days}d, event retention: {event_days}d)')
