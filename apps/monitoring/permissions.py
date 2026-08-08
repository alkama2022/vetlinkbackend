from rest_framework import permissions

MONITORING_ROLES = {'SYSTEM_ADMIN', 'SUPER_ADMIN'}


class IsMonitoringAdmin(permissions.BasePermission):
    """Only administrators and engineers (staff) may read/modify monitoring data."""

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False
        return (user.user_type in MONITORING_ROLES or user.is_superuser or user.is_staff)
