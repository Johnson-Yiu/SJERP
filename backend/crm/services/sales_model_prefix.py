"""Previewable, history-preserving Sales Model Prefix changes."""

import hashlib
import json
import re

from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError

from crm.models import Product, SKU
from crm.services.sku_plans import _sales_model_for_base, save_version
from crm.sku_identity import build_sku_identity, complete_sales_model_abbreviations, identity_conflict_messages, parameter_pairs


def normalize_sales_model_prefix(value):
    value = str(value or "").strip().upper()
    if not value or not re.fullmatch(r"[A-Z0-9]+", value):
        raise ValidationError({"sales_model_prefix": "销售型号只能包含字母和数字，例如 BTY、COB320 或 SMD120。"})
    return value


def _baseline(product, rows, prefix):
    payload = {
        "product": product.pk,
        "product_updated_at": str(product.updated_at),
        "prefix": prefix,
        "skus": [
            {
                "id": sku.pk,
                "updated_at": str(sku.updated_at),
                "sales_model": sku.sales_model or "",
                "sales_model_abbreviations": sku.sales_model_abbreviations,
            }
            for sku in rows
        ],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def _preview(product, new_prefix, lock_skus=False):
    new_prefix = normalize_sales_model_prefix(new_prefix)
    if Product.objects.exclude(pk=product.pk).filter(sales_model_prefix__iexact=new_prefix).exists():
        raise ValidationError({"sales_model_prefix": "该销售型号前缀已被其他产品使用。"})

    queryset = product.skus.filter(active=True).order_by("pk")
    if lock_skus:
        queryset = queryset.select_for_update()
    rows = list(queryset)
    target_ids = {sku.pk for sku in rows}
    used_models = {
        value for value in SKU.objects.exclude(pk__in=target_ids).values_list("sales_model", flat=True) if value
    }
    old_prefix = product.sales_model_prefix or ""
    product.sales_model_prefix = new_prefix
    affected = []
    conflicts = []
    try:
        for sku in rows:
            abbreviations = complete_sales_model_abbreviations(
                sku.sales_model_abbreviations,
                parameter_pairs(product, sku.parameter_values),
            )
            generated = build_sku_identity(
                product,
                sku.specification,
                sku.parameter_values,
                sku.product_details,
                abbreviations,
            )
            new_model = _sales_model_for_base(
                generated.get("sales_model_base", ""), used_models, sku.sales_model or ""
            )
            if new_model:
                used_models.add(new_model)
            if new_model != (sku.sales_model or ""):
                conflicts.extend(identity_conflict_messages(
                    sales_model=new_model,
                    exclude_sku_ids=target_ids,
                ))
                affected.append({
                    "sku_id": sku.pk,
                    "sku_code": sku.sku,
                    "old_sales_model": sku.sales_model or "",
                    "new_sales_model": new_model,
                })
    finally:
        product.sales_model_prefix = old_prefix
    if conflicts:
        raise ValidationError({"sales_model": list(dict.fromkeys(conflicts))})
    return {
        "product": product.pk,
        "old_prefix": old_prefix,
        "new_prefix": new_prefix,
        "affected_skus": affected,
        "baseline": _baseline(product, rows, new_prefix),
    }


def preview_sales_model_prefix(product, new_prefix):
    return _preview(product, new_prefix)


@transaction.atomic
def apply_sales_model_prefix(product_id, new_prefix, baseline):
    product = Product.objects.select_for_update().get(pk=product_id)
    preview = _preview(product, new_prefix, lock_skus=True)
    if not baseline or baseline != preview["baseline"]:
        raise ValidationError({"baseline": "产品或 SKU 已变化，请重新预览后再确认。"})

    try:
        # The inner savepoint turns a race on either unique identity into a
        # validation response while the outer transaction still rolls back every SKU update.
        with transaction.atomic():
            rows = {sku.pk: sku for sku in product.skus.filter(active=True).select_for_update().order_by("pk")}
            for change in preview["affected_skus"]:
                sku = rows[change["sku_id"]]
                save_version(
                    sku,
                    type("PrefixPlan", (), {"version": sku.schema_version})(),
                    changed_fields=["sales_model"],
                    change_reason=f"Sales Model Prefix 从 {preview['old_prefix']} 变更为 {preview['new_prefix']}",
                )
                sku.sales_model = change["new_sales_model"]
                sku.save(update_fields=["sales_model", "updated_at"])
            product.sales_model_prefix = preview["new_prefix"]
            product.save(update_fields=["sales_model_prefix", "updated_at"])
    except IntegrityError:
        raise ValidationError({"sales_model": "Sales Model 或销售型号前缀与现有数据冲突，请重新预览后再确认。"})
    return preview
