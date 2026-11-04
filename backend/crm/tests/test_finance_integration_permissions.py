"""Isolated ordinary-role routing checks; never enable RBAC on a running app."""
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from crm.models import (AccessRole, EmployeeProfile, FinanceFact, FinanceInstruction,
                        OperationLog, OrganizationUnit, Position, RolePermission)
from crm.services import finance_closeout as ledger
from crm.tests.test_finance_closeout import CloseoutFixture
from crm.tests.test_sales_data_scope import RBAC_SETTINGS


@override_settings(**RBAC_SETTINGS, PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class FinanceLedgerOrdinaryRoleTests(CloseoutFixture, TestCase):
    def setUp(self):
        self.setup_ledger()
        self.user = get_user_model().objects.create_user('synthetic-ledger-reader', password=None)
        unit = OrganizationUnit.objects.create(code='SYNTH-LEDGER-UNIT', name='合成财务验收组')
        position = Position.objects.create(unit=unit, code='SYNTH-LEDGER-POS', name='合成验收岗位')
        self.role = AccessRole.objects.create(code='synthetic-ledger-role', name='合成财务只读', default_data_scope='all')
        self.profile = EmployeeProfile.objects.create(user=self.user, display_name='合成财务角色', unit=unit, position=position)
        self.profile.roles.add(self.role)
        self.finance = RolePermission.objects.create(role=self.role, module='finance', can_view=True)
        self.transactions = RolePermission.objects.create(role=self.role, module='transactions', can_view=True)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def grant(self, **values):
        for name, value in values.items():
            setattr(self.finance, name, value)
        self.finance.save()

    def test_authorized_ordinary_reader_can_list_account_ledger(self):
        response = self.client.get('/api/finance-ledger/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual({r['id'] for r in response.data['accounts']}, {self.account.pk, self.second.pk})
        self.assertFalse(self.user.is_superuser)

    def test_readonly_preview_is_allowed_and_never_writes(self):
        before = (FinanceInstruction.objects.count(), FinanceFact.objects.count(), OperationLog.objects.count())
        response = self.client.post('/api/finance-ledger/preview/', self.data(), format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIs(response.data['written'], False)
        self.assertEqual((FinanceInstruction.objects.count(), FinanceFact.objects.count(), OperationLog.objects.count()), before)
        self.assertEqual(self.client.post('/api/finance-ledger/instructions/', self.data(), format='json').status_code, 403)
        self.assertEqual(self.client.post('/api/finance-ledger/post/', {'id': 1, 'voucher_checked': True}, format='json').status_code, 403)
        self.assertEqual((FinanceInstruction.objects.count(), FinanceFact.objects.count(), OperationLog.objects.count()), before)

    def test_creator_without_update_can_create_but_cannot_post(self):
        self.grant(can_create=True, can_update=False)
        response = self.client.post('/api/finance-ledger/instructions/', self.data(), format='json')
        self.assertEqual(response.status_code, 201, response.data)
        instruction = FinanceInstruction.objects.get(pk=response.data['id'])
        self.assertEqual(instruction.created_actor['user_id'], self.user.pk)
        self.assertEqual(self.client.post('/api/finance-ledger/post/', {'id': instruction.pk, 'voucher_checked': True}, format='json').status_code, 403)
        self.assertEqual(FinanceFact.objects.count(), 0)
        account = self.client.post('/api/finance-ledger/accounts/',
                                   {'code': 'SYNTH-CREATED-BANK', 'name': '合成新账户', 'account_type': 'bank',
                                    'ownership': 'own', 'ownership_reason': '合成开户核实'}, format='json')
        self.assertEqual(account.status_code, 201, account.data)
        proof = self.client.post('/api/finance-ledger/vouchers/',
                                 {'file': SimpleUploadedFile('synthetic-role.pdf', b'%PDF-1.4\nSynthetic role voucher\n%%EOF')}, format='multipart')
        self.assertEqual(proof.status_code, 201, proof.data)

    def test_updater_without_create_can_post_but_cannot_create(self):
        pending, _ = ledger.submit(self.data(), self.maker)
        self.grant(can_create=False, can_update=True)
        response = self.client.post('/api/finance-ledger/post/', {'id': pending.pk, 'voucher_checked': True}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['actor']['kind'], 'authenticated_user')
        self.assertEqual(response.data['actor']['user_id'], self.user.pk)
        before = FinanceInstruction.objects.count()
        self.assertEqual(self.client.post('/api/finance-ledger/instructions/', self.data(), format='json').status_code, 403)
        self.assertEqual(FinanceInstruction.objects.count(), before)

    def test_viewonly_cannot_export_but_each_existing_export_grant_can(self):
        self.fact()
        path = '/api/finance-ledger/facts/'
        self.assertEqual(self.client.get(path, {'export': 'csv'}).status_code, 403)
        self.grant(can_export=True)
        finance = self.client.get(path, {'export': 'csv'})
        self.assertEqual(finance.status_code, 200)
        self.assertIn(b'100.00', finance.content)
        self.grant(can_export=False)
        RolePermission.objects.create(role=self.role, module='reports', can_export=True)
        reports = self.client.get(path, {'export': 'csv'})
        self.assertEqual(reports.status_code, 200)
        self.assertEqual(reports.content, finance.content)
        self.grant(can_view=False)
        denied = self.client.get(path, {'export': 'csv'})
        self.assertEqual(denied.status_code, 403)
        self.assertNotIn(b'100.00', denied.content)

    def test_missing_view_transactions_scope_or_active_profile_remains_denied(self):
        self.grant(can_create=True, can_update=True, can_export=True)
        before = (FinanceInstruction.objects.count(), FinanceFact.objects.count(), OperationLog.objects.count())
        cases = ['finance_view', 'transactions_view', 'limited_scope', 'inactive_profile']
        for case in cases:
            with self.subTest(case=case):
                self.finance.can_view = case != 'finance_view'
                self.finance.save()
                self.transactions.can_view = case != 'transactions_view'
                self.transactions.save()
                self.role.default_data_scope = 'self' if case == 'limited_scope' else 'all'
                self.role.save()
                self.profile.active = case != 'inactive_profile'
                self.profile.save()
                # Clear cached profile state, so this verifies the persisted gate.
                self.client.force_authenticate(get_user_model().objects.get(pk=self.user.pk))
                for method, path, data in [('get', '/api/finance-ledger/', {}),
                                           ('post', '/api/finance-ledger/preview/', self.data()),
                                           ('post', '/api/finance-ledger/instructions/', self.data()),
                                           ('get', '/api/finance-ledger/facts/', {'export': 'csv'})]:
                    response = getattr(self.client, method)(path, data, **({'format': 'json'} if method == 'post' else {}))
                    self.assertEqual(response.status_code, 403, (case, path, response.data))
                    self.assertNotIn(self.account.code, str(response.data))
        self.assertEqual((FinanceInstruction.objects.count(), FinanceFact.objects.count(), OperationLog.objects.count()), before)
