from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.exceptions import ValidationError

from crm import history_operational_inventory as opening
from crm.models import HistoryInventoryBaseline, HistoryTakeoverSourceRecord, InventoryMovement
from crm.services.fulfillment import location_quantity, sku_metrics
from crm.tests.test_history_takeover import HistoryTakeoverFixtureMixin


@override_settings(AUDIT_LOG_ENABLED=True)
class CoreHistoryStockCrossTests(HistoryTakeoverFixtureMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.application, self.group, _ = self.application_and_group()
        base = f'/api/import/history-takeovers/{self.application.pk}/groups/{self.group.pk}/'
        result = self.client.post(base + 'review/', {'decision': 'approve', 'note': '合成盘点核对', 'confirm_manual': True}, format='json')
        self.assertEqual(result.status_code, 200, result.data)
        result = self.client.post(base + 'execute/', {}, format='json')
        self.assertEqual(result.status_code, 200, result.data)
        source = HistoryTakeoverSourceRecord.objects.get(group=self.group, record_type='库存盘点')
        self.maker = get_user_model().objects.create_superuser(username='cross-stock-maker', password='test-only')
        self.reviewer = get_user_model().objects.create_superuser(username='cross-stock-reviewer', password='test-only')
        opening.propose(self.group.pk, [{'source_id': source.pk, 'goods_ownership': 'own', 'unit_cost': '3.25', 'cost_currency': 'USD', 'no_lot': False}], '合成盘点及成本核对', True, self.maker)
        opening.approve(self.group.pk, '合成盘点已复核', self.reviewer)
        self.default = {'warehouse': '默认仓', 'warehouse_type': '自有仓', 'lot_reference': ''}
        self.history = {'warehouse': 'SYN-WH-01', 'warehouse_type': '自有仓', 'lot_reference': 'LOT-HT-01'}

    def test_existing_legacy_default_movement_blocks_opening_without_double_count(self):
        InventoryMovement.objects.create(movement_no='CROSS-OLD-1', movement_date=date(2025, 1, 1), type='adjust_in', sku=self.sku, quantity=Decimal('4'))
        with self.assertRaises(ValidationError):
            opening.execute(self.group.pk, self.maker)
        self.assertFalse(HistoryInventoryBaseline.objects.filter(group=self.group).exists())
        self.assertEqual(sku_metrics(self.sku)['actual_quantity'], Decimal('4'))
        self.assertEqual(location_quantity(self.sku, self.default), Decimal('4'))
        self.assertEqual(location_quantity(self.sku, self.history), Decimal('0'))

    def test_opening_and_later_default_stock_are_not_borrowed_across_locations(self):
        ids, replay = opening.execute(self.group.pk, self.maker)
        self.assertFalse(replay)
        self.assertEqual(len(ids), 1)
        incoming = {'movement_date': '2025-01-01', 'type': 'adjust_in', 'sku': self.sku.pk, 'quantity': '4', 'unit_cost': '0', **self.default}
        response = self.client.post('/api/inventory-movements/', incoming, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(sku_metrics(self.sku)['actual_quantity'], Decimal('22'))
        outgoing = {**incoming, 'type': 'sample_out', 'quantity': '5'}
        response = self.client.post('/api/inventory-movements/', outgoing, format='json')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(location_quantity(self.sku, self.default), Decimal('4'))
        self.assertEqual(location_quantity(self.sku, self.history), Decimal('18'))
        response = self.client.post('/api/inventory-movements/', {**outgoing, 'quantity': '4'}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(location_quantity(self.sku, self.default), Decimal('0'))
        self.assertEqual(location_quantity(self.sku, self.history), Decimal('18'))
        self.assertEqual(sku_metrics(self.sku)['actual_quantity'], Decimal('18'))
