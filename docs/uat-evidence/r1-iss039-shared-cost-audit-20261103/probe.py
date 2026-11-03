"""Read-only audit probes: new in-memory database only; no business database."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'backend'))
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['APP_STAGE'] = 'development'
os.environ['MEDIA_ROOT'] = tempfile.mkdtemp(prefix='iss039-probe-')
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
sys.dont_write_bytecode = True
import django
django.setup()
from django.apps import apps
from django.test.runner import DiscoverRunner
from crm.tests.test_iss039_shared_purchase_costs import SharedPurchaseCostPermissionTests
from crm.models import OperationLog, PurchaseOrder, PurchaseCostAllocation, InventoryReservation


class AuditProbe(SharedPurchaseCostPermissionTests):
    def test_quantity_is_accepted_but_not_amount_proportional(self):
        self.login(self.procurement)
        # Two purchase rows: 10 * 1000 and 10 * 100; equal quantities, unequal money.
        second = self.purchase.items.create(sku=self.sku, quantity=10, unit_price=100)
        payload = self.payload()
        payload['allocations'] = [
            {'purchase_item': self.item.pk, 'target_type': 'order', 'order': self.order_a.pk, 'quantity': '10'},
            {'purchase_item': second.pk, 'target_type': 'order', 'order': self.order_b.pk, 'quantity': '10'},
        ]
        payload['expenses'][0]['method'] = 'quantity'
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        shares = [str(row['additional_amount']) for row in response.data['allocations']]
        self.assertEqual(shares, ['500.00', '500.00'])
        payload['version'] = 1
        payload['expenses'][0]['method'] = 'amount'
        response2 = self.client.post(self.url, payload, format='json')
        self.assertEqual(response2.status_code, 200, response2.data)
        amount_shares = [str(row['additional_amount']) for row in response2.data['allocations']]
        self.assertEqual(amount_shares, ['909.09', '90.91'])
        print('QUANTITY_RULE_COUNTEREXAMPLE', json.dumps({'quantity': shares, 'amount': amount_shares}))

    def business_snapshot(self):
        excluded = {OperationLog, PurchaseOrder, PurchaseCostAllocation, InventoryReservation}
        return {model._meta.label: list(model.objects.order_by('pk').values())
                for model in apps.get_app_config('crm').get_models() if model not in excluded}

    def test_save_preserves_all_other_business_rows_and_audits_time(self):
        self.login(self.procurement)
        before = self.business_snapshot()
        response = self.client.post(self.url, self.payload(), format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.business_snapshot(), before)
        log = OperationLog.objects.get(entity='crm.purchaseorder', object_id=str(self.purchase.pk))
        self.assertEqual(log.operator_id, self.procurement.pk)
        self.assertIsNotNone(log.created_at)
        self.assertEqual(log.after_data['cost_allocation']['version'], 1)
        print('SIDE_EFFECTS', len(before), 'CRM model tables unchanged; reservations separately excluded as derived state')
        print('AUDIT', log.operator_id, log.created_at.isoformat(), log.changed_fields)

    def test_audit_failure_rolls_back_costs_and_derived_state(self):
        self.login(self.procurement)
        before = list(self.item.cost_allocations.values())
        reservations = list(InventoryReservation.objects.values())
        with patch('crm.views.record_operation', side_effect=RuntimeError('ISS039 audit fault')):
            with self.assertRaisesRegex(RuntimeError, 'ISS039 audit fault'):
                self.client.post(self.url, self.payload(), format='json')
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.cost_allocation_version, 0)
        self.assertEqual(self.purchase.additional_costs, [])
        self.assertEqual(list(self.item.cost_allocations.values()), before)
        self.assertEqual(list(InventoryReservation.objects.values()), reservations)
        self.assertFalse(OperationLog.objects.exists())
        print('AUDIT_FAILURE_ROLLBACK verified')

    def test_preview_and_readonly_rejection_have_no_writes(self):
        self.login(self.procurement)
        before = self.business_snapshot()
        response = self.client.post(self.url.replace('cost-allocation/', 'cost-allocation-preview/'), self.payload(), format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.business_snapshot(), before)
        self.login(self.viewer)
        for url in [self.url, self.url.replace('cost-allocation/', 'cost-allocation-preview/')]:
            self.assertEqual(self.client.post(url, self.payload(), format='json').status_code, 403)
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.cost_allocation_version, 0)
        self.assertEqual(self.item.cost_allocations.count(), 1)
        self.assertFalse(OperationLog.objects.exists())
        print('PREVIEW_AND_DENIAL no writes verified')

    def test_ordinary_purchase_patch_cannot_override_allocation_fields(self):
        self.login(self.procurement)
        self.assertEqual(self.client.post(self.url, self.payload(), format='json').status_code, 200)
        self.purchase.refresh_from_db()
        costs = self.purchase.additional_costs
        response = self.client.patch(f'/api/purchase-orders/{self.purchase.pk}/',
            {'cost_allocation_version': 0, 'additional_costs': [{'amount': '-999', 'method': 'bad'}]}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.cost_allocation_version, 1)
        self.assertEqual(self.purchase.additional_costs, costs)
        print('ORDINARY_PATCH allocation fields ignored as model editable=False; version and expenses unchanged')


if __name__ == '__main__':
    capture = io.StringIO()
    with contextlib.redirect_stdout(capture), contextlib.redirect_stderr(capture):
        print('Python', sys.version, 'Django', django.get_version())
        print('DATABASE_URL=', os.environ['DATABASE_URL'], 'APP_STAGE=', os.environ['APP_STAGE'], 'MEDIA_ROOT=', os.environ['MEDIA_ROOT'])
        names = [name for name in AuditProbe.__dict__ if name.startswith('test_')]
        failures = DiscoverRunner(verbosity=2, interactive=False).run_tests(['__main__.AuditProbe.' + name for name in names])
        print('EXIT=', int(bool(failures)))
    raw = capture.getvalue()
    with zipfile.ZipFile(Path(__file__).with_name('probe.raw.zip'), 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('probe.raw.log', raw)
    print(raw)
    sys.exit(bool(failures))
