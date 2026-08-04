from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.apps import apps
from django.conf import settings

from .models import AuditLog
from .middleware import get_current_request
from django.db import connection


def _build_audit_payload(instance, action, request=None):
    user = getattr(request, 'user', None) if request is not None else None
    ip = None
    if request is not None:
        ip = request.META.get('REMOTE_ADDR') or request.META.get('HTTP_X_FORWARDED_FOR')

    user_id = getattr(user, 'id', None)
    username = getattr(user, 'email', '') if user is not None and getattr(user, 'is_authenticated', False) else ''
    role = getattr(user, 'user_type', '') if user is not None and getattr(user, 'is_authenticated', False) else ''

    resource_type = f"{instance._meta.app_label}.{instance._meta.model_name}"
    resource_id = str(getattr(instance, 'id', getattr(instance, 'pk', '')))

    return {
        'user_id': user_id,
        'username': username,
        'role': role,
        'ip_address': ip,
        'action': action,
        'resource_type': resource_type,
        'resource_id': resource_id,
        'summary': getattr(instance, '__str__', lambda: '')() if instance is not None else '',
        'metadata': {},
    }


@receiver(post_save)
def on_model_saved(sender, instance, created, **kwargs):
    # Avoid logging AuditLog itself to prevent recursion
    if sender.__name__ == 'AuditLog':
        return

    request = get_current_request()
    payload = _build_audit_payload(instance, 'create' if created else 'update', request=request)
    # Avoid attempting to write audit rows during migrations or before the
    # audit table exists. Check the DB table list first.
    try:
        if AuditLog._meta.db_table not in connection.introspection.table_names():
            return
    except Exception:
        return

    try:
        AuditLog.objects.create(**payload)
    except Exception:
        # Swallow exceptions to not break app flow
        pass


@receiver(post_delete)
def on_model_deleted(sender, instance, **kwargs):
    if sender.__name__ == 'AuditLog':
        return

    request = get_current_request()
    payload = _build_audit_payload(instance, 'delete', request=request)
    try:
        if AuditLog._meta.db_table not in connection.introspection.table_names():
            return
    except Exception:
        return

    try:
        AuditLog.objects.create(**payload)
    except Exception:
        pass
