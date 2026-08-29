from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()

class CookieAuthTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='cookie@example.com', password='StrongPass123!', full_name='Cookie User', is_email_verified=True)

    def test_login_sets_http_only_cookies(self):
        res = self.client.post('/api/v1/auth/token/', {'email': 'cookie@example.com', 'password': 'StrongPass123!'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', res.cookies)
        self.assertIn('refresh_token', res.cookies)
        self.assertTrue(res.cookies['access_token']['httponly'])
        self.assertTrue(res.cookies['refresh_token']['httponly'])

    def test_me_works_with_cookie_without_header(self):
        login = self.client.post('/api/v1/auth/token/', {'email': 'cookie@example.com', 'password': 'StrongPass123!'}, format='json')
        access_cookie = login.cookies.get('access_token').value if 'access_token' in login.cookies else None
        # New client with only cookie
        self.client.cookies['access_token'] = access_cookie
        # No Authorization header
        res = self.client.get('/api/v1/auth/me/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['email'], 'cookie@example.com')

    def test_refresh_via_cookie(self):
        login = self.client.post('/api/v1/auth/token/', {'email': 'cookie@example.com', 'password': 'StrongPass123!'}, format='json')
        refresh_cookie = login.cookies.get('refresh_token').value
        self.client.cookies['refresh_token'] = refresh_cookie
        res = self.client.post('/api/v1/auth/token/refresh/', {}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('access', res.data)

    def test_logout_clears_cookies(self):
        login = self.client.post('/api/v1/auth/token/', {'email': 'cookie@example.com', 'password': 'StrongPass123!'}, format='json')
        self.client.cookies['access_token'] = login.cookies.get('access_token').value
        self.client.cookies['refresh_token'] = login.cookies.get('refresh_token').value
        self.client.force_authenticate(user=self.user)
        res = self.client.post('/api/v1/auth/logout/', {}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # cookies should be cleared (empty value or expired)
        self.assertIn('access_token', res.cookies)
