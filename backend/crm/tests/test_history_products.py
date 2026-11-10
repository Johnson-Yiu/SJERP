import csv
import io
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from decimal import Decimal
from unittest.mock import patch

from django.db import close_old_connections, connection, connections
from django.test import TestCase, TransactionTestCase, override_settings

from crm.history_product_models import ArchivedHistoryLine, HistoryProductLink, HistoryProductRule
from crm.history_products import apply_links
from crm.models import (
    GoodsReceipt, HistoryTakeoverEvent, HistoryTakeoverSourceRecord, InventoryMovement, InventoryReservation,
    Order, OrderItem, PaymentPlan, PurchaseOrder, PurchaseOrderItem, Shipment, SKU, Transaction,
)
from crm.tests.test_history_takeover import HistoryTakeoverFixtureMixin


ROOT = "/api/import/history-products/"


class HistoryProductFixture(HistoryTakeoverFixtureMixin):
    long_product_name = False

    def setUp(self):
        super().setUp()
        rows = self.source_rows(order_state="open", supplier_order_state="open")
        self.sku.delete()
        for sheet in ("履约记录", "库存盘点", "收付款计划", "收付款流水"):
            rows[sheet] = []
        rows["销售订单"][0].update(currency="CNY", shipping_fee="10", discount="5")
        original = rows["销售明细"][0]
        rows["销售明细"] = [
            {**original, "source_line_id": str(number), "sku_code": name, "sku_name_snapshot": name,
             "quantity_base": "2", "unit_price": price, "product_category_snapshot": "旧分类",
             "specification_snapshot": "24W", "cost_price_snapshot": "9", "cost_currency_snapshot": "CNY"}
            for number, name, price in ((1, "A", "50"), (2, "A1", "25"), (3, "A2灯", "25"))
        ]
        if self.long_product_name:
            rows["销售明细"][2]["sku_name_snapshot"] += " · " + "合成超长名称用于检查窄屏与批量预览换行" * 6
        rows["采购明细"][0].update(sku_code="A", sku_name_snapshot="A", specification_snapshot="18W")
        self.rows = rows
        self.application, self.group, _ = self.application_and_group(rows)
        self.group_url = f"/api/import/history-takeovers/{self.application.pk}/groups/{self.group.pk}/"
        reviewed = self.client.post(self.group_url + "review/", {
            "decision": "approve", "note": "已核实合成原资料", "confirm_manual": True,
        }, format="json")
        self.assertEqual(reviewed.status_code, 200, reviewed.data)
        archived = self.client.post(self.group_url + "execute/", {}, format="json")
        self.assertEqual(archived.status_code, 200, archived.data)
        self.sources = self.group.source_records.filter(target_model="crm.ArchivedHistoryLine")
        self.sales_ids = list(self.sources.filter(record_type="销售明细").values_list("pk", flat=True))

    def preview(self, ids, sku=None, operation="link", reason="", **extra):
        return self.client.post(ROOT + "preview/", {
            "ids": ids, "target": sku.pk if sku else None, "operation": operation, "reason": reason, **extra,
        }, format="json")

    def submit(self, preview):
        return self.client.post(ROOT + "apply/", {"token": preview.data["token"]}, format="json")

    def report(self, grouping):
        response = self.client.get("/api/reports/historical/", {"grouping": grouping, "date_from": "2024-01-01", "date_to": "2024-12-31"})
        self.assertEqual(response.status_code, 200, response.data)
        return response.data["sales"]

    def target(self, code="B"):
        return SKU.objects.create(product=self.product, sku=code, display_name_cn="正式灯具 " + code, specification="24W", unit="pcs")


class HistoricalProductLinkingTests(HistoryProductFixture, TestCase):
    def test_archive_with_empty_master_then_link_single_and_batch(self):
        self.assertEqual(SKU.objects.count(), 0)
        self.assertEqual(ArchivedHistoryLine.objects.count(), 4)
        self.assertEqual(OrderItem.objects.count() + PurchaseOrderItem.objects.count(), 0)
        order, purchase = Order.objects.get(), PurchaseOrder.objects.get()
        self.assertEqual(order.total_amount, Decimal("205"))
        self.assertEqual(purchase.total_amount, Decimal("15"))
        self.assertEqual(self.report("original")["pending_count"], 3)
        originals = list(self.sources.values_list("source_snapshot", flat=True))
        frozen = list(ArchivedHistoryLine.objects.values_list("facts", flat=True))

        b = self.target()
        single = self.preview(self.sales_ids[:1], b, save_rule=True)
        self.assertEqual(single.status_code, 200, single.data)
        self.assertEqual(self.submit(single).data, {"updated": 1})
        self.assertEqual(HistoryProductRule.objects.count(), 1)
        batch = self.preview(self.sales_ids[1:], b)
        self.assertEqual(batch.status_code, 200, batch.data)
        self.assertEqual(batch.data["quantities"], {"pcs": Decimal("4")})
        self.assertEqual(batch.data["amounts"], {"CNY": Decimal("100")})
        self.assertEqual(self.submit(batch).data, {"updated": 2})
        self.assertEqual(self.submit(batch).data, {"updated": 2})
        self.assertEqual(HistoryTakeoverEvent.objects.filter(event_type="history_product_linked", actor=self.admin).count(), 3)
        self.assertEqual(SKU.objects.count(), 1)

        detail = self.client.get(f"/api/orders/{order.pk}/")
        self.assertEqual(detail.status_code, 200, detail.data)
        self.assertEqual([row["name"] for row in detail.data["historical_products"]], ["A", "A1", "A2灯"])
        self.assertTrue(all(row["sku"]["id"] == b.pk for row in detail.data["historical_products"]))
        self.assertEqual(len(self.report("original")["by_sku"]), 3)
        report = self.report("linked")
        self.assertEqual(report["by_sku"][0]["id"], b.pk)
        self.assertEqual(report["by_sku"][0]["amount"], Decimal("200"))
        self.assertEqual(report["adjustments_rmb"], Decimal("5"))
        self.assertEqual(report["amount_rmb"], Decimal("205"))

        b.display_name_cn, b.cost_price, b.active = "B 新名称", Decimal("99"), False
        b.save()
        self.assertEqual(self.report("linked")["by_sku"][0]["amount"], Decimal("200"))
        self.assertEqual(self.report("linked")["by_category"][0]["label"], "旧分类")
        self.assertEqual(list(self.sources.values_list("source_snapshot", flat=True)), originals)
        self.assertEqual(list(ArchivedHistoryLine.objects.values_list("facts", flat=True)), frozen)
        self.assertEqual(HistoryProductLink.objects.count(), 3)
        for model in (InventoryMovement, InventoryReservation, PaymentPlan, Transaction, GoodsReceipt, Shipment):
            self.assertFalse(model.objects.exists(), model.__name__)

        exported = self.client.get(ROOT + "export/", {"target": "B"})
        self.assertEqual(exported.status_code, 200)
        csv_rows = list(csv.DictReader(io.StringIO(exported.content.decode("utf-8-sig"))))
        self.assertEqual({row["历史商品"] for row in csv_rows}, {"A", "A1", "A2灯"})
        self.assertTrue(all(row["正式 SKU"] == "B" and row["来源"] == "Legacy synthetic system" for row in csv_rows))

    def test_conflict_rebind_unlink_and_audit_failure_are_atomic(self):
        b, c = self.target(), self.target("C")
        purchase_id = self.sources.get(record_type="采购明细").pk
        conflict = self.preview([purchase_id, self.sales_ids[0]], b)
        self.assertEqual(conflict.status_code, 409, conflict.data)
        self.assertEqual(len(conflict.data["conflicts"]), 1)
        self.assertFalse(HistoryProductLink.objects.exists())

        stale = self.preview(self.sales_ids, b)
        other = self.preview(self.sales_ids[:1], c)
        self.assertEqual(self.submit(other).data, {"updated": 1})
        self.assertEqual(self.submit(stale).status_code, 409)
        self.assertEqual(HistoryProductLink.objects.count(), 1)
        self.assertEqual(self.preview(self.sales_ids[:1], b, operation="change").status_code, 400)
        change = self.preview(self.sales_ids[:1], b, operation="change", reason="已核对原单")
        self.assertEqual(self.submit(change).data, {"updated": 1})
        unlink = self.preview(self.sales_ids[:1], operation="unlink", reason="原单待重新核实")
        self.assertEqual(self.submit(unlink).data, {"updated": 1})
        self.assertIsNone(HistoryProductLink.objects.get(pk=self.sales_ids[0]).sku_id)

        batch = self.preview(self.sales_ids, b)
        before = list(HistoryProductLink.objects.values())
        create_event = HistoryTakeoverEvent.objects.create

        def fail_second(**values):
            if values["details"]["source_id"] == self.sales_ids[1]:
                raise RuntimeError("synthetic audit failure")
            return create_event(**values)

        with patch("crm.history_products.HistoryTakeoverEvent.objects.create", side_effect=fail_second):
            with self.assertRaisesRegex(RuntimeError, "synthetic audit failure"):
                apply_links(HistoryTakeoverSourceRecord.objects.all(), self.admin, batch.data["token"])
        self.assertEqual(list(HistoryProductLink.objects.values()), before)
        self.assertEqual(self.submit(batch).data, {"updated": 3})

    def test_repeat_source_cannot_create_duplicate_detail(self):
        rows = deepcopy(self.rows)
        rows["销售订单"][0]["order_no"] = "SYNTHETIC-REPEAT-SALE"
        rows["采购订单"][0]["purchase_no"] = "SYNTHETIC-REPEAT-PURCHASE"
        app, group, _ = self.application_and_group(rows)
        url = f"/api/import/history-takeovers/{app.pk}/groups/{group.pk}/"
        reviewed = self.client.post(url + "review/", {"decision": "approve", "note": "检查重复来源", "confirm_manual": True}, format="json")
        if reviewed.status_code == 200:
            self.assertIn(self.client.post(url + "execute/", {}, format="json").status_code, (400, 409))
        else:
            self.assertEqual(reviewed.status_code, 400)
        self.assertEqual(ArchivedHistoryLine.objects.count(), 4)


@skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL row locks")
@override_settings(FILE_UPLOAD_MAX_MEMORY_SIZE=1024 * 1024, FILE_UPLOAD_TEMP_DIR=None)
class HistoryProductPostgresTests(HistoryProductFixture, TransactionTestCase):
    def test_overlapping_operators_cannot_split_or_overwrite_a_batch(self):
        from django.contrib.auth import get_user_model
        from rest_framework.test import APIClient

        other = get_user_model().objects.create_superuser(username="h1-second-operator")
        b, c = self.target(), self.target("C")
        left = self.preview(self.sales_ids[:2], b)
        right_client = APIClient()
        right_client.force_authenticate(other)
        right = right_client.post(ROOT + "preview/", {"ids": self.sales_ids[1:], "target": c.pk, "operation": "link"}, format="json")
        self.assertEqual(left.status_code, 200, left.data)
        self.assertEqual(right.status_code, 200, right.data)
        barrier = Barrier(2)

        def worker(actor, token):
            close_old_connections()
            try:
                client = APIClient()
                client.force_authenticate(actor)
                barrier.wait(timeout=10)
                result = client.post(ROOT + "apply/", {"token": token}, format="json")
                return result.status_code, result.data
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(worker, self.admin, left.data["token"]), pool.submit(worker, other, right.data["token"])]
            results = [future.result(timeout=30) for future in futures]
        self.assertEqual(sorted(status for status, _ in results), [200, 409], results)
        self.assertEqual(HistoryProductLink.objects.count(), 2)
        self.assertEqual(HistoryProductLink.objects.values("sku_id").distinct().count(), 1)
        self.assertEqual(HistoryTakeoverEvent.objects.filter(event_type="history_product_linked").count(), 2)
