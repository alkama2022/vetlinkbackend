"""Audit event signals for important business actions.

Keeps logging code OUT of business views/models: model creation events are
captured here via Django signals, using the thread-local request (set by
apps.core.middleware.ThreadLocalMiddleware) for the acting user.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.core.middleware import get_current_user, get_current_request
from apps.monitoring.services import record_event

# A registry of (model_path, event_category, action, actor_getter)
_WATCHED_MODELS = [
    ('apps.appointments.models', 'Appointment', 'APPOINTMENT', 'appointment.created', None),
    ('apps.surveillance.models', 'DiseaseReport', 'SURVEILLANCE', 'disease_report.created', None),
    ('apps.consultations.models', 'ConsultationRequest', 'CONSULTATION',
     'consultation.created', None),
    ('apps.billing.models', 'Invoice', 'BILLING', 'billing.invoice.created', None),
    ('apps.marketplace.models', 'MarketplaceListing', 'MARKETPLACE',
     'marketplace.listing.created', 'seller'),
    ('apps.community.models', 'CommunityPost', 'COMMUNITY', 'community.post.created', 'author'),
    ('apps.veterinarians.models', 'Veterinarian', 'VETERINARIAN',
     'veterinarian.registered', 'user'),
    ('apps.payments.models', 'WithdrawalRequest', 'WITHDRAWAL',
     'payment.withdrawal_requested', 'wallet.user'),
    ('apps.payments.models', 'Payment', 'PAYMENT', 'payment.initialized', 'invoice.veterinarian'),
    ('apps.chat.models', 'Conversation', 'CHAT', 'chat.conversation.created', 'created_by'),
]


def _make_handler(category, action, actor_attr):
    def handler(sender, instance, created, **kwargs):
        if not created:
            return
        request = get_current_request()
        actor = None
        if actor_attr:
            try:
                for part in actor_attr.split('.'):
                    actor = getattr(actor if actor is not None else instance, part)
            except Exception:
                actor = None
        actor = actor or get_current_user()
        details = {}
        code_attr = getattr(instance, 'get_code', None) or getattr(
            instance, 'id', None)
        record_event(
            category=category,
            action=action,
            actor=actor,
            target_type=instance._meta.model_name,
            target_id=str(getattr(instance, 'id', '')),
            details=details,
            request=request,
        )
    return handler


_registered = False


def register_monitoring_signals():
    global _registered
    if _registered:
        return
    for module_path, model_name, category, action, actor_attr in _WATCHED_MODELS:
        try:
            module = __import__(module_path, fromlist=[model_name])
            model = getattr(module, model_name)
            receiver(post_save, sender=model)(_make_handler(category, action, actor_attr))
        except Exception:
            continue
    _registered = True
