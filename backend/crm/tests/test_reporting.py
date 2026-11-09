from datetime import date, datetime
from decimal import Decimal
import csv
import io
from zoneinfo import ZoneInfo

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from crm.models import ContractChangeRequest, Customer, InventoryMovement, Order, Product, ProductCategory, PurchaseOrder, RolePermission, SKU, Supplier, Transaction
from crm.services.finance import void_transaction
from crm.services.profit import order_profit_summary
from crm.tests import test_sales_data_scope as scope_fixture


class ReportingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(code="REPORT", name="Buyer", country="China", region="亚洲", owner="Alice")
        self.supplier = Supplier.objects.create(name="Factory", code="RP", country="China", main_products="LED驱动电源")
        self.category = ProductCategory.objects.create(name="照明")
        product = Product.objects.create(code="REPORT", name="Lamp", category=self.category)
        self.sku = SKU.objects.create(sku="REPORT-1", product=product, unit="pcs", specification="a")
        self.sku2 = SKU.objects.create(sku="REPORT-2", product=product, unit="box", specification="b")
        self.order = Order.objects.create(order_no="REPORT-O", customer=self.customer, customer_name_snapshot="Buyer", customer_country_snapshot="China", order_date=date(2026, 9, 1), currency="USD", exchange_rate=7, shipping_fee=3, discount=1, status="confirmed")
        self.order.items.create(sku=self.sku, quantity=2, unit_price=10, product_category_reference_snapshot=str(self.category.pk), product_category_name_snapshot=self.category.name)
        self.order.items.create(sku=self.sku2, quantity=1, unit_price=5, product_category_reference_snapshot=str(self.category.pk), product_category_name_snapshot=self.category.name)

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
        order = Order.objects.create(order_no="PREVIOUS", customer=self.customer, order_date=date(2026, 8, 2), shipping_fee=27, status="confirmed")
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
        purchase = PurchaseOrder.objects.create(purchase_no="REPORT-P", supplier=self.supplier, supplier_country_snapshot="China", order_date=date(2026, 9, 2), status="ordered", exchange_rate=7)
        purchase.items.create(sku=self.sku, quantity=3, unit_price=4, product_category_reference_snapshot=str(self.category.pk), product_category_name_snapshot=self.category.name)
        data = self.query(source="purchase", group_by="country")
        self.assertEqual(data['rows'][0]['label'], 'China')
        self.assertEqual(data['totals']['amount'], Decimal(84))
        self.assertEqual(self.query(source="purchase", group_by="supplier", filter_supplier=str(self.supplier.pk))['totals']['count'], 1)

    def test_sales_report_includes_approved_contract_adjustments_as_separate_rows(self):
        ContractChangeRequest.objects.create(order=self.order, amount_delta=Decimal("-20"), notes="折让", status="approved")
        data = self.query(group_by="sku")
        self.assertEqual(data["totals"]["amount"], Decimal("49"))  # (20 + 5 + 3 - 1 - 20) * 7
        adjustment = next(row for row in data["rows"] if row["key"] == "__adjustment__")
        self.assertEqual(adjustment["label"], "订单金额调整")
        ContractChangeRequest.objects.filter(order=self.order).update(amount_delta=Decimal("20"))
        self.assertEqual(self.query(group_by="customer")["totals"]["amount"], Decimal("329"))

    def test_purchase_report_includes_approved_contract_adjustments_without_additional_costs(self):
        purchase = PurchaseOrder.objects.create(purchase_no="REPORT-ADJUST", supplier=self.supplier, order_date=date(2026, 9, 2), status="ordered", exchange_rate=1)
        purchase.items.create(sku=self.sku, quantity=10, unit_price=10)
        ContractChangeRequest.objects.create(purchase_order=purchase, amount_delta=Decimal("20"), notes="加项", status="approved")
        self.assertEqual(self.query(source="purchase", group_by="supplier")["totals"]["amount"], Decimal("120"))
        ContractChangeRequest.objects.filter(purchase_order=purchase).update(amount_delta=Decimal("-20"))
        self.assertEqual(self.query(source="purchase", group_by="supplier")["totals"]["amount"], Decimal("80"))

    def test_purchase_report_excludes_draft_and_cancelled_contracts(self):
        for purchase_no, status, amount in (
            ("REPORT-PO-ORDERED", "ordered", "200"),
            ("REPORT-PO-DRAFT", "draft", "100"),
            ("REPORT-PO-CANCELLED", "cancelled", "300"),
        ):
            purchase = PurchaseOrder.objects.create(
                purchase_no=purchase_no, supplier=self.supplier, order_date=date(2026, 9, 3), status=status,
            )
            purchase.items.create(sku=self.sku, quantity=1, unit_price=Decimal(amount))

        data = self.query(source="purchase", group_by="supplier")

        self.assertEqual(data["totals"]["amount"], Decimal("200"))
        self.assertEqual(data["totals"]["count"], 1)

    def test_profit_report_excludes_draft_and_cancelled_contracts(self):
        draft = Order.objects.create(order_no="REPORT-PROFIT-D", customer=self.customer, order_date=date(2026, 9, 2), status="draft")
        draft.items.create(sku=self.sku, quantity=1, unit_price=99)
        cancelled = Order.objects.create(order_no="REPORT-PROFIT-C", customer=self.customer, order_date=date(2026, 9, 2), status="cancelled")
        cancelled.items.create(sku=self.sku, quantity=1, unit_price=99)
        data = self.query(source="profit", group_by="customer")
        self.assertEqual(data["totals"]["count"], 1)
        self.assertEqual(data["totals"]["amount"], order_profit_summary(self.order)["estimated_profit_rmb"])

    def test_cash_only_confirmed_and_signed_actual_amount(self):
        for i, (direction, status, actual) in enumerate([('income', 'confirmed', 50), ('expense', 'confirmed', 20), ('income', 'pending', 100), ('income', 'cancelled', 200)]):
            Transaction.objects.create(transaction_no=f'R{i}', transaction_date=date(2026, 9, 1), direction=direction, status=status, amount=10, exchange_rate=7, rmb_amount=actual, category='Bank')
        data = self.query(source="cash", group_by="direction")
        self.assertEqual(data['totals']['amount'], Decimal(30))
        self.assertEqual(data['totals']['count'], 2)
        self.assertEqual(self.query(source="cash", filter_direction="expense")['totals']['amount'], Decimal(-20))

    def test_voided_transaction_is_excluded_from_cash_dashboard(self):
        row = Transaction.objects.create(
            transaction_no="R-VOID", transaction_date=date(2026, 9, 1), direction="income",
            kind="other_income", category="其他收入", amount=Decimal("50"),
            exchange_rate=Decimal("7"), rmb_amount=Decimal("350"), currency="USD",
        )
        void_transaction(row, "报表测试作废")

        data = self.query(source="cash", group_by="direction")
        self.assertEqual(data['totals']['amount'], Decimal("0"))
        self.assertEqual(data['totals']['count'], 0)

    def test_inventory_net_change_per_unit(self):
        for i, (kind, quantity) in enumerate([('purchase_in', 10), ('sale_out', 4)]):
            InventoryMovement.objects.create(movement_no=f'IM{i}', movement_date=date(2026, 9, 3), type=kind, sku=self.sku, quantity=quantity)
        self.assertEqual(self.query(source="inventory", group_by="sku")['totals']['quantities'], {"pcs": Decimal(6)})

    def test_customer_growth_and_invalid_inputs(self):
        Customer.objects.filter(pk=self.customer.pk).update(created_at=datetime(2026, 9, 5, tzinfo=ZoneInfo('Asia/Shanghai')))
        self.assertEqual(self.query(source="customers", group_by="owner")['rows'][0]['count'], 1)
        for params in [{"source": "invalid"}, {"source": "purchase", "group_by": "customer"}, {"date_from": "bad"}, {"date_from": "2026-10-01", "date_to": "2026-09-01"}, {"date_from": "1900-01-01", "date_to": "2026-09-01"}, {"grain": "hour"}, {"date_field": "customer__created_at"}, {"filter_secret": "x"}]:
            self.assertEqual(self.client.get('/api/reports/data/', params).status_code, 400, params)

    def test_country_and_customer_cross_group_preserves_totals_and_distinct_documents(self):
        other = Customer.objects.create(code="REPORT-2", name="Second buyer", country="China", region="亚洲")
        order = Order.objects.create(order_no="REPORT-O-2", customer=other, customer_name_snapshot=other.name, customer_country_snapshot="China", order_date=date(2026, 9, 2), currency="CNY", exchange_rate=1, status="confirmed")
        order.items.create(sku=self.sku, quantity=3, unit_price=10, product_category_reference_snapshot=str(self.category.pk), product_category_name_snapshot=self.category.name)
        data = self.query(group_by="country", group_by_2="customer")
        self.assertEqual(data["group_by_2"], "customer")
        self.assertEqual(data["totals"]["amount"], Decimal("219"))
        self.assertEqual(data["totals"]["count"], 2)
        self.assertEqual(data["totals"]["quantities"], {"pcs": Decimal("5"), "box": Decimal("1")})
        self.assertEqual({tuple(item["dimension"] for item in row["groups"]) for row in data["rows"]}, {("country", "customer")})
        self.assertEqual(sum(row["amount"] for row in data["rows"]), Decimal("219"))
        self.assertTrue(all(row["key"] != row["groups"][0]["key"] for row in data["rows"]))

    def test_category_and_sku_cross_group_keeps_units_and_document_count(self):
        data = self.query(group_by="category", group_by_2="sku")
        self.assertEqual(data["totals"]["amount"], Decimal("189"))
        self.assertEqual(data["totals"]["count"], 1)
        self.assertEqual(data["totals"]["quantities"], {"pcs": Decimal("2"), "box": Decimal("1")})
        self.assertEqual(len(data["rows"]), 3)
        self.assertTrue(all(len(row["groups"]) == 2 for row in data["rows"]))
        self.assertEqual({row["groups"][1]["dimension"] for row in data["rows"]}, {"sku"})

    def test_time_and_customer_cross_group_uses_date_bucket_and_no_future_bucket(self):
        customer = Customer.objects.create(code="REPORT-PAST", name="August buyer", country="China")
        order = Order.objects.create(order_no="REPORT-AUG", customer=customer, order_date=date(2026, 8, 2), currency="CNY", exchange_rate=1, status="confirmed")
        order.items.create(sku=self.sku, quantity=1, unit_price=8)
        future = Order.objects.create(order_no="REPORT-FUTURE", customer=customer, order_date=date(2026, 10, 1), currency="CNY", exchange_rate=1, status="confirmed")
        future.items.create(sku=self.sku, quantity=1, unit_price=100)
        response = self.client.get('/api/reports/data/', {"date_from": "2026-08-01", "date_to": "2026-09-30", "group_by": "time", "group_by_2": "customer", "grain": "month"})
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data
        self.assertEqual(data["totals"]["amount"], Decimal("197"))
        self.assertEqual({row["groups"][0]["key"] for row in data["rows"]}, {"2026-08", "2026-09"})
        self.assertNotIn("2026-10", {row["groups"][0]["key"] for row in data["rows"]})

    def test_cross_group_rejects_invalid_duplicate_or_time_filter_dimensions(self):
        for params in (
            {"group_by": "customer", "group_by_2": "customer"},
            {"group_by": "time", "group_by_2": "time"},
            {"source": "purchase", "group_by": "supplier", "group_by_2": "customer"},
            {"group_by": "customer", "group_by_2": "time", "filter_time": "2026-09"},
        ):
            response = self.client.get('/api/reports/data/', {"date_from": "2026-09-01", "date_to": "2026-09-30", **params})
            self.assertEqual(response.status_code, 400, params)

    def test_cross_group_filter_and_csv_have_the_same_two_group_columns(self):
        filtered = self.query(group_by="country", group_by_2="customer", filter_country="China")
        self.assertEqual(filtered["totals"]["amount"], Decimal("189"))
        response = self.client.get('/api/reports/data/', {"date_from": "2026-09-01", "date_to": "2026-09-30", "group_by": "country", "group_by_2": "customer", "filter_country": "China", "export": "csv"})
        self.assertEqual(response.status_code, 200)
        rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))
        self.assertEqual(rows[3][:2], ["国家/地区", "客户"])
        self.assertEqual(rows[4][0], "China")
        self.assertEqual(rows[-1][0], "合计（单据去重）")
        self.assertEqual(Decimal(rows[-1][2]), Decimal("189"))
        self.assertEqual(int(rows[-1][3]), 1)

    def test_sales_details_reconcile_country_customer_group_and_keep_adjustment_separate(self):
        response = self.client.get('/api/reports/details/', {
            "source": "sales", "date_from": "2026-09-01", "date_to": "2026-09-30",
            "group_by": "country", "group_by_2": "customer", "group_value": "China",
            "group_2_value": str(self.customer.pk), "page_size": 50,
        })
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data
        self.assertEqual(data["totals"]["amount"], Decimal("189"))
        self.assertEqual(data["totals"]["count"], 1)
        self.assertEqual(data["totals"]["quantities"], {"pcs": Decimal("2"), "box": Decimal("1")})
        self.assertEqual(sum(row["amount"] for row in data["rows"]), Decimal("189"))
        self.assertEqual([row["record_type"] for row in data["rows"]].count("adjustment"), 1)
        item_rows = [row for row in data["rows"] if not row["is_adjustment"]]
        self.assertEqual({row["document_no"] for row in item_rows}, {"REPORT-O"})
        self.assertEqual({row["unit"] for row in item_rows}, {"pcs", "box"})
        self.assertTrue(all(row["document_id"] == self.order.pk for row in data["rows"]))

    def test_historical_dimensions_remain_frozen_after_customer_and_product_master_changes(self):
        new_category = ProductCategory.objects.create(name="新分类")
        self.customer.country = "France"
        self.customer.save(update_fields=["country"])
        product = self.sku.product
        product.category = new_category
        product.save(update_fields=["category"])
        later_order = Order.objects.create(
            order_no="REPORT-O-LATER", customer=self.customer, customer_name_snapshot="Buyer",
            customer_country_snapshot="France", order_date=date(2026, 9, 3), currency="USD",
            exchange_rate=7, status="confirmed",
        )
        later_order.items.create(
            sku=self.sku, quantity=1, unit_price=2,
            product_category_reference_snapshot=str(new_category.pk),
            product_category_name_snapshot=new_category.name,
        )

        country = self.query(group_by="country")
        categories = self.query(group_by="category")
        self.assertIn("China", {row["label"] for row in country["rows"]})
        self.assertIn("France", {row["label"] for row in country["rows"]})
        self.assertIn("照明", {row["label"] for row in categories["rows"]})
        self.assertIn("新分类", {row["label"] for row in categories["rows"]})
        historical_category = next(row for row in categories["rows"] if row["label"] == "照明")
        current_category = next(row for row in categories["rows"] if row["label"] == "新分类")

        detail = self.client.get("/api/reports/details/", {
            "source": "sales", "date_from": "2026-09-01", "date_to": "2026-09-30",
            "group_by": "category", "group_value": historical_category["key"], "page_size": 50,
        })
        self.assertEqual(detail.status_code, 200, detail.data)
        self.assertEqual(detail.data["totals"]["amount"], Decimal("175"))
        self.assertEqual(len(detail.data["rows"]), 2)
        current_detail = self.client.get("/api/reports/details/", {
            "source": "sales", "date_from": "2026-09-01", "date_to": "2026-09-30",
            "group_by": "category", "group_value": current_category["key"], "page_size": 50,
        })
        self.assertEqual(current_detail.status_code, 200, current_detail.data)
        self.assertEqual(current_detail.data["totals"]["amount"], Decimal("14"))

        exported = self.client.get("/api/reports/data/", {
            "source": "sales", "group_by": "country", "date_from": "2026-09-01",
            "date_to": "2026-09-30", "export": "csv",
        })
        self.assertEqual(exported.status_code, 200)
        csv_text = exported.content.decode("utf-8-sig")
        self.assertIn("China", csv_text)
        self.assertIn("France", csv_text)
        category_export = self.client.get("/api/reports/data/", {
            "source": "sales", "group_by": "category", "date_from": "2026-09-01",
            "date_to": "2026-09-30", "export": "csv",
        })
        self.assertIn("照明", category_export.content.decode("utf-8-sig"))
        self.assertIn("新分类", category_export.content.decode("utf-8-sig"))

    def test_sales_details_follow_sku_group_without_repeating_order_amount(self):
        response = self.client.get('/api/reports/details/', {
            "source": "sales", "date_from": "2026-09-01", "date_to": "2026-09-30",
            "group_by": "sku", "group_value": str(self.sku.pk), "page_size": 50,
        })
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data
        self.assertEqual(data["totals"]["amount"], Decimal("140"))
        self.assertEqual(data["totals"]["count"], 1)
        self.assertEqual(len(data["rows"]), 1)
        self.assertEqual(data["rows"][0]["amount"], Decimal("140"))
        self.assertFalse(data["rows"][0]["is_adjustment"])

    def test_purchase_details_are_paginated_and_reconcile_purchase_adjustment(self):
        purchase = PurchaseOrder.objects.create(purchase_no="REPORT-P-DETAIL", supplier=self.supplier, order_date=date(2026, 9, 2), status="ordered", exchange_rate=7)
        purchase.items.create(sku=self.sku, quantity=3, unit_price=4)
        purchase.items.create(sku=self.sku2, quantity=2, unit_price=5)
        ContractChangeRequest.objects.create(purchase_order=purchase, amount_delta=Decimal("6"), status="approved")
        response = self.client.get('/api/reports/details/', {
            "source": "purchase", "date_from": "2026-09-01", "date_to": "2026-09-30",
            "group_by": "supplier", "group_value": str(self.supplier.pk), "page": 1, "page_size": 2,
        })
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data
        self.assertEqual(data["totals"]["amount"], Decimal("196"))
        self.assertEqual(data["totals"]["count"], 1)
        self.assertEqual(data["count"], 3)
        self.assertEqual(data["page_size"], 2)
        self.assertEqual(len(data["rows"]), 2)
        self.assertEqual(data["totals"]["quantities"], {"pcs": Decimal("3"), "box": Decimal("2")})

    def test_details_reject_invalid_selection_and_keep_historical_order_out(self):
        historical = Order.objects.create(order_no="REPORT-HISTORY-DETAIL", customer=self.customer, order_date=date(2026, 9, 4), currency="CNY", exchange_rate=1, status="confirmed", historical_only=True)
        historical.items.create(sku=self.sku, quantity=1, unit_price=999)
        response = self.client.get('/api/reports/details/', {
            "source": "sales", "date_from": "2026-09-01", "date_to": "2026-09-30",
            "group_by": "customer", "group_value": str(self.customer.pk), "filter_time": "2026-09",
        })
        self.assertEqual(response.status_code, 400)
        response = self.client.get('/api/reports/details/', {
            "source": "sales", "date_from": "2026-09-01", "date_to": "2026-09-30",
            "group_by": "customer", "group_value": str(self.customer.pk), "page_size": 50,
        })
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["totals"]["amount"], Decimal("189"))

    def test_historical_only_order_is_not_in_formal_cross_group_report(self):
        historical = Order.objects.create(order_no="REPORT-HISTORY", customer=self.customer, order_date=date(2026, 9, 4), currency="CNY", exchange_rate=1, status="confirmed", historical_only=True)
        historical.items.create(sku=self.sku, quantity=1, unit_price=999)
        data = self.query(group_by="country", group_by_2="customer")
        self.assertEqual(data["totals"]["amount"], Decimal("189"))
        self.assertEqual(data["totals"]["count"], 1)

    def test_every_catalog_dimension_runs(self):
        catalog = self.client.get('/api/reports/catalog/').data
        for source, spec in catalog['sources'].items():
            for dimension in spec['dimensions']:
                self.query(source=source, group_by=dimension)

    def test_export_has_full_rows_and_formula_protection(self):
        Order.objects.filter(pk=self.order.pk).update(customer_name_snapshot='=HYPERLINK("example")')
        response = self.client.get('/api/reports/data/', {"source": "sales", "group_by": "customer", "date_from": "2026-09-01", "date_to": "2026-09-30", "export": "csv"})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8-sig')
        self.assertIn("'=HYPERLINK", content)
        self.assertIn('189', content)
        self.assertEqual(list(csv.reader(io.StringIO(content)))[3], ["客户", "金额（人民币）", "去重单据/档案数", "数量（按单位）"])

    def test_catalog_and_region_edit_api(self):
        self.assertEqual(self.client.patch(f'/api/customers/{self.customer.pk}/', {"region": "华南"}, format='json').status_code, 200)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.region, '华南')


@override_settings(**scope_fixture.RBAC_SETTINGS, PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ReportingDimensionPermissionTests(TestCase):
    make_employee = scope_fixture.SalesDataScopeTests.make_employee

    def setUp(self):
        scope_fixture.SalesDataScopeTests.setUp(self)
        self.client.force_authenticate(self.employee_a.user)
        category = ProductCategory.objects.create(name="权限测试分类")
        product = Product.objects.create(code="REPORT-SCOPE", name="权限测试产品", category=category)
        sku = SKU.objects.create(sku="REPORT-SCOPE-1", product=product, unit="pcs")
        order = Order.objects.create(order_no="REPORT-SCOPE-O", customer=self.customer_a, order_date=date(2026, 10, 1), currency="CNY", exchange_rate=1, status="confirmed")
        order.items.create(sku=sku, quantity=1, unit_price=10)

    def test_second_dimension_requires_its_own_view_permission(self):
        RolePermission.objects.filter(role=self.roles["self"], module="customers").update(can_view=False)
        response = self.client.get('/api/reports/data/', {"date_from": "2026-10-01", "date_to": "2026-10-31", "group_by": "sku", "group_by_2": "customer"})
        self.assertEqual(response.status_code, 403, response.data)

    def test_raw_details_require_original_record_permission(self):
        RolePermission.objects.filter(role=self.roles["self"], module="orders").update(can_view=False)
        response = self.client.get('/api/reports/details/', {
            "date_from": "2026-10-01", "date_to": "2026-10-31",
            "group_by": "sku", "group_value": "1",
        })
        self.assertEqual(response.status_code, 403, response.data)

    def test_old_sales_report_url_is_rejected_when_orders_view_is_revoked(self):
        RolePermission.objects.filter(role=self.roles["self"], module="orders").update(can_view=False)
        response = self.client.get('/api/reports/data/', {
            "source": "sales", "group_by": "customer", "date_field": "order_date",
            "date_from": "2026-10-01", "date_to": "2026-10-31",
        })
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(response.data["detail"], "你没有权限执行此财务操作。")
        self.assertNotIn("rows", response.data)
