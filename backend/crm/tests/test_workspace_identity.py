from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient


@override_settings(APP_STAGE='development', DEBUG=True, DEVELOPMENT_SUPERADMIN=True, RBAC_ENFORCEMENT=False)
class WorkspaceIdentityContractTests(TestCase):
    def test_anonymous_development_identity_has_no_fabricated_user_id(self):
        response = APIClient().get('/api/session/current-operator/')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data['user_id'])
        self.assertFalse(response.data['authenticated'])
        self.assertTrue(response.data['development_superadmin'])

    def test_equal_display_names_do_not_conflate_authenticated_accounts(self):
        users = [get_user_model().objects.create_user(username=f'workspace-synthetic-{i}', first_name='Same', last_name='Name') for i in (1, 2)]
        seen = []
        for user in users:
            client = APIClient()
            client.force_authenticate(user=user)
            response = client.get('/api/session/current-operator/')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data['user_id'], user.pk)
            self.assertTrue(response.data['authenticated'])
            self.assertTrue(response.data['development_superadmin'])
            seen.append(response.data['user_id'])
        self.assertNotEqual(*seen)
