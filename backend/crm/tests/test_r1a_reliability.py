"""R1-A scoped regression. Fixtures and fault injection are not real UI evidence."""
from datetime import date
from decimal import Decimal as D
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from crm.models import Customer, Product, SKU, Supplier, Order, PurchaseOrder, PaymentPlan, Transaction, InventoryMovement
from crm.services.finance import record_transaction
from crm.services.fulfillment import record_receipt, reverse_receipt, confirm_shipment, reverse_shipment, sku_metrics
from crm.services.purchase_lifecycle import place_purchase_order


class R1AReliabilityTests(TestCase):
    def setUp(self):
        self.day = date(2026, 10, 18)
        self.client = APIClient()
        self.customer = Customer.objects.create(code='R1A-C', name='R1A synthetic')
        self.supplier = Supplier.objects.create(code='RA', name='R1A synthetic supplier')
        self.sku = SKU.objects.create(sku='R1A-S', product=Product.objects.create(code='R1A-P', name='R1A'))
        self.order = Order.objects.create(order_no='R1A-O', customer=self.customer, order_date=self.day, expected_ship_date=self.day, currency='USD', exchange_rate=D('7.1'), status='confirmed')
        self.order_item = self.order.items.create(sku=self.sku, quantity=D('10'), unit_price=D('50'))
        self.purchase = PurchaseOrder.objects.create(purchase_no='R1A-PO', supplier=self.supplier, order_date=self.day, currency='USD', exchange_rate=D('7.2'))
        self.item = self.purchase.items.create(sku=self.sku, quantity=D('10'), unit_price=D('12.5'))

    def snapshot(self):
        self.purchase.refresh_from_db()
        return {'stock':sku_metrics(self.sku), 'status':self.purchase.status,
                'movements':list(InventoryMovement.objects.order_by('pk').values()),
                'receipts':list(self.item.receipts.order_by('pk').values()),
                'plans':list(PaymentPlan.objects.order_by('pk').values()),
                'transactions':list(Transaction.objects.order_by('pk').values())}

    def receive(self, qty):
        return record_receipt(self.item, {'quantity':D(qty), 'unit_cost':D('12.5'), 'receipt_date':self.day})

    def test_independent_purchase_no_source_partial_receipt_reversal_and_payment(self):
        place_purchase_order(self.purchase)
        self.assertIsNone(self.purchase.order_id)
        self.assertIsNone(self.item.supplier_sku_id)
        first = self.receive('4')
        self.assertEqual(sku_metrics(self.sku)['in_transit_quantity'], D('6'))
        reverse_receipt(first, 'R1A partial')
        self.assertEqual(sku_metrics(self.sku)['in_transit_quantity'], D('10'))
        self.receive('10')
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.status, 'completed')
        for amount, rate in [('40','7.15'), ('85','7.2')]:
            record_transaction({'purchase_order':self.purchase, 'kind':'supplier_payment', 'amount':D(amount), 'currency':'USD', 'exchange_rate':D(rate)})
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.paid_amount, D('125'))
        self.assertEqual(sum((t.rmb_amount for t in self.purchase.transactions.all()), D('0')), D('898'))
        self.assertTrue(all(p.remaining_amount == 0 for p in self.purchase.payment_plans.all()))

    def test_consumed_receipt_rejection_is_unchanged_then_shipment_reversal_restores_stock(self):
        place_purchase_order(self.purchase)
        receipt = self.receive('10')
        shipment = confirm_shipment(self.order, {'shipment_date':self.day,'items':[{'order_item':self.order_item.pk,'quantity':D('10')}]})
        before = self.snapshot()
        with self.assertRaises(ValidationError): reverse_receipt(receipt, 'consumed')
        self.assertEqual(self.snapshot(), before)
        reverse_shipment(shipment, 'R1A restore')
        self.assertEqual(sku_metrics(self.sku)['actual_quantity'], D('10'))
        self.assertEqual(sku_metrics(self.sku)['reserved_quantity'], D('10'))
        reverse_receipt(receipt, 'now available')
        before = self.snapshot()
        with self.assertRaises(ValidationError): reverse_receipt(receipt, 'duplicate')
        self.assertEqual(self.snapshot(), before)

    def test_receipt_failure_after_movement_insert_rolls_back_all_side_effects(self):
        place_purchase_order(self.purchase)
        before = self.snapshot()
        with patch('crm.services.fulfillment.rebalance_sku_reservations', side_effect=RuntimeError('R1A injected failure')):
            with self.assertRaises(RuntimeError): self.receive('4')
        self.assertEqual(self.snapshot(), before)

    def test_usd_direct_split_exact_decimals_and_invalid_amount_atomicity(self):
        response = self.client.post('/api/transactions/', {'transaction_date':str(self.day),'order':self.order.pk,'kind':'customer_receipt','direction':'income','category':'客户收款','amount':'340','currency':'USD','exchange_rate':'7.25'}, format='json')
        self.assertEqual(response.status_code,201,response.data)
        self.assertEqual(sum((t.amount for t in self.order.transactions.all()),D('0')),D('340'))
        self.assertEqual(sum((t.rmb_amount for t in self.order.transactions.all()),D('0')),D('2465'))
        self.assertEqual(sum((p.remaining_amount for p in self.order.payment_plans.all()),D('0')),D('160'))
        before = self.snapshot()
        for amount in ['0','-1','NaN','Infinity']:
            response = self.client.post('/api/transactions/', {'transaction_date':str(self.day),'order':self.order.pk,'kind':'customer_receipt','direction':'income','category':'客户收款','amount':amount,'currency':'USD','exchange_rate':'7.25'}, format='json')
            self.assertEqual(response.status_code,400,response.data)
            self.assertEqual(self.snapshot(),before)

    def test_transaction_number_replay_cannot_create_duplicate_or_partially_settle(self):
        payload={'transaction_date':str(self.day),'transaction_no':'R1A-RETRY','order':self.order.pk,'kind':'customer_receipt','direction':'income','category':'客户收款','amount':'340','currency':'USD','exchange_rate':'7.25'}
        response=self.client.post('/api/transactions/',payload,format='json')
        self.assertEqual(response.status_code,201,response.data)
        before=self.snapshot()
        response=self.client.post('/api/transactions/',payload,format='json')
        self.assertEqual(response.status_code,400,response.data)
        self.assertEqual(self.snapshot(),before)

    def test_finance_failure_after_first_split_rolls_back_all_rows_and_plans(self):
        # Fault injection exercises the real service transaction, not a real network failure.
        before=self.snapshot()
        original=Transaction.objects.create
        calls=[]
        def fail_second(**kwargs):
            calls.append(kwargs)
            if len(calls)==2: raise RuntimeError('R1A second split failure')
            return original(**kwargs)
        with patch.object(Transaction.objects,'create',side_effect=fail_second):
            with self.assertRaises(RuntimeError):
                record_transaction({'order':self.order,'kind':'customer_receipt','amount':D('340'),'currency':'USD','exchange_rate':D('7.25')})
        self.assertEqual(len(calls),2)
        self.assertEqual(self.snapshot(),before)
