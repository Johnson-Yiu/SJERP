from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.test import TestCase
from rest_framework.test import APIClient

from crm.models import Customer, InventoryMovement, Order, Product, ProductCategory, PurchaseOrder, SKU, Supplier, Transaction


class ReportingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(code="REPORT", name="Buyer", country="China", region="亚洲", owner="Alice")
        self.supplier = Supplier.objects.create(name="Factory", code="RP", country="China", main_products="LED驱动电源")
        category = ProductCategory.objects.create(name="照明")
        product = Product.objects.create(code="REPORT", name="Lamp", category=category)
        self.sku = SKU.objects.create(sku="REPORT-1", product=product, unit="pcs", specification="a")
        self.sku2 = SKU.objects.create(sku="REPORT-2", product=product, unit="box", specification="b")
        self.order = Order.objects.create(order_no="REPORT-O", customer=self.customer, order_date=date(2026, 9, 1), currency="USD", exchange_rate=7, shipping_fee=3, discount=1)
        self.order.items.create(sku=self.sku, quantity=2, unit_price=10)
        self.order.items.create(sku=self.sku2, quantity=1, unit_price=5)

    def query(self, **kwargs):
        response = self.client.get('/api/reports/data/', {"date_from": "2026-09-01", "date_to": "2026-09-30", **kwargs})
        self.assertEqual(response.status_code, 200, getattr(response, "data", response.content))
        return response.data

    def test_sales_reconciles_and_counts_documents_once(self):
        data = self.query(group_by="sku")
        self.assertEqual(data['totals']['amount'], Decimal(189))
        self.assertEqual(sum(row['amount'] for row in data['rows']), Decimal(189))
        self.assertEqual(data['totals']['count'], 1)
        self.assertEqual(data['totals']['quantities'], {"pcs": Decimal(2), "box": Decimal(1)})
        self.assertEqual(len(data['rows']), 3)
        self.assertEqual(self.query(group_by="category")['rows'][0]['count'], 1)

    def test_currency_and_excluded_status(self):
        for status in ['cancelled', 'draft', 'confirmed']:
            order = Order.objects.create(order_no=f"REPORT-{status}", customer=self.customer, order_date=date(2026, 9, 30), status=status, currency="CNY", exchange_rate=1)
            order.items.create(sku=self.sku, quantity=1, unit_price=20)
        data = self.query(group_by="currency")
        self.assertEqual(data['totals']['amount'], Decimal(209))
        self.assertEqual(data['totals']['count'], 2)

    def test_product_filter_excludes_order_adjustment(self):
        data = self.query(group_by="customer", filter_sku=str(self.sku.pk))
        self.assertEqual(data['totals']['amount'], Decimal(140))
        self.assertEqual(data['totals']['quantities'], {"pcs": Decimal(2)})

    def test_region_and_empty_filter(self):
        self.assertEqual(self.query(group_by="region")['rows'][0]['label'], '亚洲')
        self.customer.region = ''
        self.customer.save()
        self.assertEqual(self.query(group_by="region", filter_region='')['rows'][0]['label'], '未填写')

    def test_time_buckets_zero_fill_and_comparison(self):
        order = Order.objects.create(order_no="PREVIOUS", customer=self.customer, order_date=date(2026, 8, 2), shipping_fee=27)
        data = self.query(grain="day")
        self.assertEqual(len(data['rows']), 30)
        self.assertEqual(data['rows'][1]['amount'], 0)
        self.assertEqual(data['previous']['amount'], Decimal(27))
        self.assertEqual(data['changes']['amount'], Decimal(600))
        self.assertEqual(self.query(grain="week")['rows'][0]['key'], '2026-08-31')
        self.assertEqual(self.query(grain="quarter")['rows'][0]['key'], '2026-Q3')
        self.assertEqual(self.query(grain="year")['rows'][0]['key'], '2026')

    def test_date_boundary_and_null_due_date(self):
        self.assertEqual(self.query(date_field="expected_ship_date")['totals']['count'], 0)
        self.assertEqual(self.query(date_from="2026-09-01", date_to="2026-09-01")['totals']['count'], 1)
        self.assertEqual(self.query(date_from="2026-09-02")['totals']['count'], 0)

    def test_year_comparison_handles_leap_day(self):
        data = self.query(date_from="2024-02-29", date_to="2024-02-29", comparison="year")
        self.assertEqual(data['comparison_period'], {"date_from": date(2023, 2, 28), "date_to": date(2023, 2, 28)})
        self.assertIsNone(data['changes']['amount'])

    def test_created_at_uses_business_timezone(self):
        Order.objects.filter(pk=self.order.pk).update(created_at=datetime(2026, 8, 31, 16, 0, tzinfo=ZoneInfo('UTC')))
        self.assertEqual(self.query(date_field="created_at", date_to="2026-09-01")['totals']['count'], 1)

    def test_purchase_without_sales_order_and_supplier_country(self):
        purchase = PurchaseOrder.objects.create(purchase_no="REPORT-P", supplier=self.supplier, order_date=date(2026, 9, 2), status="ordered", exchange_rate=7)
        purchase.items.create(sku=self.sku, quantity=3, unit_price=4)
        data = self.query(source="purchase", group_by="country")
        self.assertEqual(data['rows'][0]['label'], 'China')
        self.assertEqual(data['totals']['amount'], Decimal(84))
        self.assertEqual(self.query(source="purchase", group_by="supplier", filter_supplier=str(self.supplier.pk))['totals']['count'], 1)

    def test_cash_only_confirmed_and_signed_actual_amount(self):
        for i, (direction, status, actual) in enumerate([('income', 'confirmed', 50), ('expense', 'confirmed', 20), ('income', 'pending', 100), ('income', 'cancelled', 200)]):
            Transaction.objects.create(transaction_no=f'R{i}', transaction_date=date(2026, 9, 1), direction=direction, status=status, amount=10, exchange_rate=7, rmb_amount=actual, category='Bank')
        data = self.query(source="cash", group_by="direction")
        self.assertEqual(data['totals']['amount'], Decimal(30))
        self.assertEqual(data['totals']['count'], 2)
        self.assertEqual(self.query(source="cash", filter_direction="expense")['totals']['amount'], Decimal(-20))

    def test_inventory_net_change_per_unit(self):
        for i, (kind, quantity) in enumerate([('purchase_in', 10), ('sale_out', 4)]):
            InventoryMovement.objects.create(movement_no=f'IM{i}', movement_date=date(2026, 9, 3), type=kind, sku=self.sku, quantity=quantity)
        self.assertEqual(self.query(source="inventory", group_by="sku")['totals']['quantities'], {"pcs": Decimal(6)})

    def test_customer_growth_and_invalid_inputs(self):
        Customer.objects.filter(pk=self.customer.pk).update(created_at=datetime(2026, 9, 5, tzinfo=ZoneInfo('Asia/Shanghai')))
        self.assertEqual(self.query(source="customers", group_by="owner")['rows'][0]['count'], 1)
        for params in [{"source": "invalid"}, {"source": "purchase", "group_by": "customer"}, {"date_from": "bad"}, {"date_from": "2026-10-01", "date_to": "2026-09-01"}, {"date_from": "1900-01-01", "date_to": "2026-09-01"}, {"grain": "hour"}, {"date_field": "customer__created_at"}, {"filter_secret": "x"}]:
            self.assertEqual(self.client.get('/api/reports/data/', params).status_code, 400, params)

    def test_every_catalog_dimension_runs(self):
        catalog = self.client.get('/api/reports/catalog/').data
        for source, spec in catalog['sources'].items():
            for dimension in spec['dimensions']:
                self.query(source=source, group_by=dimension)

    def test_export_has_full_rows_and_formula_protection(self):
        self.customer.name = '=HYPERLINK("example")'
        self.customer.save()
        response = self.client.get('/api/reports/data/', {"source": "sales", "group_by": "customer", "date_from": "2026-09-01", "date_to": "2026-09-30", "export": "csv"})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8-sig')
        self.assertIn("'=HYPERLINK", content)
        self.assertIn('189', content)

    def test_catalog_and_region_edit_api(self):
        self.assertEqual(self.client.patch(f'/api/customers/{self.customer.pk}/', {"region": "华南"}, format='json').status_code, 200)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.region, '华南')
