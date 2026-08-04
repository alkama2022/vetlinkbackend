from rest_framework import permissions


class RolePermission(permissions.BasePermission):
    """Allow access only to users whose `user_type` is included in allowed roles.

    This class is intended to be subclassed or instantiated through
    `RolePermissionFactory(...)` with a concrete list of allowed role values.

    This class expects `request.user.user_type` to be present on the authenticated user.
    """

    allowed_roles = set()

    def __init__(self, allowed_roles=None):
        if allowed_roles is None:
            allowed_roles = self.allowed_roles
        self.allowed_roles = set(allowed_roles)

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        return (user.user_type in self.allowed_roles) or user.is_superuser


def RolePermissionFactory(allowed_roles):
    class CustomRolePermission(RolePermission):
        def __init__(self):
            super().__init__(allowed_roles=allowed_roles)

    CustomRolePermission.__name__ = f"RolePermission_{'_'.join(allowed_roles)}"
    return CustomRolePermission


class IsVeterinarianOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and (user.user_type == 'VETERINARIAN' or user.is_superuser))


class IsLabStaffOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and (user.user_type == 'LAB_STAFF' or user.is_superuser))


class IsClinicStaffOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and (user.user_type in ('VETERINARIAN','CLINIC_ADMIN','PHARMACIST') or user.is_superuser))


class IsGovernmentOfficerOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and (user.user_type == 'GOVERNMENT_OFFICER' or user.is_superuser))
