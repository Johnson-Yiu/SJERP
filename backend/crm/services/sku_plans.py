"""Reviewable SKU schema changes without rewriting business documents or stock."""
import hashlib
import json
from collections import defaultdict
from copy import deepcopy

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from crm.models import Product, SKU, SKUParameterPlan, SKURelationship, SKUVersion
from crm.sku_identity import build_sku_identity, category_attributes, complete_sales_model_abbreviations, identity_conflict_messages, identity_signature, normalize_display_name, normalize_parameter_token, parameter_pairs, raw_parameter_value
from .supplier_candidates import parameter_value


def definitions_for(product, use_published_plan=True, category_order=None):
    fields = ("category_id", "key", "name", "unit", "include_in_sku", "include_in_sales_model", "uppercase", "required", "default_value")
    return [{key: getattr(a, key, "" if key in {"unit", "default_value"} else False) for key in fields}
            for a in category_attributes(product, use_published_plan=use_published_plan, category_order=category_order)]


def _sales_model_for_base(base, used, current=""):
    if not base:
        return current or ""
    # Existing numbered models remain stable when their parameter base is unchanged.
    legacy_suffix = current[len(base) + 1:] if current.startswith(f"{base}-") else ""
    model = current if current == base or legacy_suffix.isdigit() else base
    if normalize_parameter_token(model) in {normalize_parameter_token(value) for value in used}:
        raise ValidationError({"sales_model": f"Sales Model“{model}”重复，请调整参与型号生成的参数或缩写。"})
    return model


def _refreshable_identity(sku, product, definitions, used_models):
    product._sku_definitions = definitions
    abbreviations = complete_sales_model_abbreviations(sku.sales_model_abbreviations, parameter_pairs(product, sku.parameter_values))
    generated = build_sku_identity(product, sku.specification, sku.parameter_values, sku.product_details, abbreviations)
    new_model = _sales_model_for_base(generated.get("sales_model_base", ""), used_models, sku.sales_model or "")
    return generated, abbreviations, new_model


def _version_fields_for(sku, new_name, new_model, new_parameters=None):
    fields = []
    if new_parameters is not None and sku.parameter_values != new_parameters:
        fields.append("parameter_values")
    if sku.display_name_cn != new_name:
        fields.append("display_name_cn")
    if sku.sales_model != new_model:
        fields.append("sales_model")
    return fields


def _category_scope(category):
    scope = {category.pk}
    pending = [category.pk]
    while pending:
        children = list(category.__class__.objects.filter(parent_id__in=pending).values_list("pk", flat=True))
        pending = [child for child in children if child not in scope]
        scope.update(pending)
    return scope


def _reordered_definitions(product, category_id, attribute_ids):
    order = {category_id: {attribute_id: (index, attribute_id) for index, attribute_id in enumerate(attribute_ids)}}
    live = definitions_for(product, use_published_plan=False, category_order=order)
    plan = product.sku_parameter_plans.filter(status="published").order_by("-version").first()
    if not plan:
        return live, None
    live_order = {(definition["category_id"], definition["key"].casefold()): index for index, definition in enumerate(live)}
    definitions = sorted(
        deepcopy(plan.definitions),
        key=lambda definition: live_order.get((definition.get("category_id"), str(definition.get("key", "")).casefold()), 10**9),
    )
    return definitions, plan


def preview_category_attribute_reorder(category, attribute_ids):
    """Build the identity changes caused by a proposed category attribute order."""
    scope = _category_scope(category)
    products = Product.objects.filter(Q(category_id__in=scope) | Q(additional_categories__in=scope)).distinct().prefetch_related("additional_categories")
    changes = []
    for product in products:
        definitions, _ = _reordered_definitions(product, category.pk, attribute_ids)
        product._sku_definitions = definitions
        rows = list(product.skus.filter(active=True).order_by("id"))
        used_models = {value for value in SKU.objects.exclude(product=product).values_list("sales_model", flat=True) if value}
        for sku in rows:
            generated, abbreviations, new_model = _refreshable_identity(sku, product, definitions, used_models)
            new_name = generated.get("display_name_cn", "")
            if new_model:
                used_models.add(new_model)
            if sku.display_name_cn != new_name or sku.sales_model != new_model:
                changes.append({
                    "product_id": product.pk,
                    "sku_id": sku.pk,
                    "sku_code": sku.sku,
                    "old_display_name_cn": sku.display_name_cn,
                    "new_display_name_cn": new_name,
                    "old_sales_model": sku.sales_model or "",
                    "new_sales_model": new_model,
                    "abbreviations": abbreviations,
                })
        del product._sku_definitions
    return {"affected_skus": len(changes), "changes": changes}


@transaction.atomic
def apply_category_attribute_reorder(category, attribute_ids):
    """Persist the proposed order and refresh current SKU identities atomically."""
    preview = preview_category_attribute_reorder(category, attribute_ids)
    conflicts = []
    target_ids = {change["sku_id"] for change in preview["changes"]}
    names = {}
    models = {}
    for change in preview["changes"]:
        name_key = normalize_display_name(change["new_display_name_cn"])
        if name_key and name_key in names:
            conflicts.append(f"内部识别名称“{change['new_display_name_cn']}”在本次排序结果中与 SKU {names[name_key]} 重复。")
        elif name_key:
            names[name_key] = change["sku_code"]
        model_key = normalize_parameter_token(change["new_sales_model"])
        if model_key and model_key in models:
            conflicts.append(f"Sales Model“{change['new_sales_model']}”在本次排序结果中与 SKU {models[model_key]} 重复。")
        elif model_key:
            models[model_key] = change["sku_code"]
        conflicts.extend(identity_conflict_messages(
            change["new_display_name_cn"],
            change["new_sales_model"],
            exclude_sku_ids=target_ids,
        ))
    if conflicts:
        raise ValidationError({"duplicate_sku": list(dict.fromkeys(conflicts))})

    scope = _category_scope(category)
    product_ids = Product.objects.filter(
        Q(category_id__in=scope) | Q(additional_categories__in=scope)
    ).values_list("pk", flat=True).distinct()
    products = Product.objects.select_for_update().filter(pk__in=product_ids).order_by("pk").prefetch_related("additional_categories")
    changes_by_product = {}
    for change in preview["changes"]:
        changes_by_product.setdefault(change["product_id"], {})[change["sku_id"]] = change
    for product in products:
        definitions, plan = _reordered_definitions(product, category.pk, attribute_ids)
        product._sku_definitions = definitions
        if plan and plan.definitions != definitions:
            plan.definitions = definitions
            plan.baseline = baseline(product)
            plan.save(update_fields=["definitions", "baseline", "updated_at"])
        for sku_id, change in changes_by_product.get(product.pk, {}).items():
            sku = SKU.objects.select_for_update().get(pk=sku_id)
            save_version(sku, plan or type("Plan", (), {"version": sku.schema_version})(),
                         changed_fields=["display_name_cn", "sales_model"], change_reason="分类属性排序变更并刷新 SKU")
            sku.display_name_cn = change["new_display_name_cn"]
            sku.display_name_key = normalize_display_name(change["new_display_name_cn"]) or None
            sku.sales_model = change["new_sales_model"] or sku.sales_model
            sku.sales_model_abbreviations = change["abbreviations"]
            sku.save()
        del product._sku_definitions
    return preview


def baseline(product):
    data = {"definitions": definitions_for(product), "skus": list(product.skus.order_by("id").values("id", "updated_at", "active", "parameter_values"))}
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()


def validate_definitions(definitions):
    if not isinstance(definitions, list) or len(definitions) > 40:
        raise ValidationError("参数方案须为不超过 40 项的列表。")
    seen = set()
    for d in definitions:
        if not isinstance(d, dict) or not isinstance(d.get("key"), str) or not d["key"].strip() or not d.get("name"):
            raise ValidationError("每个参数必须有名称和稳定标识。")
        key = d["key"].strip().casefold()
        if key in seen or ":" in key:
            raise ValidationError("参数标识不能重复或包含冒号。")
        seen.add(key)
        d["key"] = key
        for field in ("include_in_sku", "include_in_sales_model", "uppercase", "required"):
            if not isinstance(d.get(field, False), bool):
                raise ValidationError("参数开关须为布尔值。")
            d.setdefault(field, False)
        for field in ("name", "unit", "default_value"):
            if not isinstance(d.get(field, ""), str) or len(d.get(field, "")) > 200:
                raise ValidationError("参数名称、单位和默认值须为不超过 200 字的文本。")
            d.setdefault(field, "")
        if not isinstance(d.get("category_id"), int) or d["category_id"] < 0:
            raise ValidationError("参数所属分组无效。")
    return definitions


@transaction.atomic
def draft_plan(product):
    product = Product.objects.select_for_update().get(pk=product.pk)
    draft = product.sku_parameter_plans.filter(status="draft").first()
    if draft:
        return draft
    version = (product.sku_parameter_plans.order_by("-version").values_list("version", flat=True).first() or 0) + 1
    return SKUParameterPlan.objects.create(product=product, version=version, definitions=definitions_for(product), baseline=baseline(product))


def analyze(plan):
    product = plan.product
    stale = baseline(product) != plan.baseline
    definitions = validate_definitions(deepcopy(plan.definitions))
    old_definitions = {d["key"]: d for d in definitions_for(product)}
    product._sku_definitions = definitions
    rows = list(product.skus.filter(active=True).order_by("id"))
    groups = defaultdict(list)
    missing = []
    assignments = plan.assignments
    if not isinstance(assignments, dict) or set(assignments) - {str(row.pk) for row in rows}:
        raise ValidationError("补值或拆分方案包含无效 SKU，请刷新草稿。")
    for sku in rows:
        variants = assignments.get(str(sku.pk), [sku.parameter_values])
        if not isinstance(variants, list) or not 1 <= len(variants) <= 50:
            raise ValidationError("每个 SKU 应保留 1–50 个实际组合；停用请使用 SKU 停用功能。")
        for variant in variants:
            if not isinstance(variant, dict) or any(not isinstance(v, (str, int, float)) for v in variant.values()):
                raise ValidationError("每个组合的参数必须是单个文本值。")
            values = deepcopy(sku.parameter_values)
            values.update(variant)
            for d in definitions:
                key = f"{d['category_id']}:{d['key']}"
                # Prefer an explicit assignment, then the prior value, then a reviewed default.
                raw = variant[key] if key in variant else (raw_parameter_value(variant, key, d["name"]) or raw_parameter_value(values, key, d["name"]) or d["default_value"])
                values[key] = raw
                if (d["required"] or d["include_in_sku"] or d["include_in_sales_model"]) and not str(raw).strip():
                    missing.append({"sku": sku.sku, "parameter": d["name"]})
            signature = identity_signature(product, values) or f"product={product.pk}|base"
            if len(signature) > 500:
                raise ValidationError("参数组合过长，请缩短参数值。")
            groups[signature].append({"sku": sku, "values": values, "split": len(variants) > 1})
    result = []
    identity_changes = []
    used_models = {value for value in SKU.objects.exclude(product=product).values_list("sales_model", flat=True) if value}
    for signature, entries in groups.items():
        source_ids = sorted({e["sku"].pk for e in entries})
        if len(source_ids) != len(entries):
            raise ValidationError("拆分后的组合重复，请删除重复组合。")
        first = entries[0]
        if len({e["sku"].unit for e in entries}) > 1:
            raise ValidationError("计量单位不同的 SKU 不能合并，请保留区分参数。")
        changed = any(parameter_value(first["sku"].parameter_values, f"{d['category_id']}:{d['key']}") !=
                      parameter_value(first["values"], f"{d['category_id']}:{d['key']}")
                      for d in definitions if d["include_in_sku"] or d["include_in_sales_model"])
        changed = changed or any(d["key"] in old_definitions and old_definitions[d["key"]]["unit"] != d["unit"]
                                 for d in definitions if d["include_in_sku"] or d["include_in_sales_model"])
        replace = len(source_ids) > 1 or any(e["split"] for e in entries) or changed
        values = deepcopy(first["values"])
        conflicts = []
        for d in definitions:
            if d["include_in_sku"] or d["include_in_sales_model"]:
                continue
            key = f"{d['category_id']}:{d['key']}"
            if len({parameter_value(e["values"], key) for e in entries}) > 1:
                conflicts.append(d["name"])
                aliases = {d["key"].casefold(), d["name"].casefold(), d["key"].split("/")[0].casefold()}
                values = {k: v for k, v in values.items() if k.split(":")[-1].casefold() not in aliases}
                values[key] = ""
                if d["required"]:
                    missing.append({"sku": " + ".join(e["sku"].sku for e in entries), "parameter": d["name"] + "（合并取值不一致）"})
        action = "refresh" if changed and len(source_ids) == 1 and len(entries) == 1 and not entries[0]["split"] else ("new" if replace else "keep")
        result.append({"signature": signature, "source_ids": source_ids, "source_codes": [e["sku"].sku for e in entries], "values": values,
                       "ordinary_conflicts": conflicts, "action": action})
        if action in {"refresh", "keep"}:
            source = entries[0]["sku"]
            original_values = source.parameter_values
            source.parameter_values = values
            generated, _, new_model = _refreshable_identity(source, product, definitions, used_models)
            source.parameter_values = original_values
            if new_model:
                used_models.add(new_model)
            if source.display_name_cn != generated.get("display_name_cn", "") or source.sales_model != new_model:
                identity_changes.append({
                    "sku_id": source.pk,
                    "sku_code": source.sku,
                    "old_display_name_cn": source.display_name_cn,
                    "new_display_name_cn": generated.get("display_name_cn", ""),
                    "old_sales_model": source.sales_model or "",
                    "new_sales_model": new_model,
                    "action": action,
                })
    del product._sku_definitions
    return {"stale": stale, "missing": missing, "groups": result, "identity_changes": identity_changes, "current_count": len(rows), "new_count": sum(g["action"] == "new" for g in result), "result_count": len(result), "history_rewritten": 0}


def save_version(sku, plan, changed_fields=None, change_reason=None):
    SKUVersion.objects.create(sku=sku, version_no=(sku.versions.order_by("-version_no").values_list("version_no", flat=True).first() or 0) + 1,
        sku_code_snapshot=sku.sku, sales_model_snapshot=sku.sales_model or "", display_name_cn_snapshot=sku.display_name_cn,
        description_cn_snapshot=sku.description_cn, description_en_snapshot=sku.description_en,
        parameter_values_snapshot=sku.parameter_values, product_details_snapshot=sku.product_details,
        specification_snapshot=sku.specification, changed_fields=changed_fields or ["parameter_values", "schema_version"],
        change_reason=change_reason or f"发布参数方案 V{plan.version}")


@transaction.atomic
def publish(plan):
    Product.objects.select_for_update().get(pk=plan.product_id)
    plan = SKUParameterPlan.objects.select_for_update().select_related("product").get(pk=plan.pk)
    if plan.status != "draft":
        raise ValidationError("该方案已发布。")
    impact = analyze(plan)
    if impact["stale"]:
        raise ValidationError("SKU 或参数已变化，请刷新草稿并重新分析。")
    if impact["missing"]:
        raise ValidationError({"missing": impact["missing"]})
    rows = {s.pk: s for s in plan.product.skus.select_for_update().filter(active=True)}
    product = plan.product
    product._sku_definitions = plan.definitions
    archived = set()
    used_models = {value for value in SKU.objects.exclude(pk__in=rows).values_list("sales_model", flat=True) if value}
    for group in impact["groups"]:
        from .sku_combination_rules import validate_combination
        validate_combination(product, group["values"])
        source = rows[group["source_ids"][0]]
        if group["action"] == "keep":
            old_parameters = source.parameter_values
            source.parameter_values = group["values"]
            generated, abbreviations, new_model = _refreshable_identity(source, product, plan.definitions, used_models)
            source.parameter_values = old_parameters
            changed_fields = _version_fields_for(source, source.display_name_cn, new_model, group["values"])
            if source.schema_version != plan.version:
                changed_fields.append("schema_version")
            if changed_fields:
                save_version(source, plan, changed_fields=sorted(set(changed_fields)))
            source.parameter_values = group["values"]
            source.identity_signature = group["signature"]
            source.sales_model_abbreviations = abbreviations
            source.schema_version = plan.version
            source.save()
            if new_model:
                used_models.add(new_model)
        elif group["action"] == "refresh":
            source.parameter_values = group["values"]
            generated, abbreviations, new_model = _refreshable_identity(source, product, plan.definitions, used_models)
            new_name = generated.get("display_name_cn", "")
            conflicts = identity_conflict_messages(new_name, new_model, group["signature"], exclude_sku_id=source.pk)
            if conflicts:
                raise ValidationError({"duplicate_sku": conflicts})
            changed_fields = _version_fields_for(source, new_name, new_model, group["values"])
            if source.schema_version != plan.version:
                changed_fields.append("schema_version")
            if changed_fields:
                save_version(source, plan, changed_fields=sorted(set(changed_fields)), change_reason=f"参数值变更并刷新 SKU V{plan.version}")
            source.display_name_cn = new_name
            source.display_name_key = normalize_display_name(new_name) or None
            source.sales_model = new_model or source.sales_model
            source.sales_model_abbreviations = abbreviations
            source.identity_signature = group["signature"]
            source.schema_version = plan.version
            source.save()
            if new_model:
                used_models.add(new_model)
        else:
            for source_id in group["source_ids"]:
                save_version(rows[source_id], plan, change_reason=f"拆分或合并 SKU 参数方案 V{plan.version}")
            abbreviations = complete_sales_model_abbreviations(source.sales_model_abbreviations, parameter_pairs(product, group["values"]))
            generated = build_sku_identity(product, source.specification, group["values"], source.product_details, abbreviations)
            new_model = _sales_model_for_base(generated.get("sales_model_base", ""), used_models)
            conflicts = identity_conflict_messages(sales_model=new_model)
            if conflicts:
                raise ValidationError({"duplicate_sku": conflicts})
            target = SKU(product=product, parameter_values=group["values"], identity_signature=group["signature"], schema_version=plan.version,
                display_name_cn=generated.get("display_name_cn", ""), sales_model=new_model or None, sales_model_abbreviations=abbreviations,
                description_cn=generated.get("description_cn", ""), description_en=generated.get("description_en", ""),
                unit=source.unit, currency=source.currency, cost_price=source.cost_price, cost_currency=source.cost_currency,
                cost_verified_at=source.cost_verified_at, cost_verified_by=source.cost_verified_by, default_price=source.default_price)
            target.save(preserve_unknown_cost_currency=True)
            if new_model:
                used_models.add(new_model)
            for source_id in group["source_ids"]:
                SKURelationship.objects.create(source=rows[source_id], target=target, plan=plan)
                archived.add(source_id)
    SKU.objects.filter(pk__in=archived).update(active=False, updated_at=timezone.now())
    plan.status = "published"
    plan.published_at = timezone.now()
    plan.save()
    return impact
