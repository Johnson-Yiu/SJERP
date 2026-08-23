"""Helpers for the stable/internal and commercial SKU identities.

The project already stores SKU parameter values as JSON.  This module keeps
the conversion from those values to human-readable names and descriptions in
one place so API, imports, and future background jobs do not grow separate
formatting rules.
"""


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


def _category_attributes(product):
    categories = []
    category = getattr(product, "category", None)
    while category:
        categories.append(category)
        category = category.parent
    additional = list(product.additional_categories.all()) if product.pk else []
    merged = {}
    for category in reversed(categories + additional):
        for attribute in category.attributes.all():
            merged[attribute.key.lower()] = attribute
    return list(merged.values())


def parameter_pairs(product, parameter_values=None):
    parameter_values = parameter_values or {}
    pairs = []
    for attribute in _category_attributes(product):
        keys = [
            f"{attribute.category_id}:{attribute.key}",
            attribute.key,
            attribute.name,
        ]
        raw = next((parameter_values[key] for key in keys if key in parameter_values), "")
        values = _values(raw)
        if not values:
            continue
        for value in values:
            formatted = _with_unit(value, attribute.unit)
            if attribute.uppercase:
                formatted = formatted.upper()
            pairs.append({"name": attribute.name, "value": formatted, "unit": attribute.unit})
    if not pairs:
        for key, raw in (parameter_values or {}).items():
            for value in _values(raw):
                pairs.append({"name": str(key), "value": value, "unit": ""})
    return pairs


def _detail_tokens(product_details):
    tokens = []
    for detail in product_details or []:
        if not isinstance(detail, dict):
            continue
        model = str(detail.get("model") or "").strip()
        if model:
            tokens.append(model)
    return tokens


def build_sku_identity(product, specification="", parameter_values=None, product_details=None):
    """Return generated display and description values for one SKU."""
    pairs = parameter_pairs(product, parameter_values)
    details = _detail_tokens(product_details)
    legacy_specification = str(specification or "").strip()
    detail_text = " / ".join(details)
    pair_values = [pair["value"] for pair in pairs]
    readable_parts = [str(product.name or "").strip(), detail_text, *pair_values]
    display_name_cn = " ".join(part for part in readable_parts if part)
    if not display_name_cn:
        display_name_cn = str(product.name or "").strip()
    if legacy_specification and not pair_values and not detail_text:
        display_name_cn = " ".join(part for part in [product.name, legacy_specification] if part)

    cn_pairs = [f"{pair['name']}：{pair['value']}" for pair in pairs]
    description_cn = "，".join(part for part in [str(product.name or "").strip(), detail_text, *cn_pairs] if part)
    if not description_cn:
        description_cn = display_name_cn or legacy_specification

    english_name = str(getattr(product, "name_en", "") or product.name or "").strip()
    english_values = [pair["value"] for pair in pairs]
    description_en = ", ".join(part for part in [english_name, detail_text, *english_values] if part)
    if not description_en:
        description_en = display_name_cn or legacy_specification

    return {
        "display_name_cn": display_name_cn,
        "description_cn": description_cn,
        "description_en": description_en,
    }
