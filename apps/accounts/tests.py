"""
Tests for the accounts app — Auth, Registration, Login, Profile, Change Password.
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User
from apps.veterinarians.models import VeterinarianProfile


def make_user(email="farmer@test.ng", password="securepass123", **kwargs):
    """Helper to create a test user."""
    defaults = {
        "full_name": "Test Farmer",
        "user_type": User.UserType.FARMER,
        "lga": "Kano Municipal",
    }
    defaults.update(kwargs)
    return User.objects.create_user(email=email, password=password, **defaults)


class RegistrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("user_register")

    def test_register_success(self):
        data = {
            "email": "newuser@test.ng",
            "password": "strongpass123",
            "full_name": "New User",
            "user_type": "FARMER",
            "lga": "Kano Municipal",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email="newuser@test.ng").exists())

    def test_register_duplicate_email(self):
        make_user(email="dup@test.ng")
        data = {
            "email": "dup@test.ng",
            "password": "anotherpass123",
            "full_name": "Another User",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_short_password(self):
        data = {
            "email": "shortpass@test.ng",
            "password": "abc",
            "full_name": "Short Pass",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_missing_required_fields(self):
        response = self.client.post(self.url, {"email": "incomplete@test.ng"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class FarmerOnlyRegistrationTests(TestCase):
    """Public registration must create FARMER accounts only."""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("user_register")

    def _register(self, **overrides):
        data = {
            "email": "farmernew@test.ng",
            "password": "strongpass123",
            "full_name": "New Farmer",
            "lga": "Kano Municipal",
        }
        data.update(overrides)
        return self.client.post(self.url, data, format="json")

    def test_farmer_registers_normally(self):
        response = self._register()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="farmernew@test.ng")
        self.assertEqual(user.user_type, User.UserType.FARMER)

    def test_farmer_registers_with_explicit_farmer_role(self):
        response = self._register(user_type="FARMER")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="farmernew@test.ng")
        self.assertEqual(user.user_type, User.UserType.FARMER)

    def test_register_with_veterinarian_role_rejected(self):
        response = self._register(user_type="VETERINARIAN")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="farmernew@test.ng").exists())

    def test_register_with_admin_role_rejected(self):
        for role in ("ADMIN", "SYSTEM_ADMIN", "SUPER_ADMIN"):
            response = self._register(user_type=role)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="farmernew@test.ng").exists())

    def test_register_with_lab_role_rejected(self):
        for role in ("LAB_STAFF", "LAB_TECH"):
            response = self._register(user_type=role)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="farmernew@test.ng").exists())

    def test_register_with_clinic_government_pharmacist_rejected(self):
        for role in ("CLINIC_ADMIN", "GOVERNMENT_OFFICER", "PHARMACIST", "RECEPTIONIST"):
            response = self._register(user_type=role)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="farmernew@test.ng").exists())

    def test_register_with_professional_profile_fields_creates_farmer_account(self):
        response = self._register(vet_code="VET999", license_number="LIC999")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="farmernew@test.ng")
        self.assertEqual(user.user_type, User.UserType.FARMER)
        self.assertFalse(VeterinarianProfile.objects.filter(user=user).exists())


class RoleEscalationTests(TestCase):
    """Farmers must never be able to escalate their role through the API."""

    def setUp(self):
        self.client = APIClient()
        self.user = make_user(email="escalate@test.ng", password="escalatepass123")
        self.url = reverse("user_profile")

    def _authenticate(self):
        resp = self.client.post(
            reverse("token_obtain_pair"),
            {"email": "escalate@test.ng", "password": "escalatepass123"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")

    def test_farmer_cannot_change_role_to_veterinarian(self):
        self._authenticate()
        response = self.client.patch(self.url, {"user_type": "VETERINARIAN"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertEqual(self.user.user_type, User.UserType.FARMER)

    def test_farmer_cannot_change_role_to_admin(self):
        self._authenticate()
        response = self.client.patch(self.url, {"user_type": "SUPER_ADMIN"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertEqual(self.user.user_type, User.UserType.FARMER)

    def test_farmer_can_still_update_profile_fields(self):
        self._authenticate()
        response = self.client.patch(self.url, {"full_name": "Updated Farmer"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, "Updated Farmer")
        self.assertEqual(self.user.user_type, User.UserType.FARMER)


class ProfessionalLoginTests(TestCase):
    """Professionals are login-only; accounts are created by administrators."""

    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse("user_register")

    def _make_vet(self):
        user = User.objects.create_user(
            email="vet@test.ng",
            password="vetpass123",
            full_name="Dr. Vet",
            user_type=User.UserType.VETERINARIAN,
            is_email_verified=True,
        )
        VeterinarianProfile.objects.create(
            user=user,
            vet_code="VET001",
            full_name="Dr. Vet",
            license_number="VCN/2015/4521",
            qualifications="DVM",
            specializations=["Mixed Practice"],
            species_treated=["Cattle"],
            diseases_expertise=["FMD"],
            years_experience=5,
            languages=["English", "Hausa"],
            clinic_name="Kano Vet Clinic",
            clinic_address="10 Zoo Road",
            lga="Kano Municipal",
            service_area=["Kano Municipal"],
            whatsapp_number="08012345678",
            phone="08012345678",
            email="vet@test.ng",
        )
        return user

    def test_veterinarian_logs_in_with_vet_code_and_license(self):
        self._make_vet()
        response = self.client.post(
            reverse("vet_login"),
            {"vet_code": "VET001", "license_number": "VCN/2015/4521"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["user_type"], "VETERINARIAN")

    def test_veterinarian_cannot_register_through_public_registration(self):
        self._make_vet()
        response = self.client.post(
            self.register_url,
            {
                "email": "vet2@test.ng",
                "password": "strongpass123",
                "full_name": "Another Vet",
                "user_type": "VETERINARIAN",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="vet2@test.ng").exists())

    def test_authenticated_veterinarian_cannot_use_farmer_registration(self):
        vet = self._make_vet()
        self.client.force_authenticate(user=vet)
        response = self.client.post(
            self.register_url,
            {
                "email": "vet3@test.ng",
                "password": "strongpass123",
                "full_name": "Vet Three",
                "user_type": "VETERINARIAN",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="vet3@test.ng").exists())

    def test_veterinarian_owns_admin_created_role_and_cannot_change_it(self):
        vet = self._make_vet()
        self.client.force_authenticate(user=vet)
        response = self.client.patch(
            reverse("user_profile"),
            {"user_type": "FARMER"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        vet.refresh_from_db()
        self.assertEqual(vet.user_type, User.UserType.VETERINARIAN)

    def test_no_public_signup_route_for_professionals(self):
        for path in (
            '/api/v1/auth/vet-register/',
            '/api/v1/auth/lab-register/',
            '/api/v1/auth/clinic-register/',
            '/api/v1/auth/pharmacist-register/',
            '/api/v1/auth/government-register/',
        ):
            response = self.client.post(path, {}, format="json")
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, path)

    def test_no_public_signup_route_for_veterinarian_profile(self):
        response = self.client.post('/api/v1/veterinarians/register/', {}, format="json")
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED))
        self.assertFalse(VeterinarianProfile.objects.exists())

    def test_professional_account_creation_requires_authentication(self):
        response = self.client.post('/api/v1/veterinarians/', {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class LoginTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("token_obtain_pair")
        self.user = make_user(email="login@test.ng", password="loginpass123")

    def test_login_success(self):
        response = self.client.post(
            self.url,
            {"email": "login@test.ng", "password": "loginpass123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["email"], "login@test.ng")

    def test_login_wrong_password(self):
        response = self.client.post(
            self.url,
            {"email": "login@test.ng", "password": "wrongpassword"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_nonexistent_user(self):
        response = self.client.post(
            self.url,
            {"email": "ghost@test.ng", "password": "whatever123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_inactive_user(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(
            self.url,
            {"email": "login@test.ng", "password": "loginpass123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ProfileTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user(email="profile@test.ng", password="profilepass123")
        self.url = reverse("user_profile")

    def _login(self):
        resp = self.client.post(
            reverse("token_obtain_pair"),
            {"email": "profile@test.ng", "password": "profilepass123"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")

    def test_get_profile_authenticated(self):
        self._login()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "profile@test.ng")

    def test_get_profile_unauthenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_profile(self):
        self._login()
        response = self.client.patch(self.url, {"full_name": "Updated Name"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["full_name"], "Updated Name")
        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, "Updated Name")


class ChangePasswordTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user(email="changepw@test.ng", password="oldpass123")
        self.url = reverse("change_password")

    def _login(self):
        resp = self.client.post(
            reverse("token_obtain_pair"),
            {"email": "changepw@test.ng", "password": "oldpass123"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")

    def test_change_password_success(self):
        self._login()
        response = self.client.post(
            self.url,
            {"old_password": "oldpass123", "new_password": "newSecurePass456"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newSecurePass456"))

    def test_change_password_wrong_current(self):
        self._login()
        response = self.client.post(
            self.url,
            {"old_password": "wrongpass", "new_password": "newSecurePass456"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_unauthenticated(self):
        response = self.client.post(
            self.url,
            {"old_password": "oldpass123", "new_password": "newSecurePass456"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
