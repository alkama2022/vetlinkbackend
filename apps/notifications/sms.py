"""
SMS notification service for VetLink Kano.

Supports Africa's Talking as the primary provider. Configure via environment:
  SMS_PROVIDER= africastalking  (or 'console' for dev/stub)
  SMS_API_KEY=your_africastalking_api_key
  SMS_SENDER_ID=VETLINK
  SMS_USERNAME=your_africastalking_username

In development (SMS_PROVIDER=console), messages are logged to stdout.
"""

import logging
import os

logger = logging.getLogger('vetlink.sms')

SMS_PROVIDER = os.getenv('SMS_PROVIDER', 'console')
SMS_API_KEY = os.getenv('SMS_API_KEY', '')
SMS_USERNAME = os.getenv('SMS_USERNAME', '')
SMS_SENDER_ID = os.getenv('SMS_SENDER_ID', 'VETLINK')


def send_sms(phone_number: str, message: str) -> bool:
    """Send an SMS to the given phone number.

    Returns True if sent successfully, False otherwise.
    Never raises exceptions — failures are logged.
    """
    if not phone_number:
        logger.warning('SMS skipped: no phone number provided')
        return False

    normalized = phone_number.strip().replace(' ', '').replace('-', '')
    if not normalized.startswith('+'):
        # Assume Nigerian numbers if no country code
        if normalized.startswith('0'):
            normalized = '+234' + normalized[1:]
        else:
            normalized = '+234' + normalized

    try:
        if SMS_PROVIDER == 'africastalking':
            return _send_via_africastalking(normalized, message)
        else:
            return _send_via_console(normalized, message)
    except Exception as exc:
        logger.error('SMS failed to %s: %s', normalized, exc)
        return False


def _send_via_africastalking(phone_number: str, message: str) -> bool:
    """Send SMS via Africa's Talking API."""
    try:
        import africastalking
    except ImportError:
        logger.error('africastalking package not installed. Run: pip install africastalking')
        return False

    try:
        africastalking.initialize(
            username=SMS_USERNAME,
            api_key=SMS_API_KEY,
        )
        sms = africastalking.SMS
        response = sms.send(
            message=message,
            recipients=[phone_number],
            sender_id=SMS_SENDER_ID,
        )
        # Africa's Talking returns a dict with 'SMSMessageData'
        data = response.get('SMSMessageData', {})
        recipients = data.get('Recipients', [])
        if recipients and recipients[0].get('status') == 'Success':
            logger.info('SMS sent to %s', phone_number)
            return True
        else:
            logger.warning('SMS delivery status: %s', data)
            return False
    except Exception as exc:
        logger.error('Africa\'s Talking SMS error: %s', exc)
        return False


def _send_via_console(phone_number: str, message: str) -> bool:
    """Stub: log SMS to console (development mode)."""
    logger.info('[SMS CONSOLE STUB] To: %s | Message: %s', phone_number, message)
    print(f'[SMS] To: {phone_number}\nMessage: {message}\n')
    return True


# ─── High-level notification helpers ──────────────────────────────────────────

def notify_disease_report_created(report, farmer_phone: str) -> bool:
    """Send SMS to farmer confirming disease report submission."""
    message = (
        f'VetLink: Your disease report {report.report_code} for {report.disease} '
        f'has been received. A government officer will review it shortly. '
        f'Report status: {report.alert_status}.'
    )
    return send_sms(farmer_phone, message)


def notify_disease_report_status_changed(report, farmer_phone: str) -> bool:
    """Notify farmer when their disease report status changes."""
    message = (
        f'VetLink: Your disease report {report.report_code} status has been updated to '
        f'{report.alert_status}.'
    )
    return send_sms(farmer_phone, message)


def notify_appointment_reminder(appointment, phone: str) -> bool:
    """Send appointment reminder SMS."""
    message = (
        f'VetLink Reminder: You have an appointment on {appointment.date} at {appointment.time}. '
        f'Please arrive on time.'
    )
    return send_sms(phone, message)


def notify_drug_stock_low(drug_name: str, current_qty: int, phone: str) -> bool:
    """Notify clinic admin when drug stock is low."""
    message = (
        f'VetLink Alert: {drug_name} stock is low ({current_qty} remaining). '
        f'Please restock soon.'
    )
    return send_sms(phone, message)


def notify_consultation_assigned(consultation, vet_phone: str) -> bool:
    """Notify a vet when a consultation is assigned to them."""
    message = (
        f'VetLink: You have been assigned consultation {consultation.consultation_code} '
        f'from {consultation.farmer_name}. Species: {consultation.species}.'
    )
    return send_sms(vet_phone, message)
