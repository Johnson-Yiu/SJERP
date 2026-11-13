"""Atomic, append-only quantity changes for confirmed sales orders."""

import hashlib
import json
from copy import copy
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Sum

from crm.history_products import document_lines
from crm.models import AdvanceAllocation, Order, OrderItem, OrderQuantityAdjustment, PaymentPlan
from crm.money import LEGACY_AMOUNT_CALCULATION_VERSION, document_total, legacy_document_total, money
from crm.services.finance import _sync_plan_status, _writeoff_total
from crm.services.fulfillment import _shipped_quantity, order_item_metrics, rebalance_sku_reservations
from crm.permissions import development_superadmin_enabled
from crm.services.historical import reject_historical


QUANTITY_QUANTUM = Decimal("0.01")
MONEY_QUANTUM = Decimal("0.0001")
ADJUSTABLE_STATUSES = {"confirmed", "production", "shipped"}
FINANCIAL_MASK = "财务影响信息受权限保护。"
PROCUREMENT_MASK = "采购影响信息受权限保护。"


class QuantityAdjustmentConflict(ValidationError):
    """A stale preview or duplicate request must not overwrite newer work."""


def _fits_decimal(value, *, max_digits, decimal_places):
    sign, digits, exponent = value.as_tuple()
    integer_digits = max(0, len(digits) + exponent) if exponent < 0 else len(digits) + exponent
    return integer_digits + decimal_places <= max_digits


def _decimal(value, label, *, positive=True, quantum=QUANTITY_QUANTUM, max_digits=14, decimal_places=2):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError(f"{label}必须是有效数字。")
    if not number.is_finite() or (positive and number <= 0) or (not positive and number < 0):
        raise ValidationError(f"{label}必须是大于零的有效数字。" if positive else f"{label}不能为负数。")
    try:
        quantized = number.quantize(quantum)
    except (InvalidOperation, ValueError):
        raise ValidationError(f"{label}超出系统可保存范围。")
    if number != quantized:
        raise ValidationError(f"{label}最多保留 {abs(quantum.as_tuple().exponent)} 位小数。")
    if not _fits_decimal(quantized, max_digits=max_digits, decimal_places=decimal_places):
        raise ValidationError(f"{label}超出系统可保存范围。")
    return quantized


def _money(value):
    try:
        result = Decimal(value).quantize(MONEY_QUANTUM)
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError("订单金额超出系统可保存范围。")
    if not _fits_decimal(result, max_digits=14, decimal_places=4):
        raise ValidationError("订单金额超出系统可保存范围。")
    return result


def _json_decimal(value):
    return str(value)


def _request_key(payload):
    key = str(payload.get("request_key") or "").strip()
    if not key:
        raise ValidationError("请提供请求幂等键，重复提交时必须沿用同一请求幂等键。")
    if len(key) > 100:
        raise ValidationError("请求幂等键过长。")
    return key


def _canonical_request(payload):
    reason = str(payload.get("reason") or "").strip()
    if not reason:
        raise ValidationError("数量变更原因不能为空。")
    try:
        version = int(payload.get("version"))
    except (TypeError, ValueError):
        raise ValidationError("请使用订单当前的数量变更版本重新预览。")
    raw_items = payload.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise ValidationError("请至少提交一条订单明细的数量变更。")
    canonical_items = []
    for row in raw_items:
        if not isinstance(row, dict):
            raise ValidationError("数量变更明细格式无效。")
        try:
            item_id = int(row.get("order_item"))
        except (TypeError, ValueError):
            raise ValidationError("数量变更明细缺少有效订单行。")
        value_key = "new_trade_quantity" if "new_trade_quantity" in row else "new_quantity"
        if value_key not in row:
            raise ValidationError("每条订单明细都必须填写新的数量。")
        canonical_items.append({"order_item": item_id, value_key: str(row[value_key])})
    canonical_items.sort(key=lambda row: row["order_item"])
    canonical = {"version": version, "reason": reason, "items": canonical_items}
    fingerprint = hashlib.sha256(json.dumps(canonical, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    return version, reason, canonical_items, fingerprint


def _line_value(item, row):
    if item.trade_unit_id or item.trade_quantity is not None or item.trade_unit_price is not None:
        snapshot = item.trade_snapshot or {}
        if item.trade_quantity is None or item.trade_unit_price is None:
            raise ValidationError("原交易数量或单价缺失，不能安全调整。")
        if not item.trade_unit_id and not isinstance(snapshot.get("allow_fraction"), bool):
            raise ValidationError("原交易单位缺少拆分规则，不能安全调整。")
        try:
            factor = Decimal(str(snapshot["factor"]))
        except (KeyError, InvalidOperation, TypeError, ValueError):
            raise ValidationError(f"{item.sku_code_snapshot or item.sku.sku} 缺少可靠的交易单位换算快照，不能安全调整。")
        if not factor.is_finite() or factor <= 0:
            raise ValidationError("原交易单位换算关系无效，不能安全调整。")
        if not item.trade_unit_id and item.trade_quantity * factor != item.quantity:
            raise ValidationError("原交易数量与基础数量不符合换算快照，不能安全调整。")
        if "new_trade_quantity" in row:
            trade_quantity = _decimal(row["new_trade_quantity"], "交易数量")
        elif not item.trade_unit_id and "new_quantity" in row:
            requested_base = _decimal(row["new_quantity"], "基础数量")
            trade_quantity = _decimal(requested_base / factor, "换算后的交易数量")
            if trade_quantity * factor != requested_base:
                raise ValidationError("原交易单位无法准确换算该基础数量。")
        else:
            raise ValidationError(f"{item.sku_code_snapshot or item.sku.sku} 必须按原交易单位填写数量。")
        if not snapshot.get("allow_fraction", False) and trade_quantity != trade_quantity.to_integral_value():
            raise ValidationError(f"{item.sku_code_snapshot or item.sku.sku} 的原交易单位只允许整包装数量。")
        base_quantity = trade_quantity * factor
        exact_base_quantity = base_quantity
        try:
            base_quantity = base_quantity.quantize(QUANTITY_QUANTUM)
        except (InvalidOperation, ValueError):
            raise ValidationError("交易单位换算后的基础数量超出系统可保存范围。")
        if exact_base_quantity != base_quantity or not _fits_decimal(base_quantity, max_digits=14, decimal_places=2):
            raise ValidationError("交易单位换算后的基础数量不符合系统精度。")
        return trade_quantity, base_quantity
    if "new_quantity" not in row:
        raise ValidationError(f"{item.sku_code_snapshot or item.sku.sku} 必须填写基础数量。")
    return None, _decimal(row["new_quantity"], "基础数量")


def _normalized_lines(order, canonical_items):
    item_ids = [row["order_item"] for row in canonical_items]
    if len(set(item_ids)) != len(item_ids):
        raise ValidationError("同一订单行不能重复提交。")
    items = {
        item.pk: item
        for item in order.items.select_for_update(of=("self",)).select_related("sku", "trade_unit").filter(pk__in=item_ids)
    }
    if len(items) != len(item_ids):
        raise ValidationError("数量变更明细不属于当前销售订单。")
    normalized = []
    line_amount = Decimal if order.amount_calculation_version == LEGACY_AMOUNT_CALCULATION_VERSION else money
    for row in canonical_items:
        item = items[row["order_item"]]
        trade_quantity, base_quantity = _line_value(item, row)
        shipped = _shipped_quantity(item)
        if base_quantity < shipped:
            raise ValidationError(
                f"{item.sku_code_snapshot or item.sku.sku} 的新数量不能低于已发货数量 {shipped}。"
            )
        proposed = copy(item)
        proposed.quantity = base_quantity
        if trade_quantity is not None:
            proposed.trade_quantity = trade_quantity
        normalized.append({
            "item": item,
            "old_quantity": item.quantity,
            "new_quantity": base_quantity,
            "old_trade_quantity": item.trade_quantity,
            "new_trade_quantity": trade_quantity,
            "old_amount": line_amount(item.amount),
            "new_amount": line_amount(proposed.amount),
            "proposed": proposed,
            "shipped_quantity": shipped,
        })
    changed = [row for row in normalized if row["new_quantity"] != row["old_quantity"]]
    if not changed:
        raise ValidationError("数量没有变化。")
    return changed


def _receivable_plans(order):
    return order.payment_plans.select_for_update().filter(direction="receivable").exclude(
        status="cancelled",
    ).order_by("-due_date", "-id")


def _company_fee_credit(order, plans):
    # Direct receipts can include an applied fee smaller than the fee on the
    # voucher. Advance allocations already store the exact applied fee split.
    receipts = order.transactions.filter(
        status="confirmed", kind="customer_receipt", direction="income",
        plan__in=plans, fee_responsibility="company", fee_evidence__isnull=False,
    )
    direct_credit = sum((
        row.settlement_amount - row.amount for row in receipts
        if 0 < row.settlement_amount - row.amount <= row.bank_fee_amount
    ), Decimal("0"))
    allocated_credit = AdvanceAllocation.objects.filter(
        plan__in=plans, is_active=True, advance__status="confirmed", cash_amount__isnull=False,
    ).aggregate(total=Sum("fee_credit_amount"))["total"] or Decimal("0")
    return direct_credit + allocated_credit


def _financial_state(order, before_total, after_total):
    old_total = _money(before_total)
    target_total = _money(after_total)
    continuation = getattr(order, "history_continuation", None)
    financial_order = continuation.archived_order if continuation else order
    plans = list(_receivable_plans(financial_order))
    planned = sum((plan.planned_amount for plan in plans), Decimal("0"))
    settled = sum((plan.settled_amount for plan in plans), Decimal("0"))
    reductions = [_writeoff_total(plan) for plan in plans]
    balances = [
        plan.planned_amount - plan.settled_amount - reduction
        for plan, reduction in zip(plans, reductions)
    ]
    outstanding = sum((balance for plan, balance in zip(plans, balances) if plan.status == "open"), Decimal("0"))
    paid = _money(financial_order.paid_amount)
    fee_credit = _company_fee_credit(financial_order, plans)
    reasons = []
    if not continuation and planned != old_total:
        reasons.append(f"现有应收计划合计 {_money(planned)} 与订单金额 {old_total} 不一致")
    if settled != paid + fee_credit:
        reasons.append(f"应收已核销 {_money(settled)} 与净实收 {paid} 加已核销手续费 {_money(fee_credit)} 不符，请核对流水")
    if any(
        reduction < 0 or balance < 0 or (plan.status == "settled" and balance != 0)
        for plan, reduction, balance in zip(plans, reductions, balances)
    ):
        reasons.append("应收计划余额或状态异常，请核对核销及抵减记录")
    delta = _money(target_total - old_total)
    if delta < 0 and -delta > outstanding:
        reasons.append("数量减少超过未结应收计划余额")
    return {
        "before_total": old_total,
        "after_total": target_total,
        "amount_delta": delta,
        "planned": _money(planned),
        "settled": _money(settled),
        "paid": paid,
        "fee_credit": _money(fee_credit),
        "receivable_reduction": _money(sum(reductions, Decimal("0"))),
        "outstanding_before": _money(outstanding),
        "outstanding_after": _money(outstanding + delta),
        "blocking_reasons": reasons,
    }


def _contract_totals(order, normalized):
    lines = list(document_lines(order))
    proposed = {row["item"].pk: row["proposed"] for row in normalized}
    legacy = order.amount_calculation_version == LEGACY_AMOUNT_CALCULATION_VERSION
    calculate = legacy_document_total if legacy else document_total
    terms = {"shipping_fee": order.shipping_fee, "discount": order.discount}
    approved = order.approved_change_amount
    before = calculate(lines, **terms) + approved
    after = calculate([proposed.get(line.pk, line) for line in lines], **terms) + approved
    return (before, after) if legacy else (money(before), money(after))


def _metrics_snapshot(item, *, quantity_overrides=None):
    metrics = order_item_metrics(item)
    overrides = quantity_overrides or {}
    group_items = list(
        OrderItem.objects.filter(order_id=item.order_id, sku_id=item.sku_id).order_by("id")
    )
    ordered_quantity = sum((overrides.get(row.pk, row.quantity) for row in group_items), Decimal("0"))
    shipped_quantity = sum((_shipped_quantity(row) for row in group_items), Decimal("0"))
    allocated = sum(
        (
            row.reservations.aggregate(total=Sum("quantity"))["total"] or Decimal("0")
            for row in group_items
        ),
        Decimal("0"),
    )
    purchased = metrics["purchased_quantity"]
    received = metrics["received_quantity"]
    outstanding_purchase = max(Decimal("0"), purchased - received)
    to_procure = max(Decimal("0"), ordered_quantity - shipped_quantity - allocated - outstanding_purchase)
    excess = max(Decimal("0"), purchased - ordered_quantity)
    return {
        "order_item": item.pk,
        "group_key": f"{item.order_id}:{item.sku_id}",
        "sku_code": item.sku_code_snapshot or item.sku.sku,
        "base_unit": (item.trade_snapshot or {}).get("base_unit") or item.unit_snapshot or item.sku.unit,
        "ordered_quantity": _json_decimal(ordered_quantity),
        "shipped_quantity": _json_decimal(shipped_quantity),
        "purchased_quantity": _json_decimal(purchased),
        "received_quantity": _json_decimal(received),
        "in_transit_quantity": _json_decimal(metrics["in_transit_quantity"]),
        "to_procure_quantity": _json_decimal(to_procure),
        "procurement_excess_quantity": _json_decimal(excess),
    }


def _build_preview(order, normalized, *, financial_strict=False):
    financial = _financial_state(order, *_contract_totals(order, normalized))
    lines = []
    warnings = []
    warning_details = []
    warned_procurement_groups = set()
    quantity_overrides = {row["item"].pk: row["new_quantity"] for row in normalized}
    before_groups = {}
    after_groups = {}
    for row in normalized:
        item = row["item"]
        group_key = f"{item.order_id}:{item.sku_id}"
        before = before_groups.setdefault(group_key, _metrics_snapshot(item))
        after = after_groups.setdefault(group_key, _metrics_snapshot(item, quantity_overrides=quantity_overrides))
        excess = Decimal(after["procurement_excess_quantity"])
        if Decimal(before["purchased_quantity"]) > 0 and group_key not in warned_procurement_groups and excess <= 0:
            message = f"{after['sku_code']} 采购需求已变化；已有采购保持原样，请人工核对数量及交期。"
            warnings.append(message)
            warning_details.append({"kind": "procurement", "group_key": group_key, "message": message})
            warned_procurement_groups.add(group_key)
        if excess > 0 and group_key not in warned_procurement_groups:
            message = (
                f"{after['sku_code']} 可能产生采购过剩 {excess} {after['base_unit']}，请人工处理，系统不会自动取消采购单。"
            )
            warnings.append(
                message
            )
            warning_details.append({"kind": "procurement", "group_key": group_key, "message": message})
            warned_procurement_groups.add(group_key)
        lines.append({
            "order_item": item.pk,
            "sku": item.sku_id,
            "sku_code": after["sku_code"],
            "sales_model": item.sales_model_snapshot,
            "display_name": item.display_name_snapshot,
            "base_unit": after["base_unit"],
            "trade_unit": item.trade_unit_id,
            "trade_snapshot": item.trade_snapshot,
            "old_trade_quantity": _json_decimal(row["old_trade_quantity"]) if row["old_trade_quantity"] is not None else None,
            "new_trade_quantity": _json_decimal(row["new_trade_quantity"]) if row["new_trade_quantity"] is not None else None,
            "old_quantity": _json_decimal(row["old_quantity"]),
            "new_quantity": _json_decimal(row["new_quantity"]),
            "quantity_delta": _json_decimal(row["new_quantity"] - row["old_quantity"]),
            "old_amount": _json_decimal(row["old_amount"]),
            "new_amount": _json_decimal(row["new_amount"]),
            "amount_delta": _json_decimal(row["new_amount"] - row["old_amount"]),
            "shipped_quantity": _json_decimal(row["shipped_quantity"]),
            "before": before,
            "after": after,
        })
    if financial["blocking_reasons"]:
        warnings.extend(financial["blocking_reasons"])
        warning_details.extend({"kind": "financial", "message": message} for message in financial["blocking_reasons"])
    result = {
        "order": order.pk,
        "order_no": order.order_no,
        "status": order.status,
        "version": order.quantity_change_version,
        "reason_required": True,
        "lines": lines,
        "financial": {
            "currency": order.currency,
            "before_total": _json_decimal(financial["before_total"]),
            "after_total": _json_decimal(financial["after_total"]),
            "amount_delta": _json_decimal(financial["amount_delta"]),
            "paid_amount": _json_decimal(financial["paid"]),
            "planned_amount": _json_decimal(financial["planned"]),
            "settled_amount": _json_decimal(financial["settled"]),
            "fee_credit_amount": _json_decimal(financial["fee_credit"]),
            "receivable_reduction_amount": _json_decimal(financial["receivable_reduction"]),
            "outstanding_before": _json_decimal(financial["outstanding_before"]),
            "outstanding_after": _json_decimal(financial["outstanding_after"]),
        },
        "warnings": warnings,
        "warning_details": warning_details,
        "blocking_reasons": financial["blocking_reasons"],
        "can_submit": not financial["blocking_reasons"],
    }
    if financial_strict and financial["blocking_reasons"]:
        raise ValidationError("；".join(financial["blocking_reasons"]))
    return result


@transaction.atomic
def preview_quantity_adjustment(order, payload):
    order = Order.objects.select_for_update().get(pk=order.pk)
    reject_historical(order, "调整订单数量")
    version, _reason, canonical_items, _fingerprint = _canonical_request(payload)
    if order.status not in ADJUSTABLE_STATUSES:
        raise ValidationError("只有已确认、生产中或已发货的正式订单可以调整数量。")
    if version != order.quantity_change_version:
        raise QuantityAdjustmentConflict("订单数量已被其他操作更新，请刷新后重新预览。")
    normalized = _normalized_lines(order, canonical_items)
    return _build_preview(order, normalized)


def _apply_payment_delta(order, financial, adjustment_id):
    delta = Decimal(str(financial["amount_delta"]))
    continuation = getattr(order, "history_continuation", None)
    financial_order = continuation.archived_order if continuation else order
    if delta > 0:
        return PaymentPlan.objects.create(
            order=financial_order,
            direction="receivable",
            due_date=order.expected_ship_date,
            planned_amount=delta,
            currency=order.currency,
            notes=f"数量变更 #{adjustment_id} 增加应收",
        )
    if delta == 0:
        return None
    remaining = -delta
    affected = None
    for plan in _receivable_plans(financial_order).filter(status="open"):
        reducible = plan.remaining_amount
        reduction = min(reducible, remaining)
        if reduction <= 0:
            continue
        plan.planned_amount -= reduction
        if plan.planned_amount == 0:
            plan.status = "cancelled"
        else:
            _sync_plan_status(plan)
        plan.notes = f"{plan.notes}\n数量变更 #{adjustment_id} 调减 {_json_decimal(reduction)}"
        plan.save(update_fields=["planned_amount", "status", "notes", "updated_at"])
        affected = plan
        remaining -= reduction
        if remaining == 0:
            break
    if remaining != 0:
        raise ValidationError("数量减少超过可调整的未结应收计划余额。")
    return affected


@transaction.atomic
def apply_quantity_adjustment(order, payload, *, operator=None):
    order = Order.objects.select_for_update().get(pk=order.pk)
    reject_historical(order, "调整订单数量")
    key = _request_key(payload)
    version, reason, canonical_items, fingerprint = _canonical_request(payload)
    existing = OrderQuantityAdjustment.objects.select_for_update().filter(request_key=key).first()
    if existing:
        if existing.order_id != order.pk or existing.request_fingerprint != fingerprint:
            raise ValidationError("请求幂等键已用于另一项数量变更，不能重复使用。")
        preview = existing.impact.get("preview", {})
        return existing, True, {
            **preview,
            "version": preview.get("version", version) + 1,
            "after_metrics": existing.impact.get("after_metrics", []),
            "warnings": existing.impact.get("warnings", []),
        }
    if order.status not in ADJUSTABLE_STATUSES:
        raise ValidationError("只有已确认、生产中或已发货的正式订单可以调整数量。")
    if version != order.quantity_change_version:
        raise QuantityAdjustmentConflict("订单数量已被其他操作更新，请刷新后重新提交。")
    # Use the same order -> SKU -> order-line lock order as shipment.
    affected_sku_ids = sorted(set(order.items.filter(
        pk__in=[row["order_item"] for row in canonical_items],
    ).values_list("sku_id", flat=True)))
    from crm.models import SKU
    list(SKU.objects.select_for_update().filter(pk__in=affected_sku_ids).order_by("pk"))
    normalized = _normalized_lines(order, canonical_items)
    preview = _build_preview(order, normalized, financial_strict=True)
    old_version = order.quantity_change_version
    financial = preview["financial"]
    before_lines = preview["lines"]
    try:
        with transaction.atomic():
            adjustment = OrderQuantityAdjustment.objects.create(
                order=order,
                operator=operator if getattr(operator, "is_authenticated", False) else None,
                request_key=key,
                request_fingerprint=fingerprint,
                reason=reason,
                before_total_amount=financial["before_total"],
                after_total_amount=financial["after_total"],
                amount_delta=financial["amount_delta"],
                lines=before_lines,
                impact={"preview": preview, "warnings": preview["warnings"]},
            )
    except IntegrityError:
        if OrderQuantityAdjustment.objects.filter(request_key=key).exists():
            raise QuantityAdjustmentConflict("请求幂等键已用于另一项数量变更，请重新预览。")
        raise
    for row in normalized:
        item = row["item"]
        item.quantity = row["new_quantity"]
        if row["new_trade_quantity"] is not None:
            item.trade_quantity = row["new_trade_quantity"]
        item.save(update_fields=["quantity", "trade_quantity"])
    order.quantity_change_version = old_version + 1
    if order.status == "shipped" and any(
        row["new_quantity"] > row["shipped_quantity"] for row in normalized
    ):
        order.status = "production"
        order.save(update_fields=["quantity_change_version", "status", "updated_at"])
    else:
        order.save(update_fields=["quantity_change_version", "updated_at"])
    _apply_payment_delta(order, financial, adjustment.pk)
    for sku_id in affected_sku_ids:
        from crm.models import SKU
        rebalance_sku_reservations(SKU.objects.get(pk=sku_id))
    after_lines = []
    warnings = list(preview["warnings"])
    after_groups = {}
    for row in normalized:
        row["item"].refresh_from_db()
        group_key = f"{row['item'].order_id}:{row['item'].sku_id}"
        after = after_groups.setdefault(group_key, _metrics_snapshot(row["item"]))
        if Decimal(after["procurement_excess_quantity"]) > 0 and not any(
            warning.startswith(after["sku_code"]) for warning in warnings
        ):
            warnings.append(
                f"{after['sku_code']} 可能产生采购过剩 {after['procurement_excess_quantity']} {after['base_unit']}，请人工处理。"
            )
        if group_key not in {line["group_key"] for line in after_lines}:
            after_lines.append(after)
    impact = {
        "operator_kind": "authenticated" if getattr(operator, "is_authenticated", False) else (
            "development" if development_superadmin_enabled() else "unknown"
        ),
        "preview": preview,
        "warnings": warnings,
        "after_metrics": after_lines,
        "payment_plan_delta": _json_decimal(financial["amount_delta"]),
        "order_status": order.status,
    }
    adjustment.impact = impact
    adjustment.save(update_fields=["impact", "updated_at"])
    return adjustment, False, {**preview, "version": order.quantity_change_version, "after_metrics": after_lines, "warnings": warnings}


def _warning_details(data):
    details = data.get("warning_details") if isinstance(data, dict) else None
    if isinstance(details, list):
        return [entry for entry in details if isinstance(entry, dict) and entry.get("message")]
    messages = data.get("warnings", []) if isinstance(data, dict) else []
    details = []
    for message in messages:
        text = str(message)
        if "采购" in text:
            kind = "procurement"
        elif any(term in text for term in ("应收", "收款", "订单金额", "资金", "金额")):
            kind = "financial"
        else:
            kind = "restricted"
        details.append({"kind": kind, "message": text})
    return details


def redact_quantity_adjustment_response(data, *, include_financial, include_procurement):
    if not isinstance(data, dict):
        return data
    response = dict(data)
    lines = []
    for line in data.get("lines", []) or []:
        if not isinstance(line, dict):
            continue
        safe_line = dict(line)
        if not include_financial:
            for key in ("old_amount", "new_amount", "amount_delta"):
                safe_line.pop(key, None)
        if not include_procurement:
            for key in ("before", "after"):
                safe_line.pop(key, None)
        lines.append(safe_line)
    response["lines"] = lines
    if not include_procurement:
        response.pop("after_metrics", None)
    details = _warning_details(data)
    visible_warnings = []
    for entry in details:
        kind = entry.get("kind")
        if kind == "financial" and not include_financial:
            message = FINANCIAL_MASK
        elif kind == "procurement" and not include_procurement:
            message = PROCUREMENT_MASK
        elif kind not in {"financial", "procurement"} and not (include_financial or include_procurement):
            message = "该影响提示需要相应业务权限查看。"
        else:
            message = entry["message"]
        if message not in visible_warnings:
            visible_warnings.append(message)
    response["warnings"] = visible_warnings
    response.pop("warning_details", None)
    raw_blocking = data.get("blocking_reasons", []) or []
    response["blocking_reasons"] = list(raw_blocking) if include_financial else ([FINANCIAL_MASK] if raw_blocking else [])
    financial = dict(data.get("financial") or {})
    if not include_financial:
        for key in financial:
            if key != "currency":
                financial[key] = None
    response["financial"] = financial
    response["financial_visible"] = include_financial
    response["procurement_visible"] = include_procurement
    return response


def serialize_adjustment(row, *, include_financial=True, include_procurement=None):
    # Keep the historical single-flag call contract safe for internal callers;
    # API views pass both visibility flags explicitly.
    if include_procurement is None:
        include_procurement = include_financial
    preview = redact_quantity_adjustment_response(
        row.impact.get("preview", {}),
        include_financial=include_financial,
        include_procurement=include_procurement,
    )
    lines = []
    for line in row.lines:
        safe_line = dict(line)
        if not include_financial:
            for key in ("old_amount", "new_amount", "amount_delta"):
                safe_line.pop(key, None)
        if not include_procurement:
            for key in ("before", "after"):
                safe_line.pop(key, None)
        lines.append(safe_line)
    impact = dict(row.impact)
    impact["preview"] = preview
    if not include_financial:
        impact["payment_plan_delta"] = None
    if not include_procurement:
        impact.pop("after_metrics", None)
    impact["warnings"] = redact_quantity_adjustment_response(
        {"warnings": impact.get("warnings", [])},
        include_financial=include_financial,
        include_procurement=include_procurement,
    )["warnings"]
    if not include_financial:
        impact["financial_visible"] = False
    if not include_procurement:
        impact["procurement_visible"] = False
    result = {
        "id": row.pk,
        "order": row.order_id,
        "order_no": row.order.order_no,
        "operator": row.operator_id,
        "operator_name": (row.operator.get_full_name() or row.operator.username) if row.operator_id else (
            "开发身份（未实名）" if row.impact.get("operator_kind") == "development" else "未记录实名操作人"
        ),
        "request_key": row.request_key,
        "reason": row.reason,
        "created_at": row.created_at,
        "before_total_amount": row.before_total_amount if include_financial else None,
        "after_total_amount": row.after_total_amount if include_financial else None,
        "amount_delta": row.amount_delta if include_financial else None,
        "financial_visible": include_financial,
        "procurement_visible": include_procurement,
        "lines": lines,
        "impact": impact,
    }
    return result
