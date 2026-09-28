"""Order-shortage procurement planning and draft creation."""

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from crm.document_numbers import allocate_purchase_no
from crm.models import Order, OrderItem, PurchaseOrder, PurchaseOrderItem, SupplierSKU
from crm.services.fulfillment import order_item_metrics


ZERO = Decimal("0")
GENERATABLE_ORDER_STATUSES = {"confirmed", "production"}


def _draft_procurement_rows(order):
    """Return draft quantities attributable to this order, preserving their source."""
    quantities = []
    rows = PurchaseOrderItem.objects.filter(
        purchase_order__status="draft",
        sku_id__in=order.items.values("sku_id"),
    ).filter(
        Q(purchase_order__order=order, purchase_order__cost_allocation_version=0)
        | Q(cost_allocations__target_type="order", cost_allocations__order=order)
    ).distinct().select_related("purchase_order").prefetch_related("cost_allocations")
    for row in rows:
        if row.purchase_order.cost_allocation_version:
            quantity = sum(
                (
                    allocation.quantity
                    for allocation in row.cost_allocations.all()
                    if allocation.target_type == "order" and allocation.order_id == order.id
                ),
                ZERO,
            )
        else:
            quantity = row.quantity
        if quantity > ZERO:
            quantities.append((row.sku_id, row.supplier_sku_id, quantity))
    return quantities


def draft_procurement_quantities(order, items=None):
    """Distribute draft coverage by source first, then by SKU for legacy residuals."""
    items = list(items if items is not None else order.items.select_related("sku").order_by("id"))
    remaining_by_item = {
        item.id: order_item_metrics(item)["to_procure_quantity"] for item in items
    }
    quantities = {item.id: ZERO for item in items}
    items_by_source = defaultdict(list)
    items_by_sku = defaultdict(list)
    for item in items:
        items_by_sku[item.sku_id].append(item)
        if item.supplier_sku_id:
            items_by_source[(item.sku_id, item.supplier_sku_id)].append(item)

    residual_by_sku = defaultdict(lambda: ZERO)
    for sku_id, supplier_sku_id, quantity in _draft_procurement_rows(order):
        remaining_draft = quantity
        if supplier_sku_id:
            for item in items_by_source[(sku_id, supplier_sku_id)]:
                coverage = min(remaining_draft, remaining_by_item[item.id])
                quantities[item.id] += coverage
                remaining_by_item[item.id] -= coverage
                remaining_draft -= coverage
                if remaining_draft <= ZERO:
                    break
        residual_by_sku[sku_id] += remaining_draft

    for sku_id, remaining_draft in residual_by_sku.items():
        for item in items_by_sku[sku_id]:
            coverage = min(remaining_draft, remaining_by_item[item.id])
            quantities[item.id] += coverage
            remaining_by_item[item.id] -= coverage
            remaining_draft -= coverage
            if remaining_draft <= ZERO:
                break
    return quantities


def _source_issue(item):
    source = item.supplier_sku
    if source is None:
        return "请先选择本次采购供应商"
    if not source.is_active:
        return "当前订单行指定的 Supplier SKU 已停用，请重新选择供应商。"
    if source.sku_id != item.sku_id:
        return "当前订单行指定的 Supplier SKU 与 SKU 不匹配，请重新选择供应商。"
    if item.supplier_currency_snapshot and item.supplier_currency_snapshot != source.currency:
        return "供应商采购币种自订单分配后发生变化，请重新选择供应商或使用普通采购流程确认。"
    return ""


def build_procurement_plan(order):
    """Build a live, non-persistent procurement plan for one sales order."""
    items = list(
        order.items.select_related("sku", "supplier_sku", "supplier_sku__supplier").order_by("id")
    )
    draft_quantities = draft_procurement_quantities(order, items)
    rows = []
    for item in items:
        metrics = order_item_metrics(item)
        draft_quantity = draft_quantities[item.id]
        draftable_quantity = max(ZERO, metrics["to_procure_quantity"] - draft_quantity)
        source = item.supplier_sku
        blocking_reason = _source_issue(item)
        warnings = []
        currency = item.supplier_currency_snapshot or (source.currency if source else "")
        reference_price = item.supplier_price_snapshot
        if reference_price is None and source is not None:
            reference_price = source.purchase_price
            warnings.append("订单行缺少供应商价格快照，当前仅以 Supplier SKU 参考价供确认。")
        if not item.supplier_currency_snapshot and source is not None:
            warnings.append("订单行缺少供应商币种快照，当前以 Supplier SKU 币种供确认。")
        moq = item.supplier_moq_snapshot if item.supplier_moq_snapshot is not None else (source.moq if source else None)
        lead_time_days = item.supplier_lead_time_days_snapshot
        if lead_time_days is None and source is not None:
            lead_time_days = source.lead_time_days
        if moq and draftable_quantity and draftable_quantity < moq:
            warnings.append(f"待采购数量低于供应商 MOQ {moq}")
        if order.status not in GENERATABLE_ORDER_STATUSES:
            blocking_reason = "当前销售订单状态不允许生成采购草稿。"
        elif not blocking_reason and draftable_quantity <= ZERO:
            blocking_reason = "当前没有可继续生成采购草稿的数量。"
        rows.append({
            "order_item": item.id,
            "sku": item.sku_id,
            "sku_code": item.sku_code_snapshot or item.sku.sku,
            "display_name": item.display_name_snapshot or item.sku.display_name_cn or item.sku.product.name,
            "base_unit": item.trade_snapshot.get("base_unit", item.unit_snapshot or item.sku.unit),
            "order_quantity": item.quantity,
            "allocated_quantity": metrics["allocated_quantity"],
            "to_procure_quantity": metrics["to_procure_quantity"],
            "draft_procurement_quantity": draft_quantity,
            "draftable_quantity": draftable_quantity,
            "supplier_sku": source.id if source else None,
            "supplier": source.supplier_id if source else None,
            "supplier_name": item.supplier_name_snapshot or (source.supplier.name if source else ""),
            "supplier_model": item.supplier_model_snapshot or (source.supplier_model if source else ""),
            "supplier_sku_code": item.supplier_sku_code_snapshot or (source.supplier_sku_code if source else ""),
            "reference_purchase_price": reference_price if reference_price is not None else ZERO,
            "currency": currency,
            "moq": moq,
            "lead_time_days": lead_time_days,
            "can_generate": not blocking_reason and draftable_quantity > ZERO,
            "blocking_reason": blocking_reason,
            "warnings": warnings,
        })
    groups = {}
    for row in rows:
        if not row["can_generate"]:
            continue
        key = (row["supplier"], row["currency"])
        group = groups.setdefault(key, {
            "supplier": row["supplier"], "supplier_name": row["supplier_name"], "currency": row["currency"],
            "items": [], "lead_time_days": 0,
        })
        group["items"].append(row["order_item"])
        group["lead_time_days"] = max(group["lead_time_days"], row["lead_time_days"] or 0)
    for group in groups.values():
        group["suggested_exchange_rate"] = Decimal("1") if group["currency"] == "CNY" else None
        group["suggested_expected_arrival_date"] = (
            timezone.localdate() + timedelta(days=group["lead_time_days"])
            if group["lead_time_days"] else None
        )
    return {"order": order.id, "order_no": order.order_no, "items": rows, "groups": list(groups.values())}


def _as_date(value):
    if value in (None, "") or isinstance(value, date):
        return value or None
    try:
        return date.fromisoformat(str(value))
    except ValueError as error:
        raise ValidationError("预计到货日期格式无效。") from error


@transaction.atomic
def create_purchase_drafts(order, payload):
    """Create all requested draft purchase orders atomically from a fresh plan."""
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status not in GENERATABLE_ORDER_STATUSES:
        raise ValidationError("只有已确认或生产中的销售订单可以生成采购草稿。")
    items = list(
        OrderItem.objects.select_for_update(of=("self",)).select_related("sku", "supplier_sku", "supplier_sku__supplier")
        .filter(order=order).order_by("id")
    )
    source_ids = sorted({item.supplier_sku_id for item in items if item.supplier_sku_id})
    if source_ids:
        list(SupplierSKU.objects.select_for_update().filter(pk__in=source_ids).order_by("id"))
    list(PurchaseOrder.objects.select_for_update().filter(order=order, status="draft").order_by("id"))
    plan = build_procurement_plan(order)
    plan_by_item = {row["order_item"]: row for row in plan["items"]}
    groups = payload.get("groups") or []
    if not groups:
        raise ValidationError("请至少选择一组采购草稿明细。")

    used_items, group_keys, validated_groups = set(), set(), []
    for group in groups:
        supplier_id = group.get("supplier")
        currency = str(group.get("currency") or "")
        group_key = (supplier_id, currency)
        if group_key in group_keys:
            raise ValidationError("同一供应商和币种只能生成一张采购草稿。")
        group_keys.add(group_key)
        exchange_rate = group.get("exchange_rate")
        if currency == "CNY":
            if exchange_rate not in (None, "", Decimal("1"), 1, "1"):
                raise ValidationError("CNY 采购草稿的汇率必须为 1。")
            exchange_rate = Decimal("1")
        elif exchange_rate is None or Decimal(exchange_rate) <= ZERO:
            raise ValidationError(f"{currency or '非 CNY'} 采购草稿必须填写大于 0 的汇率。")
        else:
            exchange_rate = Decimal(exchange_rate)
        lines = []
        for line in group.get("items") or []:
            quantity = Decimal(line.get("quantity", ZERO))
            if quantity == ZERO:
                continue
            if quantity < ZERO:
                raise ValidationError("采购数量不能为负。")
            price = Decimal(line.get("unit_price", ZERO))
            if price < ZERO:
                raise ValidationError("采购单价不能为负。")
            item_id = line.get("order_item")
            if item_id in used_items or item_id not in plan_by_item:
                raise ValidationError("采购明细必须属于当前订单，且不能重复。")
            planned = plan_by_item[item_id]
            if not planned["can_generate"]:
                raise ValidationError(planned["blocking_reason"] or "当前订单行不能生成采购草稿。")
            if planned["supplier"] != supplier_id or planned["currency"] != currency:
                raise ValidationError("采购草稿必须使用订单行当前指定的供应商和币种。")
            if quantity > planned["draftable_quantity"]:
                raise ValidationError("本次采购数量不能超过当前可生成草稿数量。")
            used_items.add(item_id)
            lines.append((planned, quantity, price))
        if lines:
            validated_groups.append({
                "supplier_id": supplier_id, "currency": currency, "exchange_rate": exchange_rate,
                "expected_arrival_date": _as_date(group.get("expected_arrival_date")), "lines": lines,
            })
    if not validated_groups:
        raise ValidationError("请至少选择一条采购数量大于 0 的明细。")

    item_by_id = {item.id: item for item in items}
    purchases = []
    for group in validated_groups:
        purchase = PurchaseOrder.objects.create(
            purchase_no=allocate_purchase_no(), order=order, supplier_id=group["supplier_id"],
            order_date=timezone.localdate(), expected_arrival_date=group["expected_arrival_date"],
            status="draft", currency=group["currency"], exchange_rate=group["exchange_rate"],
            notes=f"由销售订单 {order.order_no} 的采购缺口生成",
        )
        for planned, quantity, price in group["lines"]:
            item = item_by_id[planned["order_item"]]
            PurchaseOrderItem.objects.create(
                purchase_order=purchase, sku=item.sku, supplier_sku=item.supplier_sku,
                quantity=quantity, unit_price=price,
            )
        purchases.append(purchase)
    return purchases
