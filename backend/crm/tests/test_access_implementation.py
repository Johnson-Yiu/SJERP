import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections, connections
from django.test import Client, TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from rest_framework.test import APIClient
from crm.models import AccessRole, Customer, EmployeeProfile, OperationLog, OrganizationUnit, Position, RolePermission


@override_settings(APP_STAGE='production', DEBUG=False, DEVELOPMENT_SUPERADMIN=False, RBAC_ENFORCEMENT=True,
                   AUDIT_LOG_ENABLED=True, PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class SessionAndRoleTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser('synthetic-session', password='synthetic-password')
        self.client = Client(enforce_csrf_checks=True)

    def post_json(self, path, data, token=None):
        headers = {'HTTP_X_CSRFTOKEN': token} if token else {}
        return self.client.post(path, data=json.dumps(data), content_type='application/json', **headers)

    def test_real_login_csrf_rotation_audit_logout_and_inactive(self):
        self.assertEqual(self.post_json('/api/session/login/', {'username': self.user.username, 'password': 'synthetic-password'}).status_code, 403)
        self.client.get('/api/session/csrf/')
        token = self.client.cookies['csrftoken'].value
        wrong = self.post_json('/api/session/login/', {'username': self.user.username, 'password': 'wrong'}, token)
        unknown = self.post_json('/api/session/login/', {'username': 'missing-synthetic', 'password': 'wrong'}, token)
        self.assertEqual((wrong.status_code, wrong.json()), (unknown.status_code, unknown.json()))
        session = self.client.session
        session['synthetic'] = True
        session.save()
        old_key = session.session_key
        response = self.post_json('/api/session/login/', {'username': self.user.username, 'password': 'synthetic-password'}, token)
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(self.client.session.session_key, old_key)
        self.assertTrue(self.client.get('/api/session/current-operator/').json()['authenticated'])
        rotated = self.client.cookies['csrftoken'].value
        customer = Customer.objects.create(name='Synthetic before', code='SYN-AUTH')
        result = self.client.patch(f'/api/customers/{customer.pk}/', data=json.dumps({'name': 'Synthetic audited customer'}),
                                   content_type='application/json', HTTP_X_CSRFTOKEN=rotated)
        self.assertEqual(result.status_code, 200, result.content)
        self.assertTrue(OperationLog.objects.filter(operator=self.user, entity='crm.customer').exists())
        self.assertEqual(self.post_json('/api/session/logout/', {}, rotated).status_code, 200)
        self.assertFalse(self.client.get('/api/session/current-operator/').json()['authenticated'])
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])
        self.client.get('/api/session/csrf/')
        token = self.client.cookies['csrftoken'].value
        self.assertEqual(self.post_json('/api/session/login/', {'username': self.user.username, 'password': 'synthetic-password'}, token).status_code, 400)

    def test_reserved_role_update_delete_and_rows_are_rejected(self):
        self.client.force_login(self.user)
        self.client.get('/api/session/csrf/')
        token = self.client.cookies['csrftoken'].value
        role = AccessRole.objects.get(code='superadmin')
        row, _ = RolePermission.objects.get_or_create(role=role, module='customers', defaults={'can_view': True})
        before = list(RolePermission.objects.filter(role=role).values_list('pk', 'module', 'can_view'))
        for method, payload in [('patch', {'active': False}), ('put', {'name': role.name, 'code': role.code, 'active': False})]:
            response = getattr(self.client, method)(f'/api/access-roles/{role.pk}/', data=json.dumps(payload), content_type='application/json', HTTP_X_CSRFTOKEN=token)
            self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.delete(f'/api/access-roles/{role.pk}/', HTTP_X_CSRFTOKEN=token).status_code, 400)
        self.assertEqual(self.post_json(f'/api/access-roles/{role.pk}/permission-matrix/', {'permissions': []}, token).status_code, 400)
        changed = self.client.patch(f'/api/role-permissions/{row.pk}/', data=json.dumps({'can_view': False}),
                                    content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(changed.status_code, 400)
        self.assertEqual(self.client.delete(f'/api/role-permissions/{row.pk}/', HTTP_X_CSRFTOKEN=token).status_code, 400)
        role.refresh_from_db()
        self.assertTrue(role.active)
        self.assertEqual(role.code, 'superadmin')
        self.assertEqual(list(RolePermission.objects.filter(role=role).values_list('pk', 'module', 'can_view')), before)

    def test_real_session_rechecks_permission_revocation_and_deactivation(self):
        user = get_user_model().objects.create_user('synthetic-employee', password='synthetic-password')
        unit = OrganizationUnit.objects.create(name='Synthetic unit', code='AUTH-UNIT')
        position = Position.objects.create(name='Synthetic position', code='AUTH-POS', unit=unit)
        role = AccessRole.objects.create(name='Synthetic viewer', code='synthetic-viewer')
        permission = RolePermission.objects.create(role=role, module='customers', can_view=True)
        profile = EmployeeProfile.objects.create(user=user, unit=unit, position=position, display_name='Synthetic employee')
        profile.roles.add(role)
        self.client.get('/api/session/csrf/')
        token = self.client.cookies['csrftoken'].value
        self.assertEqual(self.post_json('/api/session/login/', {'username': user.username, 'password': 'synthetic-password'}, token).status_code, 200)
        self.assertEqual(self.client.get('/api/customers/').status_code, 200)
        permission.can_view = False
        permission.save(update_fields=['can_view'])
        self.assertEqual(self.client.get('/api/customers/').status_code, 403)
        user.is_active = False
        user.save(update_fields=['is_active'])
        self.assertIn(self.client.get('/api/customers/').status_code, (401, 403))
        self.assertFalse(self.client.get('/api/session/current-operator/').json()['authenticated'])

    def test_audit_failure_rolls_back_ordinary_role_update(self):
        self.client.force_login(self.user)
        self.client.get('/api/session/csrf/')
        token = self.client.cookies['csrftoken'].value
        role = AccessRole.objects.create(name='Synthetic prior', code='synthetic-audit-role')
        with patch('crm.audit.record_operation', side_effect=RuntimeError('synthetic audit failure')):
            with self.assertRaises(RuntimeError):
                self.client.patch(f'/api/access-roles/{role.pk}/', data=json.dumps({'name': 'Changed'}),
                                  content_type='application/json', HTTP_X_CSRFTOKEN=token)
        role.refresh_from_db()
        self.assertEqual(role.name, 'Synthetic prior')

    def test_audit_failure_rolls_back_role_creation(self):
        self.client.force_login(self.user)
        self.client.get('/api/session/csrf/')
        token = self.client.cookies['csrftoken'].value
        with patch('crm.audit.record_operation', side_effect=RuntimeError('synthetic audit failure')):
            with self.assertRaises(RuntimeError):
                self.post_json('/api/access-roles/', {'name': 'Synthetic creation', 'code': 'synthetic-creation'}, token)
        self.assertFalse(AccessRole.objects.filter(code='synthetic-creation').exists())

    def test_invalid_matrix_after_valid_row_does_not_partially_write(self):
        self.client.force_login(self.user)
        self.client.get('/api/session/csrf/')
        token = self.client.cookies['csrftoken'].value
        role = AccessRole.objects.create(name='Synthetic matrix', code='synthetic-matrix')
        original = RolePermission.objects.create(role=role, module='customers', can_view=True)
        response = self.post_json(f'/api/access-roles/{role.pk}/permission-matrix/',
                                  {'permissions': [{'module': 'customers', 'can_view': False}, {'module': 'invalid'}]}, token)
        self.assertEqual(response.status_code, 400)
        original.refresh_from_db()
        self.assertTrue(original.can_view)
        self.assertEqual(RolePermission.objects.filter(role=role).count(), 1)

    def test_matrix_audit_records_user_and_failure_rolls_back(self):
        self.client.force_login(self.user)
        self.client.get('/api/session/csrf/')
        token = self.client.cookies['csrftoken'].value
        role = AccessRole.objects.create(name='Synthetic audit matrix', code='synthetic-audit-matrix')
        payload = {'permissions': [{'module': 'customers', 'can_view': True}]}
        with patch('crm.views.record_operation', side_effect=RuntimeError('synthetic audit failure')):
            with self.assertRaises(RuntimeError):
                self.post_json(f'/api/access-roles/{role.pk}/permission-matrix/', payload, token)
        self.assertFalse(RolePermission.objects.filter(role=role).exists())
        self.assertEqual(self.post_json(f'/api/access-roles/{role.pk}/permission-matrix/', payload, token).status_code, 200)
        row = OperationLog.objects.get(operator=self.user, action_label='修改角色权限')
        self.assertEqual(row.before_data['permissions'], [])
        self.assertTrue(row.after_data['permissions'][0]['can_view'])

    def test_format_suffix_preserves_streaming_voucher_limit(self):
        client = APIClient()
        client.force_authenticate(self.user)
        for path in ('/api/finance-ledger/vouchers.json', '/api/rmb-cash-events/voucher-upload.json'):
            with self.subTest(path=path):
                upload = SimpleUploadedFile('synthetic.bin', b'x' * (10 * 1024 * 1024 + 1))
                response = client.post(path, {'file': upload, 'sources': '[]'}, format='multipart')
                self.assertEqual(response.status_code, 413, response.data)


@override_settings(APP_STAGE='production', DEBUG=False, DEVELOPMENT_SUPERADMIN=False, RBAC_ENFORCEMENT=True)
class ReservedRoleConcurrencyTests(TransactionTestCase):
    @skipUnlessDBFeature('has_select_for_update')
    def test_parallel_role_changes_are_both_rejected(self):
        user = get_user_model().objects.create_superuser('synthetic-parallel', password=None)
        role = AccessRole.objects.get(code='superadmin')
        barrier = Barrier(2)
        def worker(code):
            close_old_connections()
            try:
                local_user = get_user_model().objects.get(pk=user.pk)
                client = APIClient()
                client.force_authenticate(local_user)
                barrier.wait(timeout=10)
                return client.patch(f'/api/access-roles/{role.pk}/', {'code': code}, format='json').status_code
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as executor:
            statuses = list(executor.map(worker, ['synthetic-a', 'synthetic-b']))
        self.assertEqual(statuses, [400, 400])
        role.refresh_from_db()
        self.assertEqual(role.code, 'superadmin')
