"""
Tests for the accounts app — Auth, Registration, Login, Profile, Change Password.
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User


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
