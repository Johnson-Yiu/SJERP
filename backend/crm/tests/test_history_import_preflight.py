import io
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from openpyxl import Workbook, load_workbook
from rest_framework.test import APIClient

from crm.history_import_preflight import HISTORY_V1_SCHEMAS, HistoryPreflightPermission, SHEET_SCHEMAS
from crm.models import (
    CSVImportBatch,
    CSVImportPreviewAudit,
    CSVImportRowAudit,
    Customer,
    GoodsReceipt,
    InventoryMovement,
    InventoryReservation,
    OperationLog,
    Order,
    OrderItem,
    PaymentPlan,
    Product,
    ProductCategory,
    PurchaseOrder,
    PurchaseOrderItem,
    Shipment,
    ShipmentItem,
    SKU,
    SKUTradeUnit,
    Supplier,
    Transaction,
)


BUSINESS_MODELS = (
    Customer, Supplier, Product, SKU, Order, OrderItem, PurchaseOrder,
    PurchaseOrderItem, PaymentPlan, Transaction, GoodsReceipt, Shipment, SKUTradeUnit,
    ShipmentItem, InventoryMovement, InventoryReservation, OperationLog,
    CSVImportBatch, CSVImportPreviewAudit, CSVImportRowAudit,
)


@override_settings(AUDIT_LOG_ENABLED=True)
class HistoryImportPreflightTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.operator = get_user_model().objects.create_superuser(
            username="iss121-preflight-admin",
            email="iss121-preflight@example.test",
            password="local-test-only",
        )
        self.client.force_authenticate(self.operator)
        self.media = tempfile.TemporaryDirectory(prefix="iss121-preflight-media-")
        self.addCleanup(self.media.cleanup)
        self.media_settings = override_settings(MEDIA_ROOT=self.media.name)
        self.media_settings.enable()
        self.addCleanup(self.media_settings.disable)

    def create_masters(self):
        customer = Customer.objects.create(
            code="ISS121-C1", name="合成历史客户", country="US", address="Synthetic address",
        )
        supplier = Supplier.objects.create(code="S1", name="合成历史供应商")
        category = ProductCategory.objects.create(name="合成历史分类")
        product = Product.objects.create(code="ISS121-P1", name="合成历史产品", sales_model_prefix="I121", category=category)
        sku = SKU.objects.create(
            sku="ISS121-S1", product=product, display_name_cn="合成历史 SKU", unit="pcs",
        )
        return customer, supplier, sku

    def business_snapshot(self):
        counts = {model.__name__: model.objects.count() for model in BUSINESS_MODELS}
        customer = Customer.objects.order_by("pk").values("id", "code", "name", "country", "address").first()
        sku = SKU.objects.order_by("pk").values("id", "sku", "unit", "cost_price").first()
        orders = list(Order.objects.order_by("pk").values("id", "order_no", "status", "currency", "customer_country_snapshot"))
        order_items = list(OrderItem.objects.order_by("pk").values("id", "quantity", "product_category_reference_snapshot", "product_category_name_snapshot"))
        purchases = list(PurchaseOrder.objects.order_by("pk").values("id", "purchase_no", "supplier_country_snapshot"))
        purchase_items = list(PurchaseOrderItem.objects.order_by("pk").values("id", "quantity", "product_category_reference_snapshot", "product_category_name_snapshot"))
        plans = list(PaymentPlan.objects.order_by("pk").values("id", "planned_amount", "settled_amount", "status"))
        transactions = list(Transaction.objects.order_by("pk").values("id", "amount", "status", "kind"))
        movements = list(InventoryMovement.objects.order_by("pk").values("id", "sku_id", "quantity", "type"))
        return counts, customer, sku, orders, order_items, purchases, purchase_items, plans, transactions, movements

    def group_row(self, group_id="G-1", **overrides):
        return {
            "group_id": group_id,
            "source_system": "Synthetic legacy export",
            "exported_at": date(2025, 1, 2),
            "coverage_status": "complete",
            "truth_status": "真实",
            "evidence_reference": "synthetic://source-manifest",
            **overrides,
        }

    def sales_order_row(self, customer, *, group_id="G-1", source_id="SO-SRC-1", order_no="OLD-SO-1", state="open", **overrides):
        return {
            "group_id": group_id,
            "source_record_id": source_id,
            "order_no": order_no,
            "order_date": date(2024, 8, 1),
            "lifecycle_state": state,
            "customer_code": customer.code,
            "customer_name_snapshot": customer.name,
            "customer_country_snapshot": "United States",
            "customer_address_snapshot": "Historical address",
            "customer_contact_name_snapshot": "Historical contact",
            "customer_phone_snapshot": "555-0101",
            "customer_email_snapshot": "history@example.test",
            "currency": "USD",
            "exchange_rate": "1.000000",
            "shipping_fee": "0.0000",
            "discount": "0.0000",
            "truth_status": "真实",
            "voucher_reference": "synthetic://order-document",
            **overrides,
        }

    def sales_line_row(self, sku, *, group_id="G-1", parent_id="SO-SRC-1", line_id="1", **overrides):
        return {
            "group_id": group_id,
            "source_order_id": parent_id,
            "source_line_id": line_id,
            "sku_code": sku.sku,
            "sku_name_snapshot": sku.display_name_cn,
            # Synthetic fixture evidence is explicit; never derive a historical
            # category from today's product master during preflight testing.
            "product_category_snapshot": "合成历史分类",
            "sales_model_snapshot": "HIST-MODEL",
            "description_snapshot": "Historical description",
            "unit_snapshot": "pcs",
            "base_unit_snapshot": "pcs",
            "quantity_base": "10.00",
            "unit_price": "12.123456789012",
            "trade_quantity": None,
            "trade_unit_snapshot": None,
            "trade_unit_price": None,
            "trade_factor_snapshot": None,
            "allow_fraction_snapshot": None,
            "truth_status": "真实",
            "voucher_reference": "synthetic://order-line",
            **overrides,
        }

    def workbook_bytes(self, rows=None, *, formula_cell=None):
        rows = rows or {}
        workbook = Workbook()
        instructions = workbook.active
        instructions.title = "使用说明"
        instructions.append(["ISS-121 历史数据只读预检模板"])
        instructions.append(["仅预检，不会导入或修改 ERP 业务数据。"])
        for sheet_name, schema in SHEET_SCHEMAS.items():
            sheet = workbook.create_sheet(sheet_name)
            sheet.append([column["label"] for column in schema])
            for record in rows.get(sheet_name, []):
                values = [record.get(column["key"]) for column in schema]
                sheet.append(values)
            if formula_cell and formula_cell[0] == sheet_name:
                _, row_number, column_key, formula = formula_cell
                column_number = next(i for i, column in enumerate(schema, start=1) if column["key"] == column_key)
                sheet.cell(row=row_number, column=column_number, value=formula)
        output = io.BytesIO()
        workbook.save(output)
        workbook.close()
        return output.getvalue()

    def upload(self, data, *, filename="history.xlsx"):
        from django.core.files.uploadedfile import SimpleUploadedFile

        return self.client.post(
            "/api/import/history-preflight/",
            {"file": SimpleUploadedFile(filename, data, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            format="multipart",
        )

    def basic_sales_workbook(self, customer, sku, *, order_overrides=None, line_overrides=None, rows_extra=None):
        rows = {
            "分组": [self.group_row()],
            "销售订单": [self.sales_order_row(customer, **(order_overrides or {}))],
            "销售明细": [self.sales_line_row(sku, **(line_overrides or {}))],
        }
        for sheet_name, records in (rows_extra or {}).items():
            rows.setdefault(sheet_name, []).extend(records)
        return self.workbook_bytes(rows)

    def test_valid_exact_master_preflight_returns_rows_and_changes_no_business_state(self):
        customer, _supplier, sku = self.create_masters()
        data = self.basic_sales_workbook(customer, sku)
        before = self.business_snapshot()

        response = self.upload(data)

        self.assertEqual(response.status_code, 200, getattr(response, "data", response.content))
        self.assertTrue(response.data["preflight_only"])
        self.assertFalse(response.data["approval_or_migration"])
        self.assertFalse(response.data["business_write_performed"])
        line = next(item for item in response.data["results"] if item["sheet"] == "销售明细")
        self.assertEqual(line["status"], "通过", line)
        order = next(item for item in response.data["results"] if item["sheet"] == "销售订单")
        self.assertEqual(order["status"], "警告")
        self.assertTrue(any("未结" in reason["message"] for reason in order["reasons"]))
        self.assertEqual(self.business_snapshot(), before)
        self.assertEqual(list(Path(self.media.name).iterdir()), [])

    def test_delivered_template_headers_match_parser_and_empty_template_is_safely_rejected(self):
        template_path = (
            Path(__file__).resolve().parents[3]
            / "docs/uat-evidence/r1-iss121-history-import-preflight-20261103/ISS-121-history-import-template.xlsx"
        )
        self.assertTrue(template_path.is_file(), template_path)
        data = template_path.read_bytes()
        workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=False)
        try:
            self.assertEqual(workbook.sheetnames, ["使用说明", *SHEET_SCHEMAS.keys()])
            for sheet_name, columns in SHEET_SCHEMAS.items():
                header = next(workbook[sheet_name].iter_rows(min_row=1, max_row=1, values_only=True))
                current = [column["label"] for column in columns]
                v1 = [column["label"] for column in HISTORY_V1_SCHEMAS[sheet_name]]
                legacy_inventory = [column["label"] for column in columns if column["key"] not in {"warehouse_type", "lot_reference"}]
                self.assertIn(list(header), [current, v1, legacy_inventory], sheet_name)
        finally:
            workbook.close()

        current_template = self.client.get("/api/import/history-takeovers/template/")
        self.assertEqual(current_template.status_code, 200, current_template.content[:200])
        self.assertIn('history-takeover-template-v2.xlsx', current_template["Content-Disposition"])
        current_book = load_workbook(io.BytesIO(current_template.content), read_only=True, data_only=False)
        try:
            self.assertEqual(current_book.sheetnames, ["使用说明", *SHEET_SCHEMAS.keys()])
            self.assertIn("历史产品主分类快照", list(next(current_book["销售明细"].iter_rows(min_row=1, max_row=1, values_only=True))))
            self.assertIn("历史供应商国家/地区快照", list(next(current_book["采购订单"].iter_rows(min_row=1, max_row=1, values_only=True))))
        finally:
            current_book.close()

        customer, _supplier, sku = self.create_masters()
        before = self.business_snapshot()
        empty_response = self.upload(data)

        self.assertEqual(empty_response.status_code, 400, empty_response.data)
        self.assertIn("没有可预检的数据行", empty_response.data["detail"])

        sample_rows = {
            "分组": [self.group_row()],
            "销售订单": [self.sales_order_row(customer)],
            "销售明细": [self.sales_line_row(sku)],
        }
        filled = load_workbook(io.BytesIO(data), data_only=False)
        for sheet_name, records in sample_rows.items():
            header = list(next(filled[sheet_name].iter_rows(min_row=1, max_row=1, values_only=True)))
            current_schema = SHEET_SCHEMAS[sheet_name]
            candidates = [current_schema, HISTORY_V1_SCHEMAS[sheet_name]]
            if sheet_name == "库存盘点":
                candidates.append([column for column in current_schema if column["key"] not in {"warehouse_type", "lot_reference"}])
            columns = next(schema for schema in candidates if header == [column["label"] for column in schema])
            for row_number, record in enumerate(records, start=2):
                for column_number, column in enumerate(columns, start=1):
                    filled[sheet_name].cell(row=row_number, column=column_number, value=record.get(column["key"]))
        filled_bytes = io.BytesIO()
        filled.save(filled_bytes)
        filled.close()
        response = self.upload(filled_bytes.getvalue())

        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["preflight_only"])
        # The delivered v1 workbook predates this frozen field. Its missing
        # historical category must remain unknown and require manual review.
        self.assertEqual(response.data["summary"]["overall_status"], "待人工核实")
        self.assertEqual(self.business_snapshot(), before)
        self.assertEqual(list(Path(self.media.name).iterdir()), [])

    def test_missing_historical_category_snapshot_stays_unknown_without_writing(self):
        customer, _supplier, sku = self.create_masters()
        data = self.basic_sales_workbook(customer, sku, line_overrides={"product_category_snapshot": ""})
        before = self.business_snapshot()

        response = self.upload(data)

        self.assertEqual(response.status_code, 200, response.data)
        line = next(item for item in response.data["results"] if item["sheet"] == "销售明细")
        self.assertEqual(line["status"], "待人工核实")
        self.assertTrue(any("历史产品主分类快照缺失" in reason["message"] for reason in line["reasons"]))
        self.assertTrue(any("不要从当前产品分类回填" in action for action in line["suggested_actions"]))
        self.assertEqual(self.business_snapshot(), before)
        self.assertEqual(list(Path(self.media.name).iterdir()), [])

    def test_missing_required_invalid_date_and_decimal_are_reported_by_original_row(self):
        customer, _supplier, sku = self.create_masters()
        data = self.basic_sales_workbook(
            customer,
            sku,
            order_overrides={"order_date": "31/13/2024", "customer_name_snapshot": "", "currency": "usd"},
            line_overrides={"quantity_base": "1.234", "unit_price": "1.1234567890123"},
        )
        before = self.business_snapshot()

        response = self.upload(data)

        self.assertEqual(response.status_code, 200, response.data)
        order = next(item for item in response.data["results"] if item["sheet"] == "销售订单")
        line = next(item for item in response.data["results"] if item["sheet"] == "销售明细")
        self.assertEqual(order["row"], 2)
        self.assertEqual(line["row"], 2)
        self.assertEqual(order["status"], "阻断")
        self.assertEqual(line["status"], "阻断")
        self.assertTrue(any("YYYY-MM-DD" in reason["message"] for reason in order["reasons"]))
        self.assertTrue(any("必填字段" in reason["message"] for reason in order["reasons"]))
        self.assertTrue(any("币种" in reason["message"] for reason in order["reasons"]))
        self.assertTrue(any("位小数" in reason["message"] for reason in line["reasons"]))
        self.assertEqual(self.business_snapshot(), before)

    def test_decimal_integer_digits_cannot_exceed_current_model_precision(self):
        customer, _supplier, sku = self.create_masters()
        data = self.basic_sales_workbook(
            customer,
            sku,
            line_overrides={"unit_price": "1000000000000.000000000000"},
        )

        response = self.upload(data)

        line = next(item for item in response.data["results"] if item["sheet"] == "销售明细")
        self.assertEqual(line["status"], "阻断")
        self.assertTrue(any("整数位数超过模型精度" in reason["message"] for reason in line["reasons"]))

    def test_formula_cells_and_non_xlsx_are_rejected_without_side_effects(self):
        customer, _supplier, sku = self.create_masters()
        rows = {
            "分组": [self.group_row()],
            "销售订单": [self.sales_order_row(customer)],
            "销售明细": [self.sales_line_row(sku)],
        }
        formula_data = self.workbook_bytes(rows, formula_cell=("销售订单", 2, "notes", "=1+1"))
        before = self.business_snapshot()

        formula_response = self.upload(formula_data)
        csv_response = self.upload(b"a,b\n1,2\n", filename="history.csv")

        self.assertEqual(formula_response.status_code, 400, formula_response.data)
        self.assertIn("公式", formula_response.data["detail"])
        self.assertEqual(csv_response.status_code, 400, csv_response.data)
        self.assertIn(".xlsx", csv_response.data["detail"])
        self.assertEqual(self.business_snapshot(), before)

    def test_missing_sku_code_proposes_name_candidate_but_never_auto_links_ambiguous_name(self):
        customer = Customer.objects.create(code="ISS121-C2", name="重名核实客户")
        p1 = Product.objects.create(code="ISS121-P2", name="同名产品", sales_model_prefix="I122")
        p2 = Product.objects.create(code="ISS121-P3", name="同名产品", sales_model_prefix="I123")
        sku1 = SKU.objects.create(sku="ISS121-S2", product=p1, display_name_cn="不同SKU甲", unit="pcs")
        SKU.objects.create(sku="ISS121-S3", product=p2, display_name_cn="不同SKU乙", unit="pcs")
        line = self.sales_line_row(sku1, sku_code="", sku_name_snapshot="同名产品")
        before = self.business_snapshot()

        response = self.upload(self.basic_sales_workbook(customer, sku1, line_overrides=line))

        self.assertEqual(response.status_code, 200, response.data)
        result = next(item for item in response.data["results"] if item["sheet"] == "销售明细")
        self.assertEqual(result["status"], "待人工核实")
        self.assertTrue(any("多个主档" in reason["message"] for reason in result["reasons"]))
        self.assertTrue(all(item.get("match") != "编码精确匹配" for item in result["related_records"]))
        self.assertEqual(self.business_snapshot(), before)

    def test_unmatched_master_is_blocked_and_unique_name_only_customer_is_manual_review(self):
        customer, _supplier, sku = self.create_masters()
        rows = {
            "分组": [self.group_row()],
            "销售订单": [self.sales_order_row(customer, customer_code="", customer_name_snapshot=customer.name)],
            "销售明细": [self.sales_line_row(sku, sku_code="NO-SUCH-SKU", sku_name_snapshot="不存在 SKU")],
        }
        response = self.upload(self.workbook_bytes(rows))
        order = next(item for item in response.data["results"] if item["sheet"] == "销售订单")
        line = next(item for item in response.data["results"] if item["sheet"] == "销售明细")
        self.assertEqual(order["status"], "待人工核实")
        self.assertTrue(any("仅发现一个名称候选" in reason["message"] for reason in order["reasons"]))
        self.assertEqual(line["status"], "阻断")
        self.assertTrue(any("未找到可关联" in reason["message"] for reason in line["reasons"]))

    def test_existing_order_and_duplicate_source_rows_are_reported_not_silently_deduplicated(self):
        customer, _supplier, sku = self.create_masters()
        Order.objects.create(order_no="OLD-SO-1", customer=customer, order_date=date(2024, 8, 1))
        rows = {
            "分组": [self.group_row()],
            "销售订单": [self.sales_order_row(customer), self.sales_order_row(customer)],
            "销售明细": [self.sales_line_row(sku)],
        }
        before = self.business_snapshot()

        response = self.upload(self.workbook_bytes(rows))

        self.assertEqual(response.status_code, 200, response.data)
        order_rows = [item for item in response.data["results"] if item["sheet"] == "销售订单"]
        self.assertEqual(len(order_rows), 2)
        self.assertTrue(all(item["status"] == "阻断" for item in order_rows))
        self.assertTrue(any("数据库中已有相同销售订单编号" in reason["message"] for item in order_rows for reason in item["reasons"]))
        self.assertTrue(any("重复" in reason["message"] for item in order_rows for reason in item["reasons"]))
        self.assertEqual(self.business_snapshot(), before)

    def test_reuploading_same_workbook_is_repeatable_and_remains_read_only(self):
        customer, _supplier, sku = self.create_masters()
        data = self.basic_sales_workbook(customer, sku)
        before = self.business_snapshot()

        first = self.upload(data)
        second = self.upload(data)

        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(second.data["results"], first.data["results"])
        self.assertTrue(second.data["preflight_only"])
        self.assertFalse(second.data["business_write_performed"])
        self.assertEqual(self.business_snapshot(), before)
        self.assertEqual(list(Path(self.media.name).iterdir()), [])

    def test_missing_parent_dependency_blocks_group_and_line(self):
        customer, _supplier, sku = self.create_masters()
        data = self.basic_sales_workbook(customer, sku, line_overrides={"source_order_id": "MISSING-PARENT"})

        response = self.upload(data)

        line = next(item for item in response.data["results"] if item["sheet"] == "销售明细")
        group = next(item for item in response.data["results"] if item["sheet"] == "分组")
        self.assertEqual(line["status"], "阻断")
        self.assertEqual(group["status"], "阻断")
        self.assertTrue(any("订单不存在或不唯一" in reason["message"] for reason in line["reasons"]))

    def test_simulated_history_is_blocked_and_row_limit_is_enforced(self):
        customer, _supplier, sku = self.create_masters()
        simulated = self.basic_sales_workbook(customer, sku, line_overrides={"truth_status": "模拟"})
        simulated_response = self.upload(simulated)
        simulated_line = next(item for item in simulated_response.data["results"] if item["sheet"] == "销售明细")
        self.assertEqual(simulated_line["status"], "阻断")
        self.assertTrue(any("模拟数据不得进入" in reason["message"] for reason in simulated_line["reasons"]))

        with patch("crm.history_import_preflight.MAX_ROWS", 1):
            too_many = self.upload(self.basic_sales_workbook(customer, sku))
        self.assertEqual(too_many.status_code, 413, too_many.data)
        self.assertIn("数据行", too_many.data["detail"])

    def test_unverified_pending_cash_and_open_settled_cancelled_plans_do_not_write_or_confirm(self):
        customer, _supplier, sku = self.create_masters()
        plan_open = {
            "group_id": "G-1", "source_plan_id": "PLAN-OPEN", "source_order_id": "SO-SRC-1",
            "direction": "receivable", "due_date": date(2024, 10, 1), "planned_amount": "100.0000",
            "settled_amount": "40.0000", "currency": "USD", "lifecycle_state": "open",
            "settlement_detail_complete": "no", "truth_status": "待核实", "voucher_reference": "",
        }
        plan_settled = {
            "group_id": "G-1", "source_plan_id": "PLAN-DONE", "source_order_id": "SO-SRC-1",
            "direction": "receivable", "due_date": date(2024, 9, 1), "planned_amount": "50.0000",
            "settled_amount": "50.0000", "currency": "USD", "lifecycle_state": "settled",
            "settlement_detail_complete": "yes", "truth_status": "真实", "voucher_reference": "synthetic://settled-plan",
        }
        plan_cancelled = {
            "group_id": "G-1", "source_plan_id": "PLAN-CANCEL", "source_order_id": "SO-SRC-1",
            "direction": "receivable", "due_date": None, "planned_amount": "0.0000",
            "settled_amount": "0.0000", "currency": "USD", "lifecycle_state": "cancelled",
            "settlement_detail_complete": "yes", "truth_status": "真实", "voucher_reference": "synthetic://cancelled-plan",
        }
        tx_pending = {
            "group_id": "G-1", "source_record_id": "TX-PENDING", "transaction_no": "OLD-TX-PENDING",
            "transaction_date": date(2024, 9, 5), "direction": "income", "kind": "customer_receipt",
            "amount": "40.0000", "currency": "USD", "exchange_rate": "1.000000",
            "source_status": "pending", "customer_code": customer.code, "source_order_id": "SO-SRC-1",
            "source_plan_id": "PLAN-OPEN", "truth_status": "待核实", "voucher_reference": "",
        }
        tx_confirmed = {
            "group_id": "G-1", "source_record_id": "TX-CONFIRMED", "transaction_no": "OLD-TX-DONE",
            "transaction_date": date(2024, 9, 2), "direction": "income", "kind": "customer_receipt",
            "amount": "50.0000", "currency": "USD", "exchange_rate": "1.000000",
            "source_status": "confirmed", "customer_code": customer.code, "source_order_id": "SO-SRC-1",
            "source_plan_id": "PLAN-DONE", "truth_status": "真实", "voucher_reference": "synthetic://receipt",
        }
        rows_extra = {"收付款计划": [plan_open, plan_settled, plan_cancelled], "收付款流水": [tx_pending, tx_confirmed]}
        data = self.basic_sales_workbook(customer, sku, order_overrides={"lifecycle_state": "partial"}, rows_extra=rows_extra)
        before = self.business_snapshot()

        response = self.upload(data)

        self.assertEqual(response.status_code, 200, response.data)
        tx_rows = [item for item in response.data["results"] if item["sheet"] == "收付款流水"]
        self.assertEqual(tx_rows[0]["status"], "待人工核实")
        self.assertTrue(any("不计入已确认资金" in reason["message"] for reason in tx_rows[0]["reasons"]))
        plan_rows = [item for item in response.data["results"] if item["sheet"] == "收付款计划"]
        self.assertEqual(len(plan_rows), 3)
        self.assertTrue(any("已结清" in reason["message"] for item in plan_rows for reason in item["reasons"]))
        self.assertTrue(any("已取消" in reason["message"] for item in plan_rows for reason in item["reasons"]))
        self.assertEqual(self.business_snapshot(), before)

    def test_receipt_reversal_over_original_quantity_is_blocked(self):
        customer, supplier, sku = self.create_masters()
        purchase = {
            "group_id": "G-1", "source_record_id": "PO-SRC-1", "purchase_no": "OLD-PO-1",
            "order_date": date(2024, 7, 1), "lifecycle_state": "partial", "supplier_code": supplier.code,
            "supplier_name_snapshot": supplier.name, "supplier_country_snapshot": "US", "supplier_address_snapshot": "Old address",
            "supplier_contact_name_snapshot": "Old contact", "supplier_phone_snapshot": "555-0111",
            "supplier_email_snapshot": "supplier@example.test", "currency": "USD", "exchange_rate": "1.000000",
            "truth_status": "真实", "voucher_reference": "synthetic://purchase-order",
        }
        purchase_line = {
            "group_id": "G-1", "source_purchase_id": "PO-SRC-1", "source_line_id": "1",
            "sku_code": sku.sku, "sku_name_snapshot": sku.display_name_cn,
            "product_category_snapshot": "合成历史分类", "unit_snapshot": "pcs",
            "base_unit_snapshot": "pcs", "quantity_base": "5.00", "unit_price": "3.000000000000",
            "truth_status": "真实", "voucher_reference": "synthetic://purchase-line",
        }
        receipt = {
            "group_id": "G-1", "source_event_id": "GR-1", "event_type": "goods_receipt",
            "parent_source_id": "PO-SRC-1", "source_line_id": "1", "event_date": date(2024, 7, 5),
            "sku_code": sku.sku, "sku_name_snapshot": sku.display_name_cn, "unit_snapshot": "pcs",
            "base_unit_snapshot": "pcs", "quantity_base": "5.00", "lifecycle_state": "effective",
            "truth_status": "真实", "voucher_reference": "synthetic://receipt",
        }
        reversal = {**receipt, "source_event_id": "GR-REV-1", "event_type": "receipt_reversal", "event_date": date(2024, 7, 6), "quantity_base": "6.00", "reversal_of_source_event_id": "GR-1"}
        rows = {"分组": [self.group_row()], "采购订单": [purchase], "采购明细": [purchase_line], "履约记录": [receipt, reversal]}
        before = self.business_snapshot()

        response = self.upload(self.workbook_bytes(rows))

        self.assertEqual(response.status_code, 200, response.data)
        original_result = next(item for item in response.data["results"] if item["sheet"] == "履约记录" and item["source_record_id"] == "GR-1")
        self.assertEqual(original_result["status"], "阻断")
        self.assertTrue(any("累计冲销数量超过原履约数量" in reason["message"] for reason in original_result["reasons"]))
        self.assertEqual(self.business_snapshot(), before)

    def test_partial_purchase_receipt_dependency_and_trade_unit_fraction_rules(self):
        customer, supplier, sku = self.create_masters()
        purchase = {
            "group_id": "G-1", "source_record_id": "PO-SRC-1", "purchase_no": "OLD-PO-1",
            "order_date": date(2024, 7, 1), "lifecycle_state": "partial", "supplier_code": supplier.code,
            "supplier_name_snapshot": supplier.name, "supplier_country_snapshot": "US", "supplier_address_snapshot": "Old address",
            "supplier_contact_name_snapshot": "Old contact", "supplier_phone_snapshot": "555-0111",
            "supplier_email_snapshot": "supplier@example.test", "currency": "USD", "exchange_rate": "1.000000",
            "truth_status": "真实", "voucher_reference": "synthetic://purchase-order",
        }
        purchase_line = {
            "group_id": "G-1", "source_purchase_id": "PO-SRC-1", "source_line_id": "1",
            "sku_code": sku.sku, "sku_name_snapshot": sku.display_name_cn,
            "product_category_snapshot": "合成历史分类", "unit_snapshot": "pcs",
            "base_unit_snapshot": "pcs", "quantity_base": "5.00", "unit_price": "3.000000000000",
            "truth_status": "真实", "voucher_reference": "synthetic://purchase-line",
        }
        receipt = {
            "group_id": "G-1", "source_event_id": "GR-VALID", "event_type": "goods_receipt",
            "parent_source_id": "PO-SRC-1", "source_line_id": "1", "event_date": date(2024, 7, 5),
            "sku_code": sku.sku, "sku_name_snapshot": sku.display_name_cn, "unit_snapshot": "pcs",
            "base_unit_snapshot": "pcs", "quantity_base": "3.00", "lifecycle_state": "effective",
            "truth_status": "真实", "voucher_reference": "synthetic://receipt",
        }
        purchase_rows = {
            "分组": [self.group_row()], "采购订单": [purchase], "采购明细": [purchase_line], "履约记录": [receipt],
        }
        response = self.upload(self.workbook_bytes(purchase_rows))
        receipt_result = next(item for item in response.data["results"] if item["sheet"] == "履约记录")
        self.assertEqual(receipt_result["status"], "通过")

        SKUTradeUnit.objects.create(sku=sku, name="10件箱", unit="carton", factor="10", allow_fraction=False)
        valid_line = self.sales_line_row(
            sku, quantity_base="20.00", unit_snapshot="carton", base_unit_snapshot="pcs",
            trade_quantity="2.00", trade_unit_snapshot="carton", trade_unit_price="12.3456",
            trade_factor_snapshot="10.00", allow_fraction_snapshot=False,
        )
        valid_trade = self.upload(self.basic_sales_workbook(customer, sku, line_overrides=valid_line))
        valid_trade_result = next(item for item in valid_trade.data["results"] if item["sheet"] == "销售明细")
        self.assertEqual(valid_trade_result["status"], "通过")

        invalid_line = {**valid_line, "quantity_base": "15.00", "trade_quantity": "1.50"}
        invalid_trade = self.upload(self.basic_sales_workbook(customer, sku, line_overrides=invalid_line))
        invalid_trade_result = next(item for item in invalid_trade.data["results"] if item["sheet"] == "销售明细")
        self.assertEqual(invalid_trade_result["status"], "阻断")
        self.assertTrue(any("不可拆分" in reason["message"] for reason in invalid_trade_result["reasons"]))

    def test_cancelled_and_completed_orders_keep_distinct_non_importable_lifecycle_evidence(self):
        customer, _supplier, sku = self.create_masters()
        rows = {
            "分组": [self.group_row()],
            "销售订单": [
                self.sales_order_row(customer, source_id="SO-CANCEL", order_no="OLD-SO-CANCEL", state="cancelled"),
                self.sales_order_row(customer, source_id="SO-DONE", order_no="OLD-SO-DONE", state="completed"),
            ],
            "销售明细": [
                self.sales_line_row(sku, parent_id="SO-CANCEL", line_id="1"),
                self.sales_line_row(sku, parent_id="SO-DONE", line_id="1"),
            ],
        }

        response = self.upload(self.workbook_bytes(rows))

        cancelled = next(item for item in response.data["results"] if item["sheet"] == "销售订单" and item["source_record_id"] == "SO-CANCEL")
        completed_line = next(item for item in response.data["results"] if item["sheet"] == "销售明细" and item["related_records"] and any(rel.get("source_record_id") == "SO-DONE" for rel in item["related_records"]))
        self.assertEqual(cancelled["status"], "警告")
        self.assertTrue(any("已取消" in reason["message"] for reason in cancelled["reasons"]))
        self.assertEqual(completed_line["status"], "待人工核实")
        self.assertTrue(any("已完成但可核实履约数量不足" in reason["message"] for reason in completed_line["reasons"]))

    def test_missing_voucher_and_partial_coverage_are_not_reported_as_pass(self):
        customer, _supplier, sku = self.create_masters()
        rows = {
            "分组": [self.group_row(coverage_status="partial")],
            "销售订单": [self.sales_order_row(customer, voucher_reference="")],
            "销售明细": [self.sales_line_row(sku, voucher_reference="")],
        }
        response = self.upload(self.workbook_bytes(rows))
        group = next(item for item in response.data["results"] if item["sheet"] == "分组")
        line = next(item for item in response.data["results"] if item["sheet"] == "销售明细")
        self.assertEqual(group["status"], "待人工核实")
        self.assertEqual(line["status"], "待人工核实")
        self.assertTrue(any("凭证引用" in reason["message"] for reason in line["reasons"]))
        self.assertFalse(response.data["summary"]["overall_status"] == "通过")

    def test_csv_report_escapes_formula_like_source_identifiers(self):
        customer, _supplier, sku = self.create_masters()
        rows = {
            "分组": [self.group_row()],
            "销售订单": [self.sales_order_row(customer, source_id="+SUM(1,1)")],
            "销售明细": [self.sales_line_row(sku)],
        }

        response = self.upload(self.workbook_bytes(rows), filename="history.xlsx")
        from django.core.files.uploadedfile import SimpleUploadedFile

        csv_response = self.client.post(
            "/api/import/history-preflight/?report=csv",
            {"file": SimpleUploadedFile("history.xlsx", self.workbook_bytes(rows), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(csv_response.status_code, 200)
        self.assertIn("'+SUM(1,1)", csv_response.content.decode("utf-8-sig"))
        self.assertNotIn("database_id", csv_response.content.decode("utf-8-sig"))

    def test_oversized_file_gets_http_413_and_unauthorized_user_is_denied(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        with override_settings(CSV_IMPORT_MAX_BYTES=128):
            response = self.client.post(
                "/api/import/history-preflight/",
                {"file": SimpleUploadedFile("too-large.xlsx", b"x" * 1024, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                format="multipart",
            )
        self.assertEqual(response.status_code, 413, getattr(response, "data", response.content))
        self.assertFalse(response.wsgi_request._csv_import_upload_limit_exceeded.get("bytes_forwarded", 1))

        self.client.force_authenticate(get_user_model().objects.create_user(username="iss121-no-permission"))
        with override_settings(APP_STAGE="staging", DEBUG=False, DEVELOPMENT_SUPERADMIN=False, RBAC_ENFORCEMENT=True):
            denied = self.upload(b"invalid")
        self.assertEqual(denied.status_code, 403)

    def test_limited_data_scope_is_denied_before_workbook_parsing(self):
        user = get_user_model().objects.create_user(username="iss121-scoped-user")
        self.client.force_authenticate(user)
        with (
            override_settings(APP_STAGE="staging", DEBUG=False, DEVELOPMENT_SUPERADMIN=False, RBAC_ENFORCEMENT=True),
            patch("crm.history_import_preflight.user_can", return_value=True),
            patch("crm.history_import_preflight.effective_data_scope", return_value="owned"),
        ):
            denied = self.upload(b"not-an-xlsx")
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.data["detail"], HistoryPreflightPermission.message)

    def multi_line_partial_rows(self, kind, quantities, *, uncertain_second=False, reversal=False, coverage="complete"):
        customer, supplier, first_sku = self.create_masters()
        product = Product.objects.create(code="ISS121-KG-P", name="合成重量产品", sales_model_prefix="I124")
        second_sku = SKU.objects.create(sku="ISS121-KG", product=product, display_name_cn="合成重量 SKU", unit="kg")
        skus = (first_sku, second_sku)
        is_sales = kind == "sales"
        parent_id = "SO-SRC-1" if is_sales else "PO-SRC-1"
        if is_sales:
            parent = self.sales_order_row(customer, state="partial")
            lines = [self.sales_line_row(sku, line_id=str(i), unit_snapshot=sku.unit, base_unit_snapshot=sku.unit) for i, sku in enumerate(skus, 1)]
            parent_sheet, line_sheet = "销售订单", "销售明细"
            event_type, reversal_type = "shipment", "shipment_reversal"
        else:
            parent = {
                "group_id": "G-1", "source_record_id": parent_id, "purchase_no": "OLD-PO-1",
                "order_date": date(2024, 7, 1), "lifecycle_state": "partial", "supplier_code": supplier.code,
                "supplier_name_snapshot": supplier.name, "supplier_country_snapshot": "US", "supplier_address_snapshot": "Old address",
                "supplier_contact_name_snapshot": "Old contact", "supplier_phone_snapshot": "555-0111",
                "supplier_email_snapshot": "supplier@example.test", "currency": "USD", "exchange_rate": "1.000000",
                "truth_status": "真实", "voucher_reference": "synthetic://purchase",
            }
            lines = [{
                "group_id": "G-1", "source_purchase_id": parent_id, "source_line_id": str(i),
                "sku_code": sku.sku, "sku_name_snapshot": sku.display_name_cn,
                "product_category_snapshot": "合成历史分类", "unit_snapshot": sku.unit,
                "base_unit_snapshot": sku.unit, "quantity_base": "10.00", "unit_price": "3.000000000000",
                "supplier_name_snapshot": supplier.name, "truth_status": "真实", "voucher_reference": "synthetic://line",
            } for i, sku in enumerate(skus, 1)]
            parent_sheet, line_sheet = "采购订单", "采购明细"
            event_type, reversal_type = "goods_receipt", "receipt_reversal"
        events = []
        for i, (sku, quantity) in enumerate(zip(skus, quantities), 1):
            if not quantity:
                continue
            events.append({
                "group_id": "G-1", "source_event_id": f"EV-{i}", "event_type": event_type,
                "parent_source_id": parent_id, "source_line_id": str(i), "event_date": date(2024, 8, 2),
                "sku_code": sku.sku, "sku_name_snapshot": sku.display_name_cn, "unit_snapshot": sku.unit,
                "base_unit_snapshot": sku.unit, "quantity_base": str(quantity), "lifecycle_state": "effective",
                "truth_status": "待核实" if uncertain_second and i == 2 else "真实", "voucher_reference": "synthetic://event",
            })
        if reversal:
            events.append({**events[0], "source_event_id": "EV-REV", "event_type": reversal_type,
                           "quantity_base": "4", "reversal_of_source_event_id": "EV-1"})
        return {"分组": [self.group_row(coverage_status=coverage)], parent_sheet: [parent], line_sheet: lines, "履约记录": events}, parent_sheet, line_sheet

    def test_partial_multiline_mixed_progress_is_consistent_for_sales_and_purchase(self):
        for kind in ("sales", "purchase"):
            with self.subTest(kind=kind):
                with transaction.atomic():
                    rows, parent_sheet, line_sheet = self.multi_line_partial_rows(kind, (10, 0))
                    before = self.business_snapshot()
                    with CaptureQueriesContext(connection) as queries:
                        response = self.upload(self.workbook_bytes(rows))
                    self.assertEqual(response.status_code, 200, response.data)
                    writes = [query["sql"] for query in queries if query["sql"].lstrip().upper().startswith(
                        ("INSERT ", "UPDATE ", "DELETE ", "REPLACE ", "CREATE ", "ALTER ", "DROP ")
                    )]
                    self.assertEqual(writes, [])
                    line_results = [item for item in response.data["results"] if item["sheet"] == line_sheet]
                    self.assertEqual(len(line_results), 2)
                    for item in line_results:
                        self.assertFalse(any("行项目数量不呈现部分履约状态" in reason["message"] for reason in item["reasons"]), item)
                    self.assertEqual(self.business_snapshot(), before)
                    self.assertEqual(list(Path(self.media.name).iterdir()), [])
                    transaction.set_rollback(True)

    def test_partial_order_uses_all_lines_and_only_verified_fulfillment(self):
        cases = (
            ("each_partial", (4, 5), {}, False, False),
            ("all_complete", (10, 10), {}, True, False),
            ("none_started", (0, 0), {}, True, False),
            ("part_reversed", (10, 0), {"reversal": True}, False, False),
            ("unverified_event", (10, 10), {"uncertain_second": True}, False, True),
            ("incomplete_coverage", (0, 0), {"coverage": "partial"}, False, True),
        )
        for kind in ("sales", "purchase"):
            for name, quantities, options, mismatch, uncertain in cases:
                with self.subTest(kind=kind, case=name), transaction.atomic():
                    rows, parent_sheet, line_sheet = self.multi_line_partial_rows(kind, quantities, **options)
                    before = self.business_snapshot()
                    response = self.upload(self.workbook_bytes(rows))
                    self.assertEqual(response.status_code, 200, response.data)
                    parent = next(item for item in response.data["results"] if item["sheet"] == parent_sheet)
                    lines = [item for item in response.data["results"] if item["sheet"] == line_sheet]
                    messages = [reason["message"] for reason in parent["reasons"]]
                    self.assertEqual(any("部分履约状态与已核实履约记录不一致" in message for message in messages), mismatch, parent)
                    self.assertEqual(any("无法确定整单履约状态" in message for message in messages), uncertain, parent)
                    self.assertFalse(any("行项目数量不呈现部分履约状态" in reason["message"] for item in lines for reason in item["reasons"]))
                    if uncertain:
                        group = next(item for item in response.data["results"] if item["sheet"] == "分组")
                        self.assertEqual(group["status"], "待人工核实")
                    self.assertEqual(self.business_snapshot(), before)
                    self.assertEqual(list(Path(self.media.name).iterdir()), [])
                    transaction.set_rollback(True)

    def test_fulfillment_lifecycle_is_independent_of_financial_settlement(self):
        cases = (("open", (0, 0), "settled"), ("completed", (10, 10), "open"),
                 ("cancelled", (0, 0), "settled"), ("partial", (10, 0), "settled"))
        for kind in ("sales", "purchase"):
            for order_state, quantities, plan_state in cases:
                with self.subTest(kind=kind, order_state=order_state, plan_state=plan_state), transaction.atomic():
                    rows, parent_sheet, line_sheet = self.multi_line_partial_rows(kind, quantities)
                    rows[parent_sheet][0]["lifecycle_state"] = order_state
                    parent_key = "source_order_id" if kind == "sales" else "source_purchase_id"
                    parent_id = "SO-SRC-1" if kind == "sales" else "PO-SRC-1"
                    rows["收付款计划"] = [{
                        "group_id": "G-1", "source_plan_id": "PLAN-1", parent_key: parent_id,
                        "direction": "receivable" if kind == "sales" else "payable",
                        "planned_amount": "100", "settled_amount": "100" if plan_state == "settled" else "0",
                        "currency": "USD", "lifecycle_state": plan_state,
                        "settlement_detail_complete": "no", "truth_status": "真实", "voucher_reference": "synthetic://plan",
                    }]
                    before = self.business_snapshot()
                    response = self.upload(self.workbook_bytes(rows))
                    self.assertEqual(response.status_code, 200, response.data)
                    parent = next(item for item in response.data["results"] if item["sheet"] == parent_sheet)
                    lines = [item for item in response.data["results"] if item["sheet"] == line_sheet]
                    self.assertFalse(any("部分履约状态与已核实履约记录不一致" in reason["message"] for reason in parent["reasons"]))
                    self.assertFalse(any("已完成但可核实履约数量不足" in reason["message"] or "已取消订单仍有关联有效履约" in reason["message"] for item in lines for reason in item["reasons"]))
                    self.assertEqual(self.business_snapshot(), before)
                    self.assertEqual(list(Path(self.media.name).iterdir()), [])
                    transaction.set_rollback(True)

    def test_line_overfulfillment_and_excess_reversal_remain_independent_checks(self):
        for kind in ("sales", "purchase"):
            for case in ("overfulfilled", "excess_reversal"):
                with self.subTest(kind=kind, case=case), transaction.atomic():
                    rows, parent_sheet, line_sheet = self.multi_line_partial_rows(
                        kind, (11, 0) if case == "overfulfilled" else (5, 0),
                        reversal=case == "excess_reversal",
                    )
                    if case == "excess_reversal":
                        rows["履约记录"][-1]["quantity_base"] = "6"
                    before = self.business_snapshot()
                    response = self.upload(self.workbook_bytes(rows))
                    self.assertEqual(response.status_code, 200, response.data)
                    line = next(item for item in response.data["results"] if item["sheet"] == line_sheet and item["source_record_id"] == "1")
                    messages = [reason["message"] for reason in line["reasons"]]
                    if case == "overfulfilled":
                        self.assertTrue(any("履约数量超过订单行数量" in message for message in messages), line)
                    else:
                        self.assertTrue(any("有效履约数量为负数" in message for message in messages), line)
                        original = next(item for item in response.data["results"] if item["sheet"] == "履约记录" and item["source_record_id"] == "EV-1")
                        self.assertTrue(any("累计冲销数量超过原履约数量" in reason["message"] for reason in original["reasons"]), original)
                        group = next(item for item in response.data["results"] if item["sheet"] == "分组")
                        self.assertEqual(group["status"], "阻断")
                    parent = next(item for item in response.data["results"] if item["sheet"] == parent_sheet)
                    self.assertTrue(any("无法确定整单履约状态" in reason["message"] for reason in parent["reasons"]))
                    self.assertEqual(self.business_snapshot(), before)
                    self.assertEqual(list(Path(self.media.name).iterdir()), [])
                    transaction.set_rollback(True)
