import csv
import io
from datetime import date, datetime, timezone as datetime_timezone
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from crm.models import (
    Customer,
    FollowUp,
    Order,
    OrderItem,
    Product,
    ProductCategory,
    SKU,
    Transaction,
)


class DashboardImportTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.operator = get_user_model().objects.create_superuser(
            username="dashboard-csv-operator", email="dashboard-csv@example.com", password="secret",
        )
        self.client.force_authenticate(self.operator)
        self.customer = Customer.objects.create(code="J1-CUSTOMER", name="J1 Buyer")
        self.category = ProductCategory.objects.create(name="J1 Lights")
        self.product = Product.objects.create(
            code="J1-PRODUCT", name="J1 Lamp", sales_model_prefix="J1L", category=self.category,
        )
        self.sku = SKU.objects.create(sku="J1-SKU", product=self.product, specification="Warm", unit="pcs")

    def create_order(self, number, status, amount, order_date=None):
        order = Order.objects.create(
            order_no=number, customer=self.customer, order_date=order_date or timezone.localdate(), status=status,
        )
        OrderItem.objects.create(order=order, sku=self.sku, quantity=1, unit_price=Decimal(amount))
        return order

    def upload_csv(self, entity, headers, rows):
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer)
        writer.writerow(headers)
        writer.writerows(rows)
        content = buffer.getvalue().encode("utf-8")
        preview = self.client.post("/api/import/csv/preview/", {
            "entity": entity, "file": SimpleUploadedFile("import.csv", content, content_type="text/csv"),
        }, format="multipart")
        if preview.status_code != 200 or preview.data["errors"]:
            return preview
        with override_settings(AUDIT_LOG_ENABLED=True):
            return self.client.post("/api/import/csv/execute/", {
                "entity": entity, "preview_token": preview.data["preview_token"],
                "file": SimpleUploadedFile("import.csv", content, content_type="text/csv"),
            }, format="multipart")

    def test_dashboard_sales_metrics_exclude_draft_and_cancelled_orders(self):
        self.create_order("J1-DRAFT", "draft", "100")
        formal = self.create_order("J1-CONFIRMED", "confirmed", "200")
        self.create_order("J1-CANCELLED", "cancelled", "300")

        response = self.client.get("/api/dashboard/")

        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertEqual(Decimal(str(data["summary"]["sales_ytd"])), Decimal("200"))
        self.assertEqual(data["summary"]["orders_ytd"], 1)
        month_row = next(row for row in data["monthly_sales"] if row["month"] == formal.order_date.strftime("%Y-%m"))
        self.assertEqual(Decimal(str(month_row["sales"])), Decimal("200"))
        self.assertEqual(month_row["orders"], 1)
        self.assertEqual(data["top_customers"][0]["orders"], 1)
        self.assertEqual(Decimal(str(data["top_customers"][0]["sales"])), Decimal("200"))
        self.assertEqual(sum((Decimal(str(row["sales"])) for row in data["category_sales"]), Decimal("0")), Decimal("200"))
        self.assertEqual([row["order_no"] for row in data["recent_orders"]], ["J1-CONFIRMED"])

    def test_dashboard_and_sales_report_use_same_formal_order_total(self):
        today = timezone.localdate()
        order = self.create_order("J1-REPORT-MATCH", "confirmed", "200", today)
        order.shipping_fee = Decimal("10")
        order.discount = Decimal("5")
        order.save(update_fields=["shipping_fee", "discount"])
        dashboard = self.client.get("/api/dashboard/").data
        report = self.client.get("/api/reports/data/", {
            "source": "sales", "group_by": "customer", "date_from": date(today.year, 1, 1).isoformat(),
            "date_to": today.isoformat(),
        })

        self.assertEqual(report.status_code, 200)
        self.assertEqual(Decimal(str(dashboard["summary"]["sales_ytd"])), report.data["totals"]["amount"])
        self.assertEqual(report.data["totals"]["amount"], order.total_amount)

    @patch("crm.views.timezone.localdate", return_value=date(2026, 10, 22))
    def test_dashboard_uses_one_server_date_window_for_operating_metrics(self, _today):
        self.create_order("J1-BEFORE-TREND", "confirmed", "2", date(2025, 10, 31))
        trend_start = self.create_order("J1-TREND-START", "confirmed", "3", date(2025, 11, 1))
        year_start = self.create_order("J1-YEAR-START", "confirmed", "10", date(2026, 1, 1))
        today_order = self.create_order("J1-TODAY", "confirmed", "20", date(2026, 10, 22))
        self.create_order("J1-TOMORROW", "confirmed", "40", date(2026, 10, 23))
        self.create_order("J1-NEXT-MONTH", "confirmed", "50", date(2026, 11, 1))
        historical = self.create_order("J1-HISTORICAL", "confirmed", "60", date(2026, 10, 10))
        historical.historical_only = True
        historical.save(update_fields=["historical_only"])
        self.create_order("J1-DRAFT", "draft", "70", date(2026, 10, 22))
        self.create_order("J1-CANCELLED", "cancelled", "80", date(2026, 10, 22))

        Transaction.objects.create(
            transaction_no="J1-TODAY-INCOME", transaction_date=date(2026, 10, 22), direction="income",
            category="客户收款", amount=Decimal("10"), currency="USD", exchange_rate=Decimal("7"),
            rmb_amount=Decimal("10"), status="confirmed",
        )
        Transaction.objects.create(
            transaction_no="J1-TODAY-EXPENSE", transaction_date=date(2026, 10, 22), direction="expense",
            category="办公费用", amount=Decimal("3"), currency="USD", exchange_rate=Decimal("7"),
            rmb_amount=Decimal("3"), status="confirmed",
        )
        Transaction.objects.create(
            transaction_no="J1-FUTURE-INCOME", transaction_date=date(2026, 10, 23), direction="income",
            category="客户收款", amount=Decimal("20"), currency="USD", exchange_rate=Decimal("7"),
            rmb_amount=Decimal("20"), status="confirmed",
        )
        Transaction.objects.create(
            transaction_no="J1-FUTURE-PENDING", transaction_date=date(2026, 10, 22), direction="income",
            category="客户收款", amount=Decimal("100"), currency="USD", exchange_rate=Decimal("7"),
            rmb_amount=Decimal("100"), status="pending",
        )

        response = self.client.get("/api/dashboard/")

        self.assertEqual(response.status_code, 200, response.data)
        data = response.data
        self.assertEqual(data["date_ranges"], {
            "as_of": date(2026, 10, 22), "year_start": date(2026, 1, 1), "year_end": date(2026, 10, 22),
            "trend_start": date(2025, 11, 1), "trend_end": date(2026, 10, 22),
        })
        self.assertEqual(Decimal(str(data["summary"]["sales_ytd"])), Decimal("30"))
        self.assertEqual(data["summary"]["sales_last_ytd"], 0)
        self.assertEqual(data["summary"]["orders_ytd"], 2)
        self.assertEqual(data["top_customers"][0]["orders"], 2)
        self.assertEqual(Decimal(str(data["top_customers"][0]["sales"])), Decimal("30"))
        self.assertEqual(sum((Decimal(str(row["sales"])) for row in data["category_sales"]), Decimal("0")), Decimal("30"))
        self.assertEqual(Decimal(str(data["summary"]["receipts_rmb"])), Decimal("10"))
        self.assertEqual(Decimal(str(data["summary"]["payments_rmb"])), Decimal("3"))
        self.assertNotIn("J1-HISTORICAL", [row["order_no"] for row in data["recent_orders"]])

        self.assertEqual(len(data["monthly_sales"]), 12)
        self.assertEqual([row["month"] for row in data["monthly_sales"]], [
            "2025-11", "2025-12", "2026-01", "2026-02", "2026-03", "2026-04",
            "2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10",
        ])
        month_by_key = {row["month"]: row for row in data["monthly_sales"]}
        self.assertEqual(Decimal(str(month_by_key[trend_start.order_date.strftime("%Y-%m")]["sales"])), Decimal("3"))
        self.assertEqual(Decimal(str(month_by_key[year_start.order_date.strftime("%Y-%m")]["sales"])), Decimal("10"))
        self.assertEqual(Decimal(str(month_by_key[today_order.order_date.strftime("%Y-%m")]["sales"])), Decimal("20"))
        self.assertEqual(month_by_key["2025-12"]["sales"], Decimal("0"))
        self.assertEqual(month_by_key["2025-12"]["orders"], 0)
        self.assertNotIn("2026-11", month_by_key)
        self.assertNotIn("2025-10", month_by_key)

    @patch("crm.views.timezone.localdate", return_value=date(2026, 10, 22))
    def test_dashboard_keeps_empty_trend_empty_when_no_orders_in_window(self, _today):
        response = self.client.get("/api/dashboard/")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["monthly_sales"], [])
        self.assertEqual(response.data["summary"]["orders_ytd"], 0)

    @patch("crm.reporting.timezone.localdate", return_value=date(2026, 10, 22))
    def test_custom_report_can_still_query_a_future_period(self, _today):
        self.create_order("J1-FUTURE-REPORT", "confirmed", "45", date(2026, 11, 1))

        response = self.client.get("/api/reports/data/", {
            "source": "sales", "group_by": "customer", "date_from": "2026-11-01", "date_to": "2026-11-30",
        })

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["period"], {"date_from": date(2026, 11, 1), "date_to": date(2026, 11, 30)})
        self.assertEqual(response.data["totals"]["amount"], Decimal("45"))

    def test_customer_import_ignores_status_and_follow_up_projection(self):
        customer_fields = self.client.get("/api/import/templates/").data["customers"]
        self.assertNotIn("status", customer_fields)
        self.assertNotIn("next_follow_up", customer_fields)
        existing = Customer.objects.create(
            code="J1-EXISTING", name="Existing Buyer", status="company", next_follow_up=date(2026, 11, 1),
        )
        response = self.upload_csv(
            "customers",
            ["code", "name", "status", "next_follow_up", "country"],
            [["J1-NEW", "Imported Lead", "company", "2026-10-01", "China"],
             ["J1-EXISTING", "Existing Buyer Updated", "lead", "2026-10-02", "Japan"]],
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["created"], 1)
        self.assertEqual(response.data["updated"], 1)
        new_customer = Customer.objects.get(code="J1-NEW")
        existing.refresh_from_db()
        self.assertEqual(new_customer.status, "lead")
        self.assertIsNone(new_customer.next_follow_up)
        self.assertEqual(existing.status, "company")
        self.assertEqual(existing.next_follow_up, date(2026, 11, 1))
        self.assertEqual(existing.country, "Japan")

    def test_product_import_requires_an_existing_category(self):
        response = self.upload_csv(
            "products", ["code", "name", "sales_model_prefix", "category"],
            [["J1-MISSING-CAT", "New product", "J1M", "Not established"]],
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["errors"][0]["message"], "产品分类不存在，请先建立分类。")
        self.assertFalse(Product.objects.filter(code="J1-MISSING-CAT").exists())
        self.assertFalse(ProductCategory.objects.filter(name="Not established").exists())

    def test_product_import_creates_with_existing_category_and_serializer_fields(self):
        response = self.upload_csv(
            "products", ["code", "name", "sales_model_prefix", "category", "description"],
            [["J1-NEW-PRODUCT", "New catalog item", "J1N", self.category.name, "catalog import"]],
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["created"], 1)
        imported = Product.objects.get(code="J1-NEW-PRODUCT")
        self.assertEqual(imported.category_id, self.category.pk)
        self.assertEqual(imported.sales_model_prefix, "J1N")

    def test_product_import_rejects_category_change_for_unfrozen_sku_schema(self):
        other_category = ProductCategory.objects.create(name="J1 Other")
        response = self.upload_csv(
            "products", ["code", "name", "category"],
            [[self.product.code, self.product.name, other_category.name]],
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["errors"]), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.category_id, self.category.pk)

    def test_sku_import_obeys_unit_freeze_when_business_records_exist(self):
        self.create_order("J1-SKU-USED", "confirmed", "100")
        response = self.upload_csv(
            "skus", ["sku", "product_code", "specification", "unit", "cost_price", "default_price", "currency"],
            [[self.sku.sku, self.product.code, self.sku.specification, "box", "3", "10", "USD"]],
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["errors"]), 1)
        self.assertIn("已有业务记录的 SKU 不能更换计量单位", response.data["errors"][0]["message"])
        self.sku.refresh_from_db()
        self.assertEqual(self.sku.unit, "pcs")

    def test_sku_import_creates_new_sku_through_serializer_rules(self):
        response = self.upload_csv(
            "skus", ["sku", "product_code", "specification", "unit", "cost_price", "default_price", "currency"],
            [["J1-SKU-NEW", self.product.code, "Cool", "pcs", "3", "10", "USD"]],
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["created"], 1)
        imported = SKU.objects.get(sku="J1-SKU-NEW")
        self.assertEqual(imported.product_id, self.product.pk)
        self.assertEqual(imported.specification, "Cool")
        self.assertTrue(imported.schema_version)

    def test_transaction_import_records_formal_receipt_and_duplicate_does_not_overwrite(self):
        order = self.create_order("J1-RECEIPT-ORDER", "confirmed", "100")
        response = self.upload_csv(
            "transactions",
            ["transaction_no", "transaction_date", "direction", "category", "amount", "currency", "exchange_rate", "customer_code", "order_no", "reference", "notes"],
            [["J1-RECEIPT", timezone.localdate().isoformat(), "income", "客户收款", "25", "USD", "1", self.customer.code, order.order_no, "bank-1", "imported receipt"]],
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["created"], 1)
        receipt = Transaction.objects.get(transaction_no="J1-RECEIPT")
        self.assertEqual(receipt.kind, "customer_receipt")
        self.assertEqual(receipt.order_id, order.pk)
        self.assertEqual(receipt.amount, Decimal("25"))

        duplicate = self.upload_csv(
            "transactions",
            ["transaction_no", "transaction_date", "direction", "category", "amount", "currency", "exchange_rate", "customer_code", "order_no", "reference", "notes"],
            [["J1-RECEIPT", timezone.localdate().isoformat(), "income", "客户收款", "90", "USD", "1", self.customer.code, order.order_no, "changed", "must not overwrite"]],
        )
        receipt.refresh_from_db()
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(len(duplicate.data["errors"]), 1)
        self.assertEqual(receipt.amount, Decimal("25"))
        self.assertEqual(receipt.reference, "bank-1")
        self.assertEqual(receipt.notes, "imported receipt")


class DashboardCurrentFollowUpTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def create_follow_up(self, customer_code, name, followed_day, next_date):
        customer, _ = Customer.objects.get_or_create(code=customer_code, defaults={"name": name})
        return FollowUp.objects.create(
            customer=customer,
            followed_at=datetime(2026, 9, followed_day, 9, 0, tzinfo=datetime_timezone.utc),
            type="call",
            next_follow_up_mode="set" if next_date is not None else "clear",
            next_follow_up=date.fromisoformat(next_date) if next_date is not None else None,
        )

    @patch("crm.views.timezone.localdate", return_value=date(2026, 9, 30))
    def test_dashboard_counts_and_lists_only_each_customers_latest_follow_up(self, _today):
        old_a = self.create_follow_up("J1-DUE-A", "Future follow-up", 1, "2026-09-10")
        latest_a = self.create_follow_up("J1-DUE-A", "Future follow-up", 20, "2026-10-10")
        old_b = self.create_follow_up("J1-DUE-B", "Overdue follow-up", 1, "2026-09-10")
        latest_b = self.create_follow_up("J1-DUE-B", "Overdue follow-up", 20, "2026-09-25")
        old_c = self.create_follow_up("J1-DUE-C", "No next follow-up", 1, "2026-09-10")
        latest_c = self.create_follow_up("J1-DUE-C", "No next follow-up", 20, None)

        self.assertEqual(Customer.objects.get(code="J1-DUE-A").next_follow_up, date(2026, 10, 10))
        self.assertEqual(Customer.objects.get(code="J1-DUE-B").next_follow_up, date(2026, 9, 25))
        self.assertIsNone(Customer.objects.get(code="J1-DUE-C").next_follow_up)

        response = self.client.get("/api/dashboard/")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["summary"]["follow_ups_due"], 1)
        self.assertEqual([row["id"] for row in response.data["due_follow_ups"]], [latest_b.id])
        self.assertNotIn(old_a.id, [row["id"] for row in response.data["due_follow_ups"]])
        self.assertNotIn(latest_a.id, [row["id"] for row in response.data["due_follow_ups"]])
        self.assertNotIn(old_b.id, [row["id"] for row in response.data["due_follow_ups"]])
        self.assertNotIn(old_c.id, [row["id"] for row in response.data["due_follow_ups"]])
        self.assertNotIn(latest_c.id, [row["id"] for row in response.data["due_follow_ups"]])

    @patch("crm.views.timezone.localdate", return_value=date(2026, 9, 30))
    def test_deleting_latest_follow_up_restores_previous_overdue_dashboard_item(self, _today):
        previous = self.create_follow_up("J1-DUE-DELETE", "Restored follow-up", 1, "2026-09-10")
        latest = self.create_follow_up("J1-DUE-DELETE", "Restored follow-up", 20, "2026-09-25")
        latest.delete()

        customer = Customer.objects.get(code="J1-DUE-DELETE")
        self.assertEqual(customer.next_follow_up, date(2026, 9, 10))

        response = self.client.get("/api/dashboard/")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["summary"]["follow_ups_due"], 1)
        self.assertEqual([row["id"] for row in response.data["due_follow_ups"]], [previous.id])
