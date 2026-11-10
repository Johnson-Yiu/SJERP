from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from crm.tests.historical_database import HistoricalMigrationTestCase
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from rest_framework.test import APIClient
from crm.models import HSCode, Product
from crm.views import _import_row


@override_settings(APP_STAGE='development', DEBUG=True, DEVELOPMENT_SUPERADMIN=True, RBAC_ENFORCEMENT=False)


class HSCodeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.code = HSCode.objects.create(code='8539510000')
        self.product = Product.objects.create(code='HS-P1', name='灯具', sales_model_prefix='HST')

    def test_create_product_without_hs_and_reject_direct_assignment(self):
        response = self.client.post('/api/products/', {'name': '新灯具', 'sales_model_prefix': 'HSN'}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIsNone(response.data['hs_code'])
        response = self.client.patch(f'/api/products/{self.product.pk}/', {'hs_code': self.code.pk}, format='json')
        self.assertEqual(response.status_code, 400)
        self.product.refresh_from_db()
        self.assertIsNone(self.product.hs_code_id)

    def test_assignment_preservation_and_protected_delete(self):
        url = f'/api/hs-codes/{self.code.pk}/assign-products/'
        response = self.client.put(url, {'product_ids': [self.product.pk]}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        response = self.client.patch(f'/api/products/{self.product.pk}/', {'name': '更新名称'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['hs_code_value'], self.code.code)
        self.assertEqual(self.client.delete(f'/api/hs-codes/{self.code.pk}/').status_code, 400)
        self.assertEqual(self.client.put(url, {'product_ids': [999999]}, format='json').status_code, 400)
        self.product.refresh_from_db()
        self.assertEqual(self.product.hs_code_id, self.code.pk)
        self.assertEqual(self.client.put(url, {'product_ids': []}, format='json').status_code, 200)
        self.product.refresh_from_db()
        self.assertIsNone(self.product.hs_code_id)

    def test_import_does_not_require_or_overwrite_hs(self):
        self.product.hs_code = self.code
        self.product.save()
        _import_row('products', {'code': self.product.code, 'name': '导入更新', 'hs_code': 'OTHER'})
        self.product.refresh_from_db()
        self.assertEqual(self.product.hs_code_id, self.code.pk)

    @override_settings(APP_STAGE='production', DEBUG=False, DEVELOPMENT_SUPERADMIN=False)
    def test_maintenance_requires_admin_even_without_global_rbac(self):
        user = get_user_model().objects.create_user(username='regular')
        self.client.force_authenticate(user)
        self.assertFalse(self.client.get('/api/session/current-operator/').data['can_manage_hs_codes'])
        self.assertEqual(self.client.post('/api/hs-codes/', {'code': '123456'}, format='json').status_code, 403)
        self.assertEqual(self.client.put(f'/api/hs-codes/{self.code.pk}/assign-products/', {'product_ids': []}, format='json').status_code, 403)
        user.is_superuser = True
        user.save()
        self.assertEqual(self.client.post('/api/hs-codes/', {'code': '123456'}, format='json').status_code, 201)

    def test_inactive_assignment_keeps_existing_allows_release_and_rejects_new_atomically(self):
        self.code.active = False
        self.code.save()
        self.product.hs_code = self.code
        self.product.save()
        other = Product.objects.create(code='HS-P2', name='第二产品', sales_model_prefix='HS2')
        url = f'/api/hs-codes/{self.code.pk}/assign-products/'
        self.assertEqual(self.client.put(url, {'product_ids': [other.pk]}, format='json').status_code, 400)
        self.product.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(self.product.hs_code_id, self.code.pk)
        self.assertIsNone(other.hs_code_id)
        self.assertEqual(self.client.put(url, {'product_ids': [self.product.pk]}, format='json').status_code, 200)
        self.assertEqual(self.client.put(url, {'product_ids': []}, format='json').status_code, 200)
        self.product.refresh_from_db()
        self.assertIsNone(self.product.hs_code_id)

    def test_duplicate_code_rejected_without_changing_existing_product_identity(self):
        self.product.hs_code = self.code
        self.product.save()
        response = self.client.post('/api/hs-codes/', {'code': self.code.code, 'description': '重复'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('code', response.data)
        self.assertEqual(HSCode.objects.filter(code=self.code.code).count(), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.hs_code_id, self.code.pk)

    def test_development_capability(self):
        self.assertTrue(self.client.get('/api/session/current-operator/').data['can_manage_hs_codes'])


class HSMigrationTests(HistoricalMigrationTestCase):
    def test_existing_codes_are_deduplicated_and_reversible(self):
        old = [('crm', '0052_alter_packingplancarton_partial_carton_policy_snapshot')]
        new = [('crm', '0053_hs_code_catalog')]
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes("crm")
        executor.migrate(old)
        try:
            ProductBefore = executor.loader.project_state(old).apps.get_model('crm', 'Product')
            for index, code in enumerate(['8539510000', '8539510000', '']):
                ProductBefore.objects.create(code=f'MIG{index}', name=f'Product {index}', hs_code=code)
            executor = MigrationExecutor(connection)
            executor.migrate(new)
            apps = executor.loader.project_state(new).apps
            ProductAfter = apps.get_model('crm', 'Product')
            self.assertEqual(apps.get_model('crm', 'HSCode').objects.count(), 1)
            self.assertEqual(ProductAfter.objects.filter(hs_code__code='8539510000').count(), 2)
            self.assertIsNone(ProductAfter.objects.get(code='MIG2').hs_code_id)
            executor = MigrationExecutor(connection)
            executor.migrate(old)
            self.assertEqual(ProductBefore.objects.filter(hs_code='8539510000').count(), 2)
        finally:
            MigrationExecutor(connection).migrate(latest)
