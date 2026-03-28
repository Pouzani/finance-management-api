from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase


class RegisterViewTests(APITestCase):
    url = '/api/auth/register/'

    def test_register_success(self):
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'Str0ng!Pass',
            'password2': 'Str0ng!Pass',
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertTrue(User.objects.filter(username='testuser').exists())

    def test_register_password_mismatch(self):
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'Str0ng!Pass',
            'password2': 'WrongPass!',
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_username(self):
        User.objects.create_user(username='existing', password='pass')
        data = {
            'username': 'existing',
            'email': 'other@example.com',
            'password': 'Str0ng!Pass',
            'password2': 'Str0ng!Pass',
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_missing_fields(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginViewTests(APITestCase):
    url = '/api/auth/login/'

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='Str0ng!Pass'
        )

    def test_login_success(self):
        response = self.client.post(self.url, {'username': 'testuser', 'password': 'Str0ng!Pass'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_wrong_password(self):
        response = self.client.post(self.url, {'username': 'testuser', 'password': 'wrong'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_unknown_user(self):
        response = self.client.post(self.url, {'username': 'nobody', 'password': 'pass'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MeViewTests(APITestCase):
    url = '/api/auth/me/'
    login_url = '/api/auth/login/'

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', email='test@example.com', password='Str0ng!Pass'
        )

    def _get_token(self):
        response = self.client.post(self.login_url, {'username': 'testuser', 'password': 'Str0ng!Pass'})
        return response.data['access']

    def test_me_authenticated(self):
        token = self._get_token()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')
        self.assertEqual(response.data['email'], 'test@example.com')

    def test_me_unauthenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ProtectedEndpointTests(APITestCase):
    """Verify that existing API endpoints require authentication."""
    login_url = '/api/auth/login/'

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='Str0ng!Pass')

    def _get_token(self):
        response = self.client.post(self.login_url, {'username': 'testuser', 'password': 'Str0ng!Pass'})
        return response.data['access']

    def test_accounts_requires_auth(self):
        response = self.client.get('/api/accounts/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_transactions_requires_auth(self):
        response = self.client.get('/api/transactions/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_accounts_accessible_with_auth(self):
        token = self._get_token()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/accounts/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
