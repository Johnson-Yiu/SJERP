import csv
import io
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from crm.models import Customer, Product, SKU, Transaction
from crm.views import _import_row


class SafeCsvImportTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def content(self, headers, rows):
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(headers)
        writer.writerows(rows)
        return output.getvalue().encode("utf-8")

    def preview(self, entity, headers, rows):
        content = self.content(headers, rows)
        response = self.client.post("/api/import/csv/preview/", {
            "entity": entity, "file": SimpleUploadedFile("test.csv", content, content_type="text/csv"),
        }, format="multipart")
        return response, content

    def execute(self, entity, content, token):
        return self.client.post("/api/import/csv/execute/", {
            "entity": entity, "preview_token": token,
            "file": SimpleUploadedFile("test.csv", content, content_type="text/csv"),
        }, format="multipart")

    def assert_state_rejected(self, entity, content, token):
        response = self.execute(entity, content, token)
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(response.data["detail"], "数据状态已发生变化，请重新预览后再导入。")

    def test_customer_create_becomes_existing_rejects_without_overwriting(self):
        preview, content = self.preview("customers", ["code", "name"], [["STATE-C", "Imported"]])
        customer = Customer.objects.create(code="STATE-C", name="Other operation")
        self.assert_state_rejected("customers", content, preview.data["preview_token"])
        customer.refresh_from_db()
        self.assertEqual(customer.name, "Other operation")

    def test_customer_update_changed_since_preview_rejects_all_rows(self):
        customer = Customer.objects.create(code="STATE-C", name="Original")
        preview, content = self.preview("customers", ["code", "name"], [["NEW-C", "New"], ["STATE-C", "Imported"]])
        customer.name = "Other operation"
        customer.save()
        self.assert_state_rejected("customers", content, preview.data["preview_token"])
        customer.refresh_from_db()
        self.assertEqual(customer.name, "Other operation")
        self.assertFalse(Customer.objects.filter(code="NEW-C").exists())

    def test_product_update_changed_since_preview_rejects(self):
        product = Product.objects.create(code="STATE-P", name="Original", sales_model_prefix="STATE")
        preview, content = self.preview("products", ["code", "name"], [["STATE-P", "Imported"]])
        self.assertFalse(preview.data["errors"], preview.data)
        product.name = "Other operation"
        product.save()
        self.assert_state_rejected("products", content, preview.data["preview_token"])
        product.refresh_from_db()
        self.assertEqual(product.name, "Other operation")

    def test_sku_bulk_update_without_timestamp_change_rejects(self):
        product = Product.objects.create(code="STATE-P", name="Product", sales_model_prefix="STATE")
        sku = SKU.objects.create(sku="STATE-S", product=product, specification="Original")
        preview, content = self.preview("skus", ["sku", "product_code", "specification"], [["STATE-S", "STATE-P", "Original"]])
        self.assertFalse(preview.data["errors"], preview.data)
        SKU.objects.filter(pk=sku.pk).update(specification="Other operation")
        self.assert_state_rejected("skus", content, preview.data["preview_token"])
        sku.refresh_from_db()
        self.assertEqual(sku.specification, "Other operation")

    def test_transaction_created_since_preview_rejects(self):
        preview, content = self.preview("transactions", ["transaction_no", "transaction_date", "direction", "category", "amount", "currency"], [["STATE-T", "2026-01-01", "income", "其他收入", "2", "CNY"]])
        self.assertFalse(preview.data["errors"], preview.data)
        existing = Transaction.objects.create(transaction_no="STATE-T", transaction_date="2026-01-01", direction="income", category="其他收入", amount=1, currency="CNY", exchange_rate=1)
        self.assert_state_rejected("transactions", content, preview.data["preview_token"])
        existing.refresh_from_db()
        self.assertEqual(existing.amount, 1)
        self.assertEqual(Transaction.objects.count(), 1)

    def test_unchanged_update_executes_successfully(self):
        customer = Customer.objects.create(code="STATE-C", name="Original")
        preview, content = self.preview("customers", ["code", "name"], [["STATE-C", "Imported"]])
        response = self.execute("customers", content, preview.data["preview_token"])
        self.assertEqual(response.status_code, 200, response.data)
        customer.refresh_from_db()
        self.assertEqual(customer.name, "Imported")

    def test_valid_preview_returns_counts_and_writes_nothing(self):
        response, _ = self.preview("customers", ["code", "name"], [[f"CSV-{index}", f"Buyer {index}"] for index in range(10)])
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual((response.data["total"], response.data["created"], response.data["updated"]), (10, 10, 0))
        self.assertFalse(response.data["errors"])
        self.assertTrue(response.data["preview_token"])
        self.assertEqual(Customer.objects.count(), 0)

    def test_invalid_row_and_duplicate_key_leave_database_unchanged(self):
        response, _ = self.preview("customers", ["code", "name"], [
            ["CSV-1", "Buyer 1"], ["CSV-2", "Buyer 2"], ["CSV-3", "Buyer 3"], ["CSV-4", "Buyer 4"], ["CSV-5", ""], ["CSV-2", "Duplicate"],
        ])
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["row"] for item in response.data["errors"]], [6, 7])
        self.assertEqual(Customer.objects.count(), 0)

    def test_execute_is_atomic_and_rejects_changed_file(self):
        headers = ["code", "name"]
        response, content = self.preview("customers", headers, [[f"CSV-{index}", f"Buyer {index}"] for index in range(5)])
        changed = self.content(headers, [["CSV-other", "Other"]])
        rejected = self.execute("customers", changed, response.data["preview_token"])
        self.assertEqual(rejected.status_code, 400)
        self.assertEqual(Customer.objects.count(), 0)

        calls = {"count": 0}
        def fail_on_tenth(entity, row):
            calls["count"] += 1
            if calls["count"] == 10:  # preview + validation consume 9 calls before execute row 5
                raise RuntimeError("unexpected write failure")
            return _import_row(entity, row)

        with patch("crm.views._import_row", side_effect=fail_on_tenth):
            failed = self.execute("customers", content, response.data["preview_token"])
        self.assertEqual(failed.status_code, 400)
        self.assertEqual(Customer.objects.count(), 0)

    def test_execute_success_and_token_errors(self):
        response, content = self.preview("customers", ["code", "name"], [["CSV-1", "Buyer 1"]])
        self.assertEqual(self.execute("customers", content, "bad-token").status_code, 400)
        with patch("crm.views.signing.loads", side_effect=__import__("django.core.signing", fromlist=["SignatureExpired"]).SignatureExpired("expired")):
            self.assertEqual(self.execute("customers", content, response.data["preview_token"]).status_code, 400)
        success = self.execute("customers", content, response.data["preview_token"])
        self.assertEqual(success.status_code, 200, success.data)
        self.assertTrue(Customer.objects.filter(code="CSV-1").exists())
        # The original create token must not become an update on replay.
        replay = self.execute("customers", content, response.data["preview_token"])
        self.assertEqual(replay.status_code, 400, replay.data)
        self.assertEqual(Customer.objects.count(), 1)
        self.assertEqual(Customer.objects.get(code="CSV-1").name, "Buyer 1")

    def test_file_guards_and_duplicate_transaction(self):
        for content, message in ((b"", "CSV 文件为空。"), (b"code,name\n", "CSV 没有数据行。"), (b"name\nBuyer\n", "CSV 缺少必要字段：code。")):
            response = self.client.post("/api/import/csv/preview/", {"entity": "customers", "file": SimpleUploadedFile("test.csv", content)}, format="multipart")
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.data["detail"], message)
        over_limit = self.content(["code", "name"], [[str(index), "Buyer"] for index in range(5001)])
        response = self.client.post("/api/import/csv/preview/", {"entity": "customers", "file": SimpleUploadedFile("large.csv", over_limit)}, format="multipart")
        self.assertEqual(response.status_code, 400)
        self.assertIn("5000", response.data["detail"])

        Transaction.objects.create(transaction_no="CSV-TXN", transaction_date="2026-01-01", direction="income", category="其他收入", amount=1, currency="CNY", exchange_rate=1)
        response, _ = self.preview("transactions", ["transaction_no", "transaction_date", "direction", "category", "amount"], [["CSV-TXN", "2026-01-02", "income", "其他收入", "1"]])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["errors"][0]["row"], 2)
        self.assertEqual(Transaction.objects.count(), 1)

    def test_orders_and_legacy_endpoint_remain_safe(self):
        orders = self.client.post("/api/import/csv/", {"entity": "orders"}, format="multipart")
        self.assertEqual(orders.status_code, 400)
        self.assertIn("正式订单导入暂未开放", orders.data["detail"])
        legacy = self.client.post("/api/import/csv/", {"entity": "customers", "file": SimpleUploadedFile("test.csv", b"code,name\nCSV-1,Buyer\n")}, format="multipart")
        self.assertEqual(legacy.status_code, 200)
        self.assertTrue(legacy.data["preview_token"])
        self.assertFalse(Customer.objects.exists())
