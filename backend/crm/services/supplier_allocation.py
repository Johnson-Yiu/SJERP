"""Sales-order supplier allocation rules.

An order line remains linked to the internal SKU.  Choosing a supplier only
records the purchasing source and the values seen when that choice was made;
it never rewrites the SKU master or historical quotation/order names.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from crm.models import OrderItem, SupplierSKU

from .supplier_candidates import candidates


def _source_type(row):
    types = row.get("source_types") or []
    if "manual" in types:
        return "manual"
    if "rule_match" in types:
        return "rule_match"
    if "historical_purchase" in types:
        return "historical_purchase"
    return "supplier_sku"


def supplier_options(order_item):
    """Return candidate suppliers with enough data for the allocation drawer."""
    rows = candidates(order_item.sku)
    selected_id = order_item.supplier_sku_id
    for row in rows:
        row["selected_for_order"] = bool(selected_id and any(
            source["id"] == selected_id for source in row["supplier_skus"]
        ))
        row["selection_block_reason"] = "" if row["can_allocate"] else "尚未建立启用中的 Supplier SKU，不能直接下采购单"
    return rows


@transaction.atomic
def allocate_order_item_supplier(order_item_id, supplier_sku_id, *, scope="order_only", note=""):
    """Assign one active SupplierSKU to a sales-order line and snapshot it."""
    item = OrderItem.objects.select_for_update().select_related("order", "sku", "supplier_sku").get(pk=order_item_id)
    try:
        source = SupplierSKU.objects.select_for_update().select_related("supplier", "sku").get(pk=supplier_sku_id)
    except SupplierSKU.DoesNotExist as error:
        raise ValidationError("所选 Supplier SKU 不存在。") from error

    if item.order.status in {"cancelled", "completed"}:
        raise ValidationError("已完成或已取消的订单不能重新分配供应商。")
    if not source.is_active:
        raise ValidationError("只能选择启用中的 Supplier SKU。")
    if source.sku_id != item.sku_id:
        raise ValidationError("所选 Supplier SKU 不属于当前订单行的内部 SKU。")
    if scope not in {"order_only", "recommended"}:
        raise ValidationError("供应商分配范围无效。")
    if item.sku.candidate_overrides.filter(supplier_id=source.supplier_id, is_allowed=False).exists():
        raise ValidationError("该 SKU 已排除此供应商，不能分配。")

    matched = next((row for row in supplier_options(item) if row["supplier"] == source.supplier_id), None)
    if not matched:
        raise ValidationError("该供应商不在当前 SKU 的候选池中，请先维护规则或人工加入候选。")

    if scope == "recommended":
        SupplierSKU.objects.filter(sku_id=source.sku_id, is_preferred=True).exclude(pk=source.pk).update(
            is_preferred=False,
            updated_at=timezone.now(),
        )
        if not source.is_preferred:
            source.is_preferred = True
            source.save(update_fields=["is_preferred", "updated_at"])

    item.supplier_sku = source
    item.supplier_name_snapshot = source.supplier.name
    item.supplier_model_snapshot = source.supplier_model
    item.supplier_sku_code_snapshot = source.supplier_sku_code
    item.supplier_barcode_snapshot = source.supplier_barcode
    item.supplier_characteristics_snapshot = source.characteristics or {}
    item.supplier_price_snapshot = source.purchase_price
    item.supplier_currency_snapshot = source.currency
    item.supplier_moq_snapshot = source.moq
    item.supplier_lead_time_days_snapshot = source.lead_time_days
    item.supplier_allocation_source = _source_type(matched)
    item.supplier_allocation_sources_snapshot = matched.get("sources", [])
    item.supplier_allocation_scope = scope
    item.supplier_allocation_note = str(note or "").strip()
    item.supplier_allocated_at = timezone.now()
    item.save(update_fields=[
        "supplier_sku", "supplier_name_snapshot", "supplier_model_snapshot",
        "supplier_sku_code_snapshot", "supplier_barcode_snapshot",
        "supplier_characteristics_snapshot", "supplier_price_snapshot",
        "supplier_currency_snapshot", "supplier_moq_snapshot",
        "supplier_lead_time_days_snapshot", "supplier_allocation_source",
        "supplier_allocation_sources_snapshot", "supplier_allocation_scope",
        "supplier_allocation_note", "supplier_allocated_at",
    ])
    return item


def supplier_allocation_payload(item):
    source = item.supplier_sku
    return {
        "order_item": item.pk,
        "sku": item.sku_id,
        "supplier_sku": source.pk if source else None,
        "supplier": source.supplier_id if source else None,
        "supplier_name": item.supplier_name_snapshot,
        "supplier_model": item.supplier_model_snapshot,
        "supplier_sku_code": item.supplier_sku_code_snapshot,
        "supplier_barcode": item.supplier_barcode_snapshot,
        "characteristics": item.supplier_characteristics_snapshot or {},
        "purchase_price": item.supplier_price_snapshot,
        "currency": item.supplier_currency_snapshot,
        "moq": item.supplier_moq_snapshot,
        "lead_time_days": item.supplier_lead_time_days_snapshot,
        "source": item.supplier_allocation_source,
        "sources": item.supplier_allocation_sources_snapshot or [],
        "scope": item.supplier_allocation_scope,
        "note": item.supplier_allocation_note,
        "allocated_at": item.supplier_allocated_at,
    }
