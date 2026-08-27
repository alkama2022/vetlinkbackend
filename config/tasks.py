from celery import shared_task
from django.utils import timezone


@shared_task
def check_drug_expiry():
    """Check for expired and expiring-soon drugs."""
    from django.core.management import call_command
    call_command('check_drug_expiry', '--days=30')


@shared_task
def send_appointment_reminders():
    """Send SMS reminders for upcoming appointments."""
    from datetime import date, timedelta
    from apps.appointments.models import Appointment
    from apps.notifications.sms import send_sms

    tomorrow = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
    appointments = Appointment.objects.filter(
        date=tomorrow, status='Scheduled'
    ).select_related('patient')

    for appt in appointments:
        try:
            # Look up owner phone from patient or appointment
            phone = getattr(appt.patient, 'owner_phone', '') if appt.patient else ''
            if phone:
                send_sms(
                    phone,
                    f'VetLink Reminder: Appointment for {appt.animal} tomorrow at {appt.time}. '
                    f'Reason: {appt.reason}.'
                )
        except Exception:
            pass


@shared_task
def cleanup_old_notifications():
    """Archive notifications older than 90 days."""
    from datetime import timedelta
    from apps.notifications.models import Notification

    cutoff = timezone.now() - timedelta(days=90)
    deleted, _ = Notification.objects.filter(created_at__lt=cutoff).delete()
    return f'Archived {deleted} old notifications'
