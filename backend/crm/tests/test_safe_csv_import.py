import csv
import hashlib
import io
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from crm.models import CSVImportBatch, CSVImportRowAudit, Customer, OperationLog, Product, SKU, Transaction
from crm.views import _import_row, _read_import_csv


@override_settings(AUDIT_LOG_ENABLED=True)
class SafeCsvImportTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.operator = get_user_model().objects.create_superuser(
            username="csv-audit-operator",
            email="csv-audit@example.com",
            password="secret",
        )
        self.client.force_authenticate(self.operator)

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
        batch = CSVImportBatch.objects.get(batch_id=response.data["import_batch_id"])
        self.assertEqual(batch.status, "failed")
        self.assertEqual(batch.entity, entity)
        self.assertEqual(batch.rows.count(), batch.total_rows)
        self.assertTrue(batch.rows.filter(result="failed").exists())

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

    def test_missing_sku_product_returns_stable_api_message(self):
        response, _ = self.preview(
            "skus",
            ["sku", "product_code", "specification", "unit", "cost_price", "default_price", "currency"],
            [["BAD-SKU", "MISSING-PRODUCT", "Spec", "pcs", "1", "2", "USD"]],
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["errors"][0]["message"], "找不到所引用的产品，请核对 product_code。")
        self.assertFalse(SKU.objects.filter(sku="BAD-SKU").exists())

    def test_execute_is_atomic_and_rejects_changed_file(self):
        headers = ["code", "name"]
        response, content = self.preview("customers", headers, [[f"CSV-{index}", f"Buyer {index}"] for index in range(5)])
        changed = self.content(headers, [["CSV-other", "Other"]])
        rejected = self.execute("customers", changed, response.data["preview_token"])
        self.assertEqual(rejected.status_code, 400)
        self.assertEqual(Customer.objects.count(), 0)

        calls = {"count": 0}
        def fail_on_sixth(entity, row, user=None):
            calls["count"] += 1
            if calls["count"] == 6:  # validation consumes five calls before the real write path
                raise RuntimeError("unexpected write failure")
            return _import_row(entity, row, user=user)

        with patch("crm.views._import_row", side_effect=fail_on_sixth):
            failed = self.execute("customers", content, response.data["preview_token"])
        self.assertEqual(failed.status_code, 400)
        self.assertEqual(Customer.objects.count(), 0)
        batch = CSVImportBatch.objects.get(batch_id=failed.data["import_batch_id"])
        self.assertEqual(batch.status, "failed")
        self.assertEqual(batch.operator_id, self.operator.pk)
        self.assertEqual(batch.rows.count(), 5)
        self.assertTrue(batch.rows.filter(result="failed", error_message__contains="unexpected write failure").exists())

    def test_success_records_batch_row_before_after_hash_and_operation_link(self):
        customer = Customer.objects.create(code="AUDIT-C", name="Before")
        headers = ["code", "name"]
        content = self.content(headers, [["AUDIT-C", "After"]])
        preview, _ = self.preview("customers", headers, [["AUDIT-C", "After"]])
        response = self.execute("customers", content, preview.data["preview_token"])
        self.assertEqual(response.status_code, 200, response.data)

        batch = CSVImportBatch.objects.get(batch_id=response.data["import_batch_id"])
        self.assertEqual(batch.status, "succeeded")
        self.assertEqual(batch.entity, "customers")
        self.assertEqual(batch.file_sha256, hashlib.sha256(content).hexdigest())
        self.assertEqual(batch.operator_id, self.operator.pk)
        row = batch.rows.get(row_number=2)
        self.assertEqual((row.business_key, row.result, row.object_id), ("AUDIT-C", "updated", str(customer.pk)))
        self.assertEqual(row.before_data["name"], "Before")
        self.assertEqual(row.after_data["name"], "After")
        operation = OperationLog.objects.get(
            entity="crm.customer", object_id=str(customer.pk), action_label="CSV 导入更新",
        )
        self.assertEqual(operation.operator_id, self.operator.pk)
        self.assertEqual(operation.metadata["csv_import_batch_id"], str(batch.batch_id))
        self.assertEqual(operation.metadata["csv_import_row_audit_id"], row.pk)
        batch_history = self.client.get("/api/operation-logs/?entity=crm.csvimportbatch")
        self.assertEqual(batch_history.status_code, 200, batch_history.data)
        self.assertEqual(batch_history.data["results"][0]["object_id"], str(batch.pk))

    def test_unauthenticated_formal_import_is_rejected_without_fake_operator(self):
        headers = ["code", "name"]
        content = self.content(headers, [["AUTH-C", "No operator"]])
        preview, _ = self.preview("customers", headers, [["AUTH-C", "No operator"]])
        anonymous = APIClient()
        response = anonymous.post("/api/import/csv/execute/", {
            "entity": "customers", "preview_token": preview.data["preview_token"],
            "file": SimpleUploadedFile("test.csv", content, content_type="text/csv"),
        }, format="multipart")
        self.assertEqual(response.status_code, 403, response.data)
        self.assertIn("不能作为审计操作人", response.data["detail"])
        self.assertFalse(CSVImportBatch.objects.exists())
        self.assertFalse(Customer.objects.exists())

    def test_products_skus_and_transactions_have_the_same_audit_contract(self):
        product_content = self.content(["code", "name", "sales_model_prefix"], [["AUDIT-P", "Imported product", "AP"]])
        product_preview, _ = self.preview("products", ["code", "name", "sales_model_prefix"], [["AUDIT-P", "Imported product", "AP"]])
        product_response = self.execute("products", product_content, product_preview.data["preview_token"])
        self.assertEqual(product_response.status_code, 200, product_response.data)

        sku_content = self.content(
            ["sku", "product_code", "specification", "unit", "default_price", "currency"],
            [["AUDIT-S", "AUDIT-P", "Spec", "pcs", "1.25", "USD"]],
        )
        sku_preview, _ = self.preview(
            "skus", ["sku", "product_code", "specification", "unit", "default_price", "currency"],
            [["AUDIT-S", "AUDIT-P", "Spec", "pcs", "1.25", "USD"]],
        )
        sku_response = self.execute("skus", sku_content, sku_preview.data["preview_token"])
        self.assertEqual(sku_response.status_code, 200, sku_response.data)

        transaction_content = self.content(
            ["transaction_no", "transaction_date", "direction", "category", "amount", "currency"],
            [["AUDIT-T", "2026-01-01", "income", "其他收入", "2.50", "CNY"]],
        )
        transaction_preview, _ = self.preview(
            "transactions", ["transaction_no", "transaction_date", "direction", "category", "amount", "currency"],
            [["AUDIT-T", "2026-01-01", "income", "其他收入", "2.50", "CNY"]],
        )
        transaction_response = self.execute("transactions", transaction_content, transaction_preview.data["preview_token"])
        self.assertEqual(transaction_response.status_code, 200, transaction_response.data)

        self.assertEqual(CSVImportBatch.objects.filter(status="succeeded").count(), 3)
        self.assertEqual(CSVImportRowAudit.objects.filter(result="created").count(), 3)
        self.assertEqual(OperationLog.objects.filter(action_label="CSV 导入创建").count(), 3)

    def test_csv_audit_rows_are_append_only(self):
        content = self.content(["code", "name"], [["APPEND-C", "Append only"]])
        preview, _ = self.preview("customers", ["code", "name"], [["APPEND-C", "Append only"]])
        response = self.execute("customers", content, preview.data["preview_token"])
        batch = CSVImportBatch.objects.get(batch_id=response.data["import_batch_id"])
        row = batch.rows.get()
        with self.assertRaises(ValidationError):
            CSVImportBatch.objects.filter(pk=batch.pk).update(failure_reason="tampered")
        with self.assertRaises(ValidationError):
            CSVImportRowAudit.objects.filter(pk=row.pk).delete()
        batch.refresh_from_db()
        self.assertEqual(batch.status, "succeeded")
        self.assertTrue(batch.rows.filter(pk=row.pk).exists())

    @override_settings(AUDIT_LOG_ENABLED=False)
    def test_audit_disabled_fails_closed_without_business_write(self):
        content = self.content(["code", "name"], [["NO-AUDIT", "Blocked"]])
        preview, _ = self.preview("customers", ["code", "name"], [["NO-AUDIT", "Blocked"]])
        response = self.execute("customers", content, preview.data["preview_token"])
        self.assertEqual(response.status_code, 503, response.data)
        self.assertIn("审计记录未启用", response.data["detail"])
        self.assertFalse(CSVImportBatch.objects.exists())
        self.assertFalse(Customer.objects.exists())

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

    def test_csv_size_limit_accepts_exact_boundary_and_reads_overflow_bounded(self):
        limit = 32
        exact_content = b"code,name\nC," + b"x" * 19 + b"\n"
        self.assertEqual(len(exact_content), limit)
        with override_settings(CSV_IMPORT_MAX_BYTES=limit):
            rows, digest = _read_import_csv("customers", SimpleUploadedFile("exact.csv", exact_content))
        self.assertEqual(len(rows), 1)
        self.assertEqual(digest, hashlib.sha256(exact_content).hexdigest())

        class ReadProbe:
            def __init__(self, content, reported_size):
                self.content = io.BytesIO(content)
                self.size = reported_size
                self.read_sizes = []

            def read(self, size=-1):
                self.read_sizes.append(size)
                return self.content.read(size)

        over_limit_content = exact_content + b"z" * (1024 * 1024)
        spoofed_size = ReadProbe(over_limit_content, reported_size=0)
        with override_settings(CSV_IMPORT_MAX_BYTES=limit):
            with self.assertRaisesRegex(ValueError, "超过大小限制") as captured:
                _read_import_csv("customers", spoofed_size)
        self.assertIsNone(captured.exception.digest)
        self.assertEqual(spoofed_size.read_sizes, [limit + 1])
        self.assertEqual(spoofed_size.content.tell(), limit + 1)

        declared_over_limit = ReadProbe(exact_content + b"!", reported_size=limit + 1)
        with override_settings(CSV_IMPORT_MAX_BYTES=limit):
            with self.assertRaisesRegex(ValueError, "超过大小限制") as captured:
                _read_import_csv("customers", declared_over_limit)
        self.assertIsNone(captured.exception.digest)
        self.assertEqual(declared_over_limit.read_sizes, [])

    def test_execute_parse_failures_create_batch_only_audits_with_exact_hashes(self):
        failures = [
            (b"", "CSV 文件为空。"),
            (b"\xff\xfe", "CSV 文件无法读取，请使用 UTF-8 或 UTF-8 BOM 编码。"),
            (b"\n", "CSV 缺少表头。"),
            (b"name\nBuyer\n", "CSV 缺少必要字段：code。"),
            (b"code,name\n", "CSV 没有数据行。"),
            (b"code,name\nC\n", "CSV 数据行的字段数与表头不一致。"),
            (b"code,name\nC,Buyer,extra\n", "CSV 数据行的字段数与表头不一致。"),
        ]
        for content, message in failures:
            with self.subTest(message=message):
                response = self.execute("customers", content, "no-preview-token")
                self.assertEqual(response.status_code, 400, response.data)
                self.assertEqual(response.data["detail"], message)
                batch = CSVImportBatch.objects.get(batch_id=response.data["import_batch_id"])
                self.assertEqual(batch.operator_id, self.operator.pk)
                self.assertEqual(batch.status, "failed")
                self.assertEqual(batch.failure_reason, message)
                self.assertEqual(batch.file_sha256, hashlib.sha256(content).hexdigest())
                self.assertEqual((batch.total_rows, batch.failed_rows), (0, 0))
                self.assertFalse(batch.rows.exists())
                self.assertFalse(Customer.objects.exists())
                self.assertFalse(OperationLog.objects.filter(entity="crm.customer").exists())

        self.assertEqual(CSVImportBatch.objects.filter(status="failed").count(), len(failures))
        self.assertEqual(OperationLog.objects.filter(entity="crm.csvimportbatch", action_label="CSV 导入失败").count(), len(failures))

    @override_settings(CSV_IMPORT_MAX_BYTES=32)
    def test_execute_oversized_file_records_batch_without_partial_hash_or_rows(self):
        content = b"code,name\nC," + b"x" * 20 + b"\n"
        self.assertGreater(len(content), 32)
        response = self.execute("customers", content, "no-preview-token")
        self.assertEqual(response.status_code, 413, response.data)
        self.assertIn("CSV 文件超过大小限制", response.data["detail"])
        batch = CSVImportBatch.objects.get(batch_id=response.data["import_batch_id"])
        self.assertEqual(batch.status, "failed")
        self.assertEqual(batch.file_sha256, "")
        self.assertEqual((batch.total_rows, batch.failed_rows), (0, 0))
        self.assertFalse(batch.rows.exists())
        self.assertFalse(Customer.objects.exists())
        self.assertFalse(OperationLog.objects.filter(entity="crm.customer").exists())

    def test_upload_stream_limit_stops_all_csv_import_routes_before_file_completion(self):
        content = b"code,name\nC," + b"x" * (1024 * 1024)
        endpoints = (
            "/api/import/csv/preview/",
            "/api/import/csv/execute/",
            "/api/import/csv/",
        )
        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                previous_batch_count = CSVImportBatch.objects.count()
                with self.settings(CSV_IMPORT_MAX_BYTES=64, FILE_UPLOAD_MAX_MEMORY_SIZE=128):
                    with patch("crm.views._read_import_csv") as read_csv:
                        response = self.client.post(
                            endpoint,
                            {
                                "entity": "customers",
                                "preview_token": "not-used-for-oversize-upload",
                                "file": SimpleUploadedFile("oversized.csv", content),
                            },
                            format="multipart",
                        )
                self.assertEqual(response.status_code, 413, response.data)
                self.assertIn("CSV 文件超过大小限制", response.data["detail"])
                read_csv.assert_not_called()
                stream_state = response.wsgi_request._csv_import_upload_limit_exceeded
                self.assertLess(stream_state["bytes_seen"], len(content))
                self.assertLessEqual(stream_state["bytes_forwarded"], 64)
                self.assertFalse(response.wsgi_request.upload_handlers[1].activated)
                self.assertFalse(response.wsgi_request.FILES)
                self.assertFalse(Customer.objects.exists())

                if endpoint == "/api/import/csv/execute/":
                    self.assertEqual(CSVImportBatch.objects.count(), previous_batch_count + 1)
                    batch = CSVImportBatch.objects.latest("created_at")
                    self.assertEqual(batch.status, "failed")
                    self.assertEqual(batch.file_sha256, "")
                    self.assertEqual((batch.total_rows, batch.failed_rows), (0, 0))
                    self.assertFalse(batch.rows.exists())
                    self.assertEqual(
                        OperationLog.objects.filter(
                            entity="crm.csvimportbatch", action_label="CSV 导入失败"
                        ).count(),
                        1,
                    )
                else:
                    self.assertEqual(CSVImportBatch.objects.count(), previous_batch_count)

        batches_before_gate_checks = CSVImportBatch.objects.count()
        with self.settings(CSV_IMPORT_MAX_BYTES=64, FILE_UPLOAD_MAX_MEMORY_SIZE=128):
            anonymous = APIClient().post(
                "/api/import/csv/execute/",
                {
                    "entity": "customers",
                    "preview_token": "not-used-for-oversize-upload",
                    "file": SimpleUploadedFile("oversized.csv", content),
                },
                format="multipart",
            )
            self.assertEqual(anonymous.status_code, 403, anonymous.data)
            self.assertFalse(hasattr(anonymous.wsgi_request, "_csv_import_upload_limit_exceeded"))
            with self.settings(AUDIT_LOG_ENABLED=False):
                audit_disabled = self.client.post(
                    "/api/import/csv/execute/",
                    {
                        "entity": "customers",
                        "preview_token": "not-used-for-oversize-upload",
                        "file": SimpleUploadedFile("oversized.csv", content),
                    },
                    format="multipart",
                )
            self.assertEqual(audit_disabled.status_code, 503, audit_disabled.data)
            self.assertFalse(hasattr(audit_disabled.wsgi_request, "_csv_import_upload_limit_exceeded"))
        self.assertEqual(CSVImportBatch.objects.count(), batches_before_gate_checks)

    def test_oversized_csv_never_reaches_builtin_memory_or_temporary_handlers(self):
        content = b"code,name\nISS052-OVER," + b"x" * (128 * 1024) + b"\n"
        endpoints = (
            "/api/import/csv/preview/",
            "/api/import/csv/execute/",
            "/api/import/csv/",
        )
        with tempfile.TemporaryDirectory() as upload_temp_dir:
            for endpoint in endpoints:
                with self.subTest(endpoint=endpoint):
                    previous_batch_count = CSVImportBatch.objects.count()
                    with self.settings(
                        CSV_IMPORT_MAX_BYTES=64 * 1024,
                        FILE_UPLOAD_MAX_MEMORY_SIZE=128,
                        FILE_UPLOAD_TEMP_DIR=upload_temp_dir,
                    ), patch("crm.views._read_import_csv") as read_csv:
                        response = self.client.post(
                            endpoint,
                            {
                                "entity": "customers",
                                "preview_token": "oversized-probe",
                                "file": SimpleUploadedFile("oversized.csv", content),
                            },
                            format="multipart",
                        )

                    self.assertEqual(response.status_code, 413, response.data)
                    self.assertIn("CSV 文件超过大小限制", response.data["detail"])
                    read_csv.assert_not_called()
                    stream_state = response.wsgi_request._csv_import_upload_limit_exceeded
                    self.assertGreater(stream_state["bytes_seen"], stream_state["limit"])
                    self.assertLess(stream_state["bytes_seen"], len(content))
                    self.assertEqual(stream_state["bytes_forwarded"], 0)
                    self.assertFalse(response.wsgi_request.upload_handlers[1].activated)
                    self.assertFalse(response.wsgi_request.FILES)
                    self.assertFalse(getattr(response.wsgi_request.upload_handlers[2], "file", None))
                    self.assertEqual(list(Path(upload_temp_dir).iterdir()), [])
                    self.assertFalse(Customer.objects.exists())

                    if endpoint == "/api/import/csv/execute/":
                        self.assertEqual(CSVImportBatch.objects.count(), previous_batch_count + 1)
                        batch = CSVImportBatch.objects.latest("created_at")
                        self.assertEqual((batch.file_sha256, batch.total_rows, batch.failed_rows), ("", 0, 0))
                        self.assertFalse(batch.rows.exists())
                    else:
                        self.assertEqual(CSVImportBatch.objects.count(), previous_batch_count)

    def test_normal_csv_above_memory_threshold_still_previews_without_temp_file(self):
        rows = [[f"SIZE-{index:03d}", f"Buyer {index:03d} " + "x" * 180] for index in range(25)]
        content = self.content(["code", "name"], rows)
        self.assertGreater(len(content), 128)
        self.assertLess(len(content), 256 * 1024)

        with tempfile.TemporaryDirectory() as upload_temp_dir:
            with self.settings(
                CSV_IMPORT_MAX_BYTES=256 * 1024,
                FILE_UPLOAD_MAX_MEMORY_SIZE=128,
                FILE_UPLOAD_TEMP_DIR=upload_temp_dir,
            ):
                response = self.client.post(
                    "/api/import/csv/preview/",
                    {"entity": "customers", "file": SimpleUploadedFile("normal.csv", content)},
                    format="multipart",
                )

            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data["created"], len(rows))
            self.assertEqual(response.data["errors"], [])
            self.assertFalse(Customer.objects.exists())
            self.assertEqual(list(Path(upload_temp_dir).iterdir()), [])

    def test_preview_parse_failure_stays_outside_formal_batch_audit(self):
        response = self.client.post(
            "/api/import/csv/preview/",
            {"entity": "customers", "file": SimpleUploadedFile("bad.csv", b"\xff")},
            format="multipart",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("UTF-8", response.data["detail"])
        self.assertFalse(CSVImportBatch.objects.exists())
        self.assertFalse(Customer.objects.exists())

    def test_malformed_execute_still_obeys_authentication_and_audit_gate(self):
        content = b"\xff"
        anonymous = APIClient()
        unauthenticated = anonymous.post(
            "/api/import/csv/execute/",
            {"entity": "customers", "preview_token": "", "file": SimpleUploadedFile("bad.csv", content)},
            format="multipart",
        )
        self.assertEqual(unauthenticated.status_code, 403, unauthenticated.data)
        self.assertFalse(CSVImportBatch.objects.exists())

        with self.settings(AUDIT_LOG_ENABLED=False):
            disabled = self.execute("customers", content, "")
        self.assertEqual(disabled.status_code, 503, disabled.data)
        self.assertIn("审计记录未启用", disabled.data["detail"])
        self.assertFalse(CSVImportBatch.objects.exists())
        self.assertFalse(Customer.objects.exists())

    def test_orders_and_legacy_endpoint_remain_safe(self):
        orders = self.client.post("/api/import/csv/", {"entity": "orders"}, format="multipart")
        self.assertEqual(orders.status_code, 400)
        self.assertIn("正式订单导入暂未开放", orders.data["detail"])
        legacy = self.client.post("/api/import/csv/", {"entity": "customers", "file": SimpleUploadedFile("test.csv", b"code,name\nCSV-1,Buyer\n")}, format="multipart")
        self.assertEqual(legacy.status_code, 200)
        self.assertTrue(legacy.data["preview_token"])
        self.assertFalse(Customer.objects.exists())
