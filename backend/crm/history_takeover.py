"""Application, review and atomic execution for controlled historical takeover."""

from __future__ import annotations

import copy
import hashlib
import json
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from .history_import_preflight import SHEET_SCHEMAS, _read_workbook, preflight_rows
from .models import (
    Customer,
    HistoryTakeoverApplication,
    HistoryTakeoverEvent,
    HistoryTakeoverGroup,
    HistoryTakeoverHandoff,
    HistoryTakeoverSourceRecord,
    Order,
    OrderItem,
    PurchaseOrder,
    PurchaseOrderItem,
    SKU,
    Supplier,
)
from .permissions import development_superadmin_enabled


class TakeoverRuleError(ValueError):
    pass


def _json_safe(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _json_hash(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _decimal(value, *, optional=False):
    if optional and value in (None, ""):
        return None
    return Decimal(str(value))


def actor_snapshot(user):
    if development_superadmin_enabled():
        return None, "开发身份（非实名）", "development"
    if not user or not user.is_authenticated:
        return None, "", "identified"
    return user, user.get_full_name() or user.get_username(), "identified"


def _event(application, group, event_type, user, details=None):
    actor, label, kind = actor_snapshot(user)
    return HistoryTakeoverEvent.objects.create(
        application=application,
        group=group,
        event_type=event_type,
        actor=actor,
        actor_label=label,
        actor_kind=kind,
        details=details or {},
    )


def _grouped_rows(rows):
    grouped = {}
    for sheet, records in rows.items():
        for record in records:
            data = record["data"]
            group_id = str(data.get("group_id") or "")
            if not group_id:
                continue
            grouped.setdefault(group_id, {}).setdefault(sheet, []).append(
                {"row": record["row"], "data": copy.deepcopy(data)}
            )
    for source_rows in grouped.values():
        for sheet in SHEET_SCHEMAS:
            source_rows.setdefault(sheet, [])
    return grouped


def _master_ids(preflight_payload):
    ids = set()
    for result in preflight_payload.get("results", []):
        for related in result.get("related_records", []):
            if related.get("database_id"):
                ids.add((related.get("type"), int(related["database_id"])))
    signature = []
    models = {"客户": Customer, "供应商": Supplier, "SKU": SKU}
    for kind, pk in sorted(ids):
        model = models.get(kind)
        if model is None:
            continue
        obj = model.objects.filter(pk=pk).first()
        if obj is None:
            signature.append([kind, pk, "missing"])
            continue
        signature.append([
            kind,
            pk,
            getattr(obj, "code", None) or getattr(obj, "sku", None),
            getattr(obj, "name", None) or getattr(obj, "display_name_cn", None),
            str(getattr(obj, "updated_at", "")),
        ])
    return signature


def _fingerprint(group_rows, preflight_payload):
    group_ids = {str(record["data"].get("group_id") or "") for rows in group_rows.values() for record in rows}
    group_results = [item for item in preflight_payload.get("results", []) if item.get("group_id") in group_ids]
    return _json_hash({"rows": group_rows, "results": group_results, "masters": _master_ids(preflight_payload)})


def _group_preflight(group, user):
    rows = copy.deepcopy(group.source_rows)
    for key, target_code in (group.resolution_map or {}).items():
        try:
            sheet, row_number, field = key.split(":", 2)
            row_number = int(row_number)
        except (ValueError, TypeError):
            raise TakeoverRuleError("主档关联修正记录格式无效。")
        if sheet not in rows:
            raise TakeoverRuleError("主档关联修正工作表无效。")
        target = next((item for item in rows[sheet] if item["row"] == row_number), None)
        if target is None:
            raise TakeoverRuleError("主档关联修正行不存在。")
        target["data"][field] = str(target_code).strip()
    payload, rows = preflight_rows(rows, user)
    return payload, rows


def _status_for_group(payload, group_id):
    rows = [item for item in payload["results"] if item.get("group_id") == group_id]
    status_rank = {"通过": 0, "警告": 1, "待人工核实": 2, "阻断": 3}
    status = max((item["status"] for item in rows), key=lambda value: status_rank[value], default="阻断")
    return status, rows


@transaction.atomic
def submit_workbook(data, filename, user):
    rows = _read_workbook(data)
    payload, rows = preflight_rows(rows, user)
    digest = hashlib.sha256(data).hexdigest()
    existing = HistoryTakeoverApplication.objects.select_for_update().filter(source_sha256=digest).exclude(status__in=["rejected", "withdrawn"]).first()
    if existing:
        _event(existing, None, "duplicate_submission_reused", user, {"source_sha256": digest})
        return existing, payload, True

    actor, label, kind = actor_snapshot(user)
    application = HistoryTakeoverApplication.objects.create(
        source_file_name=str(filename or "history.xlsx").replace("\\", "/").split("/")[-1][:240],
        source_sha256=digest,
        status="submitted",
        preflight_summary=payload["summary"],
        preflight_payload={"preflight_only": True, "summary": payload["summary"]},
        created_by=actor,
        created_by_label=label,
        created_actor_kind=kind,
    )
    grouped = _grouped_rows(rows)
    for group_id, source_rows in grouped.items():
        group_data = next((row["data"] for row in source_rows.get("分组", [])), {})
        current = _status_for_group(payload, group_id)
        normalized_status = {"阻断": "blocked", "待人工核实": "pending", "警告": "pending", "通过": "pending"}[current[0]]
        group = HistoryTakeoverGroup.objects.create(
            application=application,
            source_group_id=group_id,
            source_system=str(group_data.get("source_system") or ""),
            exported_at=group_data.get("exported_at"),
            coverage_status=str(group_data.get("coverage_status") or "unknown"),
            truth_status=str(group_data.get("truth_status") or "待核实"),
            evidence_reference=str(group_data.get("evidence_reference") or "")[:500],
            notes=str(group_data.get("notes") or ""),
            source_rows=_json_safe(source_rows),
            preflight_result=_json_safe({"status": current[0], "results": current[1]}),
            status=normalized_status,
        )
        group.source_fingerprint = _fingerprint(source_rows, payload)
        group.save(update_fields=["source_fingerprint", "updated_at"])
        _event(application, group, "group_submitted", user, {"status": current[0], "records": sum(map(len, source_rows.values()))})
    _event(application, None, "application_submitted", user, {"source_sha256": digest, "groups": list(grouped)})
    return application, payload, False


def _ensure_real_complete(group):
    if group.truth_status != "真实":
        raise TakeoverRuleError("只有管理员核实为真实的关联组可以执行；模拟和待核实资料必须留在暂存区。")
    if group.coverage_status != "complete":
        raise TakeoverRuleError("资料覆盖状态不是完整，不能执行历史承接。")
    for records in group.source_rows.values():
        for row in records:
            truth = row["data"].get("truth_status")
            if truth != "真实":
                raise TakeoverRuleError("关联组中的模拟或待核实记录不能写入历史业务单据。")


def _ensure_exact_master_codes(rows):
    for sheet, field, label in (
        ("销售订单", "customer_code", "客户"),
        ("采购订单", "supplier_code", "供应商"),
        ("销售明细", "sku_code", "SKU"),
        ("采购明细", "sku_code", "SKU"),
        ("履约记录", "sku_code", "履约 SKU"),
        ("库存盘点", "sku_code", "盘点 SKU"),
    ):
        for row in rows.get(sheet, []):
            if not row["data"].get(field):
                raise TakeoverRuleError(f"{sheet}第 {row['row']} 行的{label}尚未通过编码明确关联；请人工选择现有主档。")


def review_group(group, user, decision, note, *, confirm_manual=False):
    if decision not in {"approve", "reject"}:
        raise TakeoverRuleError("审核决定无效。")
    if not str(note or "").strip():
        raise TakeoverRuleError("请填写审核依据或拒绝原因。")
    with transaction.atomic():
        group = HistoryTakeoverGroup.objects.select_for_update().select_related("application").get(pk=group.pk)
        if group.status == "executed":
            raise TakeoverRuleError("已执行的历史记录不能重新审批或覆盖；请提交追溯更正申请。")
        if group.status in {"rejected", "withdrawn"}:
            raise TakeoverRuleError("已拒绝或已撤回的关联组不能恢复；请重新提交资料和审核申请。")
        payload, _rows = _group_preflight(group, user)
        preflight_status, results = _status_for_group(payload, group.source_group_id)
        if decision == "reject":
            group.status = "rejected"
            event = "group_rejected"
        else:
            _ensure_real_complete(group)
            _ensure_exact_master_codes(_rows)
            if preflight_status == "阻断":
                raise TakeoverRuleError("当前预检仍有阻断项，先完成人工主档关联或修正来源资料。")
            if preflight_status == "待人工核实" and not confirm_manual:
                raise TakeoverRuleError("仍有待人工核实项；确认已依据原始凭证核实后，须显式勾选确认并写明依据。")
            group.status = "approved"
            group.approved_fingerprint = _fingerprint(group.source_rows, payload)
            event = "group_approved"
        group.review_note = str(note).strip()
        actor, label, kind = actor_snapshot(user)
        group.reviewed_by = actor
        group.reviewed_by_label = label
        group.reviewed_actor_kind = kind
        group.reviewed_at = timezone.now()
        group.preflight_result = _json_safe({"status": preflight_status, "results": results})
        group.source_fingerprint = _fingerprint(group.source_rows, payload)
        group.save(update_fields=["status", "review_note", "reviewed_by", "reviewed_by_label", "reviewed_actor_kind", "reviewed_at", "preflight_result", "source_fingerprint", "approved_fingerprint", "updated_at"])
        application = group.application
        application.reviewed_by = actor
        application.reviewed_by_label = label
        application.reviewed_actor_kind = kind
        application.reviewed_at = group.reviewed_at
        application.save(update_fields=["reviewed_by", "reviewed_by_label", "reviewed_actor_kind", "reviewed_at", "updated_at"])
        _event(application, group, event, user, {"status": preflight_status, "note": group.review_note, "confirm_manual": bool(confirm_manual)})
        _refresh_application_status(application)
    return group


def _refresh_application_status(application):
    statuses = list(application.groups.values_list("status", flat=True))
    if statuses and all(status == "withdrawn" for status in statuses):
        application.status = "withdrawn"
    elif statuses and all(status in {"approved", "executed"} for status in statuses):
        application.status = "executed" if all(status == "executed" for status in statuses) else "approved"
    elif statuses and all(status in {"approved", "executed", "rejected", "blocked", "withdrawn"} for status in statuses) and any(status in {"approved", "executed"} for status in statuses):
        application.status = "partially_approved"
    elif "approved" in statuses or "executed" in statuses:
        application.status = "partially_approved"
    elif statuses and all(status == "rejected" for status in statuses):
        application.status = "rejected"
    else:
        application.status = "in_review"
    application.save(update_fields=["status", "updated_at"])


def resolve_master(group, user, *, sheet, row_number, field, target_code, note):
    if sheet not in {"销售订单", "采购订单", "销售明细", "采购明细", "履约记录", "库存盘点", "收付款流水"}:
        raise TakeoverRuleError("该工作表不支持主档关联修正。")
    expected = {
        "销售订单": {"customer_code": Customer},
        "采购订单": {"supplier_code": Supplier},
        "销售明细": {"sku_code": SKU},
        "采购明细": {"sku_code": SKU},
        "履约记录": {"sku_code": SKU},
        "库存盘点": {"sku_code": SKU},
        "收付款流水": {"customer_code": Customer, "supplier_code": Supplier},
    }
    model = expected.get(sheet, {}).get(field)
    if not model or not str(note or "").strip():
        raise TakeoverRuleError("请提供允许的目标主档字段和关联依据。")
    lookup = "sku" if model is SKU else "code"
    if model.objects.filter(**{lookup: str(target_code).strip()}).count() != 1:
        raise TakeoverRuleError("目标编码不存在或不唯一；本流程不会自动创建主档。")
    with transaction.atomic():
        group = HistoryTakeoverGroup.objects.select_for_update().select_related("application").get(pk=group.pk)
        if group.status in {"executed", "rejected", "withdrawn"}:
            raise TakeoverRuleError("已执行、拒绝或撤回的关联组不能修改主档关联；请重新提交资料和审核申请。")
        rows = next((item for item in group.source_rows.get(sheet, []) if int(item["row"]) == int(row_number)), None)
        if rows is None:
            raise TakeoverRuleError("来源行不存在。")
        key = f"{sheet}:{int(row_number)}:{field}"
        mapping = dict(group.resolution_map or {})
        before = mapping.get(key) or rows["data"].get(field)
        mapping[key] = str(target_code).strip()
        group.resolution_map = mapping
        payload, _rows = _group_preflight(group, user)
        preflight_status, result_rows = _status_for_group(payload, group.source_group_id)
        group.status = "blocked" if preflight_status == "阻断" else "pending"
        group.approved_fingerprint = ""
        group.review_note = ""
        group.preflight_result = _json_safe({"status": preflight_status, "results": result_rows})
        group.source_fingerprint = _fingerprint(group.source_rows, payload)
        group.save(update_fields=["resolution_map", "status", "approved_fingerprint", "review_note", "preflight_result", "source_fingerprint", "updated_at"])
        _event(group.application, group, "master_resolution_added", user, {"sheet": sheet, "row": int(row_number), "field": field, "before": before, "target_code": str(target_code).strip(), "note": str(note).strip()})
        _refresh_application_status(group.application)
    return group


def _record_source_id(sheet, data):
    if sheet == "销售明细":
        return f"{data.get('source_order_id', '')}:{data.get('source_line_id', '')}"
    if sheet == "采购明细":
        return f"{data.get('source_purchase_id', '')}:{data.get('source_line_id', '')}"
    for key in ("source_record_id", "source_event_id", "source_line_id", "source_plan_id"):
        if data.get(key):
            return str(data[key])
    return str(data.get("group_id") or "")


def _truth_rows(group):
    for sheet, rows in group.source_rows.items():
        for item in rows:
            data = item["data"]
            identity = _record_source_id(sheet, data)
            if identity and HistoryTakeoverSourceRecord.objects.filter(source_system=group.source_system, record_type=sheet, source_record_id=identity).exists():
                raise TakeoverRuleError(f"来源记录已由其他承接批次登记：{sheet} / {identity}。")


def _master_for(model, code, label):
    lookup = "sku" if model is SKU else "code"
    if not code:
        raise TakeoverRuleError(f"{label}未通过明确编码关联，不能猜测历史主体。")
    rows = list(model.objects.filter(**{lookup: str(code).strip()})[:2])
    if len(rows) != 1:
        raise TakeoverRuleError(f"{label}编码在执行前已不存在或不唯一，需重新审核。")
    return rows[0]


def _create_history_documents(group, rows):
    sales_orders = {}
    purchase_orders = {}
    sales_lines = {}
    purchase_lines = {}
    results = {"orders": [], "purchase_orders": [], "source_records": []}

    for entry in rows.get("销售订单", []):
        data = entry["data"]
        customer = _master_for(Customer, data.get("customer_code"), "客户")
        order = Order.objects.create(
            order_no=str(data["order_no"]).strip(), customer=customer,
            customer_name_snapshot=str(data["customer_name_snapshot"] or ""),
            customer_country_snapshot=str(data.get("customer_country_snapshot") or ""),
            customer_address_snapshot=str(data.get("customer_address_snapshot") or ""),
            customer_contact_name_snapshot=str(data.get("customer_contact_name_snapshot") or ""),
            customer_phone_snapshot=str(data.get("customer_phone_snapshot") or ""),
            customer_email_snapshot=str(data.get("customer_email_snapshot") or ""),
            quote=None, order_date=data["order_date"], status="historical", historical_only=True,
            currency=str(data["currency"]).strip(), exchange_rate=data["exchange_rate"],
            shipping_fee=data["shipping_fee"], discount=data["discount"],
            notes=str(data.get("notes") or ""),
        )
        sales_orders[str(data["source_record_id"])] = order
        results["orders"].append({"source_record_id": str(data["source_record_id"]), "id": order.pk, "order_no": order.order_no, "status": order.status})

    sales_item_rows = []
    for entry in rows.get("销售明细", []):
        data = entry["data"]
        parent = sales_orders[str(data["source_order_id"])]
        sku = _master_for(SKU, data.get("sku_code"), "SKU")
        trade_snapshot = {
            "unit": str(data.get("trade_unit_snapshot") or data["unit_snapshot"]),
            "base_unit": str(data["base_unit_snapshot"]),
            "factor": str(data.get("trade_factor_snapshot") or "1"),
            "name": str(data.get("trade_unit_snapshot") or ""),
        }
        sales_item_rows.append(OrderItem(
            order=parent, sku=sku, sku_code_snapshot=str(data.get("sku_code") or ""),
            sales_model_snapshot=str(data.get("sales_model_snapshot") or ""),
            display_name_snapshot=str(data["sku_name_snapshot"]),
            description_snapshot=str(data.get("description_snapshot") or ""),
            unit_snapshot=str(data["unit_snapshot"]), quantity=data["quantity_base"],
            unit_price=data["unit_price"], notes=str(data.get("notes") or "")[:200],
            trade_quantity=_decimal(data.get("trade_quantity"), optional=True),
            trade_unit_price=_decimal(data.get("trade_unit_price"), optional=True),
            trade_snapshot=trade_snapshot,
        ))
        sales_lines[(str(data["source_order_id"]), str(data["source_line_id"]))] = sales_item_rows[-1]
    OrderItem.objects.bulk_create(sales_item_rows)

    for entry in rows.get("采购订单", []):
        data = entry["data"]
        supplier = _master_for(Supplier, data.get("supplier_code"), "供应商")
        po = PurchaseOrder.objects.create(
            purchase_no=str(data["purchase_no"]).strip(), supplier=supplier,
            supplier_name_snapshot=str(data["supplier_name_snapshot"] or ""),
            supplier_address_snapshot=str(data.get("supplier_address_snapshot") or ""),
            supplier_contact_name_snapshot=str(data.get("supplier_contact_name_snapshot") or ""),
            supplier_phone_snapshot=str(data.get("supplier_phone_snapshot") or ""),
            supplier_email_snapshot=str(data.get("supplier_email_snapshot") or ""),
            order=None, order_date=data["order_date"], status="historical", historical_only=True,
            currency=str(data["currency"]).strip(), exchange_rate=data["exchange_rate"],
            notes=str(data.get("notes") or ""), payment_terms_snapshot=[],
        )
        purchase_orders[str(data["source_record_id"])] = po
        results["purchase_orders"].append({"source_record_id": str(data["source_record_id"]), "id": po.pk, "purchase_no": po.purchase_no, "status": po.status})

    purchase_item_rows = []
    for entry in rows.get("采购明细", []):
        data = entry["data"]
        parent = purchase_orders[str(data["source_purchase_id"])]
        sku = _master_for(SKU, data.get("sku_code"), "SKU")
        trade_snapshot = {
            "unit": str(data.get("trade_unit_snapshot") or data["unit_snapshot"]),
            "base_unit": str(data["base_unit_snapshot"]),
            "factor": str(data.get("trade_factor_snapshot") or "1"),
            "name": str(data.get("trade_unit_snapshot") or ""),
        }
        purchase_item_rows.append(PurchaseOrderItem(
            purchase_order=parent, sku=sku, supplier_sku=None,
            sku_code_snapshot=str(data.get("sku_code") or ""),
            sales_model_snapshot=str(data.get("sales_model_snapshot") or ""),
            display_name_snapshot=str(data["sku_name_snapshot"]),
            description_snapshot=str(data.get("description_snapshot") or ""),
            supplier_name_snapshot=str(data.get("supplier_name_snapshot") or ""),
            supplier_model_snapshot=str(data.get("supplier_model_snapshot") or ""),
            supplier_sku_code_snapshot=str(data.get("supplier_sku_code_snapshot") or ""),
            quantity=data["quantity_base"], unit_price=data["unit_price"],
            trade_quantity=_decimal(data.get("trade_quantity"), optional=True),
            trade_unit_price=_decimal(data.get("trade_unit_price"), optional=True),
            trade_snapshot=trade_snapshot,
        ))
        purchase_lines[(str(data["source_purchase_id"]), str(data["source_line_id"]))] = purchase_item_rows[-1]
    # bulk_create intentionally bypasses PurchaseOrderItem.save(), which would
    # create an ISS-039 cost allocation for a historical document.
    PurchaseOrderItem.objects.bulk_create(purchase_item_rows)

    for key, instance in sales_lines.items():
        results["source_records"].append(("销售明细", f"{key[0]}:{key[1]}", "crm.OrderItem", instance.pk))
    for key, instance in purchase_lines.items():
        results["source_records"].append(("采购明细", f"{key[0]}:{key[1]}", "crm.PurchaseOrderItem", instance.pk))
    return sales_orders, purchase_orders, results


def _build_remainder(rows):
    events_by_line = defaultdict(Decimal)
    for entry in rows.get("履约记录", []):
        data = entry["data"]
        if data.get("truth_status") != "真实" or data.get("lifecycle_state") != "effective":
            continue
        event_type = data.get("event_type")
        sign = Decimal("1") if event_type in {"shipment", "goods_receipt"} else Decimal("-1")
        key = (str(data.get("parent_source_id") or ""), str(data.get("source_line_id") or ""), "sales" if event_type.startswith("shipment") else "purchase")
        events_by_line[key] += sign * Decimal(str(data.get("quantity_base") or "0"))

    snapshot = {"sales_orders": [], "purchase_orders": [], "source_event_count": len(rows.get("履约记录", []))}
    for order_sheet, line_sheet, parent_field, collection, flow_kind in (
        ("销售订单", "销售明细", "source_order_id", "sales_orders", "sales"),
        ("采购订单", "采购明细", "source_purchase_id", "purchase_orders", "purchase"),
    ):
        lines_by_parent = defaultdict(list)
        for line in rows.get(line_sheet, []):
            lines_by_parent[str(line["data"].get(parent_field) or "")].append(line["data"])
        for order_entry in rows.get(order_sheet, []):
            data = order_entry["data"]
            parent_source_id = str(data["source_record_id"])
            lifecycle = str(data["lifecycle_state"])
            if lifecycle == "unknown":
                raise TakeoverRuleError(f"订单 {data.get('order_no') or data.get('purchase_no')} 的来源状态尚未核实，不能执行。")
            summary_lines = []
            for line in lines_by_parent[parent_source_id]:
                ordered = Decimal(str(line["quantity_base"]))
                completed = events_by_line[(parent_source_id, str(line["source_line_id"]), flow_kind)]
                if completed < 0 or completed > ordered:
                    raise TakeoverRuleError(f"{data.get('order_no') or data.get('purchase_no')} 行 {line['source_line_id']} 的净履约数量超出订单数量，需人工核对冲销链。")
                if lifecycle == "completed" and completed != ordered:
                    raise TakeoverRuleError(f"已结清/完成的订单 {data.get('order_no') or data.get('purchase_no')} 与履约记录数量不一致。")
                if lifecycle == "partial" and not (Decimal("0") < completed < ordered):
                    raise TakeoverRuleError(f"部分完成订单 {data.get('order_no') or data.get('purchase_no')} 缺少一致的部分履约证据。")
                if lifecycle == "open" and completed != 0:
                    raise TakeoverRuleError(f"未结订单 {data.get('order_no') or data.get('purchase_no')} 已有履约事实；请核实是否应标记为部分完成。")
                remaining = Decimal("0") if lifecycle in {"completed", "cancelled"} else ordered - completed
                summary_lines.append({
                    "source_line_id": str(line["source_line_id"]),
                    "sku_code": str(line.get("sku_code") or ""),
                    "ordered_quantity_base": str(ordered),
                    "verified_net_fulfilled_quantity_base": str(completed),
                    "remaining_quantity_base": str(remaining),
                    "unit_snapshot": str(line["unit_snapshot"]),
                })
            snapshot[collection].append({
                "source_record_id": parent_source_id,
                "source_document_no": str(data.get("order_no") or data.get("purchase_no") or ""),
                "source_lifecycle_state": lifecycle,
                "lines": summary_lines,
            })
    return snapshot


def _source_rows_for_handoff(group, rows, remainder):
    plans = rows.get("收付款计划", [])
    transactions = rows.get("收付款流水", [])
    inventory = rows.get("库存盘点", [])
    fulfillment = rows.get("履约记录", [])
    return {
        "finance": {
            "contract_version": "1",
            "status": "not_connected",
            "reason": "归档不会自动记账；须另行映射凭证和账户、复核并通过正式财务服务办理。",
            "payment_plans": [item["data"] for item in plans],
            "source_transactions": [item["data"] for item in transactions],
        },
        "inventory": {
            "contract_version": "1",
            "status": "not_connected",
            "reason": "归档不会自动启用库存；须另行核对盘点范围、所有权及成本并复核启用。",
            "count_baselines": [item["data"] for item in inventory],
        },
        "fulfillment": {
            "contract_version": "1",
            "status": "not_connected",
            "reason": "历史履约事实仅归档；剩余业务须另行核对、复核并建立接续单。",
            "source_events": [item["data"] for item in fulfillment],
            "remainder_snapshot": remainder,
        },
    }


@transaction.atomic
def execute_group(group, user):
    group = HistoryTakeoverGroup.objects.select_for_update().select_related("application").get(pk=group.pk)
    if group.status == "executed":
        return group, True
    if group.status != "approved":
        raise TakeoverRuleError("只有已审核批准的关联组可以执行。")
    _ensure_real_complete(group)
    payload, rows = _group_preflight(group, user)
    _ensure_exact_master_codes(rows)
    preflight_status, result_rows = _status_for_group(payload, group.source_group_id)
    current_fingerprint = _fingerprint(group.source_rows, payload)
    if preflight_status == "阻断" or current_fingerprint != group.approved_fingerprint:
        group.status = "needs_reapproval"
        group.source_fingerprint = current_fingerprint
        group.preflight_result = {"status": preflight_status, "results": result_rows}
        group.save(update_fields=["status", "source_fingerprint", "preflight_result", "updated_at"])
        _event(group.application, group, "execution_stopped_reapproval_required", user, {"status": preflight_status, "approved_fingerprint": group.approved_fingerprint, "current_fingerprint": current_fingerprint})
        _refresh_application_status(group.application)
        return group, False

    remainder = _build_remainder(rows)
    _truth_rows(group)
    # Validate every master reference again immediately before creating records.
    for entry in rows.get("销售订单", []):
        _master_for(Customer, entry["data"].get("customer_code"), "客户")
    for entry in rows.get("采购订单", []):
        _master_for(Supplier, entry["data"].get("supplier_code"), "供应商")
    for sheet in ("销售明细", "采购明细", "履约记录", "库存盘点"):
        for entry in rows.get(sheet, []):
            if entry["data"].get("sku_code"):
                _master_for(SKU, entry["data"]["sku_code"], "SKU")

    sales_orders, purchase_orders, created = _create_history_documents(group, rows)
    _event_payload = _source_rows_for_handoff(group, rows, remainder)
    for kind, data in _event_payload.items():
            HistoryTakeoverHandoff.objects.create(group=group, kind=kind, status="not_connected", payload=_json_safe(data))

    source_records = []
    for sheet, entries in rows.items():
        for entry in entries:
            data = entry["data"]
            source_id = _record_source_id(sheet, data)
            if not source_id:
                continue
            target_model, target_id = "", None
            if sheet == "销售订单":
                target_model, target_id = "crm.Order", sales_orders[str(data["source_record_id"])].pk
            elif sheet == "采购订单":
                target_model, target_id = "crm.PurchaseOrder", purchase_orders[str(data["source_record_id"])].pk
            elif sheet == "销售明细":
                target_model, target_id = "crm.OrderItem", next(item[3] for item in created["source_records"] if item[0] == sheet and item[1] == source_id)
            elif sheet == "采购明细":
                target_model, target_id = "crm.PurchaseOrderItem", next(item[3] for item in created["source_records"] if item[0] == sheet and item[1] == source_id)
            original_data = next((item["data"] for item in group.source_rows.get(sheet, []) if item["row"] == entry["row"]), data)
            source_records.append(HistoryTakeoverSourceRecord(
                group=group, source_system=group.source_system, record_type=sheet,
                source_record_id=source_id, source_snapshot={"source": _json_safe(original_data), "resolved": _json_safe(data)},
                target_model=target_model, target_id=target_id,
            ))
    HistoryTakeoverSourceRecord.objects.bulk_create(source_records)

    execution_result = {
        "orders": created["orders"],
        "purchase_orders": created["purchase_orders"],
        "finance_records_posted": 0,
        "inventory_movements_posted": 0,
        "fulfillment_records_posted": 0,
        "purchase_cost_allocations_created": 0,
        "handoff_status": {key: "not_connected" for key in _event_payload},
        "source_record_count": len(source_records),
    }
    group.status = "executed"
    group.execution_key = _json_hash([group.source_system, group.source_group_id, group.application.source_sha256])
    group.execution_result = execution_result
    group.remainder_snapshot = remainder
    group.finance_handoff_status = "not_connected"
    group.inventory_handoff_status = "not_connected"
    group.fulfillment_handoff_status = "not_connected"
    group.save(update_fields=["status", "execution_key", "execution_result", "remainder_snapshot", "finance_handoff_status", "inventory_handoff_status", "fulfillment_handoff_status", "updated_at"])
    _event(group.application, group, "group_executed", user, execution_result)
    _refresh_application_status(group.application)
    return group, False


def withdraw_group(group, user, reason):
    if not str(reason or "").strip():
        raise TakeoverRuleError("请填写撤回原因。")
    with transaction.atomic():
        group = HistoryTakeoverGroup.objects.select_for_update().select_related("application").get(pk=group.pk)
        if group.status == "executed":
            raise TakeoverRuleError("已有历史业务记录，不允许删除或撤回；请提交带凭证的更正申请。")
        group.status = "withdrawn"
        group.review_note = str(reason).strip()
        group.save(update_fields=["status", "review_note", "updated_at"])
        _event(group.application, group, "group_withdrawn", user, {"reason": str(reason).strip()})
        _refresh_application_status(group.application)
    return group


def submit_correction(group, user, *, kind, occurred_at, details, reason):
    if not str(reason or "").strip() or not isinstance(details, dict) or not details:
        raise TakeoverRuleError("更正申请须提供原因和具体内容。")
    if kind == "late_fact" and not occurred_at:
        raise TakeoverRuleError("迟到记录必须保留实际发生日期。")
    if occurred_at:
        try:
            if date.fromisoformat(str(occurred_at)).isoformat() != str(occurred_at):
                raise ValueError
        except ValueError as exc:
            raise TakeoverRuleError("实际发生日期须为有效的 YYYY-MM-DD。") from exc
    if kind not in {"late_fact", "correction", "voucher_added"}:
        raise TakeoverRuleError("更正类型无效。")
    with transaction.atomic():
        group = HistoryTakeoverGroup.objects.select_for_update().select_related("application").get(pk=group.pk)
        if group.status != "executed":
            raise TakeoverRuleError("只有已承接的关联组可以提交迟到记录、审计更正或补交凭证。")
        _event(group.application, group, f"{kind}_submitted", user, {
            "occurred_at": str(occurred_at or ""),
            "details": details,
            "reason": str(reason).strip(),
            "requires_review": True,
            "business_rows_overwritten": False,
            "period_reclassification_review_required": bool(occurred_at and str(occurred_at) < timezone.localdate().isoformat()),
        })
    return group


def review_correction(group, user, *, event_id, decision, note):
    if decision not in {"approve", "reject"} or not str(note or "").strip():
        raise TakeoverRuleError("请提供有效的审核决定和依据。")
    with transaction.atomic():
        group = HistoryTakeoverGroup.objects.select_for_update().select_related("application").get(pk=group.pk)
        source_event = group.events.filter(pk=event_id, event_type__in=["late_fact_submitted", "correction_submitted", "voucher_added_submitted"]).first()
        if source_event is None:
            raise TakeoverRuleError("找不到待审核的更正或补交凭证记录。")
        if group.events.filter(event_type="correction_reviewed", details__source_event_id=int(event_id)).exists():
            raise TakeoverRuleError("该追溯申请已经审核；如需补充说明，请另提交一条更正记录。")
        if decision == "approve":
            verified = list(group.verified_correction_ids or [])
            if int(event_id) not in verified:
                verified.append(int(event_id))
            group.verified_correction_ids = verified
            group.save(update_fields=["verified_correction_ids", "updated_at"])
        _event(group.application, group, "correction_reviewed", user, {
            "source_event_id": int(event_id),
            "decision": decision,
            "note": str(note).strip(),
            "source_event_unchanged": True,
            "requires_period_reclassification_review": bool(source_event.details.get("period_reclassification_review_required")),
        })
    return group
