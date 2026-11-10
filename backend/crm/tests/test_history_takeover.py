import io
import copy
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import DatabaseError, close_old_connections, connection, connections, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from openpyxl import Workbook, load_workbook
from rest_framework.test import APIClient

from crm.history_import_preflight import SHEET_SCHEMAS
from crm.history_takeover import execute_group
from crm.models import (
    Customer,
    GoodsReceipt,
    HistoryTakeoverApplication,
    HistoryTakeoverEvent,
    HistoryTakeoverGroup,
    HistoryTakeoverHandoff,
    HistoryTakeoverSourceRecord,
    InventoryMovement,
    InventoryReservation,
    OperationLog,
    Order,
    OrderItem,
    PaymentPlan,
    Product,
    PurchaseCostAllocation,
    PurchaseOrder,
    PurchaseOrderItem,
    Shipment,
    SKU,
    Supplier,
    Transaction,
)


class HistoryTakeoverFixtureMixin:
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            username="takeover-synthetic-admin", email="takeover-admin@example.test", password="test-only"
        )
        self.client.force_authenticate(self.admin)
        self.customer = Customer.objects.create(code="HT-C1", name="Synthetic History Customer", country="US")
        self.supplier = Supplier.objects.create(code="H1", name="Synthetic History Supplier")
        self.product = Product.objects.create(code="HT-P1", name="Synthetic History Product", sales_model_prefix="HT")
        self.sku = SKU.objects.create(sku="HT-S1", product=self.product, display_name_cn="Synthetic SKU", unit="pcs")

    def source_rows(self, *, group_id="HT-G1", order_state="partial", supplier_order_state="partial", truth="真实", source_system="Legacy synthetic system"):
        truth_value = truth
        return {
            "分组": [{
                "group_id": group_id, "source_system": source_system, "exported_at": date(2024, 12, 31),
                "coverage_status": "complete", "truth_status": truth_value,
                "evidence_reference": "synthetic://manifest/HT-G1", "notes": "isolated synthetic evidence",
            }],
            "销售订单": [{
                "group_id": group_id, "source_record_id": "SO-HT-1", "order_no": "HIST-SO-HT-1",
                "order_date": date(2024, 8, 1), "lifecycle_state": order_state, "customer_code": self.customer.code,
                "customer_name_snapshot": "Historical Customer Name", "customer_country_snapshot": "United States",
                "customer_address_snapshot": "Historical address", "customer_contact_name_snapshot": "Historical contact",
                "customer_phone_snapshot": "+1-555-0101", "customer_email_snapshot": "history@example.test",
                "currency": "USD", "exchange_rate": "1.000000", "shipping_fee": "0.0000", "discount": "0.0000",
                "truth_status": truth_value, "voucher_reference": "synthetic://contract/SO-HT-1", "notes": "historical-only",
            }],
            "销售明细": [{
                "group_id": group_id, "source_order_id": "SO-HT-1", "source_line_id": "1", "sku_code": self.sku.sku,
                "sku_name_snapshot": "Historical SKU Name", "sales_model_snapshot": "OLD-MODEL-1",
                "description_snapshot": "Historical product description", "unit_snapshot": "pcs", "base_unit_snapshot": "pcs",
                "quantity_base": "10.00", "unit_price": "12.000000000000", "trade_quantity": None,
                "trade_unit_snapshot": None, "trade_unit_price": None, "trade_factor_snapshot": None,
                "allow_fraction_snapshot": None, "truth_status": truth_value,
                "voucher_reference": "synthetic://contract-line/SO-HT-1-1", "notes": "source sales line",
            }],
            "采购订单": [{
                "group_id": group_id, "source_record_id": "PO-HT-1", "purchase_no": "HIST-PO-HT-1",
                "order_date": date(2024, 7, 1), "lifecycle_state": supplier_order_state, "supplier_code": self.supplier.code,
                "supplier_name_snapshot": "Historical Supplier Name", "supplier_address_snapshot": "Old supplier address",
                "supplier_contact_name_snapshot": "Supplier contact", "supplier_phone_snapshot": "+86-555-0111",
                "supplier_email_snapshot": "supplier@example.test", "currency": "USD", "exchange_rate": "1.000000",
                "truth_status": truth_value, "voucher_reference": "synthetic://contract/PO-HT-1", "notes": "historical-only",
            }],
            "采购明细": [{
                "group_id": group_id, "source_purchase_id": "PO-HT-1", "source_line_id": "1", "sku_code": self.sku.sku,
                "sku_name_snapshot": "Historical Purchase SKU", "sales_model_snapshot": "PO-OLD-MODEL",
                "description_snapshot": "Purchase description", "unit_snapshot": "pcs", "base_unit_snapshot": "pcs",
                "quantity_base": "5.00", "unit_price": "3.000000000000", "trade_quantity": None,
                "trade_unit_snapshot": None, "trade_unit_price": None, "trade_factor_snapshot": None,
                "allow_fraction_snapshot": None, "supplier_name_snapshot": "Historical Supplier Name",
                "supplier_model_snapshot": "SUP-MODEL", "supplier_sku_code_snapshot": "SUP-SKU-1",
                "truth_status": truth_value, "voucher_reference": "synthetic://purchase-line/PO-HT-1-1", "notes": "source purchase line",
            }],
            "收付款计划": [
                {"group_id": group_id, "source_plan_id": "PLAN-SO-1", "source_order_id": "SO-HT-1", "source_purchase_id": None,
                 "direction": "receivable", "due_date": date(2024, 9, 1), "planned_amount": "100.0000", "settled_amount": "40.0000",
                 "currency": "USD", "lifecycle_state": "open", "settlement_detail_complete": "yes", "truth_status": truth_value,
                 "voucher_reference": "synthetic://receivable-plan", "notes": "preserve source plan"},
                {"group_id": group_id, "source_plan_id": "PLAN-PO-1", "source_order_id": None, "source_purchase_id": "PO-HT-1",
                 "direction": "payable", "due_date": date(2024, 9, 2), "planned_amount": "15.0000", "settled_amount": "5.0000",
                 "currency": "USD", "lifecycle_state": "open", "settlement_detail_complete": "yes", "truth_status": truth_value,
                 "voucher_reference": "synthetic://payable-plan", "notes": "preserve source plan"},
            ],
            "收付款流水": [
                {"group_id": group_id, "source_record_id": "TX-SO-1", "transaction_no": "HIST-TX-SO-1", "transaction_date": date(2024, 9, 3),
                 "direction": "income", "kind": "customer_receipt", "amount": "40.0000", "currency": "USD", "exchange_rate": "1.000000",
                 "source_status": "confirmed", "customer_code": self.customer.code, "supplier_code": None, "source_order_id": "SO-HT-1",
                 "source_purchase_id": None, "source_plan_id": "PLAN-SO-1", "truth_status": truth_value,
                 "voucher_reference": "synthetic://bank/receipt", "notes": "source-only payment"},
                {"group_id": group_id, "source_record_id": "TX-PO-1", "transaction_no": "HIST-TX-PO-1", "transaction_date": date(2024, 9, 4),
                 "direction": "expense", "kind": "supplier_payment", "amount": "5.0000", "currency": "USD", "exchange_rate": "1.000000",
                 "source_status": "confirmed", "customer_code": None, "supplier_code": self.supplier.code, "source_order_id": None,
                 "source_purchase_id": "PO-HT-1", "source_plan_id": "PLAN-PO-1", "truth_status": truth_value,
                 "voucher_reference": "synthetic://bank/payment", "notes": "source-only payment"},
            ],
            "履约记录": [
                {"group_id": group_id, "source_event_id": "SHIP-HT-1", "event_type": "shipment", "parent_source_id": "SO-HT-1",
                 "source_line_id": "1", "event_date": date(2024, 8, 10), "sku_code": self.sku.sku,
                 "sku_name_snapshot": "Historical SKU Name", "unit_snapshot": "pcs", "base_unit_snapshot": "pcs",
                 "quantity_base": "4.00", "trade_quantity": None, "trade_unit_snapshot": None,
                 "lifecycle_state": "effective", "truth_status": truth_value, "voucher_reference": "synthetic://shipment", "notes": "source only"},
                {"group_id": group_id, "source_event_id": "GR-HT-1", "event_type": "goods_receipt", "parent_source_id": "PO-HT-1",
                 "source_line_id": "1", "event_date": date(2024, 7, 5), "sku_code": self.sku.sku,
                 "sku_name_snapshot": "Historical Purchase SKU", "unit_snapshot": "pcs", "base_unit_snapshot": "pcs",
                 "quantity_base": "2.00", "trade_quantity": None, "trade_unit_snapshot": None,
                 "lifecycle_state": "effective", "truth_status": truth_value, "voucher_reference": "synthetic://goods-receipt", "notes": "source only"},
            ],
            "库存盘点": [{
                "group_id": group_id, "source_record_id": "COUNT-HT-1", "count_date": date(2024, 12, 30),
                "warehouse_type": "自有仓", "warehouse": "SYN-WH-01", "lot_reference": "LOT-HT-01",
                "sku_code": self.sku.sku, "sku_name_snapshot": "Counted historical SKU", "unit_snapshot": "pcs",
                "counted_quantity": "18.00", "coverage_complete": "yes", "truth_status": truth_value,
                "voucher_reference": "synthetic://stocktake/HT-1", "notes": "baseline; do not post movement",
            }],
        }

    def workbook_bytes(self, rows=None):
        workbook = Workbook()
        instructions = workbook.active
        instructions.title = "使用说明"
        instructions.append(["HISTORY-TAKEOVER-BATCH-01 synthetic workbook"])
        instructions.append(["模拟验收资料；正式资金、库存及履约不会写入。"])
        for sheet_name, schema in SHEET_SCHEMAS.items():
            sheet = workbook.create_sheet(sheet_name)
            sheet.append([column["label"] for column in schema])
            for record in (rows or {}).get(sheet_name, []):
                sheet.append([record.get(column["key"]) for column in schema])
        output = io.BytesIO()
        workbook.save(output)
        workbook.close()
        return output.getvalue()

    def upload_application(self, rows=None, *, filename="synthetic-history.xlsx"):
        from django.core.files.uploadedfile import SimpleUploadedFile

        return self.client.post(
            "/api/import/history-takeovers/",
            {"file": SimpleUploadedFile(filename, self.workbook_bytes(rows or self.source_rows()), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            format="multipart",
        )

    def application_and_group(self, rows=None):
        rows = rows or self.source_rows()
        group_id = rows["分组"][0]["group_id"]
        response = self.upload_application(rows)
        self.assertIn(response.status_code, (200, 201), response.data)
        application = HistoryTakeoverApplication.objects.get(pk=response.data["id"])
        group = application.groups.get(source_group_id=group_id)
        return application, group, response


@override_settings(AUDIT_LOG_ENABLED=True)
class HistoryTakeoverWorkflowTests(HistoryTakeoverFixtureMixin, TestCase):
    def review_and_execute(self, application, group):
        review = self.client.post(
            f"/api/import/history-takeovers/{application.pk}/groups/{group.pk}/review/",
            {"decision": "approve", "note": "Synthetic source documents and dependencies verified for isolated acceptance.", "confirm_manual": True},
            format="json",
        )
        self.assertEqual(review.status_code, 200, review.data)
        return self.client.post(f"/api/import/history-takeovers/{application.pk}/groups/{group.pk}/execute/", {}, format="json")

    def test_downloaded_template_matches_parser_and_requires_warehouse_origin_and_lot(self):
        response = self.client.get("/api/import/history-takeovers/template/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("spreadsheetml", response["Content-Type"])
        workbook = load_workbook(io.BytesIO(response.content), read_only=True, data_only=False)
        try:
            self.assertEqual(workbook.sheetnames, ["使用说明", *SHEET_SCHEMAS.keys()])
            headers = list(next(workbook["库存盘点"].iter_rows(min_row=1, max_row=1, values_only=True)))
            self.assertIn("仓库归属", headers)
            self.assertIn("适用批次/货位", headers)
            sales_headers = list(next(workbook["销售明细"].iter_rows(min_row=1, max_row=1, values_only=True)))
            purchase_headers = list(next(workbook["采购订单"].iter_rows(min_row=1, max_row=1, values_only=True)))
            self.assertIn("历史产品主分类快照", sales_headers)
            self.assertIn("历史供应商国家/地区快照", purchase_headers)
            instructions = [row[0] for row in workbook["使用说明"].iter_rows(min_row=1, max_row=5, values_only=True)]
            self.assertTrue(any("不从当前主档回填" in str(value) for value in instructions))
        finally:
            workbook.close()

    def test_existing_document_conflict_blocks_approval_without_creating_a_duplicate(self):
        Order.objects.create(order_no="HIST-SO-HT-1", customer=self.customer, order_date=date(2024, 8, 1))
        application, group, _ = self.application_and_group()
        self.assertEqual(group.status, "blocked")
        approval = self.client.post(
            f"/api/import/history-takeovers/{application.pk}/groups/{group.pk}/review/",
            {"decision": "approve", "note": "Attempt to accept duplicate synthetic order."}, format="json",
        )
        self.assertEqual(approval.status_code, 400)
        self.assertEqual(Order.objects.filter(order_no="HIST-SO-HT-1").count(), 1)

    def test_name_candidate_requires_explicit_admin_mapping_and_preserves_source_value(self):
        rows = self.source_rows(group_id="HT-G-MAP", source_system="Synthetic mapping system")
        rows["销售订单"][0]["customer_code"] = ""
        rows["销售订单"][0]["customer_name_snapshot"] = self.customer.name
        rows["销售订单"][0]["order_no"] = "HIST-SO-HT-MAP"
        rows["采购订单"][0]["purchase_no"] = "HIST-PO-HT-MAP"
        application, group, _ = self.application_and_group(rows)
        approval_without_mapping = self.client.post(
            f"/api/import/history-takeovers/{application.pk}/groups/{group.pk}/review/",
            {"decision": "approve", "note": "A unique name candidate is not enough.", "confirm_manual": True}, format="json",
        )
        self.assertEqual(approval_without_mapping.status_code, 400)
        resolution = self.client.post(
            f"/api/import/history-takeovers/{application.pk}/groups/{group.pk}/resolve-master/",
            {"sheet": "销售订单", "row": 2, "field": "customer_code", "target_code": self.customer.code,
             "note": "Checked the source contract and the existing customer master."}, format="json",
        )
        self.assertEqual(resolution.status_code, 200, resolution.data)
        execution = self.review_and_execute(application, group)
        self.assertEqual(execution.status_code, 200, execution.data)
        source = HistoryTakeoverSourceRecord.objects.get(group=group, record_type="销售订单")
        self.assertEqual(source.source_snapshot["source"]["customer_code"], "")
        self.assertEqual(source.source_snapshot["resolved"]["customer_code"], self.customer.code)
        self.assertEqual(Order.objects.get(order_no="HIST-SO-HT-MAP").customer_id, self.customer.id)

    def test_cancelled_and_completed_lifecycle_states_are_preserved_without_replaying_fulfillment(self):
        cancelled = self.source_rows(group_id="HT-G-CANCEL", order_state="cancelled", supplier_order_state="cancelled")
        cancelled["履约记录"] = []
        app_cancel, group_cancel, _ = self.application_and_group(cancelled)
        result_cancel = self.review_and_execute(app_cancel, group_cancel)
        self.assertEqual(result_cancel.status_code, 200, result_cancel.data)
        group_cancel.refresh_from_db()
        self.assertEqual(group_cancel.remainder_snapshot["sales_orders"][0]["lines"][0]["remaining_quantity_base"], "0")
        self.assertEqual(group_cancel.remainder_snapshot["purchase_orders"][0]["lines"][0]["remaining_quantity_base"], "0")
        self.assertEqual(Shipment.objects.count(), 0)
        self.assertEqual(GoodsReceipt.objects.count(), 0)

        cancelled_events = self.source_rows(group_id="HT-G-CANCELLED-EVENTS")
        cancelled_events["分组"][0]["source_system"] = "Synthetic cancelled-event system"
        cancelled_events["销售订单"][0]["order_no"] = "HIST-SO-HT-CANCELLED-EVENTS"
        cancelled_events["采购订单"][0]["purchase_no"] = "HIST-PO-HT-CANCELLED-EVENTS"
        shipment_cancel = dict(cancelled_events["履约记录"][0])
        shipment_cancel.update(source_event_id="SHIP-HT-CANCELLED", quantity_base="6.00", lifecycle_state="cancelled")
        receipt_cancel = dict(cancelled_events["履约记录"][1])
        receipt_cancel.update(source_event_id="GR-HT-CANCELLED", quantity_base="3.00", lifecycle_state="cancelled")
        cancelled_events["履约记录"].extend([shipment_cancel, receipt_cancel])
        app_events, group_events, _ = self.application_and_group(cancelled_events)
        result_events = self.review_and_execute(app_events, group_events)
        self.assertEqual(result_events.status_code, 200, result_events.data)
        group_events.refresh_from_db()
        self.assertEqual(group_events.remainder_snapshot["sales_orders"][0]["lines"][0]["verified_net_fulfilled_quantity_base"], "4.00")
        self.assertEqual(group_events.remainder_snapshot["sales_orders"][0]["lines"][0]["remaining_quantity_base"], "6.00")
        self.assertEqual(group_events.remainder_snapshot["purchase_orders"][0]["lines"][0]["verified_net_fulfilled_quantity_base"], "2.00")
        self.assertEqual(group_events.remainder_snapshot["purchase_orders"][0]["lines"][0]["remaining_quantity_base"], "3.00")

        completed = self.source_rows(group_id="HT-G-DONE", order_state="completed", supplier_order_state="completed")
        completed["分组"][0]["source_system"] = "Synthetic completed system"
        completed["销售订单"][0]["order_no"] = "HIST-SO-HT-DONE"
        completed["采购订单"][0]["purchase_no"] = "HIST-PO-HT-DONE"
        completed["履约记录"][0]["quantity_base"] = "10.00"
        completed["履约记录"][1]["quantity_base"] = "5.00"
        app_done, group_done, _ = self.application_and_group(completed)
        result_done = self.review_and_execute(app_done, group_done)
        self.assertEqual(result_done.status_code, 200, result_done.data)
        group_done.refresh_from_db()
        self.assertEqual(group_done.remainder_snapshot["sales_orders"][0]["lines"][0]["remaining_quantity_base"], "0")
        self.assertEqual(group_done.remainder_snapshot["purchase_orders"][0]["lines"][0]["remaining_quantity_base"], "0")
        self.assertEqual(Shipment.objects.count(), 0)
        self.assertEqual(GoodsReceipt.objects.count(), 0)

    def test_complete_synthetic_group_executes_once_without_posting_finance_stock_or_fulfillment(self):
        core_counts_before = {
            "orders": Order.objects.count(), "order_items": OrderItem.objects.count(),
            "purchase_orders": PurchaseOrder.objects.count(), "purchase_items": PurchaseOrderItem.objects.count(),
            "plans": PaymentPlan.objects.count(), "transactions": Transaction.objects.count(),
            "inventory": InventoryMovement.objects.count(), "reservations": InventoryReservation.objects.count(),
            "shipments": Shipment.objects.count(), "receipts": GoodsReceipt.objects.count(),
            "cost_allocations": PurchaseCostAllocation.objects.count(), "logs": OperationLog.objects.count(),
        }
        application, group, submitted = self.application_and_group()
        self.assertFalse(submitted.data["approval_or_migration"])
        self.assertEqual(group.status, "pending")
        self.assertEqual(application.created_actor_kind, "development")
        self.assertIsNone(application.created_by)

        executed = self.review_and_execute(application, group)

        self.assertEqual(executed.status_code, 200, executed.data)
        group.refresh_from_db()
        self.assertEqual(group.status, "executed")
        self.assertEqual(group.finance_handoff_status, "not_connected")
        self.assertEqual(group.inventory_handoff_status, "not_connected")
        self.assertEqual(group.fulfillment_handoff_status, "not_connected")
        self.assertEqual(group.remainder_snapshot["sales_orders"][0]["lines"][0]["remaining_quantity_base"], "6.00")
        self.assertEqual(group.remainder_snapshot["purchase_orders"][0]["lines"][0]["remaining_quantity_base"], "3.00")

        sales = Order.objects.get(order_no="HIST-SO-HT-1")
        purchase = PurchaseOrder.objects.get(purchase_no="HIST-PO-HT-1")
        self.assertTrue(sales.historical_only)
        self.assertTrue(purchase.historical_only)
        self.assertEqual(sales.status, "historical")
        self.assertEqual(purchase.status, "historical")
        self.assertEqual(sales.customer_name_snapshot, "Historical Customer Name")
        self.assertEqual(purchase.supplier_name_snapshot, "Historical Supplier Name")
        self.assertEqual(sales.items.get().sales_model_snapshot, "OLD-MODEL-1")
        self.assertEqual(purchase.items.get().supplier_model_snapshot, "SUP-MODEL")
        self.assertFalse(purchase.items.get().cost_allocations.exists())
        self.assertEqual(sales.paid_amount, Decimal("0"))
        self.assertEqual(sales.outstanding_amount, Decimal("0"))
        self.assertEqual(purchase.paid_amount, Decimal("0"))
        self.assertEqual(purchase.unpaid_amount, Decimal("0"))

        handoffs = {item.kind: item for item in HistoryTakeoverHandoff.objects.filter(group=group)}
        self.assertEqual(set(handoffs), {"finance", "inventory", "fulfillment"})
        self.assertEqual(handoffs["finance"].payload["status"], "not_connected")
        self.assertEqual(len(handoffs["finance"].payload["source_transactions"]), 2)
        self.assertEqual(handoffs["inventory"].payload["count_baselines"][0]["warehouse_type"], "自有仓")
        self.assertEqual(handoffs["inventory"].payload["count_baselines"][0]["lot_reference"], "LOT-HT-01")
        self.assertEqual(len(handoffs["fulfillment"].payload["source_events"]), 2)

        after = {
            "orders": Order.objects.count(), "order_items": OrderItem.objects.count(),
            "purchase_orders": PurchaseOrder.objects.count(), "purchase_items": PurchaseOrderItem.objects.count(),
            "plans": PaymentPlan.objects.count(), "transactions": Transaction.objects.count(),
            "inventory": InventoryMovement.objects.count(), "reservations": InventoryReservation.objects.count(),
            "shipments": Shipment.objects.count(), "receipts": GoodsReceipt.objects.count(),
            "cost_allocations": PurchaseCostAllocation.objects.count(), "logs": OperationLog.objects.count(),
        }
        self.assertEqual(after["orders"], core_counts_before["orders"] + 1)
        self.assertEqual(after["order_items"], core_counts_before["order_items"] + 1)
        self.assertEqual(after["purchase_orders"], core_counts_before["purchase_orders"] + 1)
        self.assertEqual(after["purchase_items"], core_counts_before["purchase_items"] + 1)
        for key in ("plans", "transactions", "inventory", "reservations", "shipments", "receipts", "cost_allocations", "logs"):
            self.assertEqual(after[key], core_counts_before[key], key)

        event_count = HistoryTakeoverEvent.objects.filter(group=group).count()
        replay = self.client.post(f"/api/import/history-takeovers/{application.pk}/groups/{group.pk}/execute/", {}, format="json")
        self.assertEqual(replay.status_code, 200, replay.data)
        self.assertTrue(replay.data["idempotent_replay"])
        self.assertEqual(Order.objects.count(), after["orders"])
        self.assertEqual(PurchaseOrder.objects.count(), after["purchase_orders"])
        self.assertEqual(HistoryTakeoverSourceRecord.objects.filter(group=group).count(), submitted.data["preflight_summary"]["total_rows"])
        self.assertEqual(HistoryTakeoverEvent.objects.filter(group=group).count(), event_count)

        self.assertEqual(self.client.patch(f"/api/orders/{sales.pk}/", {"notes": "overwrite"}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(f"/api/purchase-orders/{purchase.pk}/", {"notes": "overwrite"}, format="json").status_code, 400)

    def test_rejection_missing_dependencies_conflicts_and_simulated_data_never_execute(self):
        application, group, _ = self.application_and_group()
        rejected = self.client.post(
            f"/api/import/history-takeovers/{application.pk}/groups/{group.pk}/review/",
            {"decision": "reject", "note": "Synthetic evidence rejected for test."}, format="json",
        )
        self.assertEqual(rejected.status_code, 200, rejected.data)
        self.assertEqual(self.client.post(f"/api/import/history-takeovers/{application.pk}/groups/{group.pk}/execute/", {}, format="json").status_code, 400)
        self.assertEqual(Order.objects.count(), 0)

        missing = self.source_rows()
        missing["销售明细"][0]["source_order_id"] = "SO-MISSING"
        app_missing, group_missing, _ = self.application_and_group(missing)
        self.assertEqual(group_missing.status, "blocked")
        refused = self.client.post(
            f"/api/import/history-takeovers/{app_missing.pk}/groups/{group_missing.pk}/review/",
            {"decision": "approve", "note": "Attempt blocked group."}, format="json",
        )
        self.assertEqual(refused.status_code, 400)

        simulated = self.source_rows(group_id="HT-G-SIM", truth="模拟")
        app_sim, group_sim, _ = self.application_and_group(simulated)
        approval = self.client.post(
            f"/api/import/history-takeovers/{app_sim.pk}/groups/{group_sim.pk}/review/",
            {"decision": "approve", "note": "Synthetic simulated data must remain staging."}, format="json",
        )
        self.assertEqual(approval.status_code, 400)
        self.assertEqual(PaymentPlan.objects.count(), 0)
        self.assertEqual(Transaction.objects.count(), 0)
        self.assertEqual(InventoryMovement.objects.count(), 0)

    def test_master_change_between_approval_and_execution_requires_reapproval(self):
        application, group, _ = self.application_and_group()
        approval = self.client.post(
            f"/api/import/history-takeovers/{application.pk}/groups/{group.pk}/review/",
            {"decision": "approve", "note": "Verified source and master association.", "confirm_manual": True}, format="json",
        )
        self.assertEqual(approval.status_code, 200, approval.data)
        self.customer.name = "Changed after approval"
        self.customer.save()
        execute = self.client.post(f"/api/import/history-takeovers/{application.pk}/groups/{group.pk}/execute/", {}, format="json")
        self.assertEqual(execute.status_code, 200, execute.data)
        group.refresh_from_db()
        self.assertEqual(group.status, "needs_reapproval")
        self.assertFalse(Order.objects.filter(order_no="HIST-SO-HT-1").exists())
        self.assertFalse(PurchaseOrder.objects.filter(purchase_no="HIST-PO-HT-1").exists())

    def test_failure_in_later_business_write_rolls_back_the_whole_group(self):
        application, group, _ = self.application_and_group()
        approved = self.client.post(
            f"/api/import/history-takeovers/{application.pk}/groups/{group.pk}/review/",
            {"decision": "approve", "note": "Synthetic full dependency verification.", "confirm_manual": True}, format="json",
        )
        self.assertEqual(approved.status_code, 200, approved.data)
        before = {
            "orders": Order.objects.count(), "purchase_orders": PurchaseOrder.objects.count(),
            "sources": HistoryTakeoverSourceRecord.objects.count(), "handoffs": HistoryTakeoverHandoff.objects.count(),
            "events": HistoryTakeoverEvent.objects.count(),
        }
        with patch("crm.history_takeover.PurchaseOrderItem.objects.bulk_create", side_effect=RuntimeError("synthetic failure")):
            with self.assertRaises(RuntimeError):
                execute_group(group, self.admin)
        self.assertEqual(Order.objects.count(), before["orders"])
        self.assertEqual(PurchaseOrder.objects.count(), before["purchase_orders"])
        self.assertEqual(HistoryTakeoverSourceRecord.objects.count(), before["sources"])
        self.assertEqual(HistoryTakeoverHandoff.objects.count(), before["handoffs"])
        self.assertEqual(HistoryTakeoverEvent.objects.count(), before["events"])
        group.refresh_from_db()
        self.assertEqual(group.status, "approved")

    def test_late_fact_and_voucher_review_append_without_overwriting_history(self):
        application, group, _ = self.application_and_group()
        result = self.review_and_execute(application, group)
        self.assertEqual(result.status_code, 200, result.data)
        group.refresh_from_db()
        before = group.source_rows
        transaction_count = Transaction.objects.count()
        late = self.client.post(
            f"/api/import/history-takeovers/{application.pk}/groups/{group.pk}/correction/",
            {"kind": "late_fact", "occurred_at": "2024-08-12", "reason": "Synthetic late shipment document.",
             "details": {"source_record_id": "LATE-SHIP-1", "source_document_no": "SHIP-1",
                         "description": "补录发货 1 件", "voucher_reference": "VCH-LATE-1"}}, format="json",
        )
        self.assertEqual(late.status_code, 200, late.data)
        event = HistoryTakeoverEvent.objects.get(group=group, event_type="late_fact_submitted")
        self.assertTrue(event.details["period_reclassification_review_required"])
        note = "Reviewed synthetic source voucher and retained original event trail."
        verified = self.client.post(
            f"/api/import/history-takeovers/{application.pk}/groups/{group.pk}/correction-review/",
            {"event_id": event.pk, "decision": "approve", "note": note}, format="json",
        )
        self.assertEqual(verified.status_code, 200, verified.data)
        group.refresh_from_db()
        self.assertIn(event.pk, group.verified_correction_ids)
        duplicate_review = self.client.post(
            f"/api/import/history-takeovers/{application.pk}/groups/{group.pk}/correction-review/",
            {"event_id": event.pk, "decision": "reject", "note": "Conflicting second decision."}, format="json",
        )
        self.assertEqual(duplicate_review.status_code, 400, duplicate_review.data)
        group.refresh_from_db()
        self.assertIn(event.pk, group.verified_correction_ids)
        self.assertEqual(group.source_rows, before)
        event.refresh_from_db()
        self.assertEqual(event.details["details"], {
            "source_record_id": "LATE-SHIP-1", "source_document_no": "SHIP-1",
            "description": "补录发货 1 件", "voucher_reference": "VCH-LATE-1",
        })
        audit = group.events.get(event_type="correction_reviewed")
        self.assertEqual(audit.details["source_event_id"], event.pk)
        self.assertEqual(Transaction.objects.count(), transaction_count)
        self.assertEqual(Order.objects.get(order_no="HIST-SO-HT-1").items.get().quantity, Decimal("10.00"))
        self.assertEqual(InventoryMovement.objects.count(), 0)

    def test_audit_events_are_database_append_only_and_development_identity_is_not_real_operator(self):
        application, group, _ = self.application_and_group()
        event = HistoryTakeoverEvent.objects.filter(application=application).first()
        self.assertEqual(event.actor_kind, "development")
        self.assertIsNone(event.actor_id)
        with self.assertRaises(DatabaseError), transaction.atomic():
            HistoryTakeoverEvent.objects.filter(pk=event.pk).update(event_type="rewritten")
        with self.assertRaises(DatabaseError), transaction.atomic():
            HistoryTakeoverEvent.objects.filter(pk=event.pk).delete()
        self.assertTrue(HistoryTakeoverEvent.objects.filter(pk=event.pk, event_type="group_submitted").exists())

    def test_terminal_groups_cannot_be_revived_and_group_action_returns_the_requested_group(self):
        application, first_group, _ = self.application_and_group()
        second_source_rows = copy.deepcopy(first_group.source_rows)
        for records in second_source_rows.values():
            for item in records:
                item["data"]["group_id"] = "HT-G-SECOND"
        second_group = HistoryTakeoverGroup.objects.create(
            application=application, source_group_id="HT-G-SECOND", source_system="Synthetic second group",
            coverage_status="complete", truth_status="真实", status="pending", source_rows=second_source_rows, preflight_result={},
        )
        reject_second = self.client.post(
            f"/api/import/history-takeovers/{application.pk}/groups/{second_group.pk}/review/",
            {"decision": "reject", "note": "Synthetic rejection."}, format="json",
        )
        self.assertEqual(reject_second.status_code, 200, reject_second.data)
        self.assertEqual(reject_second.data["group"]["id"], second_group.pk)

        withdrawn_app, withdrawn_group, _ = self.application_and_group(self.source_rows(group_id="HT-G-WITHDRAWN"))
        withdrawal = self.client.post(
            f"/api/import/history-takeovers/{withdrawn_app.pk}/groups/{withdrawn_group.pk}/withdraw/",
            {"reason": "Synthetic applicant withdrawal."}, format="json",
        )
        self.assertEqual(withdrawal.status_code, 200, withdrawal.data)
        self.assertEqual(withdrawal.data["group"]["id"], withdrawn_group.pk)
        withdrawn_app.refresh_from_db()
        self.assertEqual(withdrawn_app.status, "withdrawn")
        for operation, payload in (
            ("review", {"decision": "approve", "note": "Attempt to revive withdrawn group.", "confirm_manual": True}),
            ("resolve-master", {"sheet": "销售订单", "row": 2, "field": "customer_code", "target_code": self.customer.code, "note": "Attempt to remap withdrawn group."}),
        ):
            response = self.client.post(
                f"/api/import/history-takeovers/{withdrawn_app.pk}/groups/{withdrawn_group.pk}/{operation}/",
                payload, format="json",
            )
            self.assertEqual(response.status_code, 400, response.data)
        withdrawn_group.refresh_from_db()
        self.assertEqual(withdrawn_group.status, "withdrawn")

        rejected_app, rejected_group, _ = self.application_and_group(self.source_rows(group_id="HT-G-REJECTED"))
        reject = self.client.post(
            f"/api/import/history-takeovers/{rejected_app.pk}/groups/{rejected_group.pk}/review/",
            {"decision": "reject", "note": "Synthetic rejection."}, format="json",
        )
        self.assertEqual(reject.status_code, 200, reject.data)
        for operation, payload in (
            ("resolve-master", {"sheet": "销售订单", "row": 2, "field": "customer_code", "target_code": self.customer.code, "note": "Attempt to remap rejected group."}),
            ("review", {"decision": "approve", "note": "Attempt to revive rejected group.", "confirm_manual": True}),
        ):
            response = self.client.post(
                f"/api/import/history-takeovers/{rejected_app.pk}/groups/{rejected_group.pk}/{operation}/",
                payload, format="json",
            )
            self.assertEqual(response.status_code, 400, response.data)

    def test_non_admin_application_access_is_scoped_to_applicant(self):
        employee = get_user_model().objects.create_user(username="takeover-employee")
        own = HistoryTakeoverApplication.objects.create(
            source_file_name="own.xlsx", source_sha256="a" * 64,
            created_by=employee, created_by_label="Employee",
        )
        other = HistoryTakeoverApplication.objects.create(
            source_file_name="other.xlsx", source_sha256="b" * 64,
            created_by=self.admin, created_by_label="Administrator",
        )
        self.client.force_authenticate(employee)
        permissions = patch("crm.history_takeover_api.HistoryTakeoverPermission.has_permission", return_value=True)
        not_admin = patch("crm.history_takeover_api._admin_required", return_value=False)
        with permissions, not_admin:
            listing = self.client.get("/api/import/history-takeovers/")
            self.assertEqual(listing.status_code, 200)
            self.assertEqual([item["id"] for item in listing.data["results"]], [own.pk])
            self.assertEqual(self.client.get(f"/api/import/history-takeovers/{own.pk}/").status_code, 200)
            self.assertEqual(self.client.get(f"/api/import/history-takeovers/{other.pk}/").status_code, 404)
            self.assertEqual(self.client.get(f"/api/import/history-takeovers/{other.pk}/review-report.csv").status_code, 404)

            from django.core.files.uploadedfile import SimpleUploadedFile

            with patch("crm.history_takeover_api._read_bounded_upload", return_value=b"synthetic"), patch(
                "crm.history_takeover_api.submit_workbook", return_value=(other, {"summary": {}}, True)
            ):
                duplicate = self.client.post(
                    "/api/import/history-takeovers/",
                    {"file": SimpleUploadedFile("other.xlsx", b"synthetic")}, format="multipart",
                )
            self.assertEqual(duplicate.status_code, 409)
            self.assertNotIn("groups", duplicate.data)

    @override_settings(APP_STAGE="production", DEBUG=False, DEVELOPMENT_SUPERADMIN=False, RBAC_ENFORCEMENT=True)
    def test_restricted_employee_cannot_open_takeover_endpoints(self):
        self.client.force_authenticate(get_user_model().objects.create_user(username="takeover-restricted"))
        response = self.client.get("/api/import/history-takeovers/")
        self.assertEqual(response.status_code, 403)


class HistoryTakeoverPostgresConcurrencyTests(HistoryTakeoverFixtureMixin, TransactionTestCase):
    reset_sequences = True

    @override_settings(FILE_UPLOAD_MAX_MEMORY_SIZE=1024 * 1024, FILE_UPLOAD_TEMP_DIR=None)
    def test_postgres_concurrent_execute_is_serialized_by_group_lock(self):
        if connection.vendor != "postgresql":
            self.skipTest("Requires PostgreSQL row locks; SQLite is not evidence of concurrent execution safety.")
        application, group, _ = self.application_and_group()
        approval = self.client.post(
            f"/api/import/history-takeovers/{application.pk}/groups/{group.pk}/review/",
            {"decision": "approve", "note": "PostgreSQL concurrency fixture approval.", "confirm_manual": True}, format="json",
        )
        self.assertEqual(approval.status_code, 200, approval.data)
        gate = Barrier(2)

        def run_execution():
            close_old_connections()
            try:
                gate.wait(timeout=15)
                current = HistoryTakeoverGroup.objects.get(pk=group.pk)
                actor = get_user_model().objects.get(pk=self.admin.pk)
                _result, replay = execute_group(current, actor)
                return replay
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            replayed = list(pool.map(lambda _index: run_execution(), range(2)))
        group.refresh_from_db()
        self.assertEqual(group.status, "executed")
        self.assertEqual(Order.objects.filter(order_no="HIST-SO-HT-1").count(), 1)
        self.assertEqual(PurchaseOrder.objects.filter(purchase_no="HIST-PO-HT-1").count(), 1)
        self.assertEqual(group.handoffs.count(), 3)
        self.assertEqual(replayed.count(True), 1)
