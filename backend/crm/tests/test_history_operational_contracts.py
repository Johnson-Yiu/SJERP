from datetime import date
from decimal import Decimal
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import DatabaseError, close_old_connections, connection, connections, transaction
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework.exceptions import APIException

from crm import history_operational_contracts as contracts, history_operational_finance as finance_bridge, history_operational_inventory as inventory
from crm.history_operational_common import overall_status
from crm.models import (FinanceFact, HistoryOperationalContract, HistoryTakeoverSourceRecord,
    InventoryMovement, Order, PaymentPlan, PurchaseOrder, Transaction)
from crm.services.fulfillment import confirm_shipment, record_receipt, reverse_receipt, reverse_shipment, sku_metrics
from crm.services.order_lifecycle import confirm_order
from crm.services.purchase_lifecycle import place_purchase_order
from crm.services import finance_closeout
from crm.tests.test_history_takeover import HistoryTakeoverFixtureMixin


@override_settings(AUDIT_LOG_ENABLED=True)
class HistoricalOperationalContractTests(HistoryTakeoverFixtureMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.application, self.group, _ = self.application_and_group()
        self.base = f"/api/import/history-takeovers/{self.application.pk}/groups/{self.group.pk}/"
        result = self.client.post(self.base + "review/", {"decision": "approve", "note": "核对合成来源", "confirm_manual": True}, format="json")
        self.assertEqual(result.status_code, 200, result.data)
        result = self.client.post(self.base + "execute/", {}, format="json")
        self.assertEqual(result.status_code, 200, result.data)
        self.maker = get_user_model().objects.create_superuser(username="history-contract-maker", password="test-only")
        self.reviewer = get_user_model().objects.create_superuser(username="history-contract-reviewer", password="test-only")
        media = tempfile.TemporaryDirectory(prefix="history-closeout-e2e-")
        self.addCleanup(media.cleanup)
        media_settings = override_settings(MEDIA_ROOT=media.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)
        self.sources = {(item.record_type, item.source_record_id): item for item in self.group.source_records.all()}
        sale = self.sources[("销售订单", "SO-HT-1")]
        purchase = self.sources[("采购订单", "PO-HT-1")]
        self.payload = {"cutover_date": "2025-01-01", "reason": "核对合成合同、履约和未结款",
            "contracts": [
                {"source_id": sale.pk, "balance_mode": "itemized", "evidence_reference": "synthetic://sales-balance",
                 "plan_source_ids": [self.sources[("收付款计划", "PLAN-SO-1")].pk],
                 "remaining_shipping_fee": "0", "remaining_discount": "0", "amount_evidence": "synthetic://sales-amount",
                 "line_options": [{"source_id": self.sources[("销售明细", "SO-HT-1:1")].pk,
                    "unit_cost": "3.25", "cost_currency": "USD", "cost_evidence": "synthetic://sales-cost"}]},
                {"source_id": purchase.pk, "balance_mode": "itemized", "evidence_reference": "synthetic://purchase-balance",
                 "plan_source_ids": [self.sources[("收付款计划", "PLAN-PO-1")].pk], "no_additional_costs": True, "costs_evidence": "synthetic://purchase-cost",
                 "line_options": [{"source_id": self.sources[("采购明细", "PO-HT-1:1")].pk,
                    "supplier_sku_id": None, "manual_reason": "原供应商无供货档案，已核对合同", "target": "order", "sales_source_id": sale.pk}]},
            ]}

    def approve_contracts(self):
        proposal, replay = contracts.propose(self.group.pk, self.payload, self.maker)
        self.assertFalse(replay)
        self.assertEqual(proposal.status, "pending_review")
        with self.assertRaises(APIException):
            contracts.approve(self.group.pk, "申请人不可自行复核", self.maker)
        contracts.approve(self.group.pk, "已复核合成订单、余额及成本", self.reviewer)

    def activate_inventory(self):
        source = self.sources[("库存盘点", "COUNT-HT-1")]
        row = {"source_id": source.pk, "goods_ownership": "own", "unit_cost": "3.25", "cost_currency": "USD", "no_lot": False}
        inventory.propose(self.group.pk, [row], "核对合成盘点", True, self.maker)
        inventory.approve(self.group.pk, "复核合成盘点", self.reviewer)
        inventory.execute(self.group.pk, self.maker)

    @unittest.skipUnless(connection.vendor == "postgresql", "requires PostgreSQL TRUNCATE triggers")
    def test_history_records_reject_raw_truncate_and_preserve_rows(self):
        self.activate_inventory()
        inventory.reverse(self.group.pk, "合成记录撤销", self.reviewer)
        self.approve_contracts()
        contracts.execute(self.group.pk, self.maker)
        tables = ("crm_historyinventorybaseline", "crm_historyinventorybaselinereversal", "crm_historyoperationalcontract")
        with connection.cursor() as cursor:
            before = {}
            for table in tables:
                cursor.execute(f"SELECT count(*) FROM {connection.ops.quote_name(table)}")
                before[table] = cursor.fetchone()[0]
                self.assertGreater(before[table], 0)
                cursor.execute("SELECT tgenabled, tgtype FROM pg_trigger WHERE tgrelid = %s::regclass AND tgname = %s", [table, table + "_truncate_guard"])
                self.assertEqual(cursor.fetchone(), ("O", 34))
        # Flush deferred FK trigger events before TRUNCATE so PostgreSQL reaches
        # the statement guard instead of rejecting an in-use relation first.
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        for table in tables:
            with self.subTest(table=table):
                with self.assertRaisesMessage(DatabaseError, "append-only"), transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute(f"TRUNCATE TABLE {connection.ops.quote_name(table)} CASCADE")
                with connection.cursor() as cursor:
                    for checked in tables:
                        cursor.execute(f"SELECT count(*) FROM {connection.ops.quote_name(checked)}")
                        self.assertEqual(cursor.fetchone()[0], before[checked])

    def test_group_balance_stock_receipt_shipment_and_later_settlement(self):
        original_sale = Order.objects.get(order_no="HIST-SO-HT-1")
        original_purchase = PurchaseOrder.objects.get(purchase_no="HIST-PO-HT-1")
        self.approve_contracts()
        ids, replay = contracts.execute(self.group.pk, self.maker)
        self.assertFalse(replay)
        self.assertEqual(contracts.execute(self.group.pk, self.maker), (ids, True))
        self.assertEqual(len(ids), 2)
        sale_link = HistoryOperationalContract.objects.get(archived_order=original_sale)
        purchase_link = HistoryOperationalContract.objects.get(archived_purchase=original_purchase)
        sale, purchase = sale_link.continuation_order, purchase_link.continuation_purchase
        self.assertEqual(sale.items.get().quantity, Decimal("6"))
        self.assertEqual(purchase.items.get().quantity, Decimal("3"))
        self.assertEqual(purchase.items.get().cost_allocations.get().order_id, sale.pk)
        self.assertEqual(original_sale.outstanding_amount, Decimal("60"))
        self.assertEqual(original_purchase.unpaid_amount, Decimal("10"))
        self.assertEqual(original_sale.paid_amount, 0)
        self.assertEqual(original_purchase.paid_amount, 0)
        self.assertFalse(Transaction.objects.exists())
        self.assertFalse(FinanceFact.objects.exists())
        self.assertFalse(InventoryMovement.objects.exists())
        self.group.refresh_from_db()
        self.assertNotEqual(overall_status(self.group)["state"], "connected")
        account = finance_closeout.create_account({"code": "E2E-HIST", "name": "合成历史账户", "account_type": "bank", "ownership": "own", "ownership_reason": "合成资料"}, self.maker)
        voucher = finance_closeout.upload(SimpleUploadedFile("history.pdf", b"%PDF-1.4\nsynthetic history\n%%EOF"), self.maker)
        source = self.sources[("收付款流水", "TX-SO-1")]
        finance_bridge.submit_source(self.group.pk, source.pk, {"account": account.pk, "voucher": voucher.pk,
            "actual_date": "2024-09-03", "amount": "287.43", "reason": "核对合成原始银行凭证"}, self.maker)
        finance_bridge.advance_source(self.group.pk, source.pk, "approve", self.reviewer)
        finance_bridge.advance_source(self.group.pk, source.pk, "post", self.maker, voucher_checked=True)
        self.assertEqual(FinanceFact.objects.count(), 1)
        source2 = self.sources[("收付款流水", "TX-PO-1")]
        finance_bridge.submit_source(self.group.pk, source2.pk, {"account": account.pk, "voucher": voucher.pk,
            "actual_date": "2024-09-04", "amount": "35.00", "reason": "核对合成付款凭证"}, self.maker)
        finance_bridge.advance_source(self.group.pk, source2.pk, "approve", self.reviewer)
        finance_bridge.advance_source(self.group.pk, source2.pk, "post", self.maker, voucher_checked=True)
        self.assertTrue(voucher.file.storage.exists(voucher.file.name))
        self.assertFalse(Transaction.objects.exists())
        self.assertEqual(original_sale.outstanding_amount, Decimal("60"))
        self.activate_inventory()
        self.assertEqual(sku_metrics(self.sku)["actual_quantity"], Decimal("18"))
        self.assertEqual(sku_metrics(self.sku)["reserved_quantity"], 0)
        sale = confirm_order(sale)
        purchase = place_purchase_order(purchase, operator=self.maker)
        self.assertEqual(overall_status(self.group)["state"], "connected")
        response = self.client.get(f"/api/import/history-takeovers/{self.application.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["groups"][0]["operational_overall"]["state"], "connected")
        self.assertFalse(sale.payment_plans.exists())
        self.assertFalse(purchase.payment_plans.exists())
        location = {"warehouse_type": "自有仓", "warehouse": "SYN-WH-01", "lot_reference": "LOT-HT-01"}
        with self.assertRaisesMessage(Exception, "明确选择仓库"):
            record_receipt(purchase.items.get(), {"receipt_date": date(2025, 1, 3), "quantity": Decimal("3"), "unit_cost": Decimal("3")})
        receipt = record_receipt(purchase.items.get(), {"receipt_date": date(2025, 1, 3), "quantity": Decimal("3"), "unit_cost": Decimal("3"), **location})
        with self.assertRaisesMessage(Exception, "所选仓库及批次库存不足"):
            confirm_shipment(sale, {"shipment_date": date(2025, 1, 4), "items": [{"order_item": sale.items.get().pk, "quantity": Decimal("6"), **{**location, "lot_reference": "OTHER"}}]})
        shipment = confirm_shipment(sale, {"shipment_date": date(2025, 1, 4), "items": [{"order_item": sale.items.get().pk, "quantity": Decimal("6"), **location}]})
        self.assertEqual(receipt.inventory_movement.lot_reference, "LOT-HT-01")
        self.assertEqual(shipment.items.get().inventory_movement.warehouse, "SYN-WH-01")
        self.assertEqual(sku_metrics(self.sku)["actual_quantity"], Decimal("15"))
        self.client.force_authenticate(self.maker)
        sale_plan = original_sale.payment_plans.get()
        purchase_plan = original_purchase.payment_plans.get()
        for plan, amount in ((sale_plan, "20"), (purchase_plan, "4")):
            response = self.client.post(f"/api/payment-plans/{plan.pk}/settle/", {"amount": amount, "currency": "USD", "exchange_rate": "1", "transaction_date": "2025-01-05"}, format="json")
            self.assertEqual(response.status_code, 201, response.data)
        original_sale.refresh_from_db(); original_purchase.refresh_from_db()
        self.assertEqual(original_sale.outstanding_amount, Decimal("40"))
        self.assertEqual(original_purchase.unpaid_amount, Decimal("6"))
        self.assertEqual(Transaction.objects.count(), 2)
        self.assertEqual(FinanceFact.objects.count(), 2)
        reverse_shipment(shipment, "合成发货冲销")
        reverse_receipt(receipt, "合成收货冲销")
        self.assertEqual(sku_metrics(self.sku)["actual_quantity"], Decimal("18"))
        self.assertEqual((original_sale.status, original_purchase.status), ("historical", "historical"))
        item = sale.items.get()
        change = {"version": 0, "request_key": "SYNTH-HISTORY-REVISION-1", "reason": "合成追加需求",
                  "items": [{"order_item": item.pk, "new_quantity": "7"}]}
        response = self.client.post(f"/api/orders/{sale.pk}/quantity-adjustments/", change, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        original_sale.refresh_from_db()
        self.assertEqual(original_sale.outstanding_amount, Decimal("52"))
        self.assertEqual(original_sale.items.get().quantity, Decimal("10"))
        change.update({"version": 1, "request_key": "SYNTH-HISTORY-REVISION-2", "reason": "撤销合成追加",
                       "items": [{"order_item": item.pk, "new_quantity": "6"}]})
        response = self.client.post(f"/api/orders/{sale.pk}/quantity-adjustments/", change, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        original_sale.refresh_from_db()
        self.assertEqual(original_sale.outstanding_amount, Decimal("40"))
        self.assertEqual(original_sale.items.get().quantity, Decimal("10"))

    def test_failure_rolls_back_links_drafts_and_plans(self):
        self.approve_contracts()
        with patch("crm.history_operational_contracts.install_history_opening_plans", side_effect=RuntimeError("injected balance failure")):
            with self.assertRaisesRegex(RuntimeError, "injected balance failure"):
                contracts.execute(self.group.pk, self.maker)
        self.assertFalse(HistoryOperationalContract.objects.exists())
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(PurchaseOrder.objects.count(), 1)
        self.assertFalse(PaymentPlan.objects.exists())
        self.assertFalse(Transaction.objects.exists())

    def test_reversal_is_idempotent_and_preserves_records(self):
        self.approve_contracts()
        contracts.execute(self.group.pk, self.maker)
        links = list(self.group.operational_contracts.all())
        self.assertFalse(contracts.reverse(self.group.pk, "合成资料需更正", self.reviewer))
        self.assertTrue(contracts.reverse(self.group.pk, "重试", self.reviewer))
        self.assertEqual(HistoryOperationalContract.objects.count(), 2)
        self.assertEqual(PaymentPlan.objects.filter(status="cancelled").count(), 2)
        from crm.services.historical import has_verified_history_balance
        self.assertFalse(has_verified_history_balance(Order.objects.get(order_no="HIST-SO-HT-1")))
        for link in links:
            continuation = link.continuation_order or link.continuation_purchase
            continuation.refresh_from_db()
            self.assertEqual(continuation.status, "cancelled")

    def test_reversal_rejects_formal_downstream_work(self):
        self.approve_contracts()
        contracts.execute(self.group.pk, self.maker)
        link = self.group.operational_contracts.get(archived_order__isnull=False)
        confirm_order(link.continuation_order)
        with self.assertRaisesMessage(APIException, "已进入正式业务"):
            contracts.reverse(self.group.pk, "不得删除正式业务", self.reviewer)
        self.assertEqual(PaymentPlan.objects.filter(status="open").count(), 2)

    def test_reversal_audit_failure_rolls_back_all_changes(self):
        self.approve_contracts()
        contracts.execute(self.group.pk, self.maker)
        with patch("crm.services.finance_closeout.audit", side_effect=RuntimeError("injected reversal audit failure")):
            with self.assertRaisesRegex(RuntimeError, "injected reversal audit failure"):
                contracts.reverse(self.group.pk, "合成撤销", self.reviewer)
        self.assertEqual(PaymentPlan.objects.filter(status="open").count(), 2)
        self.assertEqual(Order.objects.filter(status="draft").count(), 1)
        self.assertEqual(PurchaseOrder.objects.filter(status="draft").count(), 1)

    def test_manual_movements_respect_opening_stock_location(self):
        self.activate_inventory()
        payload = {"movement_date": "2025-01-03", "type": "adjust_out", "sku": self.sku.pk, "quantity": "2"}
        response = self.client.post("/api/inventory-movements/", payload, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        payload.update({"warehouse_type": "自有仓", "warehouse": "SYN-WH-01", "lot_reference": "wrong"})
        response = self.client.post("/api/inventory-movements/", payload, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        payload["lot_reference"] = "LOT-HT-01"
        response = self.client.post("/api/inventory-movements/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        ident = response.data["id"]
        self.assertEqual(sku_metrics(self.sku)["actual_quantity"], Decimal("16"))
        changed = self.client.patch(f"/api/inventory-movements/{ident}/", {"warehouse": "OTHER"}, format="json")
        self.assertEqual(changed.status_code, 400, changed.data)
        reversed_response = self.client.post(f"/api/inventory-movements/{ident}/reverse/", {"reason": "合成盘点更正"}, format="json")
        self.assertEqual(reversed_response.status_code, 201, reversed_response.data)
        self.assertEqual(sku_metrics(self.sku)["actual_quantity"], Decimal("18"))

    def test_pending_shared_costs_must_use_formal_cost_workflow_before_placement(self):
        from django.core.exceptions import ValidationError as DjangoValidationError
        from crm.services.purchase_costs import save_costs
        options = self.payload["contracts"][1]
        options.update({"no_additional_costs": False, "additional_costs_pending": True})
        self.approve_contracts()
        contracts.execute(self.group.pk, self.maker)
        sale = self.group.operational_contracts.get(archived_order__isnull=False).continuation_order
        purchase = self.group.operational_contracts.get(archived_purchase__isnull=False).continuation_purchase
        confirm_order(sale)
        with self.assertRaisesMessage(DjangoValidationError, "公共费用尚未登记"):
            place_purchase_order(purchase, operator=self.maker)
        item = purchase.items.get()
        save_costs(purchase, {"version": 0, "allocations": [{"purchase_item": item.pk, "target_type": "order", "order": sale, "quantity": item.quantity}], "expenses": [{"name": "合成运费", "amount": Decimal("5.00"), "method": "amount"}]})
        purchase = place_purchase_order(purchase, operator=self.maker)
        self.assertEqual(purchase.additional_costs[0]["amount"], "5.00")
        self.assertEqual(purchase.status, "ordered")

    def test_balance_only_requires_explicit_amount_and_never_guesses(self):
        options = self.payload["contracts"][0]
        options.update({"balance_mode": "balance_only", "plan_source_ids": [], "balance_amount": ""})
        with self.assertRaises(APIException):
            contracts.propose(self.group.pk, self.payload, self.maker)
        self.assertFalse(HistoryOperationalContract.objects.exists())
        self.assertFalse(PaymentPlan.objects.exists())


class HistoricalContractLifecycleTests(HistoryTakeoverFixtureMixin, TestCase):
    def _run_lifecycle(self, state, amount):
        rows = self.source_rows(order_state=state, supplier_order_state=state)
        if state == "cancelled":
            rows["履约记录"] = []
        else:
            rows["履约记录"][0]["quantity_base"] = "10.00"
            rows["履约记录"][1]["quantity_base"] = "5.00"
        application, group, _ = self.application_and_group(rows)
        base = f"/api/import/history-takeovers/{application.pk}/groups/{group.pk}/"
        reviewed = self.client.post(base + "review/", {"decision": "approve", "note": "合成合同核验", "confirm_manual": True}, format="json")
        self.assertEqual(reviewed.status_code, 200, reviewed.data)
        archived = self.client.post(base + "execute/", {}, format="json")
        self.assertEqual(archived.status_code, 200, archived.data)
        maker = get_user_model().objects.create_superuser(username="lifecycle-maker", password="test-only")
        reviewer = get_user_model().objects.create_superuser(username="lifecycle-reviewer", password="test-only")
        docs = list(group.source_records.filter(record_type__in=["销售订单", "采购订单"]).order_by("pk"))
        payload = {"cutover_date": "2025-01-01", "reason": "核对合成合同状态", "contracts": [
            {"source_id": doc.pk, "balance_mode": "balance_only", "balance_amount": amount, "plan_source_ids": [],
             "evidence_reference": "synthetic://verified-balance", "line_options": []} for doc in docs]}
        contracts.propose(group.pk, payload, maker)
        contracts.approve(group.pk, "独立复核合成余额", reviewer)
        ids, replay = contracts.execute(group.pk, maker)
        self.assertFalse(replay)
        self.assertEqual(len(ids), 2)
        self.assertFalse(Order.objects.filter(status="draft").exists())
        self.assertFalse(PurchaseOrder.objects.filter(status="draft").exists())
        self.assertEqual(PaymentPlan.objects.count(), 2 if Decimal(amount) else 0)
        self.assertFalse(InventoryMovement.objects.exists())
        self.assertFalse(Transaction.objects.exists())

    def test_cancelled_contracts_do_not_recreate_fulfillment(self):
        self._run_lifecycle("cancelled", "0")

    def test_completed_contracts_can_carry_verified_unpaid_balance_only(self):
        self._run_lifecycle("completed", "10")


@unittest.skipUnless(connection.vendor == "postgresql", "requires real PostgreSQL row locks")
@override_settings(FILE_UPLOAD_TEMP_DIR=tempfile.gettempdir())
class HistoricalContractsPostgresTests(HistoryTakeoverFixtureMixin, TransactionTestCase):
    def test_concurrent_execute_creates_each_contract_once(self):
        application, group, _ = self.application_and_group()
        base = f"/api/import/history-takeovers/{application.pk}/groups/{group.pk}/"
        self.assertEqual(self.client.post(base + "review/", {"decision": "approve", "note": "核对合成资料", "confirm_manual": True}, format="json").status_code, 200)
        self.assertEqual(self.client.post(base + "execute/", {}, format="json").status_code, 200)
        maker = get_user_model().objects.create_superuser(username="contracts-pg-maker", password="test-only")
        reviewer = get_user_model().objects.create_superuser(username="contracts-pg-reviewer", password="test-only")
        sources = {(row.record_type, row.source_record_id): row for row in group.source_records.all()}
        sale = sources[("销售订单", "SO-HT-1")]
        purchase = sources[("采购订单", "PO-HT-1")]
        payload = {"cutover_date": "2025-01-01", "reason": "合成并发测试", "contracts": [
            {"source_id": sale.pk, "balance_mode": "itemized", "evidence_reference": "synthetic://sale", "plan_source_ids": [sources[("收付款计划", "PLAN-SO-1")].pk], "remaining_shipping_fee": "0", "remaining_discount": "0", "amount_evidence": "synthetic://amount", "line_options": [{"source_id": sources[("销售明细", "SO-HT-1:1")].pk, "unit_cost": "3.25", "cost_currency": "USD", "cost_evidence": "synthetic://cost"}]},
            {"source_id": purchase.pk, "balance_mode": "itemized", "evidence_reference": "synthetic://purchase", "plan_source_ids": [sources[("收付款计划", "PLAN-PO-1")].pk], "no_additional_costs": True, "costs_evidence": "synthetic://cost", "line_options": [{"source_id": sources[("采购明细", "PO-HT-1:1")].pk, "supplier_sku_id": None, "manual_reason": "核对合成合同", "target": "order", "sales_source_id": sale.pk}]},
        ]}
        contracts.propose(group.pk, payload, maker)
        contracts.approve(group.pk, "核对合成资料", reviewer)
        gate = Barrier(2)
        def worker(_index):
            close_old_connections()
            try:
                actor = get_user_model().objects.get(pk=maker.pk)
                gate.wait(timeout=20)
                return contracts.execute(group.pk, actor)
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(worker, range(2)))
        self.assertEqual(results[0][0], results[1][0])
        self.assertCountEqual([row[1] for row in results], [True, False])
        self.assertEqual(HistoryOperationalContract.objects.count(), 2)
        self.assertEqual(PaymentPlan.objects.count(), 2)
        self.assertEqual(Order.objects.filter(status="draft").count(), 1)
        self.assertEqual(PurchaseOrder.objects.filter(status="draft").count(), 1)
        self.assertFalse(InventoryMovement.objects.exists())
        self.assertFalse(Transaction.objects.exists())
