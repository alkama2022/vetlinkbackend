from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()


class AuthFlowTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='auth@example.com',
            password='StrongPass123!',
            full_name='Auth User',
            is_email_verified=True,
        )

    def test_login_returns_tokens_for_registered_user(self):
        response = self.client.post(
            '/api/v1/auth/token/',
            {'email': 'auth@example.com', 'password': 'StrongPass123!'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['email'], 'auth@example.com')

    def test_change_password_updates_existing_password(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            '/api/v1/auth/password/change/',
            {
                'old_password': 'StrongPass123!',
                'new_password': 'NewStrongPass123!',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewStrongPass123!'))
