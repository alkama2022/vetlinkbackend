from rest_framework import permissions
from .models import User


class IsSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (
            request.user.is_superuser or request.user.user_type == User.UserType.SUPER_ADMIN
        ))


class IsVeterinarian(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (
            request.user.user_type in [User.UserType.VETERINARIAN, User.UserType.SUPER_ADMIN]
        ))


class IsFarmer(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (
            request.user.user_type in [User.UserType.FARMER, User.UserType.SUPER_ADMIN]
        ))


class IsGovernmentOfficer(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (
            request.user.user_type in [User.UserType.GOVERNMENT_OFFICER, User.UserType.SUPER_ADMIN]
        ))


class IsLabStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (
            request.user.user_type in [User.UserType.LAB_STAFF, User.UserType.SUPER_ADMIN]
        ))


class IsPharmacist(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (
            request.user.user_type in [User.UserType.PHARMACIST, User.UserType.SUPER_ADMIN]
        ))
