from datetime import date
from decimal import Decimal
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections, connection, connections
from django.test import TestCase, TransactionTestCase, override_settings
from openpyxl import Workbook, load_workbook
from rest_framework.test import APIClient

from crm.models import (
    AccessRole,
    Customer,
    EmployeeProfile,
    InventoryMovement,
    InventoryReservation,
    Order,
    OrganizationUnit,
    PaymentPlan,
    Position,
    Product,
    RolePermission,
    SalesOrderImportBatch,
    SalesOrderImportSourceOrder,
    SKU,
    SKUTradeUnit,
)


HEADERS = ["来源订单编号", "客户编号", "订单日期", "币种", "SKU", "交易单位", "数量", "单价", "对人民币汇率"]
RBAC_SETTINGS = {
    "APP_STAGE": "staging",
    "DEBUG": False,
    "DEVELOPMENT_SUPERADMIN": False,
    "RBAC_ENFORCEMENT": True,
    "AUDIT_LOG_ENABLED": True,
}


def workbook_bytes(rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "订单明细"
    sheet.append(HEADERS)
    for row in rows:
        sheet.append(row)
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def upload(data):
    return SimpleUploadedFile(
        "sales-orders.xlsx",
        data,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


class SalesOrderImportApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.day = date(2026, 11, 5)
        self.customer = Customer.objects.create(code="IMP-C001", name="Import Buyer")
        self.product = Product.objects.create(code="IMP-P001", name="Import Lamp")
        self.sku = SKU.objects.create(product=self.product, sku="IMP-SKU-001", unit="pcs", cost_price="4.25")
        self.second_sku = SKU.objects.create(product=self.product, sku="IMP-SKU-002", unit="pcs", cost_price="2")
        self.box = SKUTradeUnit.objects.create(
            sku=self.sku, name="10 件/箱", unit="箱", factor="10", allow_fraction=False, is_default=True,
        )

    def rows(self, *, first_price="25", source="EXT-1001"):
        return [
            [source, self.customer.code, self.day, "USD", self.sku.sku, "箱", 2, first_price, None],
            [source, self.customer.code, self.day, "USD", self.second_sku.sku, "pcs", 3, "2.50", None],
            ["EXT-1002", self.customer.code, self.day, "CNY", self.second_sku.sku, "pcs", 1, "12", "1"],
        ]

    def preview(self, data):
        return self.client.post("/api/import/orders/preview/", {"file": upload(data)}, format="multipart")

    def execute(self, data, token):
        return self.client.post(
            "/api/import/orders/execute/",
            {"file": upload(data), "preview_token": token},
            format="multipart",
        )

    def test_template_is_a_real_xlsx_with_required_columns(self):
        response = self.client.get("/api/import/orders/template/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("sales-order-import-template.xlsx", response["Content-Disposition"])
        workbook = load_workbook(BytesIO(response.content), read_only=True)
        self.assertIn("订单明细", workbook.sheetnames)
        self.assertEqual(next(workbook["订单明细"].iter_rows(values_only=True)), tuple(HEADERS))
        workbook.close()

    def test_preview_and_execute_create_multiple_drafts_with_multiple_lines(self):
        source = workbook_bytes(self.rows())
        preview = self.preview(source)
        self.assertEqual(preview.status_code, 200, preview.data)
        self.assertEqual((preview.data["total_rows"], preview.data["total_orders"], preview.data["valid_orders"]), (3, 2, 2))
        self.assertFalse(preview.data["business_write_performed"])
        self.assertFalse(Order.objects.exists())
        self.assertFalse(SalesOrderImportBatch.objects.exists())
        self.assertFalse(SalesOrderImportSourceOrder.objects.exists())

        imported = self.execute(source, preview.data["preview_token"])
        self.assertEqual(imported.status_code, 200, imported.data)
        self.assertEqual((imported.data["created_orders"], imported.data["failed_orders"]), (2, 0))
        persisted_result = self.client.get(f"/api/import/orders/results/{imported.data['batch_id']}/")
        self.assertEqual(persisted_result.status_code, 200, persisted_result.data)
        self.assertEqual(persisted_result.data, imported.data)
        first = Order.objects.get(sales_import_source__source_order_no="EXT-1001")
        second = Order.objects.get(sales_import_source__source_order_no="EXT-1002")
        self.assertEqual(first.status, "draft")
        self.assertEqual(first.items.count(), 2)
        box_line = first.items.get(sku=self.sku)
        self.assertEqual(box_line.trade_unit_id, self.box.pk)
        self.assertEqual(box_line.trade_quantity, Decimal("2"))
        self.assertEqual(box_line.quantity, Decimal("20"))
        self.assertEqual(first.total_amount, Decimal("57.50"))
        self.assertEqual(second.currency, "CNY")
        self.assertEqual(second.exchange_rate, Decimal("1"))
        self.assertFalse(PaymentPlan.objects.filter(order__in=[first, second]).exists())
        self.assertFalse(InventoryReservation.objects.filter(order_item__order__in=[first, second]).exists())

    def test_repeated_upload_click_and_changed_content_never_duplicate_or_overwrite(self):
        source = workbook_bytes(self.rows())
        preview = self.preview(source)
        first_response = self.execute(source, preview.data["preview_token"])
        self.assertEqual(first_response.status_code, 200, first_response.data)
        repeated_click = self.execute(source, preview.data["preview_token"])
        self.assertEqual(repeated_click.status_code, 200, repeated_click.data)
        self.assertEqual(repeated_click.data, first_response.data)
        self.assertEqual(Order.objects.count(), 2)
        self.assertEqual(SalesOrderImportBatch.objects.count(), 1)

        duplicate_upload = self.preview(source)
        self.assertEqual(duplicate_upload.data["valid_orders"], 0)
        self.assertTrue(any("已导入" in item["message"] for item in duplicate_upload.data["errors"]))
        changed = self.preview(workbook_bytes(self.rows(first_price="99.50")))
        self.assertEqual(changed.data["valid_orders"], 0)
        self.assertTrue(any("已导入" in item["message"] for item in changed.data["errors"]))
        first = Order.objects.get(sales_import_source__source_order_no="EXT-1001")
        self.assertEqual(first.total_amount, Decimal("57.50"))
        self.assertEqual(first.items.get(sku=self.sku).trade_unit_price, Decimal("25"))
        self.assertEqual(self.client.delete(f"/api/orders/{first.pk}/").status_code, 400)

    def test_bad_line_rejects_its_whole_order_but_keeps_other_valid_order(self):
        rows = [
            ["EXT-BAD", self.customer.code, self.day, "USD", self.sku.sku, "箱", 1, "10", None],
            ["EXT-BAD", self.customer.code, self.day, "CNY", "NO-SUCH-SKU", "pcs", 1, "4", "1"],
            ["EXT-GOOD", self.customer.code, self.day, "CNY", self.second_sku.sku, "pcs", 2, "8", "1"],
        ]
        source = workbook_bytes(rows)
        preview = self.preview(source)
        self.assertEqual(preview.status_code, 200, preview.data)
        self.assertEqual((preview.data["valid_orders"], preview.data["invalid_orders"]), (1, 1))
        self.assertTrue(any(item["row"] == 3 and item["key"] == "EXT-BAD" for item in preview.data["errors"]))
        self.assertTrue(any("必须一致" in item["message"] for item in preview.data["errors"]))
        response = self.execute(source, preview.data["preview_token"])
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual((response.data["created_orders"], response.data["failed_orders"]), (1, 1))
        self.assertFalse(SalesOrderImportSourceOrder.objects.filter(source_order_no="EXT-BAD").exists())
        self.assertFalse(Order.objects.filter(sales_import_source__source_order_no="EXT-BAD").exists())
        good = Order.objects.get(sales_import_source__source_order_no="EXT-GOOD")
        self.assertEqual(good.items.count(), 1)

        corrected = workbook_bytes([
            ["EXT-BAD", self.customer.code, self.day, "USD", self.sku.sku, "箱", 1, "10", None],
            ["EXT-GOOD", self.customer.code, self.day, "CNY", self.second_sku.sku, "pcs", 4, "80", "1"],
        ])
        retry_preview = self.preview(corrected)
        self.assertEqual(retry_preview.data["valid_orders"], 1)
        self.assertEqual(retry_preview.data["invalid_orders"], 1)
        retry = self.execute(corrected, retry_preview.data["preview_token"])
        self.assertEqual(retry.data["created_orders"], 1)
        self.assertEqual(Order.objects.count(), 2)
        self.assertEqual(Order.objects.get(sales_import_source__source_order_no="EXT-GOOD").total_amount, Decimal("16.00"))
        self.assertEqual(Order.objects.get(sales_import_source__source_order_no="EXT-BAD").total_amount, Decimal("10.00"))

    def test_imported_draft_can_confirm_through_order_workflow(self):
        InventoryMovement.objects.create(
            movement_no="IMP-STOCK-IN", movement_date=self.day, type="adjust_in", sku=self.sku, quantity="20",
        )
        source = workbook_bytes([["EXT-CONFIRM", self.customer.code, self.day, "CNY", self.sku.sku, "箱", 2, "30", "1"]])
        preview = self.preview(source)
        created = self.execute(source, preview.data["preview_token"])
        self.assertEqual(created.data["created_orders"], 1)
        order = Order.objects.get(sales_import_source__source_order_no="EXT-CONFIRM")
        self.assertEqual(order.status, "draft")
        self.assertFalse(PaymentPlan.objects.filter(order=order).exists())
        self.assertFalse(InventoryReservation.objects.filter(order_item__order=order).exists())
        confirmed = self.client.post(f"/api/orders/{order.pk}/confirm/", {}, format="json")
        self.assertEqual(confirmed.status_code, 200, confirmed.data)
        order.refresh_from_db()
        self.assertEqual(order.status, "confirmed")
        self.assertTrue(PaymentPlan.objects.filter(order=order).exists())
        self.assertEqual(InventoryReservation.objects.get(order_item__order=order).quantity, Decimal("20"))

    @override_settings(**RBAC_SETTINGS)
    def test_import_permission_and_customer_scope_are_enforced(self):
        unauthorized = get_user_model().objects.create_user(username="sales-import-no-access", password="test-only")
        self.client.force_authenticate(user=unauthorized)
        source = workbook_bytes([["EXT-DENY", self.customer.code, self.day, "USD", self.sku.sku, "pcs", 1, "3", None]])
        self.assertEqual(self.preview(source).status_code, 403)

        unit = OrganizationUnit.objects.create(name="导入销售组", code="IMP-UNIT")
        position = Position.objects.create(unit=unit, name="销售", code="IMP-POS")
        role = AccessRole.objects.create(name="订单导入", code="IMP-ROLE", default_data_scope="self")
        for module, values in {
            "imports": {"can_view": True, "can_import": True},
            "orders": {"can_view": True, "can_create": True},
            "customers": {"can_view": True},
            "skus": {"can_view": True},
        }.items():
            RolePermission.objects.create(role=role, module=module, **values)
        scoped_user = get_user_model().objects.create_user(username="sales-import-scoped", password="test-only")
        profile = EmployeeProfile.objects.create(user=scoped_user, display_name="Import Scoped", unit=unit, position=position)
        profile.roles.add(role)
        other_customer = Customer.objects.create(code="IMP-OUTSIDE", name="Outside Scope")
        self.client.force_authenticate(user=scoped_user)
        outside = workbook_bytes([["EXT-OUTSIDE", other_customer.code, self.day, "USD", self.sku.sku, "pcs", 1, "3", None]])
        denied = self.preview(outside)
        self.assertEqual(denied.status_code, 200, denied.data)
        self.assertEqual(denied.data["valid_orders"], 0)
        self.assertTrue(any("数据范围" in item["message"] for item in denied.data["errors"]))
        self.assertFalse(Order.objects.exists())


@skipUnless(connection.vendor == "postgresql", "parallel idempotency requires independent PostgreSQL sessions")
class SalesOrderImportPostgresConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.day = date(2026, 11, 5)
        self.customer = Customer.objects.create(code="IMP-PG-C001", name="Import PG Buyer")
        product = Product.objects.create(code="IMP-PG-P001", name="Import PG Lamp")
        self.sku = SKU.objects.create(product=product, sku="IMP-PG-SKU-001", unit="pcs", cost_price="4.25")

    def test_parallel_clicks_with_the_same_preview_create_one_order_and_return_one_result(self):
        source = workbook_bytes([
            ["EXT-PG-RACE", self.customer.code, self.day, "CNY", self.sku.sku, "pcs", 2, "25", "1"],
        ])
        preview_client = APIClient()
        preview = preview_client.post(
            "/api/import/orders/preview/",
            {"file": upload(source)},
            format="multipart",
        )
        self.assertEqual(preview.status_code, 200, preview.data)
        token = preview.data["preview_token"]
        barrier = Barrier(2)

        def confirm():
            close_old_connections()
            try:
                with connections["default"].cursor() as cursor:
                    cursor.execute("SET statement_timeout = '15000ms'")
                    cursor.execute("SELECT pg_backend_pid()")
                    backend_pid = cursor.fetchone()[0]
                barrier.wait(timeout=10)
                client = APIClient()
                response = client.post(
                    "/api/import/orders/execute/",
                    {"file": upload(source), "preview_token": token},
                    format="multipart",
                )
                return backend_pid, response.status_code, response.data
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(confirm)
            second = pool.submit(confirm)
            results = [first.result(timeout=35), second.result(timeout=35)]

        self.assertEqual(len({result[0] for result in results}), 2)
        self.assertEqual([result[1] for result in results], [200, 200])
        self.assertEqual(results[0][2], results[1][2])
        self.assertEqual(results[0][2]["created_orders"], 1)
        self.assertEqual(Order.objects.filter(sales_import_source__source_order_no="EXT-PG-RACE").count(), 1)
        self.assertEqual(SalesOrderImportSourceOrder.objects.filter(source_order_no="EXT-PG-RACE").count(), 1)
        self.assertEqual(SalesOrderImportBatch.objects.count(), 1)

    def test_parallel_new_previews_for_same_source_cannot_duplicate_orders(self):
        source = workbook_bytes([
            ["EXT-PG-COLLISION", self.customer.code, self.day, "CNY", self.sku.sku, "pcs", 2, "25", "1"],
        ])
        previews = []
        for _ in range(2):
            response = APIClient().post(
                "/api/import/orders/preview/",
                {"file": upload(source)},
                format="multipart",
            )
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data["valid_orders"], 1)
            previews.append(response.data["preview_token"])

        def confirm(token):
            close_old_connections()
            try:
                with connections["default"].cursor() as cursor:
                    cursor.execute("SET statement_timeout = '15000ms'")
                    cursor.execute("SELECT pg_backend_pid()")
                    backend_pid = cursor.fetchone()[0]
                barrier.wait(timeout=10)
                client = APIClient()
                response = client.post(
                    "/api/import/orders/execute/",
                    {"file": upload(source), "preview_token": token},
                    format="multipart",
                )
                return backend_pid, response.status_code, response.data
            finally:
                connections.close_all()

        barrier = Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(confirm, previews[0])
            second = pool.submit(confirm, previews[1])
            results = [first.result(timeout=40), second.result(timeout=40)]

        self.assertEqual(len({result[0] for result in results}), 2)
        self.assertEqual([result[1] for result in results], [200, 200])
        self.assertEqual(sorted(result[2]["created_orders"] for result in results), [0, 1])
        self.assertEqual(sum(result[2]["failed_orders"] for result in results), 1)
        self.assertEqual(Order.objects.filter(sales_import_source__source_order_no="EXT-PG-COLLISION").count(), 1)
        self.assertEqual(SalesOrderImportSourceOrder.objects.filter(source_order_no="EXT-PG-COLLISION").count(), 1)
        self.assertEqual(SalesOrderImportBatch.objects.count(), 2)
        loser = next(result[2] for result in results if result[2]["created_orders"] == 0)
        self.assertEqual(loser["orders"], [])
        self.assertEqual(loser["failed_orders"], 1)
        self.assertTrue(loser["errors"])
        self.assertTrue(any("已导入" in error["message"] or "刚刚完成导入" in error["message"] for error in loser["errors"]))
