from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from apps.core.permissions import (
    RolePermissionFactory,
    IsVeterinarianOrAdmin,
    IsLabStaffOrAdmin,
    IsClinicStaffOrAdmin,
    IsGovernmentOfficerOrAdmin,
)

User = get_user_model()


class PermissionHelperTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.vet_user = User.objects.create_user(
            email='vet@example.com',
            password='Password123!',
            full_name='Vet User',
            user_type=User.UserType.VETERINARIAN,
            is_email_verified=True,
        )
        self.lab_user = User.objects.create_user(
            email='lab@example.com',
            password='Password123!',
            full_name='Lab User',
            user_type=User.UserType.LAB_STAFF,
            is_email_verified=True,
        )
        self.clinic_user = User.objects.create_user(
            email='clinic@example.com',
            password='Password123!',
            full_name='Clinic User',
            user_type=User.UserType.CLINIC_ADMIN,
            is_email_verified=True,
        )
        self.government_user = User.objects.create_user(
            email='gov@example.com',
            password='Password123!',
            full_name='Government User',
            user_type=User.UserType.GOVERNMENT_OFFICER,
            is_email_verified=True,
        )
        self.superuser = User.objects.create_superuser(
            email='super@example.com',
            password='SuperPass123!',
            full_name='Super User',
        )

    def _request_for_user(self, user):
        request = self.factory.get('/')
        request.user = user
        return request

    def test_role_permission_factory_allows_matching_roles(self):
        permission = RolePermissionFactory(['VETERINARIAN', 'CLINIC_ADMIN'])()
        self.assertTrue(permission.has_permission(self._request_for_user(self.vet_user), None))
        self.assertTrue(permission.has_permission(self._request_for_user(self.clinic_user), None))
        self.assertFalse(permission.has_permission(self._request_for_user(self.lab_user), None))

    def test_role_permission_factory_allows_superuser(self):
        permission = RolePermissionFactory(['FARMER'])()
        self.assertTrue(permission.has_permission(self._request_for_user(self.superuser), None))

    def test_is_veterinarian_or_admin(self):
        permission = IsVeterinarianOrAdmin()
        self.assertTrue(permission.has_permission(self._request_for_user(self.vet_user), None))
        self.assertTrue(permission.has_permission(self._request_for_user(self.superuser), None))
        self.assertFalse(permission.has_permission(self._request_for_user(self.lab_user), None))

    def test_is_lab_staff_or_admin(self):
        permission = IsLabStaffOrAdmin()
        self.assertTrue(permission.has_permission(self._request_for_user(self.lab_user), None))
        self.assertTrue(permission.has_permission(self._request_for_user(self.superuser), None))
        self.assertFalse(permission.has_permission(self._request_for_user(self.vet_user), None))

    def test_is_clinic_staff_or_admin(self):
        permission = IsClinicStaffOrAdmin()
        self.assertTrue(permission.has_permission(self._request_for_user(self.clinic_user), None))
        self.assertTrue(permission.has_permission(self._request_for_user(self.vet_user), None))
        self.assertTrue(permission.has_permission(self._request_for_user(self.superuser), None))
        self.assertFalse(permission.has_permission(self._request_for_user(self.lab_user), None))

    def test_is_government_officer_or_admin(self):
        permission = IsGovernmentOfficerOrAdmin()
        self.assertTrue(permission.has_permission(self._request_for_user(self.government_user), None))
        self.assertTrue(permission.has_permission(self._request_for_user(self.superuser), None))
        self.assertFalse(permission.has_permission(self._request_for_user(self.vet_user), None))
