from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from crm.models import Customer, Product, SKU, Supplier, SKUTradeUnit, Quote, Order, PurchaseOrder, InventoryMovement
from crm.services.fulfillment import sku_metrics
from crm.quotation_export_dto import build_quotation_export_dto
from crm.trade_units import amount_expression
from crm.tests.test_quotes import xlsx_cell_text


class TradeUnitsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(code='TU-C', name='Trade Buyer', country='Germany')
        self.product = Product.objects.create(code='TU-P', name='Strip')
        self.sku = SKU.objects.create(product=self.product, sku='TU-S', unit='m')
        self.supplier = Supplier.objects.create(code='TV', name='Supplier')
        self.unit = SKUTradeUnit.objects.create(sku=self.sku, name='10m Roll', unit='Roll', factor=10)
        self.today = date.today().isoformat()

    def post(self, url, data, code=201):
        response = self.client.post('/api/' + url, data, format='json')
        self.assertEqual(response.status_code, code, response.data)
        return response.data

    def line(self, quantity='2', price='8', unit=None):
        return dict(sku=self.sku.pk, trade_unit=(unit or self.unit).pk, trade_quantity=quantity, trade_unit_price=price)

    def quote(self, line=None):
        return self.post('quotes/', dict(customer=self.customer.pk, quote_date=self.today, items=[line or self.line()]))

    def confirm_order(self, order):
        return self.post(f"orders/{order['id']}/confirm/", {}, 200)

    def place_purchase(self, purchase):
        return self.post(f"purchase-orders/{purchase['id']}/place/", {}, 200)

    def test_complete_quote_order_purchase_receipt_shipment_chain(self):
        quote = self.quote()
        self.assertEqual(Decimal(quote['items'][0]['quantity']), 20)
        self.assertEqual(Decimal(quote['total_amount']), 16)
        draft = self.client.get(f"/api/quotes/{quote['id']}/order-draft/").data
        order = self.post('orders/', draft)
        order = self.confirm_order(order)
        self.assertEqual(order['quote'], quote['id'])
        purchase = self.post('purchase-orders/', dict(supplier=self.supplier.pk, order=order['id'], order_date=self.today, items=[self.line(price='5')]))
        purchase = self.place_purchase(purchase)
        receipt = dict(purchase_item=purchase['items'][0]['id'], receipt_date=self.today, quantity='1', trade_unit=self.unit.pk, trade_quantity='1', trade_unit_price='5', unit_cost='0')
        self.post(f"purchase-orders/{purchase['id']}/receive/", receipt)
        self.assertEqual(sku_metrics(self.sku)['actual_quantity'], 10)
        po = PurchaseOrder.objects.get(pk=purchase['id'])
        self.assertEqual(po.status, 'partial')
        self.assertEqual(po.items.first().remaining_quantity, 10)
        self.post(f"purchase-orders/{purchase['id']}/receive/", receipt)
        self.assertEqual(sku_metrics(self.sku)['reserved_quantity'], 20)
        self.post(f"orders/{order['id']}/ship/", dict(shipment_date=self.today, items=[dict(order_item=order['items'][0]['id'], quantity='2', trade_unit=self.unit.pk, trade_quantity='2')]))
        self.assertEqual(sku_metrics(self.sku)['actual_quantity'], 0)
        self.assertEqual(Order.objects.get(pk=order['id']).status, 'shipped')
        movement = InventoryMovement.objects.filter(type='sale_out').get()
        self.assertEqual(movement.trade_quantity, 2)
        self.assertEqual(movement.trade_snapshot['factor'], '10.00')

    def test_history_export_revision_and_discontinued_units(self):
        quote = self.quote()
        self.client.patch(f'/api/sku-trade-units/{self.unit.pk}/', {'active': False}, format='json')
        old = Quote.objects.get(pk=quote['id'])
        dto = build_quotation_export_dto(old)
        self.assertEqual(dto.products[0].unit, 'Roll')
        self.assertEqual(Decimal(dto.products[0].quantity), 2)
        self.assertIn('10.00 m', dto.products[0].description)
        self.post('quotes/', dict(customer=self.customer.pk, quote_date=self.today, items=[self.line()]), 400)
        revision = self.post(f"quotes/{quote['id']}/revise/", {'revision_summary': 'keep units'})
        self.assertEqual(revision['items'][0]['trade_unit'], self.unit.pk)
        revision2 = self.post(f"quotes/{quote['id']}/revise/", {'revision_summary': 'quantity', 'items': [self.line(quantity='3')]})
        self.assertEqual(Decimal(revision2['items'][0]['quantity']), 30)

    def test_reject_cross_sku_fraction_overflow_and_spoofed_factor(self):
        other = SKU.objects.create(product=self.product, sku='TU-OTHER', specification='other', unit='m')
        for changes in ({'sku': other.pk}, {'trade_quantity': '.5'}, {'trade_quantity': 'NaN'}, {'trade_quantity': '100000000000'}):
            self.post('quotes/', dict(customer=self.customer.pk, quote_date=self.today, items=[{**self.line(), **changes}]), 400)
        result = self.quote({**self.line(), 'quantity': '1', 'trade_snapshot': {'factor': '999'}})
        self.assertEqual(Decimal(result['items'][0]['quantity']), 20)
        self.post('quotes/', dict(customer=self.customer.pk, quote_date=self.today, items=[self.line('100000000', '100000000')]), 400)

    def test_exact_money_for_non_divisible_prices_and_base_inventory(self):
        unit = SKUTradeUnit.objects.create(sku=self.sku, name='3m Roll', unit='Roll', factor=3)
        quote = self.quote(self.line('100', '1', unit))
        item = Quote.objects.get(pk=quote['id']).items.get()
        self.assertEqual(item.quantity, 300)
        self.assertEqual(item.amount, 100)
        self.assertEqual(Decimal(quote['total_amount']), 100)
        self.assertAlmostEqual(Quote.objects.get(pk=quote['id']).items.annotate(value=amount_expression()).get().value, Decimal(100))

    def test_catalog_immutable_default_and_supplier_scope(self):
        response = self.client.patch(f'/api/sku-trade-units/{self.unit.pk}/', {'factor': '20'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.client.patch(f'/api/sku-trade-units/{self.unit.pk}/', {'is_default': True}, format='json')
        another = self.post('sku-trade-units/', dict(sku=self.sku.pk, name='20m Roll', unit='Roll', factor='20', is_default=True))
        self.unit.refresh_from_db()
        self.assertFalse(self.unit.is_default)
        scoped = SKUTradeUnit.objects.create(sku=self.sku, supplier=self.supplier, name='Supplier roll', unit='Roll', factor=10)
        other = Supplier.objects.create(code='TX', name='Other supplier')
        self.post('purchase-orders/', dict(supplier=other.pk, order_date=self.today, items=[self.line(unit=scoped)]), 400)
        response = self.client.patch(f'/api/skus/{self.sku.pk}/', {'unit': 'pcs'}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_manual_stock_units_and_overdraw_are_atomic(self):
        data = dict(movement_date=self.today, type='adjust_in', **self.line('3', '6'))
        movement = self.post('inventory-movements/', data)
        self.assertEqual(Decimal(movement['quantity']), 30)
        self.post('inventory-movements/', {**data, 'type': 'adjust_out', 'trade_quantity': '4'}, 400)
        self.assertEqual(sku_metrics(self.sku)['actual_quantity'], 30)

    def test_legacy_base_unit_payload_unchanged(self):
        result = self.quote(dict(sku=self.sku.pk, quantity='2.5', unit_price='4'))
        self.assertEqual(Decimal(result['total_amount']), 10)
        self.assertIsNone(result['items'][0]['trade_unit'])

    def test_alternative_receipt_unit_and_atomic_over_shipment(self):
        large = SKUTradeUnit.objects.create(sku=self.sku, name='20m Roll', unit='Roll', factor=20)
        order = self.post('orders/', dict(customer=self.customer.pk, order_date=self.today, items=[self.line('2')]))
        order = self.confirm_order(order)
        purchase = self.post('purchase-orders/', dict(supplier=self.supplier.pk, order_date=self.today, items=[self.line('1', unit=large)]))
        purchase = self.place_purchase(purchase)
        self.post(f"purchase-orders/{purchase['id']}/receive/", dict(purchase_item=purchase['items'][0]['id'], receipt_date=self.today, trade_unit=self.unit.pk, trade_quantity='2', trade_unit_price='4'))
        self.assertEqual(PurchaseOrder.objects.get(pk=purchase['id']).status, 'completed')
        self.post(f"orders/{order['id']}/ship/", dict(shipment_date=self.today, items=[dict(order_item=order['items'][0]['id'], trade_unit=large.pk, trade_quantity='2', overage_reason='gift_or_sample')]), 400)
        self.assertEqual(sku_metrics(self.sku)['actual_quantity'], 20)
        self.assertEqual(Order.objects.get(pk=order['id']).shipments.count(), 0)
        self.post(f"orders/{order['id']}/ship/", dict(shipment_date=self.today, items=[dict(order_item=order['items'][0]['id'], trade_unit=large.pk, trade_quantity='1')]))
        self.assertEqual(sku_metrics(self.sku)['actual_quantity'], 0)

    def test_fractional_package_and_precision_limit(self):
        fractional = SKUTradeUnit.objects.create(sku=self.sku, name='Cut roll', unit='Roll', factor=10, allow_fraction=True)
        result = self.quote(self.line('.5', unit=fractional))
        self.assertEqual(Decimal(result['items'][0]['quantity']), 5)
        tiny = SKUTradeUnit.objects.create(sku=self.sku, name='Tiny pack', unit='Pack', factor='.01', allow_fraction=True)
        self.post('quotes/', dict(customer=self.customer.pk, quote_date=self.today, items=[self.line('.01', unit=tiny)]), 400)

    def test_order_change_generates_revision_with_trade_snapshot(self):
        quote = self.quote()
        draft = self.client.get(f"/api/quotes/{quote['id']}/order-draft/").data
        draft['items'][0]['trade_quantity'] = '3'
        order = self.post('orders/', draft)
        order = self.confirm_order(order)
        self.assertNotEqual(order['quote'], quote['id'])
        revision = Quote.objects.get(pk=order['quote']).items.get()
        self.assertEqual(revision.trade_quantity, 3)
        self.assertEqual(revision.trade_snapshot['factor'], '10.00')
        self.assertEqual(Decimal(order['total_amount']), 24)

    def test_edit_draft_order_retains_units_and_updates_amount(self):
        order = self.post('orders/', dict(customer=self.customer.pk, order_date=self.today, status='draft', items=[self.line()]))
        response = self.client.patch(f"/api/orders/{order['id']}/", {'items': [self.line('3')]}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(Decimal(response.data['total_amount']), 24)
        self.assertEqual(response.data['items'][0]['trade_unit'], self.unit.pk)

    def test_same_sku_multiple_packaging_lines_fulfill_independently(self):
        large = SKUTradeUnit.objects.create(sku=self.sku, name='20m Roll', unit='Roll', factor=20)
        InventoryMovement.objects.create(movement_no='TU-MULTI-STOCK', movement_date=self.today, type='adjust_in', sku=self.sku, quantity=60)
        quote = self.post('quotes/', dict(customer=self.customer.pk, quote_date=self.today, items=[self.line('2', '8'), self.line('2', '15', large)]))
        self.assertEqual(Decimal(quote['total_amount']), 46)
        draft = self.client.get(f"/api/quotes/{quote['id']}/order-draft/").data
        order = self.post('orders/', draft)
        order = self.confirm_order(order)
        self.assertEqual([Decimal(row['quantity']) for row in order['items']], [20, 40])
        self.assertEqual(sku_metrics(self.sku)['reserved_quantity'], 60)
        self.post(f"orders/{order['id']}/ship/", dict(shipment_date=self.today, items=[
            dict(order_item=row['id'], trade_unit=row['trade_unit'], trade_quantity=row['trade_quantity']) for row in order['items']
        ]))
        self.assertEqual(sku_metrics(self.sku)['actual_quantity'], 0)
        self.assertEqual(Order.objects.get(pk=order['id']).status, 'shipped')

    def test_actual_excel_export_uses_transaction_units(self):
        from django.contrib.auth import get_user_model
        self.client.force_authenticate(get_user_model().objects.create_user(username='trade-unit-exporter'))
        quote = self.quote(self.line('100', '8'))
        response = self.client.get(f"/api/quotes/{quote['id']}/export/")
        self.assertEqual(response.status_code, 200, getattr(response, 'data', None))
        content = b''.join(response.streaming_content) if response.streaming else response.content
        self.assertEqual(Decimal(xlsx_cell_text(content, 'J11')), 100)
        self.assertEqual(xlsx_cell_text(content, 'K11'), 'Roll')
        self.assertEqual(Decimal(xlsx_cell_text(content, 'L11')), 8)
        self.assertEqual(Decimal(xlsx_cell_text(content, 'M11')), 800)
        self.assertIn('1000.00 m', xlsx_cell_text(content, 'D11'))
