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
        events = HistoryTakeoverEvent.objects.filter(event_type="history_product_linked")
        from crm.permissions import development_superadmin_enabled
        actor, kind = (None, "development") if development_superadmin_enabled() else (self.admin, "identified")
        self.assertEqual(events.filter(actor=actor, actor_kind=kind).count(), 3)
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

        with patch("crm.history_takeover.HistoryTakeoverEvent.objects.create", side_effect=fail_second):
            with self.assertRaisesRegex(RuntimeError, "synthetic audit failure"):
                apply_links(HistoryTakeoverSourceRecord.objects.all(), self.admin, batch.data["token"])
        self.assertEqual(list(HistoryProductLink.objects.values()), before)
        self.assertEqual(self.submit(batch).data, {"updated": 3})

    def test_missing_specification_needs_evidence_and_audits_development_identity(self):
        source = self.sources.get(pk=self.sales_ids[0])
        line = ArchivedHistoryLine.objects.get(pk=source.target_id)
        line.facts = {**line.facts, "specification_snapshot": ""}
        line.save(update_fields=["facts"])
        b = self.target()
        self.assertEqual(self.preview([source.pk], b).status_code, 409)
        self.assertEqual(self.preview([source.pk], b, verified_specification="24 W").status_code, 400)
        self.assertEqual(self.preview([source.pk], b, reason="旧检验单", verified_specification="24 kW").status_code, 409)
        blank = self.target("NO-SPEC")
        blank.specification = ""
        blank.save(update_fields=["specification"])
        self.assertEqual(self.preview([source.pk], blank, reason="旧检验单", verified_specification="24W").status_code, 409)
        with override_settings(DEBUG=True, APP_STAGE="development", DEVELOPMENT_SUPERADMIN=True, RBAC_ENFORCEMENT=False):
            preview = self.preview([source.pk], b, reason="旧检验单 REF-24", verified_specification="24 W")
            self.assertEqual(preview.status_code, 200, preview.data)
            self.assertEqual(self.submit(preview).data, {"updated": 1})
        event = self.group.events.get(event_type="history_product_linked")
        self.assertEqual((event.actor_id, event.actor_kind), (None, "development"))
        self.assertEqual(event.details["after_sku"]["code"], "B")
        self.assertEqual(event.details["verified_specification"], "24 W")
        self.assertEqual(event.details["reason"], "旧检验单 REF-24")
        line.refresh_from_db()
        self.assertEqual(line.facts["specification_snapshot"], "")

    def test_candidate_rule_is_visible_without_binding_and_respects_current_specification(self):
        b = self.target()
        self.assertEqual(self.submit(self.preview(self.sales_ids[:1], b, save_rule=True)).data, {"updated": 1})
        rows = deepcopy(self.rows)
        rows["销售订单"][0].update(order_no="H2-SECOND-ORDER")
        rows["采购订单"][0].update(purchase_no="H2-SECOND-PURCHASE")
        _, group, _ = self.application_and_group(rows)
        row = next(item for item in group.preflight_result["results"] if item.get("product_candidates"))
        candidate, = row["product_candidates"]
        self.assertEqual((candidate["code"], candidate["specification"], candidate["unit"]), ("B", "24W", "pcs"))
        self.assertTrue(candidate["basis"])
        self.assertEqual(group.resolution_map, {})
        self.assertEqual(row["product_link_status"], "待关联")
        from crm.history_takeover import _group_preflight
        b.specification = "18W"
        b.save(update_fields=["specification"])
        payload, _ = _group_preflight(group, self.admin)
        self.assertFalse(any(item.get("product_candidates") for item in payload["results"]))

    def test_fifty_rounded_lines_match_preview_export_analysis_and_order(self):
        rows = deepcopy(self.rows)
        self.group.source_records.all().delete()
        ArchivedHistoryLine.objects.all().delete()
        Order.objects.all().delete()
        PurchaseOrder.objects.all().delete()
        template = rows["销售明细"][0]
        rows["销售明细"] = [
            {**template, "source_line_id": str(number), "quantity_base": "1", "unit_price": "0.335"}
            for number in range(1, 51)
        ]
        rows["分组"][0]["notes"] = "H2 50 × 0.335"
        app, group, _ = self.application_and_group(rows)
        url = f"/api/import/history-takeovers/{app.pk}/groups/{group.pk}/"
        response = self.client.post(url + "review/", {"decision": "approve", "note": "核对运费10，折扣5", "confirm_manual": True}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        response = self.client.post(url + "execute/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        ids = list(group.source_records.filter(record_type="销售明细").values_list("pk", flat=True))
        preview = self.preview(ids, self.target())
        self.assertEqual(preview.status_code, 200, preview.data)
        self.assertEqual(preview.data["amounts"], {"CNY": Decimal("17.00")})
        self.assertEqual(self.submit(preview).data, {"updated": 50})
        export = self.client.get(ROOT + "export/", {"target": "B"})
        items = list(csv.DictReader(io.StringIO(export.content.decode("utf-8-sig"))))
        self.assertEqual(len(items), 50)
        self.assertEqual(sum(Decimal(item["商品金额"]) for item in items), Decimal("17.00"))
        self.assertEqual(self.report("linked")["by_sku"][0]["amount"], Decimal("17.00"))
        order = Order.objects.get()
        self.assertEqual((order.total_amount, order.shipping_fee, order.discount), (Decimal("22"), Decimal("10"), Decimal("5")))
        self.assertEqual({line.unit_price for line in order.archived_lines.all()}, {Decimal("0.335")})

    def test_list_query_count_is_bounded_and_export_uses_same_filters(self):
        from django.test.utils import CaptureQueriesContext

        template = self.sources.get(pk=self.sales_ids[0])
        def add(start, stop):
            HistoryTakeoverSourceRecord.objects.bulk_create([
                HistoryTakeoverSourceRecord(
                    group=self.group, record_type=template.record_type, source_system=template.source_system,
                    source_record_id=f"H2-BULK-{number}", target_model=template.target_model, target_id=template.target_id,
                    source_snapshot=template.source_snapshot,
                ) for number in range(start, stop)
            ])
        filters = {"q": "H2-BULK", "status": "pending", "date_from": "2024-01-01", "date_to": "2024-12-31"}
        add(0, 50)
        with CaptureQueriesContext(connection) as small:
            first = self.client.get(ROOT, filters)
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(first.data["count"], 50)
        add(50, 500)
        with CaptureQueriesContext(connection) as large:
            first = self.client.get(ROOT, filters)
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(first.data["count"], 500)
        self.assertEqual(len(first.data["results"]), 50)
        self.assertLessEqual(len(large), 8)
        self.assertEqual(len(large), len(small))
        export = self.client.get(ROOT + "export/", filters)
        items = list(csv.DictReader(io.StringIO(export.content.decode("utf-8-sig"))))
        self.assertEqual(len(items), first.data["count"])
        self.assertEqual([item["原明细"] for item in items[:50]], [row["source_number"] for row in first.data["results"]])

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
