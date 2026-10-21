"""Atomic, append-only quantity changes for confirmed sales orders."""

import hashlib
import json
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction

from crm.models import Order, OrderItem, OrderQuantityAdjustment, PaymentPlan
from crm.services.fulfillment import _shipped_quantity, order_item_metrics, rebalance_sku_reservations


QUANTITY_QUANTUM = Decimal("0.01")
MONEY_QUANTUM = Decimal("0.0001")
ADJUSTABLE_STATUSES = {"confirmed", "production", "shipped"}


class QuantityAdjustmentConflict(ValidationError):
    """A stale preview or duplicate request must not overwrite newer work."""


def _decimal(value, label, *, positive=True, quantum=QUANTITY_QUANTUM):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError(f"{label}必须是有效数字。")
    if not number.is_finite() or (positive and number <= 0) or (not positive and number < 0):
        raise ValidationError(f"{label}必须是大于零的有效数字。" if positive else f"{label}不能为负数。")
    if number != number.quantize(quantum):
        raise ValidationError(f"{label}最多保留 {abs(quantum.as_tuple().exponent)} 位小数。")
    return number.quantize(quantum)


def _money(value):
    return Decimal(value).quantize(MONEY_QUANTUM)


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
    if item.trade_unit_id:
        if "new_trade_quantity" not in row:
            raise ValidationError(f"{item.sku_code_snapshot or item.sku.sku} 必须按原交易单位填写数量。")
        trade_quantity = _decimal(row["new_trade_quantity"], "交易数量")
        snapshot = item.trade_snapshot or {}
        try:
            factor = Decimal(str(snapshot["factor"]))
        except (KeyError, InvalidOperation, TypeError, ValueError):
            raise ValidationError(f"{item.sku_code_snapshot or item.sku.sku} 缺少可靠的交易单位换算快照，不能安全调整。")
        if not factor.is_finite() or factor <= 0:
            raise ValidationError("原交易单位换算关系无效，不能安全调整。")
        if not snapshot.get("allow_fraction", False) and trade_quantity != trade_quantity.to_integral_value():
            raise ValidationError(f"{item.sku_code_snapshot or item.sku.sku} 的原交易单位只允许整包装数量。")
        base_quantity = trade_quantity * factor
        if base_quantity != base_quantity.quantize(QUANTITY_QUANTUM):
            raise ValidationError("交易单位换算后的基础数量不符合系统精度。")
        return trade_quantity, base_quantity.quantize(QUANTITY_QUANTUM)
    if "new_quantity" not in row:
        raise ValidationError(f"{item.sku_code_snapshot or item.sku.sku} 必须填写基础数量。")
    return None, _decimal(row["new_quantity"], "基础数量")


def _normalized_lines(order, canonical_items):
    item_ids = [row["order_item"] for row in canonical_items]
    if len(set(item_ids)) != len(item_ids):
        raise ValidationError("同一订单行不能重复提交。")
    items = {
        item.pk: item
        for item in order.items.select_for_update().select_related("sku", "trade_unit").filter(pk__in=item_ids)
    }
    if len(items) != len(item_ids):
        raise ValidationError("数量变更明细不属于当前销售订单。")
    normalized = []
    for row in canonical_items:
        item = items[row["order_item"]]
        trade_quantity, base_quantity = _line_value(item, row)
        shipped = _shipped_quantity(item)
        if base_quantity < shipped:
            raise ValidationError(
                f"{item.sku_code_snapshot or item.sku.sku} 的新数量不能低于已发货数量 {shipped}。"
            )
        new_amount = (
            trade_quantity * item.trade_unit_price
            if item.trade_unit_id
            else base_quantity * item.unit_price
        )
        normalized.append({
            "item": item,
            "old_quantity": item.quantity,
            "new_quantity": base_quantity,
            "old_trade_quantity": item.trade_quantity,
            "new_trade_quantity": trade_quantity,
            "old_amount": item.amount,
            "new_amount": new_amount,
            "shipped_quantity": shipped,
        })
    return normalized


def _financial_state(order, new_total=None):
    old_total = _money(order.total_amount)
    target_total = old_total if new_total is None else _money(new_total)
    plans = list(order.payment_plans.select_for_update().exclude(status="cancelled").order_by("-due_date", "-id"))
    planned = sum((plan.planned_amount for plan in plans), Decimal("0"))
    settled = sum((plan.settled_amount for plan in plans), Decimal("0"))
    paid = _money(order.paid_amount)
    reasons = []
    if _money(planned) != old_total:
        reasons.append(f"现有应收计划合计 {_money(planned)} 与订单金额 {old_total} 不一致")
    if _money(settled) != paid:
        reasons.append(f"应收计划已核销 {_money(settled)} 与已收金额 {paid} 不一致")
    if settled > target_total:
        reasons.append(f"调整后订单金额 {target_total} 低于已收金额 {paid}，需先处理退款或资金差额")
    delta = _money(target_total - old_total)
    if delta < 0 and _money(planned + delta) < _money(settled):
        reasons.append("数量减少超过未结应收计划余额")
    return {
        "before_total": old_total,
        "after_total": target_total,
        "amount_delta": delta,
        "planned": _money(planned),
        "settled": _money(settled),
        "paid": paid,
        "outstanding_before": _money(planned - settled),
        "outstanding_after": _money(target_total - settled),
        "blocking_reasons": reasons,
    }


def _metrics_snapshot(item, new_quantity=None):
    metrics = order_item_metrics(item)
    quantity = item.quantity if new_quantity is None else new_quantity
    allocated = metrics["allocated_quantity"]
    purchased = metrics["purchased_quantity"]
    received = metrics["received_quantity"]
    shipped = metrics["shipped_quantity"]
    outstanding_purchase = max(Decimal("0"), purchased - received)
    to_procure = max(Decimal("0"), quantity - shipped - allocated - outstanding_purchase)
    excess = max(Decimal("0"), purchased - quantity)
    return {
        "order_item": item.pk,
        "sku_code": item.sku_code_snapshot or item.sku.sku,
        "base_unit": (item.trade_snapshot or {}).get("base_unit") or item.unit_snapshot or item.sku.unit,
        "ordered_quantity": _json_decimal(quantity),
        "shipped_quantity": _json_decimal(shipped),
        "purchased_quantity": _json_decimal(purchased),
        "received_quantity": _json_decimal(received),
        "in_transit_quantity": _json_decimal(metrics["in_transit_quantity"]),
        "to_procure_quantity": _json_decimal(to_procure),
        "procurement_excess_quantity": _json_decimal(excess),
    }


def _build_preview(order, normalized, *, financial_strict=False):
    before_total = order.total_amount
    after_total = before_total + sum((row["new_amount"] - row["old_amount"] for row in normalized), Decimal("0"))
    financial = _financial_state(order, after_total)
    lines = []
    warnings = []
    for row in normalized:
        item = row["item"]
        before = _metrics_snapshot(item)
        after = _metrics_snapshot(item, row["new_quantity"])
        excess = Decimal(after["procurement_excess_quantity"])
        if excess > 0:
            warnings.append(
                f"{after['sku_code']} 可能产生采购过剩 {excess} {after['base_unit']}，请人工处理，系统不会自动取消采购单。"
            )
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
            "outstanding_before": _json_decimal(financial["outstanding_before"]),
            "outstanding_after": _json_decimal(financial["outstanding_after"]),
        },
        "warnings": warnings,
        "blocking_reasons": financial["blocking_reasons"],
        "can_submit": not financial["blocking_reasons"],
    }
    if financial_strict and financial["blocking_reasons"]:
        raise ValidationError("；".join(financial["blocking_reasons"]))
    return result


def preview_quantity_adjustment(order, payload):
    version, _reason, canonical_items, _fingerprint = _canonical_request(payload)
    if order.status not in ADJUSTABLE_STATUSES:
        raise ValidationError("只有已确认、生产中或已发货的正式订单可以调整数量。")
    if version != order.quantity_change_version:
        raise QuantityAdjustmentConflict("订单数量已被其他操作更新，请刷新后重新预览。")
    normalized = _normalized_lines(order, canonical_items)
    return _build_preview(order, normalized)


def _apply_payment_delta(order, financial, adjustment_id):
    delta = Decimal(str(financial["amount_delta"]))
    if delta > 0:
        return PaymentPlan.objects.create(
            order=order,
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
    for plan in order.payment_plans.select_for_update().exclude(status="cancelled").order_by("-due_date", "-id"):
        reducible = plan.planned_amount - plan.settled_amount
        reduction = min(reducible, remaining)
        if reduction <= 0:
            continue
        plan.planned_amount -= reduction
        plan.status = "cancelled" if plan.planned_amount == 0 else ("settled" if plan.planned_amount == plan.settled_amount else "open")
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
    key = _request_key(payload)
    version, reason, canonical_items, fingerprint = _canonical_request(payload)
    existing = OrderQuantityAdjustment.objects.select_for_update().filter(request_key=key).first()
    if existing:
        if existing.order_id != order.pk or existing.request_fingerprint != fingerprint:
            raise ValidationError("请求幂等键已用于另一项数量变更，不能重复使用。")
        return existing, True, existing.impact.get("preview", {})
    if order.status not in ADJUSTABLE_STATUSES:
        raise ValidationError("只有已确认、生产中或已发货的正式订单可以调整数量。")
    if version != order.quantity_change_version:
        raise QuantityAdjustmentConflict("订单数量已被其他操作更新，请刷新后重新提交。")
    normalized = _normalized_lines(order, canonical_items)
    preview = _build_preview(order, normalized, financial_strict=True)
    old_version = order.quantity_change_version
    financial = preview["financial"]
    before_lines = preview["lines"]
    affected_sku_ids = sorted({row["item"].sku_id for row in normalized})
    for sku_id in affected_sku_ids:
        # Keep concurrent quantity changes for the same SKU in a deterministic
        # order before rebuilding reservations.
        from crm.models import SKU
        SKU.objects.select_for_update().get(pk=sku_id)
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
    for row in normalized:
        item = row["item"]
        item.quantity = row["new_quantity"]
        if item.trade_unit_id:
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
    warnings = []
    for row in normalized:
        row["item"].refresh_from_db()
        after = _metrics_snapshot(row["item"])
        if Decimal(after["procurement_excess_quantity"]) > 0:
            warnings.append(
                f"{after['sku_code']} 可能产生采购过剩 {after['procurement_excess_quantity']} {after['base_unit']}，请人工处理。"
            )
        after_lines.append(after)
    impact = {
        "preview": preview,
        "warnings": warnings,
        "after_metrics": after_lines,
        "payment_plan_delta": _json_decimal(financial["amount_delta"]),
        "order_status": order.status,
    }
    adjustment.impact = impact
    adjustment.save(update_fields=["impact", "updated_at"])
    return adjustment, False, {**preview, "version": order.quantity_change_version, "after_metrics": after_lines, "warnings": warnings}


def serialize_adjustment(row, *, include_financial=True):
    lines = row.lines
    impact = row.impact
    if not include_financial:
        lines = [
            {
                key: value
                for key, value in line.items()
                if key not in {"old_amount", "new_amount", "amount_delta", "before", "after"}
            }
            for line in row.lines
        ]
        impact = {
            "warnings": row.impact.get("warnings", []),
            "financial_visible": False,
        }
    return {
        "id": row.pk,
        "order": row.order_id,
        "order_no": row.order.order_no,
        "operator": row.operator_id,
        "operator_name": row.operator.get_full_name() or row.operator.username if row.operator_id else "系统",
        "request_key": row.request_key,
        "reason": row.reason,
        "created_at": row.created_at,
        "before_total_amount": row.before_total_amount if include_financial else None,
        "after_total_amount": row.after_total_amount if include_financial else None,
        "amount_delta": row.amount_delta if include_financial else None,
        "financial_visible": include_financial,
        "lines": lines,
        "impact": impact,
    }
