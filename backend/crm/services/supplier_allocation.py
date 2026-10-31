"""Sales-order supplier allocation rules.

An order line remains linked to the internal SKU.  Choosing a supplier only
records the purchasing source and the values seen when that choice was made;
it never rewrites the SKU master or historical quotation/order names.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from crm.models import CustomerSupplierPreference, OrderItem, SupplierSKU

from .supplier_candidates import candidate_payload


def _source_type(row):
    types = row.get("source_types") or []
    if "customer_preference" in types:
        return "customer_preference"
    if "manual" in types:
        return "manual"
    if "rule_match" in types:
        return "rule_match"
    if "historical_purchase" in types:
        return "historical_purchase"
    return "supplier_sku"


def supplier_option_payload(order_item):
    """Return customer-scoped candidates without exposing other customers."""
    payload = candidate_payload(order_item.sku, customer=order_item.order.customer)
    rows = payload["candidates"]
    selected_id = order_item.supplier_sku_id
    for row in rows:
        row["selected_for_order"] = bool(selected_id and any(
            source["id"] == selected_id for source in row["supplier_skus"]
        ))
        row["selection_block_reason"] = "" if row["can_allocate"] else "尚未建立启用中的 Supplier SKU，不能直接下采购单"
    return payload


def supplier_options(order_item):
    """Backward-compatible list form used by product and allocation callers."""
    return supplier_option_payload(order_item)["candidates"]


@transaction.atomic
def set_customer_supplier_preference(customer, sku, supplier_sku, *, user=None):
    """Persist an explicit customer+SKU preference, never a global default."""
    if supplier_sku.sku_id != sku.pk:
        raise ValidationError("所选 Supplier SKU 不属于当前内部 SKU。")
    if not supplier_sku.is_active or not supplier_sku.supplier.is_active:
        raise ValidationError("只能将启用中的供应商来源设为客户优先来源。")
    if sku.candidate_overrides.filter(supplier_id=supplier_sku.supplier_id, is_allowed=False).exists():
        raise ValidationError("该 SKU 已排除此供应商，不能设为客户优先来源。")
    operator = user if getattr(user, "is_authenticated", False) else None
    preference = CustomerSupplierPreference.objects.select_for_update().filter(customer=customer, sku=sku).first()
    if preference is None:
        return CustomerSupplierPreference.objects.create(
            customer=customer,
            sku=sku,
            supplier_sku=supplier_sku,
            created_by=operator,
            updated_by=operator,
        )
    preference.supplier_sku = supplier_sku
    preference.updated_by = operator
    preference.save(update_fields=["supplier_sku", "updated_by", "updated_at"])
    return preference


@transaction.atomic
def allocate_order_item_supplier(order_item_id, supplier_sku_id, *, scope="order_only", note=""):
    """Assign one active SupplierSKU to a sales-order line and snapshot it."""
    item = OrderItem.objects.select_for_update().select_related("order", "sku").get(pk=order_item_id)
    try:
        source = SupplierSKU.objects.select_for_update().select_related("supplier", "sku").get(pk=supplier_sku_id)
    except SupplierSKU.DoesNotExist as error:
        raise ValidationError("所选 Supplier SKU 不存在。") from error

    if item.order.status not in {"draft", "confirmed", "production"}:
        raise ValidationError("只有草稿、已确认或生产中的订单可以调整当前采购来源。")
    if not source.is_active:
        raise ValidationError("只能选择启用中的 Supplier SKU。")
    if source.sku_id != item.sku_id:
        raise ValidationError("所选 Supplier SKU 不属于当前订单行的内部 SKU。")
    if scope == "recommended":
        # Keep old clients working while moving the meaning to the scoped
        # customer preference required by ISS-024.
        scope = "customer_preferred"
    if scope not in {"order_only", "customer_preferred"}:
        raise ValidationError("供应商分配范围无效。")
    if item.sku.candidate_overrides.filter(supplier_id=source.supplier_id, is_allowed=False).exists():
        raise ValidationError("该 SKU 已排除此供应商，不能分配。")

    matched = next((row for row in supplier_options(item) if row["supplier"] == source.supplier_id), None)
    if not matched:
        raise ValidationError("该供应商不在当前 SKU 的候选池中，请先维护规则或人工加入候选。")

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
