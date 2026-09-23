"""Helpers for the stable/internal and commercial SKU identities.

The project already stores SKU parameter values as JSON.  This module keeps
the conversion from those values to human-readable names and descriptions in
one place so API, imports, and future background jobs do not grow separate
formatting rules.
"""

import re


def normalize_display_name(value):
    """Normalize the internal display name for case-insensitive uniqueness."""
    return " ".join(str(value or "").casefold().strip().split())


def normalize_parameter_token(value):
    """Normalize a parameter token for stable identity and abbreviation keys."""
    return " ".join(str(value or "").casefold().strip().split())


def raw_parameter_value(values, key, name=""):
    """Read category-scoped keys and legacy labels, retaining the original value."""
    token = str(key).strip().casefold()
    normalized = {str(k).strip().casefold(): v for k, v in (values or {}).items()}
    if token in normalized:
        return normalized[token]
    suffix = token.split(":")[-1]
    aliases = {suffix, str(name).strip().casefold()} - {""}
    # Old category editor renamed 色温 to 色温/发光颜色 without migrating JSON keys.
    aliases.update(a.split("/")[0] for a in list(aliases) if "/" in a)
    matches = [v for k, v in normalized.items() if k.split(":")[-1] in aliases]
    return matches[0] if len(matches) == 1 else ""


def normalize_abbreviation_key(value):
    """Return the canonical category/attribute/value abbreviation key."""
    parts = str(value or "").split(":", 2)
    if len(parts) != 3 or not all(part.strip() for part in parts):
        return str(value or "").strip()
    category_id, attribute_key, raw_value = parts
    return f"{category_id.strip()}:{attribute_key.strip().casefold()}:{normalize_parameter_token(raw_value)}"


def abbreviation_key(category_id, attribute_key, value):
    return normalize_abbreviation_key(f"{category_id}:{attribute_key}:{value}")


def normalize_sales_model_abbreviations(value):
    if not isinstance(value, dict):
        return {}
    result = {}
    for key, abbreviation in value.items():
        canonical_key = normalize_abbreviation_key(key)
        if not canonical_key:
            continue
        normalized_abbreviation = str(abbreviation or "").strip().upper()
        if normalized_abbreviation:
            result[canonical_key] = normalized_abbreviation
    return result


def abbreviation_for(abbreviations, pair):
    canonical = pair.get("abbreviation_key", "")
    if not canonical:
        return ""
    return normalize_sales_model_abbreviations(abbreviations).get(canonical, "")


def complete_sales_model_abbreviations(abbreviations, pairs):
    """Fill known common abbreviations without replacing user choices."""
    from .sales_model_defaults import DEFAULT_SALES_MODEL_ABBREVIATIONS

    result = normalize_sales_model_abbreviations(abbreviations)
    for pair in pairs:
        if not pair.get("include_in_sales_model") or result.get(pair.get("abbreviation_key", "")):
            continue
        candidates = [pair.get("value", ""), str(pair.get("value", "")).replace(" ", "")]
        for value in candidates:
            key = re.sub(r"\s+", "", str(value or "").strip()).casefold()
            if key in DEFAULT_SALES_MODEL_ABBREVIATIONS:
                result[pair["abbreviation_key"]] = DEFAULT_SALES_MODEL_ABBREVIATIONS[key]
                break
    return result


def identity_conflict_messages(display_name_cn="", sales_model="", signature="", exclude_sku_id=None, exclude_sku_ids=None):
    """Return human-readable conflicts across current and historical identities."""
    from .models import SKU, SKUVersion

    conflicts = []
    name_key = normalize_display_name(display_name_cn)
    model_key = normalize_parameter_token(sales_model)
    excluded_ids = set(exclude_sku_ids or [])
    if exclude_sku_id:
        excluded_ids.add(exclude_sku_id)
    current_rows = SKU.objects.exclude(pk__in=excluded_ids) if excluded_ids else SKU.objects.all()
    if name_key:
        for row in current_rows.only("sku", "display_name_cn"):
            if normalize_display_name(row.display_name_cn) == name_key:
                conflicts.append(f"内部识别名称“{display_name_cn}”已被 SKU {row.sku} 使用。")
                break
        historical = SKUVersion.objects.exclude(sku_id__in=excluded_ids) if excluded_ids else SKUVersion.objects.all()
        match = next((version for version in historical.select_related("sku")
                      if normalize_display_name(version.display_name_cn_snapshot) == name_key), None)
        if match:
            conflicts.append(f"内部识别名称“{display_name_cn}”已是 SKU {match.sku.sku} 的历史名称。")
    if model_key:
        for row in current_rows.only("sku", "sales_model"):
            if normalize_parameter_token(row.sales_model) == model_key:
                conflicts.append(f"Sales Model“{sales_model}”已被 SKU {row.sku} 使用。")
                break
        historical = SKUVersion.objects.exclude(sku_id__in=excluded_ids) if excluded_ids else SKUVersion.objects.all()
        match = next((version for version in historical.select_related("sku")
                      if normalize_parameter_token(version.sales_model_snapshot) == model_key), None)
        if match:
            conflicts.append(f"Sales Model“{sales_model}”已是 SKU {match.sku.sku} 的历史型号。")
    if signature:
        duplicate = current_rows.filter(identity_signature=signature).only("sku", "sales_model").first()
        if duplicate:
            conflicts.append(f"参数组合已被 SKU {duplicate.sku} 使用（Sales Model：{duplicate.sales_model or '未设置'}）。")
    return list(dict.fromkeys(conflicts))


def _values(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value).replace("\r", "\n").split("\n") if part.strip()]


def _with_unit(value, unit):
    value = str(value or "").strip()
    unit = str(unit or "").strip()
    if not value or not unit or value.lower().endswith(unit.lower()):
        return value
    return f"{value}{unit}"


def live_category_attributes(product, category_order=None):
    """Return live category attributes, optionally using a proposed order."""
    categories = []
    category = getattr(product, "category", None)
    while category:
        categories.append(category)
        category = category.parent
    additional = list(product.additional_categories.all()) if product.pk else []
    merged = {}
    category_order = category_order or {}
    for category in reversed(categories + additional):
        attributes = list(category.attributes.all())
        order = category_order.get(category.pk)
        if order:
            attributes.sort(key=lambda attribute: order.get(attribute.pk, (10**9, attribute.id)))
        for attribute in attributes:
            merged[attribute.key.lower()] = attribute
    return list(merged.values())


def category_attributes(product, use_published_plan=True, category_order=None):
    from types import SimpleNamespace
    definitions = getattr(product, "_sku_definitions", None)
    if definitions is None and product.pk:
        if use_published_plan:
            plan = product.sku_parameter_plans.filter(status="published").order_by("-version").first()
            if plan:
                definitions = plan.definitions
    if definitions is not None:
        return [SimpleNamespace(**definition) for definition in definitions]
    return live_category_attributes(product, category_order=category_order)


def parameter_pairs(product, parameter_values=None):
    parameter_values = parameter_values or {}
    pairs = []
    for attribute in category_attributes(product):
        keys = [
            f"{attribute.category_id}:{attribute.key}",
            attribute.key,
            attribute.name,
        ]
        raw = raw_parameter_value(parameter_values, keys[0], attribute.name)
        if not raw:
            suffix = f":{str(attribute.key).strip().casefold()}"
            raw = next((value for key, value in parameter_values.items() if str(key).strip().casefold().endswith(suffix)), "")
        values = _values(raw)
        if not values:
            continue
        for value in values:
            formatted = _with_unit(value, attribute.unit)
            if attribute.uppercase:
                formatted = formatted.upper()
            pairs.append({
                "name": attribute.name,
                "key": f"{attribute.category_id}:{attribute.key}",
                "value": formatted,
                "unit": attribute.unit,
                "include_in_sku": attribute.include_in_sku,
                "include_in_sales_model": attribute.include_in_sales_model,
                "abbreviation_key": abbreviation_key(attribute.category_id, attribute.key, value),
            })
    if not pairs and not category_attributes(product):
        for key, raw in (parameter_values or {}).items():
            for value in _values(raw):
                pairs.append({"name": str(key), "key": str(key), "value": value, "unit": "", "include_in_sku": True, "include_in_sales_model": False, "abbreviation_key": ""})
    return pairs


def identity_signature(product, parameter_values=None):
    """Return a stable signature for the values that define a SKU variant.

    This intentionally excludes prices, packaging, images and product details.
    Attribute keys are category-scoped where available, and values are normalized
    without relying on JSON object ordering.
    """
    pairs = parameter_pairs(product, parameter_values)
    identity_pairs = [pair for pair in pairs if pair.get("include_in_sku") or pair.get("include_in_sales_model")]

    def normalized(value):
        return re.sub(r"\s+", "", str(value or "").strip()).casefold()

    values = sorted(
            f"{normalized(pair.get('key') or pair.get('name'))}={normalized(pair.get('value'))}"
        for pair in identity_pairs
        if normalized(pair.get("value"))
    )
    if values:
        return f"product={product.pk}|" + "|".join(values)
    return f"product={product.pk}|base" if category_attributes(product) else ""


def build_sku_identity(product, specification="", parameter_values=None, product_details=None, sales_model_abbreviations=None):
    """Return generated display and description values for one SKU."""
    pairs = parameter_pairs(product, parameter_values)
    legacy_specification = str(specification or "").strip()
    display_pairs = [pair for pair in pairs if pair.get("include_in_sku")]
    pair_values = [pair["value"] for pair in display_pairs]
    readable_parts = [str(product.name or "").strip(), *pair_values]
    display_name_cn = "-".join(part for part in readable_parts if part)
    if not display_name_cn:
        display_name_cn = str(product.name or "").strip()
    if legacy_specification and not pair_values:
        display_name_cn = "-".join(part for part in [product.name, legacy_specification] if part)

    cn_pairs = [f"{pair['name']}：{pair['value']}" for pair in display_pairs]
    description_cn = "，".join(part for part in [str(product.name or "").strip(), *cn_pairs] if part)
    if not description_cn:
        description_cn = display_name_cn or legacy_specification

    english_name = str(getattr(product, "name_en", "") or product.name or "").strip()
    english_values = [pair["value"] for pair in display_pairs]
    description_en = ", ".join(part for part in [english_name, *english_values] if part)
    if not description_en:
        description_en = display_name_cn or legacy_specification

    abbreviations = normalize_sales_model_abbreviations(sales_model_abbreviations)
    sales_model_tokens = [abbreviation_for(abbreviations, pair) for pair in pairs if pair.get("include_in_sales_model")]
    sales_model_suffix = "".join(token for token in sales_model_tokens if token)
    sales_model_prefix = str(getattr(product, "sales_model_prefix", "") or "").strip().upper()
    sales_model_base = "-".join(part for part in [sales_model_prefix, sales_model_suffix] if part) if sales_model_suffix else ""

    return {
        "display_name_cn": display_name_cn,
        "description_cn": description_cn,
        "description_en": description_en,
        "sales_model_base": sales_model_base,
    }
