"""Dynamic supplier candidates; matching never creates purchasing identities."""
from rest_framework.exceptions import ValidationError
from crm.models import PurchaseOrderItem, SupplierCapability, SupplierCandidateOverride, SupplierSKU
from crm.sku_identity import category_attributes, normalize_parameter_token, raw_parameter_value


def parameter_value(values, key):
    return normalize_parameter_token(raw_parameter_value(values, key))


def validate_filters(product, filters):
    if not isinstance(filters, dict):
        raise ValidationError({"filters": "请选择参数及允许的取值。"})
    keys = {f"{a.category_id}:{a.key}" for a in category_attributes(product)}
    keys.update(k for sku in product.skus.all() for k in sku.parameter_values)
    for key, values in filters.items():
        if key not in keys or not isinstance(values, list) or not values or any(not isinstance(v, str) or not v.strip() for v in values):
            raise ValidationError({"filters": f"参数 {key} 或取值无效；不限的参数请不要添加条件。"})
    return filters


def matches(sku, rule):
    return all(parameter_value(sku.parameter_values, key) in {normalize_parameter_token(v) for v in values}
               for key, values in rule.filters.items())


def _candidate_row(supplier):
    return {
        "supplier": supplier.pk,
        "supplier_name": supplier.name,
        "sources": [],
        "source_types": [],
        "characteristics": {},
        "supplier_skus": [],
    }


def _add_source(row, label, source_type):
    if label not in row["sources"]:
        row["sources"].append(label)
    if source_type not in row["source_types"]:
        row["source_types"].append(source_type)


def candidates(sku):
    result = {}
    for rule in SupplierCapability.objects.filter(product=sku.product, is_active=True).select_related("supplier").order_by("id"):
        if matches(sku, rule):
            row = result.setdefault(rule.supplier_id, _candidate_row(rule.supplier))
            _add_source(row, rule.name, "rule_match")
            row["characteristics"].update(rule.characteristics)
    for source in sku.supplier_skus.filter(is_active=True).select_related("supplier"):
        row = result.setdefault(source.supplier_id, _candidate_row(source.supplier))
        row["supplier_skus"].append({
            "id": source.id,
            "code": source.supplier_sku_code,
            "model": source.supplier_model,
            "purchase_price": source.purchase_price,
            "currency": source.currency,
            "moq": source.moq,
            "lead_time_days": source.lead_time_days,
            "is_preferred": source.is_preferred,
            "characteristics": source.characteristics,
        })
        _add_source(row, "已维护供货档案", "supplier_sku")
    for item in PurchaseOrderItem.objects.filter(
        sku=sku,
        purchase_order__status__in=["ordered", "partial", "completed"],
    ).select_related("purchase_order__supplier", "supplier_sku"):
        supplier = item.purchase_order.supplier
        row = result.setdefault(item.purchase_order.supplier_id, _candidate_row(supplier))
        _add_source(row, "历史采购", "historical_purchase")
    for override in sku.candidate_overrides.select_related("supplier"):
        if not override.is_allowed:
            result.pop(override.supplier_id, None)
            continue
        row = result.setdefault(override.supplier_id, _candidate_row(override.supplier))
        _add_source(row, "人工指定", "manual")
        row["characteristics"].update(override.characteristics)
    for row in result.values():
        last = sku.purchase_order_items.filter(
            purchase_order__supplier_id=row["supplier"],
        ).exclude(purchase_order__status__in=["draft", "cancelled"]).select_related("purchase_order").order_by("-purchase_order__order_date", "-id").first()
        row["last_purchase"] = {
            "date": last.purchase_order.order_date,
            "price": last.unit_price,
            "currency": last.purchase_order.currency,
            "supplier_sku_id": last.supplier_sku_id,
        } if last else None
        row["supplier_sku_count"] = len(row["supplier_skus"])
        preferred = next((source for source in row["supplier_skus"] if source["is_preferred"]), None)
        selected = preferred or (row["supplier_skus"][0] if row["supplier_skus"] else None)
        row["can_allocate"] = bool(selected)
        row["recommended_supplier_sku_id"] = selected["id"] if selected else None
        row["recommended_source"] = "preferred" if preferred else ("first_active" if selected else None)
        row["source_label"] = "、".join(row["source_types"])
    return list(result.values())


def ensure_purchase_source(sku, supplier, order=None, currency=None):
    """Resolve a real, maintained source when one is available.

    A candidate is not itself a SupplierSKU.  Manual purchases may therefore
    proceed without a source record rather than creating fictitious AUTO data.
    ``currency`` remains accepted for compatibility with existing callers.
    """
    if order is not None:
        allocated_sources = list(order.items.filter(
            sku=sku,
            supplier_sku__supplier=supplier,
        ).values_list("supplier_sku_id", flat=True).distinct())
        if len(allocated_sources) > 1:
            raise ValidationError({"supplier_sku": "该销售订单中同一 SKU 已指定多个采购来源，请明确选择本次 Supplier SKU。"})
        if allocated_sources:
            allocated = SupplierSKU.objects.get(pk=allocated_sources[0])
            if not allocated.is_active:
                raise ValidationError({"supplier_sku": "销售订单当前采购来源已停用，请先在订单中重新选择当前采购来源。"})
            return allocated
    if sku.candidate_overrides.filter(supplier=supplier, is_allowed=False).exists():
        raise ValidationError({"supplier": "此 SKU 已排除该供应商，请先恢复候选资格。"})
    sources = list(sku.supplier_skus.filter(supplier=supplier, is_active=True).order_by("-is_preferred", "id"))
    if sources:
        if len(sources) > 1 and not sources[0].is_preferred:
            raise ValidationError({"supplier_sku": "该供应商有多个启用中的供货档案，请明确选择本次 Supplier SKU。"})
        return sources[0]
    return None


def resolve_purchase_item_sources(items, supplier, *, order=None, purchase_currency=None):
    """Resolve absent draft/new purchase sources through the same business rules."""
    for item in items:
        source = item.get("supplier_sku")
        if source is None:
            item["supplier_sku"] = ensure_purchase_source(
                item["sku"], supplier, order=order, currency=purchase_currency,
            )
    return items


def eligible_suppliers(product):
    """A supplied parent category covers its descendants, never siblings."""
    category_ids = set()
    for category in [product.category, *product.additional_categories.all()]:
        while category and category.pk not in category_ids:
            category_ids.add(category.pk)
            category = category.parent
    from crm.models import Supplier
    return Supplier.objects.filter(supply_categories__in=category_ids).distinct().order_by("name")
