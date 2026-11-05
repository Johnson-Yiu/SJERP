"""Isolated session probes; synthetic users do not establish ERP login readiness."""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import Resolver404, resolve
from rest_framework.test import APIClient
from rest_framework.views import APIView
from unittest.mock import patch
from crm.authentication import SessionAuthenticationWithChallenge


@override_settings(APP_STAGE='production', DEBUG=False, DEVELOPMENT_SUPERADMIN=False,
                   RBAC_ENFORCEMENT=True, PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
@patch.object(APIView, 'authentication_classes', [SessionAuthenticationWithChallenge])
class AccessReadinessSessionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='synthetic-access-check', password='synthetic-only', is_superuser=True)
        self.client = APIClient(enforce_csrf_checks=True)

    def test_synthetic_session_csrf_and_logout(self):
        self.assertEqual(self.client.get('/api/customers/').status_code, 401)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/api/customers/').status_code, 200)
        self.assertEqual(self.client.post('/api/customers/', {'name': 'synthetic'}, format='json').status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get('/api/customers/').status_code, 401)

    def test_deactivated_user_session_no_longer_authorizes(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/api/customers/').status_code, 200)
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])
        self.assertEqual(self.client.get('/api/customers/').status_code, 401)

    def test_expired_session_no_longer_authorizes(self):
        self.client.force_login(self.user)
        session = self.client.session
        session.set_expiry(-1)
        session.save()
        self.assertEqual(self.client.get('/api/customers/').status_code, 401)

    def test_no_named_business_login_or_logout_route(self):
        for path in ('/api/login/', '/api/logout/', '/api/session/login/', '/api/session/logout/'):
            with self.subTest(path=path), self.assertRaises(Resolver404):
                resolve(path)


@override_settings(APP_STAGE='development', DEBUG=True, DEVELOPMENT_SUPERADMIN=True, RBAC_ENFORCEMENT=False)
class AccessReadinessDevelopmentTests(TestCase):
    def test_development_identity_does_not_claim_real_authentication(self):
        response = APIClient().get('/api/session/current-operator/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['has_all_permissions'])
        self.assertFalse(response.data['audit_log_enabled'])
