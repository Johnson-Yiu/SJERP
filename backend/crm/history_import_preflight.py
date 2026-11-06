"""Read-only preflight for grouped historical ERP source workbooks.

This module deliberately does not create import batches, audit records, master
data, or business records. A successful preflight is a validation result only;
it is not approval to migrate data.
"""

from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.http import HttpResponse
from openpyxl import load_workbook
from openpyxl.utils.cell import range_boundaries
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Customer,
    GoodsReceipt,
    InventoryMovement,
    Order,
    OrderItem,
    PaymentPlan,
    PurchaseOrder,
    PurchaseOrderItem,
    Shipment,
    ShipmentItem,
    SKU,
    SKUTradeUnit,
    Supplier,
    Transaction,
)
from .permissions import development_superadmin_enabled, user_can
from .sales_scope import effective_data_scope, scope_customer_queryset


MAX_ROWS = 5000
MAX_SHEETS = 12
MAX_UNCOMPRESSED_BYTES = 200 * 1024 * 1024
PREVIEW_ONLY_NOTICE = "预检通过表示符合当前检查规则；仍需提交申请并通过审核，才能承接。"
STATUS_RANK = {"通过": 0, "警告": 1, "待人工核实": 2, "阻断": 3}
TRUTH_STATES = {"真实", "模拟", "待核实"}


def _column(key, label, kind="text", required=False, places=None, max_digits=None):
    return {"key": key, "label": label, "kind": kind, "required": required, "places": places, "max_digits": max_digits}


SHEET_SCHEMAS = {
    "分组": [
        _column("group_id", "来源关联组编号", required=True),
        _column("source_system", "原系统名称", required=True),
        _column("exported_at", "原系统导出时间", "date", True),
        _column("coverage_status", "资料覆盖状态", "enum:complete,partial,unknown", True),
        _column("truth_status", "真实性状态", "enum:真实,模拟,待核实", True),
        _column("evidence_reference", "来源/凭证引用"),
        _column("notes", "说明"),
    ],
    "销售订单": [
        _column("group_id", "来源关联组编号", required=True),
        _column("source_record_id", "原系统记录编号", required=True),
        _column("order_no", "原销售订单编号", required=True),
        _column("order_date", "业务日期", "date", True),
        _column("lifecycle_state", "原业务状态", "enum:open,partial,completed,cancelled,unknown", True),
        _column("customer_code", "客户编码"),
        _column("customer_name_snapshot", "历史客户名称快照", required=True),
        _column("customer_country_snapshot", "历史国家/地区快照"),
        _column("customer_address_snapshot", "历史地址快照"),
        _column("customer_contact_name_snapshot", "历史联系人快照"),
        _column("customer_phone_snapshot", "历史联系电话快照"),
        _column("customer_email_snapshot", "历史邮箱快照"),
        _column("currency", "币种", required=True),
        _column("exchange_rate", "历史合同汇率", "decimal", True, 6, 12),
        _column("shipping_fee", "运费", "decimal", True, 4, 14),
        _column("discount", "折扣金额", "decimal", True, 4, 14),
        _column("truth_status", "真实性状态", "enum:真实,模拟,待核实", True),
        _column("voucher_reference", "合同/凭证引用"),
        _column("notes", "说明"),
    ],
    "销售明细": [
        _column("group_id", "来源关联组编号", required=True),
        _column("source_order_id", "原销售订单记录编号", required=True),
        _column("source_line_id", "原销售明细编号", required=True),
        _column("sku_code", "SKU编码"),
        _column("sku_name_snapshot", "历史SKU名称快照", required=True),
        _column("sales_model_snapshot", "历史销售型号快照"),
        _column("description_snapshot", "历史商品描述快照"),
        _column("unit_snapshot", "历史单位快照", required=True),
        _column("base_unit_snapshot", "历史基础单位快照", required=True),
        _column("quantity_base", "基础数量", "decimal", True, 2, 14),
        _column("unit_price", "基础单位单价", "decimal", True, 12, 24),
        _column("trade_quantity", "交易单位数量", "decimal", False, 2, 14),
        _column("trade_unit_snapshot", "交易单位快照"),
        _column("trade_unit_price", "交易单位单价", "decimal", False, 4, 16),
        _column("trade_factor_snapshot", "历史换算系数快照", "decimal", False, 2, 14),
        _column("allow_fraction_snapshot", "历史允许分数包装", "boolean"),
        _column("truth_status", "真实性状态", "enum:真实,模拟,待核实", True),
        _column("voucher_reference", "订单明细凭证引用"),
        _column("notes", "说明"),
    ],
    "采购订单": [
        _column("group_id", "来源关联组编号", required=True),
        _column("source_record_id", "原系统记录编号", required=True),
        _column("purchase_no", "原采购订单编号", required=True),
        _column("order_date", "业务日期", "date", True),
        _column("lifecycle_state", "原业务状态", "enum:open,partial,completed,cancelled,unknown", True),
        _column("supplier_code", "供应商编码"),
        _column("supplier_name_snapshot", "历史供应商名称快照", required=True),
        _column("supplier_address_snapshot", "历史供应商地址快照"),
        _column("supplier_contact_name_snapshot", "历史供应商联系人快照"),
        _column("supplier_phone_snapshot", "历史供应商电话快照"),
        _column("supplier_email_snapshot", "历史供应商邮箱快照"),
        _column("currency", "币种", required=True),
        _column("exchange_rate", "历史合同汇率", "decimal", True, 6, 12),
        _column("truth_status", "真实性状态", "enum:真实,模拟,待核实", True),
        _column("voucher_reference", "合同/凭证引用"),
        _column("notes", "说明"),
    ],
    "采购明细": [
        _column("group_id", "来源关联组编号", required=True),
        _column("source_purchase_id", "原采购订单记录编号", required=True),
        _column("source_line_id", "原采购明细编号", required=True),
        _column("sku_code", "SKU编码"),
        _column("sku_name_snapshot", "历史SKU名称快照", required=True),
        _column("sales_model_snapshot", "历史销售型号快照"),
        _column("description_snapshot", "历史商品描述快照"),
        _column("unit_snapshot", "历史单位快照", required=True),
        _column("base_unit_snapshot", "历史基础单位快照", required=True),
        _column("quantity_base", "基础数量", "decimal", True, 2, 14),
        _column("unit_price", "基础单位单价", "decimal", True, 12, 24),
        _column("trade_quantity", "交易单位数量", "decimal", False, 2, 14),
        _column("trade_unit_snapshot", "交易单位快照"),
        _column("trade_unit_price", "交易单位单价", "decimal", False, 4, 16),
        _column("trade_factor_snapshot", "历史换算系数快照", "decimal", False, 2, 14),
        _column("allow_fraction_snapshot", "历史允许分数包装", "boolean"),
        _column("supplier_name_snapshot", "历史供应商名称快照"),
        _column("supplier_model_snapshot", "历史供应商型号快照"),
        _column("supplier_sku_code_snapshot", "历史供应商SKU快照"),
        _column("truth_status", "真实性状态", "enum:真实,模拟,待核实", True),
        _column("voucher_reference", "订单明细凭证引用"),
        _column("notes", "说明"),
    ],
    "收付款计划": [
        _column("group_id", "来源关联组编号", required=True),
        _column("source_plan_id", "原系统计划编号", required=True),
        _column("source_order_id", "原销售订单记录编号"),
        _column("source_purchase_id", "原采购订单记录编号"),
        _column("direction", "计划方向", "enum:receivable,payable", True),
        _column("due_date", "计划日期", "date"),
        _column("planned_amount", "计划金额", "decimal", True, 4, 14),
        _column("settled_amount", "已核销金额", "decimal", True, 4, 14),
        _column("currency", "币种", required=True),
        _column("lifecycle_state", "原计划状态", "enum:open,settled,cancelled,unknown", True),
        _column("settlement_detail_complete", "收付款明细是否完整", "enum:yes,no,unknown", True),
        _column("truth_status", "真实性状态", "enum:真实,模拟,待核实", True),
        _column("voucher_reference", "计划/对账凭证引用"),
        _column("notes", "说明"),
    ],
    "收付款流水": [
        _column("group_id", "来源关联组编号", required=True),
        _column("source_record_id", "原系统记录编号", required=True),
        _column("transaction_no", "原收付款流水编号", required=True),
        _column("transaction_date", "业务日期", "date", True),
        _column("direction", "收支方向", "enum:income,expense", True),
        _column("kind", "业务类型", "enum:other,customer_receipt,supplier_payment,order_expense,period_expense,unallocated_advance,supplier_refund,other_income,sample_expense,freight_expense,bank_fee,tax_fee,salary_expense,office_expense,travel_expense,marketing_expense,warehouse_expense,asset_expense,unallocated_payment,other_expense,refund,exchange_difference", True),
        _column("amount", "原币金额", "decimal", True, 4, 14),
        _column("currency", "币种", required=True),
        _column("exchange_rate", "历史折算汇率", "decimal", True, 6, 12),
        _column("source_status", "来源流水状态", "enum:confirmed,pending,cancelled,unknown", True),
        _column("customer_code", "客户编码"),
        _column("supplier_code", "供应商编码"),
        _column("source_order_id", "原销售订单记录编号"),
        _column("source_purchase_id", "原采购订单记录编号"),
        _column("source_plan_id", "原收付款计划编号"),
        _column("truth_status", "真实性状态", "enum:真实,模拟,待核实", True),
        _column("voucher_reference", "银行/收付款凭证引用"),
        _column("notes", "说明"),
    ],
    "履约记录": [
        _column("group_id", "来源关联组编号", required=True),
        _column("source_event_id", "原系统履约记录编号", required=True),
        _column("event_type", "履约类型", "enum:shipment,goods_receipt,shipment_reversal,receipt_reversal", True),
        _column("parent_source_id", "原销售订单/采购订单记录编号", required=True),
        _column("source_line_id", "原订单明细编号", required=True),
        _column("event_date", "履约日期", "date", True),
        _column("sku_code", "SKU编码"),
        _column("sku_name_snapshot", "履约SKU名称快照", required=True),
        _column("unit_snapshot", "历史单位快照", required=True),
        _column("base_unit_snapshot", "历史基础单位快照", required=True),
        _column("quantity_base", "基础数量", "decimal", True, 2, 14),
        _column("trade_quantity", "交易单位数量", "decimal", False, 2, 14),
        _column("trade_unit_snapshot", "交易单位快照"),
        _column("trade_factor_snapshot", "历史换算系数快照", "decimal", False, 2, 14),
        _column("allow_fraction_snapshot", "历史允许分数包装", "boolean"),
        _column("lifecycle_state", "履约状态", "enum:effective,cancelled,unknown", True),
        _column("reversal_of_source_event_id", "冲销对应原履约编号"),
        _column("truth_status", "真实性状态", "enum:真实,模拟,待核实", True),
        _column("voucher_reference", "发货/收货/冲销凭证引用"),
        _column("notes", "说明"),
    ],
    "库存盘点": [
        _column("group_id", "来源关联组编号", required=True),
        _column("source_record_id", "原系统盘点记录编号", required=True),
        _column("count_date", "盘点日期", "date", True),
        _column("warehouse_type", "仓库归属", "enum:自有仓,第三方仓", True),
        _column("warehouse", "仓库", required=True),
        _column("lot_reference", "适用批次/货位"),
        _column("sku_code", "SKU编码"),
        _column("sku_name_snapshot", "盘点SKU名称快照", required=True),
        _column("unit_snapshot", "历史基础单位快照", required=True),
        _column("counted_quantity", "实盘数量", "decimal", True, 2, 14),
        _column("coverage_complete", "盘点范围是否完整", "enum:yes,no,unknown", True),
        _column("truth_status", "真实性状态", "enum:真实,模拟,待核实", True),
        _column("voucher_reference", "盘点表/凭证引用"),
        _column("notes", "说明"),
    ],
}

REQUIRED_WORKSHEETS = {"使用说明", *SHEET_SCHEMAS.keys()}
LEGACY_INVENTORY_SCHEMA = [column for column in SHEET_SCHEMAS["库存盘点"] if column["key"] not in {"warehouse_type", "lot_reference"}]
DOMAIN_VIEW_PERMISSIONS = (
    "customers", "suppliers", "skus", "trade_units", "orders", "purchases",
    "transactions", "finance", "inventory",
)


class HistoryPreflightPermission(BasePermission):
    message = "需要历史数据预检及全部相关业务模块的完整查看权限。"

    def has_permission(self, request, view):
        if development_superadmin_enabled():
            return True
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if not user_can(user, "imports", "import"):
            return False
        if effective_data_scope(user) != "all":
            return False
        return all(user_can(user, module, "view") for module in DOMAIN_VIEW_PERMISSIONS)


class PreflightInputError(ValueError):
    def __init__(self, message, *, status_code=400):
        self.status_code = status_code
        super().__init__(message)


def _read_bounded_upload(upload, max_bytes):
    if upload is None:
        raise PreflightInputError("请选择历史数据预检工作簿。")
    if not str(getattr(upload, "name", "")).lower().endswith(".xlsx"):
        raise PreflightInputError("仅支持本任务提供的 .xlsx 模板格式。")
    size = getattr(upload, "size", None)
    if isinstance(size, int) and size > max_bytes:
        raise PreflightInputError(f"文件超过大小限制（最大 {max_bytes:,} 字节）。", status_code=413)
    chunks, total = [], 0
    while total <= max_bytes:
        try:
            chunk = upload.read(min(64 * 1024, max_bytes + 1 - total))
        except OSError as exc:
            raise PreflightInputError("工作簿读取失败，请检查文件后重试。") from exc
        if not chunk:
            break
        if not isinstance(chunk, (bytes, bytearray, memoryview)):
            raise PreflightInputError("工作簿内容无法读取。")
        chunk = bytes(chunk)
        total += len(chunk)
        if total > max_bytes:
            raise PreflightInputError(f"文件超过大小限制（最大 {max_bytes:,} 字节）。", status_code=413)
        chunks.append(chunk)
    data = b"".join(chunks)
    if not data:
        raise PreflightInputError("工作簿为空。")
    return data


def _check_xlsx_container(data):
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > 100:
                raise PreflightInputError("工作簿结构异常。")
            expanded = sum(item.file_size for item in entries)
            if expanded > MAX_UNCOMPRESSED_BYTES:
                raise PreflightInputError("工作簿解压后超过安全限制。", status_code=413)
            if any(item.file_size > 0 and item.compress_size == 0 for item in entries):
                raise PreflightInputError("工作簿压缩结构无效。")
            if any(item.compress_size and item.file_size / item.compress_size > 200 for item in entries):
                raise PreflightInputError("工作簿压缩比例超过安全限制。")
            if archive.testzip() is not None:
                raise PreflightInputError("工作簿压缩数据校验失败。")
    except PreflightInputError:
        raise
    except (OSError, zipfile.BadZipFile) as exc:
        raise PreflightInputError("文件不是有效的 .xlsx 工作簿。") from exc


def _cell_text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return value


def _parse_date(value):
    if isinstance(value, datetime):
        if value.time().isoformat() != "00:00:00":
            raise ValueError("日期不能包含时间。")
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            parsed = date.fromisoformat(value.strip())
        except ValueError as exc:
            raise ValueError("日期须为有效的 YYYY-MM-DD。") from exc
        if parsed.isoformat() != value.strip():
            raise ValueError("日期须为 YYYY-MM-DD。")
        return parsed
    raise ValueError("日期须为 YYYY-MM-DD。")


def _parse_decimal(value, places, max_digits, *, positive=False, nonnegative=False):
    if isinstance(value, bool) or value in (None, ""):
        raise ValueError("必须填写有效数字。")
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("必须填写有效数字。") from exc
    if not number.is_finite():
        raise ValueError("金额或数量必须是有限数字。")
    if max(0, -number.as_tuple().exponent) > places:
        raise ValueError(f"最多允许 {places} 位小数。")
    if max_digits is not None:
        exponent = number.as_tuple().exponent
        decimals = max(0, -exponent)
        whole_digits = max(0, len(number.as_tuple().digits) - decimals + max(0, exponent))
        if whole_digits > max_digits - places:
            raise ValueError(f"整数位数超过模型精度（最多 {max_digits - places} 位）。")
    if positive and number <= 0:
        raise ValueError("数值必须大于 0。")
    if nonnegative and number < 0:
        raise ValueError("数值不能小于 0。")
    return number


def _read_workbook(data):
    _check_xlsx_container(data)
    try:
        workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=False, keep_links=False)
    except Exception as exc:
        raise PreflightInputError("工作簿无法解析，请使用本任务模板重新保存。") from exc
    if len(workbook.sheetnames) > MAX_SHEETS or set(workbook.sheetnames) != REQUIRED_WORKSHEETS:
        raise PreflightInputError("工作簿工作表与本任务模板不一致。")
    all_rows = {}
    row_total = 0
    try:
        for sheet_name, schema in SHEET_SCHEMAS.items():
            sheet = workbook[sheet_name]
            try:
                dimension = sheet.calculate_dimension(force=sheet.max_row is None or sheet.max_column is None)
                _min_col, _min_row, max_col, max_row = range_boundaries(dimension)
            except (TypeError, ValueError) as exc:
                raise PreflightInputError(f"工作表“{sheet_name}”没有有效数据区域。") from exc
            if max_row > MAX_ROWS + 1:
                raise PreflightInputError(f"工作表“{sheet_name}”行数或列数超出模板范围。", status_code=413)
            headers = list(next(sheet.iter_rows(min_row=1, max_row=1, values_only=True), ()))
            expected = [column["label"] for column in schema]
            selected_schema = schema
            legacy_inventory = sheet_name == "库存盘点" and headers == [column["label"] for column in LEGACY_INVENTORY_SCHEMA]
            if legacy_inventory:
                selected_schema = LEGACY_INVENTORY_SCHEMA
            elif headers != expected:
                raise PreflightInputError(f"工作表“{sheet_name}”表头与模板不一致。")
            if max_col != len(selected_schema):
                raise PreflightInputError(f"工作表“{sheet_name}”行数或列数超出模板范围。", status_code=413)
            parsed = []
            for row_number, cells in enumerate(sheet.iter_rows(min_row=2, values_only=False), start=2):
                values = []
                for cell in cells:
                    if cell.data_type == "f" or cell.data_type == "e":
                        raise PreflightInputError(f"工作表“{sheet_name}”第 {row_number} 行包含公式或错误单元格。")
                    values.append(_cell_text(cell.value))
                if not any(value not in (None, "") for value in values):
                    continue
                row_total += 1
                if row_total > MAX_ROWS:
                    raise PreflightInputError(f"工作簿最多允许 {MAX_ROWS} 条数据行。", status_code=413)
                parsed.append({
                    "row": row_number,
                    "data": {**{column["key"]: value for column, value in zip(selected_schema, values)}, **({"warehouse_type": None, "lot_reference": None} if legacy_inventory else {})},
                })
            all_rows[sheet_name] = parsed
    finally:
        workbook.close()
    if not row_total:
        raise PreflightInputError("工作簿没有可预检的数据行。")
    return all_rows


def _new_result(sheet, row, data):
    return {
        "sheet": sheet,
        "row": row,
        "source_record_id": str(data.get("source_record_id") or data.get("source_event_id") or data.get("source_line_id") or data.get("source_plan_id") or data.get("group_id") or ""),
        "group_id": str(data.get("group_id") or ""),
        "status": "通过",
        "reasons": [],
        "related_records": [],
        "suggested_actions": [],
    }


def _issue(result, status_text, message, action, related=None):
    if status_text not in STATUS_RANK:
        raise ValueError("Unknown preflight result status")
    if STATUS_RANK[status_text] > STATUS_RANK[result["status"]]:
        result["status"] = status_text
    entry = {"status": status_text, "message": message}
    if entry not in result["reasons"]:
        result["reasons"].append(entry)
    if action and action not in result["suggested_actions"]:
        result["suggested_actions"].append(action)
    if related:
        for item in related:
            if item not in result["related_records"]:
                result["related_records"].append(item)


def _storage_limit_errors(sheet, data):
    """Describe source identities that cannot fit the existing history models."""
    errors = []
    if len(str(data.get("group_id") or "").strip()) > 120:
        errors.append("来源关联组编号不能超过 120 个字符。")
    if sheet == "分组" and len(str(data.get("source_system") or "")) > 160:
        errors.append("原系统名称不能超过 160 个字符。")
    if sheet in ("销售明细", "采购明细"):
        parent = "source_order_id" if sheet == "销售明细" else "source_purchase_id"
        identity = f"{data.get(parent) or ''}:{data.get('source_line_id') or ''}"
    else:
        identity = next((str(data[key]) for key in ("source_record_id", "source_event_id", "source_line_id", "source_plan_id") if data.get(key)), "")
    if len(identity) > 160:
        errors.append("来源记录编号（明细含上级编号）不能超过 160 个字符。")
    return errors


def _base_validate(sheet, record, result):
    data = record["data"]
    schema = {column["key"]: column for column in SHEET_SCHEMAS[sheet]}
    for key, column in schema.items():
        value = data.get(key)
        if column["required"] and value in (None, ""):
            data[key] = None
            _issue(result, "阻断", f"缺少必填字段：{column['label']}。", "补齐原始来源字段；不得从当前主档猜补历史事实。")
            continue
        if value in (None, ""):
            continue
        kind = column["kind"]
        try:
            if kind == "date":
                data[key] = _parse_date(value)
            elif kind == "decimal":
                positive = key in {"exchange_rate", "quantity_base", "trade_quantity", "trade_factor_snapshot", "amount"}
                nonnegative = key in {"unit_price", "shipping_fee", "discount", "planned_amount", "settled_amount", "trade_unit_price", "counted_quantity"}
                data[key] = _parse_decimal(
                    value, column["places"], column["max_digits"],
                    positive=positive, nonnegative=nonnegative,
                )
            elif kind == "boolean":
                if value in (True, "TRUE", "true", "是"):
                    data[key] = True
                elif value in (False, "FALSE", "false", "否"):
                    data[key] = False
                else:
                    raise ValueError("请填写是或否。")
            elif kind.startswith("enum:"):
                allowed = set(kind.split(":", 1)[1].split(","))
                if value not in allowed:
                    raise ValueError("值不在模板允许范围内。")
            elif key == "currency" and not re.fullmatch(r"[A-Z0-9]{3,10}", str(value)):
                raise ValueError("币种须使用大写字母或数字，长度为 3–10 位。")
        except ValueError as exc:
            data[key] = None
            _issue(result, "阻断", f"{column['label']}：{exc}", "按原始凭证修正格式、精度或允许值。")
    if sheet == "收付款计划" and data.get("planned_amount") == 0 and data.get("lifecycle_state") != "cancelled":
        _issue(result, "阻断", "只有已取消计划可为零金额。", "核对原计划金额和取消状态，不创建零余额计划。")
    if sheet == "收付款计划" and data.get("planned_amount") == 0 and data.get("settled_amount") not in (None, Decimal("0")):
        _issue(result, "阻断", "零金额取消计划不能有已核销金额。", "核对取消前计划和实际收付，保留有效资金历史。")
    truth = data.get("truth_status")
    if truth == "模拟":
        _issue(result, "阻断", "模拟数据不得进入正式历史导入候选。", "移至独立演示环境；勿将模拟记录混入正式来源。")
    elif truth == "待核实":
        _issue(result, "待人工核实", "真实性尚未核实，不能作为正式导入事实。", "核对原始业务凭证后更新真实性状态。")
    group_id = str(data.get("group_id") or "").strip()
    if not group_id:
        _issue(result, "阻断", "缺少来源关联组编号。", "按同一业务依赖链填写来源关联组编号。")
    data["group_id"] = group_id
    for error in _storage_limit_errors(sheet, data):
        _issue(result, "阻断", error, "请核对原始资料；无法准确表示时联系管理员处理，不得截断或覆盖历史编号。")


def _records_index(records, key):
    index = {}
    for record in records:
        value = str(record["data"].get(key) or "").strip()
        if value:
            index.setdefault(value, []).append(record)
    return index


def _row_relation(sheet, record):
    return {"sheet": sheet, "row": record["row"], "source_record_id": str(record["data"].get("source_record_id") or record["data"].get("source_event_id") or record["data"].get("source_line_id") or record["data"].get("source_plan_id") or "")}


def _master_candidate(model, *, key_field, code, name, name_field, queryset=None):
    queryset = queryset if queryset is not None else model.objects.all()
    if code:
        direct = list(queryset.filter(**{key_field: code})[:2])
        if len(direct) == 1:
            return "exact", direct[0], direct
    else:
        direct = []
    candidates = []
    if name:
        if model is SKU:
            candidates = list(queryset.filter(display_name_cn__iexact=name).select_related("product")[:3])
            if not candidates:
                candidates = list(queryset.filter(product__name__iexact=name).select_related("product")[:3])
        else:
            candidates = list(queryset.filter(**{f"{name_field}__iexact": name})[:3])
    if len(candidates) == 1:
        return "name_candidate", candidates[0], candidates
    if len(candidates) > 1:
        return "ambiguous", None, candidates
    return "missing", None, []


def _related_master(kind, instance, match_type):
    return {"type": kind, "database_id": instance.pk, "match": match_type}


def _check_master(sheet, record, result, *, kind, model, code_key, name_key, name_field, queryset=None):
    data = record["data"]
    code, name = str(data.get(code_key) or "").strip(), str(data.get(name_key) or "").strip()
    if not code and not name:
        _issue(result, "阻断", f"缺少{kind}编码及历史名称，无法提出关联候选。", "补齐原系统编码或保留的历史主体名称。")
        return None
    match, instance, candidates = _master_candidate(model, key_field={"customer_code": "code", "supplier_code": "code", "sku_code": "sku"}[code_key], code=code, name=name, name_field=name_field, queryset=queryset)
    if match == "exact":
        result["related_records"].append(_related_master(kind, instance, "编码精确匹配"))
        if not name:
            _issue(result, "待人工核实", f"{kind}历史名称快照缺失，不能使用当前主档名称补齐。", "从历史合同或凭证补录当时的名称快照。")
        elif name != getattr(instance, name_field, ""):
            _issue(result, "警告", f"{kind}当前主档名称与历史快照不同；两者须分别保留。", "保留输入的历史快照，不用当前主档覆盖。")
        return instance
    if match == "name_candidate":
        _issue(result, "待人工核实", f"{kind}编码未唯一匹配，仅发现一个名称候选。", "核对原始编码、历史主体和凭证后人工确认关联。", [_related_master(kind, instance, "名称候选；未自动关联")])
    elif match == "ambiguous":
        _issue(result, "待人工核实", f"{kind}名称匹配到多个主档，存在重名或歧义。", "依据原始编码和凭证人工核实；不得按名称自动选择。", [_related_master(kind, item, "重名候选") for item in candidates])
    else:
        _issue(result, "阻断", f"未找到可关联的{kind}主档。", "先核实主档映射；本预检不会自动创建主档。")
    return None


def _check_snapshot_fields(result, data, fields, kind):
    missing = [label for key, label in fields if not str(data.get(key) or "").strip()]
    if missing:
        _issue(result, "待人工核实", f"缺少历史{kind}快照字段：{'、'.join(missing)}。", "仅依据原始历史合同/凭证补充；不得以当前主档回填。")


def _validate_unit_snapshot(record, result, sku):
    data = record["data"]
    base_unit = str(data.get("base_unit_snapshot") or "").strip()
    unit_snapshot = str(data.get("unit_snapshot") or "").strip()
    trade_unit = str(data.get("trade_unit_snapshot") or "").strip()
    trade_values = [data.get("trade_quantity"), data.get("trade_unit_price"), data.get("trade_factor_snapshot"), data.get("allow_fraction_snapshot")]
    if not base_unit or not unit_snapshot:
        _issue(result, "待人工核实", "历史单位快照不完整。", "请根据原单据或交易单位快照补齐，不要按当前 SKU 单位推断。")
    if sku and base_unit and base_unit != sku.unit:
        _issue(result, "警告", "历史基础单位与当前 SKU 基础单位不同。", "保留历史单位；核对单位变更记录，不用当前单位替换。")
    if not trade_unit:
        if any(value not in (None, "") for value in trade_values):
            _issue(result, "阻断", "未填写交易单位，但交易数量/价格/换算快照有值。", "核对原始交易单位快照后成组补齐或清除无来源字段。")
        elif base_unit and unit_snapshot and base_unit != unit_snapshot:
            _issue(result, "待人工核实", "单位快照与基础单位不同，但缺少交易单位换算快照。", "核对交易单位、换算系数和是否允许分数。")
        return
    if any(value in (None, "") for value in trade_values):
        _issue(result, "待人工核实", "交易单位快照缺少数量、单价、换算系数或分数规则。", "从原单据补齐完整交易单位语义；不得读取当前规格代替历史快照。")
        return
    trade_quantity, factor = data["trade_quantity"], data["trade_factor_snapshot"]
    if factor <= 0 or data["quantity_base"] != trade_quantity * factor:
        _issue(result, "阻断", "历史换算系数须大于 0，且基础数量须等于交易数量乘以历史换算系数。", "请按原始交易单位和数量核对后修正。")
    if data["allow_fraction_snapshot"] is False and trade_quantity != trade_quantity.to_integral_value():
        _issue(result, "阻断", "历史交易单位不可拆分，但交易数量包含分数。", "核对原始包装规则；不得忽略不可拆分限制。")
    if base_unit and unit_snapshot and trade_unit != unit_snapshot:
        _issue(result, "待人工核实", "交易单位与显示单位快照不一致。", "核对历史交易单位快照。")
    if sku:
        candidates = list(SKUTradeUnit.objects.filter(sku=sku, unit=trade_unit).values("unit", "factor", "allow_fraction")[:3])
        if len(candidates) == 1:
            current = candidates[0]
            if Decimal(current["factor"]) != factor or bool(current["allow_fraction"]) != data["allow_fraction_snapshot"] or base_unit != sku.unit:
                _issue(result, "待人工核实", "当前交易单位定义与历史快照不同。", "以历史单据快照为准，核对单位版本；不得自动套用当前规则。")
        elif len(candidates) > 1:
            _issue(result, "待人工核实", "当前存在多个同名交易单位候选。", "依据历史快照人工确认，不按名称选择。")


def _add_truth_and_voucher_checks(sheet, record, result):
    data = record["data"]
    if sheet != "分组" and data.get("truth_status") == "真实" and not str(data.get("voucher_reference") or "").strip():
        _issue(result, "待人工核实", "真实历史业务记录缺少原始凭证引用。", "补充可核实的合同、流水、履约或盘点凭证引用；预检不验证文件内容或权限。")
    if sheet == "收付款流水":
        state = data.get("source_status")
        if state == "pending":
            _issue(result, "警告", "来源流水尚未确认，不计入已确认资金或订单余额。", "保留待确认状态；凭证核实后由获授权流程处理。")
        elif state == "cancelled":
            _issue(result, "警告", "来源流水已取消/作废，不得作为有效收付款重复计入。", "保留原始状态及冲销链，不改写为已确认。")
        elif state == "unknown":
            _issue(result, "待人工核实", "收付款确认状态未知。", "核对银行/收付款原始凭证后确定；不得自动确认。")
    if sheet in {"销售订单", "采购订单"}:
        state = data.get("lifecycle_state")
        if state == "open":
            _issue(result, "警告", "原业务仍未结；只能承接经核实的剩余状态，不得重计已发生收付、库存或履约。", "将历史已发生记录与待承接余额分开核对。")
        elif state == "partial":
            _issue(result, "待人工核实", "原业务部分完成；须按已核实履约和资金明细重建剩余状态。", "补齐全部收付、履约及冲销依赖后再评估。")
        elif state == "completed":
            _issue(result, "警告", "原业务已完成；保留历史事实，不将已结清记录重新生成待办。", "核对已收付、库存及履约是否完整并保持不重复。")
        elif state == "cancelled":
            _issue(result, "警告", "原业务已取消；保留取消事实及其前序记录，不作为开放业务承接。", "核对取消前已发生的资金、库存和履约及其冲销链。")
        elif state == "unknown":
            _issue(result, "待人工核实", "原业务状态未知，不能判断是否可承接剩余状态。", "依据原系统状态和原始凭证核实，不猜测启用状态。")
    elif sheet == "履约记录":
        state = data.get("lifecycle_state")
        if state == "cancelled":
            _issue(result, "警告", "履约事件已取消；保留原事件和冲销/取消关系，不计为有效履约。", "核对原始事件及关联库存流水，不删除历史记录。")
        elif state == "unknown":
            _issue(result, "待人工核实", "履约事件状态未知，不能计入已完成数量。", "核对发货/收货/冲销凭证后确定状态。")
    elif sheet == "收付款计划":
        state = data.get("lifecycle_state")
        if state == "settled":
            _issue(result, "警告", "原收付款计划已结清；只作历史核对，不重复创建余额或资金流水。", "核对已核销明细与原始凭证。")
        elif state == "cancelled":
            _issue(result, "警告", "原收付款计划已取消；不得作为待结清计划承接。", "保留原取消状态及关联流水。")
        elif state == "unknown":
            _issue(result, "待人工核实", "原收付款计划状态未知。", "核对原计划及结算凭证后再判断剩余余额。")


def _db_duplicate_checks(sheet, record, result, *, rows=None):
    data = record["data"]
    if sheet == "销售订单" and data.get("order_no"):
        candidates = list(Order.objects.filter(order_no=data.get("order_no", "")).values("id", "status", "historical_only")[:2])
        if candidates:
            _issue(result, "阻断", "数据库中已有相同销售订单编号，属于重复候选。", "人工核对原系统编号及历史业务；不得自动复用或去重。", [{"type": "sales_order", "database_id": item["id"], "status": item["status"], "historical_only": item["historical_only"]} for item in candidates])
    elif sheet == "采购订单" and data.get("purchase_no"):
        candidates = list(PurchaseOrder.objects.filter(purchase_no=data.get("purchase_no", "")).values("id", "status", "historical_only")[:2])
        if candidates:
            _issue(result, "阻断", "数据库中已有相同采购订单编号，属于重复候选。", "人工核对原系统编号及历史业务；不得自动复用或去重。", [{"type": "purchase_order", "database_id": item["id"], "status": item["status"], "historical_only": item["historical_only"]} for item in candidates])
    elif sheet == "收付款流水" and data.get("transaction_no"):
        candidates = list(Transaction.objects.filter(transaction_no=data.get("transaction_no", "")).values("id", "status")[:2])
        if candidates:
            _issue(result, "阻断", "数据库中已有相同收付款流水编号，属于重复候选。", "核对原始流水来源和状态；未核实资金不得影响已确认余额。", [{"type": "transaction", **item} for item in candidates])
    elif sheet == "履约记录":
        ref = data.get("source_event_id", "")
        if data.get("event_type") in {"shipment", "shipment_reversal"}:
            shipment = Shipment.objects.filter(shipment_no=ref).values("id", "status", "reversed_at").first()
            if shipment:
                _issue(result, "阻断", "数据库中已有相同发货记录编号。", "核对既存发货、冲销与库存流水；不得重复生成履约或库存流水。", [{"type": "shipment", **shipment}])
        movements = list(InventoryMovement.objects.filter(source_no=ref).values("id", "movement_no", "type")[:3])
        if movements:
            _issue(result, "待人工核实", "数据库中存在相同来源编号的库存流水候选。", "核对原始事件及冲销链；本预检不会创建或冲销库存流水。", [{"type": "inventory_movement", **item} for item in movements])
        if data.get("event_type") in {"goods_receipt", "receipt_reversal"}:
            parent = next((item for item in (rows or {}).get("采购订单", []) if str(item["data"].get("group_id") or "") == str(data.get("group_id") or "") and str(item["data"].get("source_record_id") or "") == str(data.get("parent_source_id") or "")), None)
            sku = SKU.objects.filter(sku=data.get("sku_code", "")).first()
            if parent and sku and isinstance(data.get("event_date"), date) and data.get("quantity_base") is not None:
                candidates = list(GoodsReceipt.objects.filter(
                    purchase_item__purchase_order__purchase_no=parent["data"].get("purchase_no", ""),
                    purchase_item__sku=sku,
                    receipt_date=data.get("event_date"),
                    quantity=data.get("quantity_base"),
                ).values("id", "purchase_item_id", "reversed_at")[:3])
                if candidates:
                    _issue(result, "待人工核实", "存在日期、采购单、SKU 和数量相同的收货记录候选；这不是自动去重结论。", "依据来源事件编号、收货单及库存流水人工核实，确认是否为同一历史事实。", [{"type": "goods_receipt_candidate", **item} for item in candidates])
        elif data.get("event_type") == "shipment" and isinstance(data.get("event_date"), date) and data.get("quantity_base") is not None:
            parent = next((item for item in (rows or {}).get("销售订单", []) if str(item["data"].get("group_id") or "") == str(data.get("group_id") or "") and str(item["data"].get("source_record_id") or "") == str(data.get("parent_source_id") or "")), None)
            if parent:
                candidates = list(ShipmentItem.objects.filter(
                    shipment__order__order_no=parent["data"].get("order_no", ""),
                    shipment__shipment_date=data["event_date"],
                    sku__sku=data.get("sku_code", ""),
                    quantity=data["quantity_base"],
                ).values("id", "shipment_id", "order_item_id")[:3])
                if candidates:
                    _issue(result, "待人工核实", "存在日期、订单、SKU 和数量相同的发货行候选；这不是自动去重结论。", "依据来源发货编号、订单行及库存流水人工核实，确认是否为同一历史事实。", [{"type": "shipment_item_candidate", **item} for item in candidates])
    elif sheet in {"销售明细", "采购明细"}:
        parent_sheet = "销售订单" if sheet == "销售明细" else "采购订单"
        parent_id_key = "source_order_id" if sheet == "销售明细" else "source_purchase_id"
        parent = next((item for item in (rows or {}).get(parent_sheet, []) if str(item["data"].get("group_id") or "") == str(data.get("group_id") or "") and str(item["data"].get("source_record_id") or "") == str(data.get(parent_id_key) or "")), None)
        if parent and data.get("sku_code") and data.get("quantity_base") is not None:
            sku = SKU.objects.filter(sku=data["sku_code"]).first()
            if sku:
                if sheet == "销售明细":
                    candidates = list(OrderItem.objects.filter(order__order_no=parent["data"].get("order_no", ""), sku=sku, quantity=data["quantity_base"]).values("id", "order_id", "unit_price")[:3])
                else:
                    candidates = list(PurchaseOrderItem.objects.filter(purchase_order__purchase_no=parent["data"].get("purchase_no", ""), sku=sku, quantity=data["quantity_base"]).values("id", "purchase_order_id", "unit_price")[:3])
                if candidates:
                    _issue(result, "待人工核实", "数据库中存在订单号、SKU 和数量相同的行项目候选；这不是自动去重结论。", "核对原系统行编号、历史单价和凭证，确认是否为同一记录。", [{"type": "order_line_candidate", **item} for item in candidates])
    elif sheet == "收付款计划":
        parent_order = None
        parent_purchase = None
        if data.get("source_order_id"):
            parent_order = next((item for item in (rows or {}).get("销售订单", []) if str(item["data"].get("group_id") or "") == str(data.get("group_id") or "") and str(item["data"].get("source_record_id") or "") == str(data["source_order_id"])), None)
        if data.get("source_purchase_id"):
            parent_purchase = next((item for item in (rows or {}).get("采购订单", []) if str(item["data"].get("group_id") or "") == str(data.get("group_id") or "") and str(item["data"].get("source_record_id") or "") == str(data["source_purchase_id"])), None)
        if data.get("planned_amount") is not None and data.get("currency"):
            candidates = PaymentPlan.objects.filter(direction=data.get("direction"), planned_amount=data["planned_amount"], currency=data["currency"])
            if parent_order:
                candidates = candidates.filter(order__order_no=parent_order["data"].get("order_no", ""))
            elif parent_purchase:
                candidates = candidates.filter(purchase_order__purchase_no=parent_purchase["data"].get("purchase_no", ""))
            else:
                candidates = candidates.none()
            matches = list(candidates.values("id", "status", "settled_amount")[:3])
            if matches:
                _issue(result, "待人工核实", "数据库中存在父单、方向、币种和金额相同的付款计划候选；这不是自动去重结论。", "核对原系统计划编号、日期及已核销凭证，不重复生成资金流水。", [{"type": "payment_plan_candidate", **item} for item in matches])
    elif sheet == "库存盘点":
        sku_code = data.get("sku_code", "")
        sku = SKU.objects.filter(sku=sku_code).first()
        if sku:
            candidates = list(InventoryMovement.objects.filter(sku=sku, warehouse=data.get("warehouse", ""), movement_date=data.get("count_date")).values("id", "movement_no", "type", "quantity")[:3])
            if candidates:
                _issue(result, "待人工核实", "盘点日同仓库、同 SKU 已有库存流水，需核对盘点基准与期间流水。", "按盘点基准和已确认流水独立核算；不得把订单分配并入实盘库存。", [{"type": "inventory_movement_candidate", **item} for item in candidates])


def _normalize_and_validate(rows):
    results = {}
    row_lookup = {}
    total = 0
    for sheet, records in rows.items():
        for record in records:
            result = _new_result(sheet, record["row"], record["data"])
            results[(sheet, record["row"])] = result
            row_lookup[(sheet, record["row"])] = record
            _base_validate(sheet, record, result)
            _add_truth_and_voucher_checks(sheet, record, result)
            total += 1
    groups = _records_index(rows["分组"], "group_id")
    for group_id, records in groups.items():
        if len(records) > 1:
            for record in records:
                _issue(results[("分组", record["row"])], "阻断", "来源关联组编号在文件中重复。", "每个来源关联组只保留一行说明。", [_row_relation("分组", item) for item in records if item is not record])
    if not groups:
        raise PreflightInputError("至少需要一行来源关联组说明。")
    for sheet, records in rows.items():
        if sheet == "分组":
            continue
        for record in records:
            result = results[(sheet, record["row"])]
            group_id = str(record["data"].get("group_id") or "")
            matches = groups.get(group_id, [])
            if len(matches) != 1:
                _issue(result, "阻断", "来源关联组不存在或不唯一。", "核对 group_id，并为相关记录补齐唯一来源组。", [_row_relation("分组", item) for item in matches])
            elif matches[0]["data"].get("coverage_status") in {"partial", "unknown"}:
                _issue(result, "待人工核实", "关联组资料覆盖不完整或未知，不能视为可导入。", "补齐该业务关联组的订单、行、资金、履约及凭证范围，或保留为待核实。", [_row_relation("分组", matches[0])])

    # Source identifiers and document numbers are identifiers, not fuzzy dedupe keys.
    unique_specs = {
        "销售订单": ("source_record_id", "order_no"),
        "销售明细": (None, None),
        "采购订单": ("source_record_id", "purchase_no"),
        "采购明细": (None, None),
        "收付款计划": ("source_plan_id", None),
        "收付款流水": ("source_record_id", "transaction_no"),
        "履约记录": ("source_event_id", None),
        "库存盘点": ("source_record_id", None),
    }
    for sheet, (source_key, business_key) in unique_specs.items():
        for key in (source_key, business_key):
            if not key:
                continue
            grouped = defaultdict(list)
            for record in rows[sheet]:
                value = str(record["data"].get(key) or "").strip()
                group_id = str(record["data"].get("group_id") or "").strip()
                if value:
                    grouped[(group_id, value)].append(record)
            for (_group_id, value), duplicates in grouped.items():
                if len(duplicates) > 1:
                    for record in duplicates:
                        label = next(column["label"] for column in SHEET_SCHEMAS[sheet] if column["key"] == key)
                        _issue(results[(sheet, record["row"])], "阻断", f"同一来源关联组内的{label}重复。", "请核对原系统记录编号；不同来源组可以使用相同编号，但业务字段相同不代表可以自动合并。", [_row_relation(sheet, item) for item in duplicates if item is not record])
    for sheet, parent_key in (("销售明细", "source_order_id"), ("采购明细", "source_purchase_id")):
        composite = defaultdict(list)
        for record in rows[sheet]:
            data = record["data"]
            key = (str(data.get("group_id") or ""), str(data.get(parent_key) or ""), str(data.get("source_line_id") or ""))
            if all(key):
                composite[key].append(record)
        for records in composite.values():
            if len(records) > 1:
                for record in records:
                    _issue(results[(sheet, record["row"])], "阻断", "同一来源订单内的原系统行编号重复。", "核对原系统明细编号；不同订单中相同的行号可以合法重复。", [_row_relation(sheet, other) for other in records if other is not record])

    return results, groups, row_lookup, total


def _check_master_and_documents(rows, results, user):
    customers = scope_customer_queryset(Customer.objects.all(), user)
    for sheet in ("销售订单", "采购订单"):
        for record in rows[sheet]:
            data = record["data"]
            result = results[(sheet, record["row"])]
            if sheet == "销售订单":
                instance = _check_master(sheet, record, result, kind="客户", model=Customer, code_key="customer_code", name_key="customer_name_snapshot", name_field="name", queryset=customers)
                _check_snapshot_fields(result, data, [
                    ("customer_name_snapshot", "客户名称"), ("customer_country_snapshot", "国家/地区"),
                    ("customer_address_snapshot", "地址"), ("customer_contact_name_snapshot", "联系人"),
                    ("customer_phone_snapshot", "电话"), ("customer_email_snapshot", "邮箱"),
                ], "客户")
            else:
                instance = _check_master(sheet, record, result, kind="供应商", model=Supplier, code_key="supplier_code", name_key="supplier_name_snapshot", name_field="name")
                _check_snapshot_fields(result, data, [
                    ("supplier_name_snapshot", "供应商名称"), ("supplier_address_snapshot", "地址"),
                    ("supplier_contact_name_snapshot", "联系人"), ("supplier_phone_snapshot", "电话"),
                    ("supplier_email_snapshot", "邮箱"),
                ], "供应商")
            _db_duplicate_checks(sheet, record, result, rows=rows)

    sku_queryset = SKU.objects.select_related("product")
    for sheet in ("销售明细", "采购明细", "履约记录", "库存盘点"):
        for record in rows[sheet]:
            data = record["data"]
            result = results[(sheet, record["row"])]
            sku = _check_master(sheet, record, result, kind="SKU", model=SKU, code_key="sku_code", name_key="sku_name_snapshot", name_field="display_name_cn", queryset=sku_queryset)
            if sku and sheet in {"销售明细", "采购明细", "履约记录"}:
                _validate_unit_snapshot(record, result, sku)
            if sheet == "库存盘点" and sku and data.get("unit_snapshot") and data["unit_snapshot"] != sku.unit:
                _issue(result, "警告", "盘点基础单位与当前 SKU 基础单位不同。", "保留历史实盘单位并核对单位变更，不应用订单预留替代实盘数量。")
            if sheet == "采购明细":
                _check_snapshot_fields(result, data, [("supplier_name_snapshot", "供应商名称")], "采购来源")
            _db_duplicate_checks(sheet, record, result, rows=rows)

    for record in rows["收付款流水"]:
        data = record["data"]
        result = results[("收付款流水", record["row"])]
        if data.get("customer_code") and data.get("supplier_code"):
            _issue(result, "阻断", "同一收付款流水不能同时归属客户和供应商。", "核实交易对手及原始银行凭证。")
        if data.get("customer_code") and not customers.filter(code=data["customer_code"]).exists():
            _issue(result, "阻断", "收付款流水客户编码未匹配当前客户主档。", "核实原系统客户映射；不得自动创建或按备注猜测。")
        if data.get("supplier_code") and not Supplier.objects.filter(code=data["supplier_code"]).exists():
            _issue(result, "阻断", "收付款流水供应商编码未匹配当前供应商主档。", "核实原系统供应商映射；不得自动创建。")
        _db_duplicate_checks("收付款流水", record, result, rows=rows)


def _check_dependencies(rows, results, groups):
    sales_orders = defaultdict(list)
    purchase_orders = defaultdict(list)
    sales_lines = defaultdict(list)
    purchase_lines = defaultdict(list)
    for record in rows["销售订单"]:
        data = record["data"]
        sales_orders[(str(data.get("group_id") or ""), str(data.get("source_record_id") or ""))].append(record)
    for record in rows["采购订单"]:
        data = record["data"]
        purchase_orders[(str(data.get("group_id") or ""), str(data.get("source_record_id") or ""))].append(record)
    for record in rows["销售明细"]:
        data = record["data"]
        sales_lines[(str(data.get("group_id") or ""), str(data.get("source_order_id") or ""), str(data.get("source_line_id") or ""))].append(record)
    for record in rows["采购明细"]:
        data = record["data"]
        purchase_lines[(str(data.get("group_id") or ""), str(data.get("source_purchase_id") or ""), str(data.get("source_line_id") or ""))].append(record)
    plans = defaultdict(list)
    events = defaultdict(list)
    transactions_by_plan = defaultdict(list)
    members_by_group = defaultdict(list)
    for record in rows["收付款计划"]:
        data = record["data"]
        plans[(str(data.get("group_id") or ""), str(data.get("source_plan_id") or ""))].append(record)
    for record in rows["履约记录"]:
        data = record["data"]
        events[(str(data.get("group_id") or ""), str(data.get("source_event_id") or ""))].append(record)
    for record in rows["收付款流水"]:
        data = record["data"]
        key = (str(data.get("group_id") or ""), str(data.get("source_plan_id") or ""))
        if key[1]:
            transactions_by_plan[key].append(record)
    for sheet, records in rows.items():
        if sheet == "分组":
            continue
        for record in records:
            members_by_group[str(record["data"].get("group_id") or "")].append((sheet, record))

    for sheet, parent_key, parents, line_key in (
        ("销售明细", "source_order_id", sales_orders, "source_line_id"),
        ("采购明细", "source_purchase_id", purchase_orders, "source_line_id"),
    ):
        parent_sheet = "销售订单" if sheet == "销售明细" else "采购订单"
        for record in rows[sheet]:
            data, result = record["data"], results[(sheet, record["row"])]
            parent_id = str(data.get(parent_key) or "")
            parent_matches = parents.get((str(data.get("group_id") or ""), parent_id), [])
            if len(parent_matches) != 1:
                _issue(result, "阻断", "明细关联的订单不存在或不唯一。", "补齐同一文件中的订单记录并核对原系统编号。")
                continue
            parent = parent_matches[0]
            if parent["data"].get("group_id") != data.get("group_id"):
                _issue(result, "阻断", "明细与订单不属于同一来源关联组。", "按原系统业务关联修正 group_id。", [_row_relation(parent_sheet, parent)])
        for (group_id, parent_id), parent_records in parents.items():
            if len(parent_records) != 1:
                continue
            child_rows = [item for item in rows[sheet] if str(item["data"].get("group_id") or "") == group_id and str(item["data"].get(parent_key) or "") == parent_id]
            if not child_rows:
                _issue(results[(parent_sheet, parent_records[0]["row"])], "阻断", "订单缺少行项目，不能作为完整业务关联组。", "补齐所有原始订单行项目；不创建空订单。")

    # Payments and plans are linked as evidence; they never create or confirm money here.
    for record in rows["收付款计划"]:
        data, result = record["data"], results[("收付款计划", record["row"])]
        sales_id, purchase_id = str(data.get("source_order_id") or ""), str(data.get("source_purchase_id") or "")
        if bool(sales_id) == bool(purchase_id):
            _issue(result, "阻断", "收付款计划必须且只能关联一个销售订单或采购订单。", "依据原计划关联补齐唯一父单。")
            continue
        parent_sheet, parent_records = ("销售订单", sales_orders.get((str(data.get("group_id") or ""), sales_id), [])) if sales_id else ("采购订单", purchase_orders.get((str(data.get("group_id") or ""), purchase_id), []))
        if len(parent_records) != 1:
            _issue(result, "阻断", "收付款计划的父订单不存在或不唯一。", "补齐同一文件中的父订单及关联组。")
            continue
        parent = parent_records[0]
        if data.get("group_id") != parent["data"].get("group_id"):
            _issue(result, "阻断", "收付款计划与父订单不属于同一来源关联组。", "按原始关联修正 group_id。", [_row_relation(parent_sheet, parent)])
        expected = "receivable" if sales_id else "payable"
        if data.get("direction") != expected:
            _issue(result, "阻断", "计划方向与父订单类型不一致。", "按原始收付款计划核对方向。", [_row_relation(parent_sheet, parent)])
        if data.get("currency") and data.get("currency") != parent["data"].get("currency"):
            _issue(result, "待人工核实", "计划币种与父订单币种不同。", "核对原币计划或存在的多币种依据。", [_row_relation(parent_sheet, parent)])
        planned, settled = data.get("planned_amount"), data.get("settled_amount")
        if planned is not None and settled is not None and settled > planned:
            _issue(result, "阻断", "已核销金额超过计划金额。", "按原始计划和流水重新核对，不改写金额。")
        state = data.get("lifecycle_state")
        if state == "settled" and planned is not None and settled is not None and planned != settled:
            _issue(result, "阻断", "已结清计划的已核销金额与计划金额不一致。", "核对原计划、收付流水和退款/冲销记录。")
        if state == "open" and planned is not None and settled is not None and settled >= planned:
            _issue(result, "阻断", "未结清计划没有剩余金额。", "核对原计划状态及已核销金额。")
        if settled and settled > 0:
            if data.get("settlement_detail_complete") != "yes":
                _issue(result, "待人工核实", "计划存在已核销金额，但流水依赖声明为不完整或未知。", "补齐关联收付款流水及凭证；未核实金额不影响已确认余额。")
            linked = transactions_by_plan.get((str(data.get("group_id") or ""), str(data.get("source_plan_id") or "")), [])
            expected_kinds = {"receivable": {"customer_receipt": Decimal("1"), "refund": Decimal("-1")}, "payable": {"supplier_payment": Decimal("1"), "supplier_refund": Decimal("-1")}}.get(data.get("direction"), {})
            confirmed = sum((tx["data"]["amount"] * expected_kinds[tx["data"].get("kind")] for tx in linked if tx["data"].get("source_status") == "confirmed" and tx["data"].get("truth_status") == "真实" and tx["data"].get("amount") is not None and tx["data"].get("kind") in expected_kinds), Decimal("0"))
            if data.get("settlement_detail_complete") == "yes" and confirmed != settled:
                _issue(result, "待人工核实", "已核销计划金额与文件内真实、已确认关联流水合计不一致。", "核对拆分、退款、作废及缺失流水；不得将计划金额当作第二笔现金。", [_row_relation("收付款流水", tx) for tx in linked])

    required_parent_kinds = {"customer_receipt": "sales", "refund": "sales", "order_expense": "sales", "supplier_payment": "purchase", "supplier_refund": "purchase"}
    for record in rows["收付款流水"]:
        data, result = record["data"], results[("收付款流水", record["row"])]
        order_id, purchase_id = str(data.get("source_order_id") or ""), str(data.get("source_purchase_id") or "")
        if order_id and purchase_id:
            _issue(result, "阻断", "收付款流水不能同时关联销售订单和采购订单。", "核对原始流水归属；不得猜测分配。")
        expected_parent = required_parent_kinds.get(data.get("kind"))
        if expected_parent == "sales" and not order_id:
            _issue(result, "待人工核实", "销售类资金流水缺少销售订单关联，可能属于 ISS-038 未核实历史归属。", "按原始凭证逐笔确认订单归属或公共费用，不按备注/参考号推断。")
        if expected_parent == "purchase" and not purchase_id:
            _issue(result, "待人工核实", "采购类资金流水缺少采购订单关联。", "按原始凭证核实供应商、采购单及付款计划。")
        parent_sheet, parent_records = ("销售订单", sales_orders.get((str(data.get("group_id") or ""), order_id), [])) if order_id else ("采购订单", purchase_orders.get((str(data.get("group_id") or ""), purchase_id), [])) if purchase_id else (None, [])
        if order_id or purchase_id:
            if len(parent_records) != 1:
                _issue(result, "阻断", "收付款流水关联的订单不存在或不唯一。", "补齐同一关联组中的父订单。")
            elif data.get("group_id") != parent_records[0]["data"].get("group_id"):
                _issue(result, "阻断", "收付款流水与父订单不属于同一来源关联组。", "依据原始凭证修正关联组。", [_row_relation(parent_sheet, parent_records[0])])
            elif order_id and data.get("customer_code") and parent_records[0]["data"].get("customer_code") and data["customer_code"] != parent_records[0]["data"].get("customer_code"):
                _issue(result, "阻断", "收付款流水客户与销售订单客户编码不一致。", "按原始银行凭证核实付款人及订单关系，不跨客户归属。", [_row_relation(parent_sheet, parent_records[0])])
            elif purchase_id and data.get("supplier_code") and parent_records[0]["data"].get("supplier_code") and data["supplier_code"] != parent_records[0]["data"].get("supplier_code"):
                _issue(result, "阻断", "收付款流水供应商与采购订单供应商编码不一致。", "按原始银行凭证核实收款方及采购关系，不跨供应商归属。", [_row_relation(parent_sheet, parent_records[0])])
        plan_id = str(data.get("source_plan_id") or "")
        if plan_id:
            plan_matches = plans.get((str(data.get("group_id") or ""), plan_id), [])
            if len(plan_matches) != 1:
                _issue(result, "阻断", "收付款流水关联的计划不存在或不唯一。", "补齐同一关联组中的原收付款计划。")
            else:
                plan = plan_matches[0]
                if data.get("group_id") != plan["data"].get("group_id"):
                    _issue(result, "阻断", "收付款流水与计划不属于同一来源关联组。", "依据原始计划修正关联组。", [_row_relation("收付款计划", plan)])
                if data.get("currency") and data.get("currency") != plan["data"].get("currency"):
                    _issue(result, "待人工核实", "收付款流水币种与关联计划币种不同。", "核对原币、结汇和计划关系，勿改写历史金额。", [_row_relation("收付款计划", plan)])
                expected_plan_parent = "source_order_id" if plan["data"].get("direction") == "receivable" else "source_purchase_id"
                actual_plan_parent = str(plan["data"].get(expected_plan_parent) or "")
                actual_tx_parent = order_id if expected_plan_parent == "source_order_id" else purchase_id
                if actual_plan_parent != actual_tx_parent:
                    _issue(result, "阻断", "收付款流水的订单归属与关联计划的父订单不一致。", "按原始银行凭证和核销关系核对，不跨订单挪用资金。", [_row_relation("收付款计划", plan)])
        elif expected_parent:
            _issue(result, "待人工核实", "合同相关收付款没有计划关联，不能安全重建核销状态。", "核对 PaymentPlan 来源和原始核销凭证。", [_row_relation(parent_sheet, parent_records[0])] if len(parent_records) == 1 else None)
        if data.get("truth_status") == "待核实" or data.get("source_status") != "confirmed":
            _issue(result, "警告", "该流水不进入已确认资金和订单余额计算。", "保持原状态，待证据和授权确认后另行处理。")
        direction_by_kind = {"customer_receipt": "income", "supplier_payment": "expense", "refund": "expense", "supplier_refund": "income"}
        expected_direction = direction_by_kind.get(data.get("kind"))
        if expected_direction and data.get("direction") != expected_direction:
            _issue(result, "阻断", "资金方向与业务类型不一致。", "依据原始银行/收付款凭证核对方向。")

    fulfillment_totals = defaultdict(Decimal)
    reversal_totals = defaultdict(Decimal)
    reversal_rows = defaultdict(list)
    valid_reversal_keys = set()
    for record in rows["履约记录"]:
        data, result = record["data"], results[("履约记录", record["row"])]
        event_type = data.get("event_type")
        if event_type not in {"shipment", "goods_receipt", "shipment_reversal", "receipt_reversal"}:
            continue
        is_sales = event_type in {"shipment", "shipment_reversal"}
        parent_map = sales_orders if is_sales else purchase_orders
        parent_sheet = "销售订单" if is_sales else "采购订单"
        parent_id = str(data.get("parent_source_id") or "")
        parent_records = parent_map.get((str(data.get("group_id") or ""), parent_id), [])
        if len(parent_records) != 1:
            _issue(result, "阻断", "履约记录父订单不存在或不唯一。", "补齐同一关联组中的销售/采购订单。")
        elif data.get("group_id") != parent_records[0]["data"].get("group_id"):
            _issue(result, "阻断", "履约记录与父订单不属于同一来源关联组。", "依据原始履约单据修正关联组。", [_row_relation(parent_sheet, parent_records[0])])
        line_sheet = "销售明细" if is_sales else "采购明细"
        line_index = sales_lines if is_sales else purchase_lines
        line_records = line_index.get((str(data.get("group_id") or ""), parent_id, str(data.get("source_line_id") or "")), [])
        if len(line_records) != 1:
            _issue(result, "阻断", "履约记录对应的原订单行不存在或不唯一。", "补齐订单行项目，不能将履约记录挂到其他 SKU。")
        else:
            line = line_records[0]
            line_data = line["data"]
            if str(line_data.get("sku_code") or "") != str(data.get("sku_code") or ""):
                _issue(result, "阻断", "履约 SKU 与原订单行 SKU 不一致。", "核对原发货/收货单和订单行编号。", [_row_relation(line_sheet, line)])
            if data.get("group_id") != line_data.get("group_id"):
                _issue(result, "阻断", "履约记录与订单行不属于同一来源关联组。", "依据原始履约单据修正关联组。", [_row_relation(line_sheet, line)])
            if event_type.endswith("_reversal"):
                original_id = str(data.get("reversal_of_source_event_id") or "")
                originals = events.get((str(data.get("group_id") or ""), original_id), [])
                if len(originals) != 1:
                    _issue(result, "阻断", "冲销履约记录未唯一关联原始履约事件。", "补齐原事件编号及冲销凭证。")
                else:
                    original = originals[0]
                    original_type = original["data"].get("event_type")
                    expected = "shipment" if event_type == "shipment_reversal" else "goods_receipt"
                    if original_type != expected or original["data"].get("group_id") != data.get("group_id") or str(original["data"].get("source_line_id")) != str(data.get("source_line_id")):
                        _issue(result, "阻断", "冲销事件与原履约类型、订单行或关联组不一致。", "核对原始冲销链，不能覆盖或删除原履约事实。", [_row_relation("履约记录", original)])
                    if str(original["data"].get("parent_source_id")) != parent_id or original["data"].get("event_type") in {"shipment_reversal", "receipt_reversal"}:
                        _issue(result, "阻断", "冲销对应的原履约事件父订单无效。", "核对原始事件编号、父单和冲销凭证。", [_row_relation("履约记录", original)])
                    elif original["data"].get("lifecycle_state") != "effective" or original["data"].get("truth_status") != "真实":
                        _issue(result, "待人工核实", "冲销对应的原履约事件不是已核实的有效真实记录。", "核实原事件状态和凭证后再核对冲销数量。", [_row_relation("履约记录", original)])
                    elif data.get("lifecycle_state") == "effective" and data.get("truth_status") == "真实" and data.get("quantity_base") is not None:
                        key = (str(data.get("group_id") or ""), original_id)
                        reversal_totals[key] += data["quantity_base"]
                        reversal_rows[key].append(record)
                        valid_reversal_keys.add((str(data.get("group_id") or ""), str(data.get("source_event_id") or "")))
            if data.get("lifecycle_state") == "effective" and data.get("truth_status") == "真实" and result["status"] != "阻断":
                is_reversal = event_type.endswith("_reversal")
                if not is_reversal or (str(data.get("group_id") or ""), str(data.get("source_event_id") or "")) in valid_reversal_keys:
                    sign = Decimal("-1") if is_reversal else Decimal("1")
                    fulfillment_totals[(line_sheet, str(data.get("group_id") or ""), parent_id, str(data.get("source_line_id")))] += sign * (data.get("quantity_base") or Decimal("0"))
    for record in rows["履约记录"]:
        data = record["data"]
        if data.get("event_type") not in {"shipment", "goods_receipt"}:
            continue
        key = (str(data.get("group_id") or ""), str(data.get("source_event_id") or ""))
        reversed_quantity = reversal_totals.get(key, Decimal("0"))
        original_quantity = data.get("quantity_base")
        if original_quantity is not None and reversed_quantity > original_quantity:
            _issue(results[("履约记录", record["row"])], "阻断", "累计冲销数量超过原履约数量。", "核对分次冲销与原事件数量，不得将其他事件数量用于抵销。", [_row_relation("履约记录", reversal) for reversal in reversal_rows[key]])
    uncertain_orders = set()
    for record in rows["履约记录"]:
        data = record["data"]
        result = results[("履约记录", record["row"])]
        if (data.get("truth_status") != "真实" or data.get("lifecycle_state") not in {"effective", "cancelled"}
                or result["status"] in {"待人工核实", "阻断"}):
            event_type = data.get("event_type")
            parent_sheets = (("销售订单",) if event_type in {"shipment", "shipment_reversal"} else
                             ("采购订单",) if event_type in {"goods_receipt", "receipt_reversal"} else
                             ("销售订单", "采购订单"))
            for parent_sheet in parent_sheets:
                uncertain_orders.add((parent_sheet, str(data.get("group_id") or ""), str(data.get("parent_source_id") or "")))
    order_progress = defaultdict(list)
    for sheet, records in (("销售明细", rows["销售明细"]), ("采购明细", rows["采购明细"])):
        parent_sheet = "销售订单" if sheet == "销售明细" else "采购订单"
        parent_key = "source_order_id" if sheet == "销售明细" else "source_purchase_id"
        parent_index = sales_orders if sheet == "销售明细" else purchase_orders
        for record in records:
            data, result = record["data"], results[(sheet, record["row"])]
            qty = data.get("quantity_base")
            if qty is not None and qty <= 0:
                _issue(result, "阻断", "订单行基础数量必须大于 0。", "按原始合同/采购单核对数量。")
            delivered = fulfillment_totals.get((sheet, str(data.get("group_id") or ""), str(data.get(parent_key) or ""), str(data.get("source_line_id"))), Decimal("0"))
            if delivered < 0:
                _issue(result, "阻断", "有效履约数量为负数，冲销超过原事件。", "核对原履约及部分冲销数量。")
            if qty is not None and delivered > qty:
                _issue(result, "待人工核实", "已核实履约数量超过订单行数量。", "核对超发/超收、增补单及冲销记录；预检不调整库存或订单数量。")
            order_key = (parent_sheet, str(data.get("group_id") or ""), str(data.get(parent_key) or ""))
            order_progress[order_key].append((record, qty, delivered, result["status"]))
            parents = parent_index.get((str(data.get("group_id") or ""), str(data.get(parent_key) or "")), [])
            if len(parents) == 1:
                state = parents[0]["data"].get("lifecycle_state")
                if state == "completed" and qty is not None and delivered < qty:
                    _issue(result, "待人工核实", "订单标记已完成但可核实履约数量不足。", "核对缺失履约行或来源状态；不得把未记录部分推断为已履约。", [_row_relation(parent_sheet, parents[0])])
                if state == "cancelled" and delivered > 0:
                    _issue(result, "待人工核实", "已取消订单仍有关联有效履约记录。", "核对取消前履约及退款/冲销事实，保留原始顺序。", [_row_relation(parent_sheet, parents[0])])

    for parent_sheet, parent_index in (("销售订单", sales_orders), ("采购订单", purchase_orders)):
        for (group_id, parent_id), parent_records in parent_index.items():
            if len(parent_records) != 1:
                continue
            parent = parent_records[0]
            if parent["data"].get("lifecycle_state") != "partial":
                continue
            order_key = (parent_sheet, group_id, parent_id)
            lines = order_progress.get(order_key, [])
            group_records = groups.get(group_id, [])
            uncertain = (
                len(group_records) != 1 or group_records[0]["data"].get("coverage_status") != "complete"
                or group_records[0]["data"].get("truth_status") != "真实"
                or parent["data"].get("truth_status") != "真实" or order_key in uncertain_orders
                or not lines or any(qty is None or qty <= 0 or delivered < 0 or delivered > qty
                                    or status in {"待人工核实", "阻断"}
                                    for _record, qty, delivered, status in lines)
            )
            parent_result = results[(parent_sheet, parent["row"])]
            if uncertain:
                _issue(parent_result, "待人工核实", "资料不完整或履约记录待核实，无法确定整单履约状态。",
                       "补齐来源覆盖及有效履约/冲销证据，不将缺失记录推断为已发生或未发生。")
                continue
            # Compare each line only with its own quantity; SKU units need not match.
            if all(delivered == 0 for _record, _qty, delivered, _status in lines) or all(
                    delivered == qty for _record, qty, delivered, _status in lines):
                _issue(parent_result, "待人工核实", "订单标记部分完成，但部分履约状态与已核实履约记录不一致。",
                       "核对原订单状态、各行履约和冲销证据；履约状态不等同于资金结清状态。",
                       [_row_relation("销售明细" if parent_sheet == "销售订单" else "采购明细", line[0]) for line in lines])

    inventory_keys = defaultdict(list)
    for record in rows["库存盘点"]:
        data, result = record["data"], results[("库存盘点", record["row"])]
        sku_key = str(data.get("sku_code") or "").strip() or str(data.get("sku_name_snapshot") or "").strip().casefold()
        key = (data.get("count_date"), str(data.get("warehouse") or "").strip(), sku_key)
        inventory_keys[key].append(record)
        if data.get("coverage_complete") in {"no", "unknown"}:
            _issue(result, "待人工核实", "盘点范围不完整或未知，不能作为启用库存基准。", "完成并签认仓库/SKU范围，库存基准与订单分配保持分离。")
    for records in inventory_keys.values():
        if len(records) > 1:
            for record in records:
                _issue(results[("库存盘点", record["row"])], "阻断", "同一日期、仓库和 SKU 存在重复盘点记录。", "核对原始盘点范围；不得自动合并数量。", [_row_relation("库存盘点", other) for other in records if other is not record])

    for group_id, group_records in groups.items():
        if len(group_records) != 1:
            continue
        group = group_records[0]
        group_result = results[("分组", group["row"])]
        if group["data"].get("coverage_status") in {"partial", "unknown"}:
            _issue(group_result, "待人工核实", "来源关联组覆盖范围不完整或未知，不能视为可导入整体。", "补齐源系统导出范围及订单、行项目、收付、履约和凭证清单。")
        members = members_by_group.get(group_id, [])
        if not members:
            _issue(group_result, "阻断", "来源关联组没有业务记录。", "补充真实来源记录或移除空分组。")
        statuses = [results[(sheet, record["row"])]["status"] for sheet, record in members]
        if "待人工核实" in statuses:
            _issue(group_result, "待人工核实", "关联组内至少一条记录需人工核实。", "按关联记录逐项核实后再评估整体迁移依赖。", [_row_relation(sheet, record) for sheet, record in members])
        if "阻断" in statuses:
            _issue(group_result, "阻断", "关联组内存在阻断记录，不能作为完整导入组。", "先修复依赖或停止该关联组；不迁移孤立明细。", [_row_relation(sheet, record) for sheet, record in members if results[(sheet, record["row"])]["status"] == "阻断"])


def _csv_safe(value):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str) if value is not None else ""
    if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + text
    return text


def _csv_response(payload):
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["工作表", "原行号", "原系统记录编号", "来源关联组编号", "结果", "原因", "关联记录", "建议动作"])
    for item in payload["results"]:
        writer.writerow([
            _csv_safe(item["sheet"]), item["row"], _csv_safe(item["source_record_id"]),
            _csv_safe(item["group_id"]), _csv_safe(item["status"]),
            _csv_safe("；".join(reason["message"] for reason in item["reasons"])),
            _csv_safe(item["related_records"]), _csv_safe("；".join(item["suggested_actions"])),
        ])
    response = HttpResponse("\ufeff" + output.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="history-preflight.csv"'
    return response


def preflight_rows(rows, user):
    results, groups, _row_lookup, total = _normalize_and_validate(rows)
    _check_master_and_documents(rows, results, user)
    _check_dependencies(rows, results, groups)
    ordered = sorted(results.values(), key=lambda item: (list(SHEET_SCHEMAS).index(item["sheet"]) if item["sheet"] in SHEET_SCHEMAS else -1, item["row"]))
    counts = {status: sum(item["status"] == status for item in ordered) for status in STATUS_RANK}
    if counts["阻断"]:
        overall = "阻断"
    elif counts["待人工核实"]:
        overall = "待人工核实"
    elif counts["警告"]:
        overall = "警告"
    else:
        overall = "通过"
    group_summary = []
    for group_id, group_records in sorted(groups.items()):
        if len(group_records) != 1:
            continue
        group_record = group_records[0]
        group_status = results[("分组", group_record["row"])]["status"]
        group_summary.append({"group_id": group_id, "status": group_status, "coverage_status": group_record["data"].get("coverage_status")})
    payload = {
        "preflight_only": True,
        "approval_or_migration": False,
        "business_write_performed": False,
        "notice": PREVIEW_ONLY_NOTICE,
        "summary": {"total_rows": total, "passed": counts["通过"], "warnings": counts["警告"], "blocked": counts["阻断"], "manual_review": counts["待人工核实"], "overall_status": overall},
        "groups": group_summary,
        "results": ordered,
    }
    return payload, rows


def preflight_bytes(data, user):
    payload, _rows = preflight_rows(_read_workbook(data), user)
    return payload


class HistoryImportPreflightView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [HistoryPreflightPermission]

    def post(self, request):
        django_request = getattr(request, "_request", request)
        upload = request.FILES.get("file")
        if getattr(django_request, "_csv_import_upload_limit_exceeded", False):
            limit = settings.CSV_IMPORT_MAX_BYTES
            detail = f"文件超过大小限制（最大 {limit:,} 字节）。"
            return Response({"detail": detail, "business_write_performed": False}, status=413)
        try:
            data = _read_bounded_upload(upload, settings.CSV_IMPORT_MAX_BYTES)
            payload = preflight_bytes(data, request.user)
        except PreflightInputError as exc:
            return Response({"detail": str(exc), "business_write_performed": False}, status=exc.status_code)
        if request.query_params.get("report", "").lower() == "csv":
            return _csv_response(payload)
        return Response(payload)
