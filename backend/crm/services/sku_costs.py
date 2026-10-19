"""SKU cost verification and quote risk helpers.

This module deliberately reports risk state, not cost amounts.  Quote callers
can therefore show a useful internal warning without widening the purchasing
cost data boundary.
"""

from datetime import timedelta

from django.utils import timezone


COST_VERIFICATION_MAX_AGE_DAYS = 90

RISK_LABELS = {
    "missing_sales_model": "缺少 Sales Model",
    "missing_supplier_source": "缺少正式 SupplierSKU 采购来源",
    "missing_reference_cost": "缺少有效采购参考成本",
    "cost_unverified": "SKU 内部成本尚未核实",
    "cost_expired": "SKU 内部成本核实已超过 90 天",
    "supplier_price_unverified": "供应商参考采购价待核实",
    "supplier_price_expired": "供应商参考采购价核实已超过 90 天",
}


def verification_state(value, currency, verified_at, *, now=None):
    """Return a stable display state without converting or inferring amounts."""
    if value is None or value <= 0 or not str(currency or "").strip():
        return "missing"
    if verified_at is None:
        return "unverified"
    current_time = now or timezone.now()
    if verified_at < current_time - timedelta(days=COST_VERIFICATION_MAX_AGE_DAYS):
        return "expired"
    return "current"


def verification_state_label(state):
    return {
        "missing": "未维护",
        "unverified": "待核实",
        "expired": "已过期",
        "current": "已核实",
    }.get(state, "未知")


def quote_risk_row(sku, *, now=None):
    """Build a quote-safe risk row for one SKU.

    The response intentionally contains no cost amount, purchase price, or
    purchasing currency.  Currency and amount remain available only through
    the purchasing-authorized SKU/SupplierSKU serializers.
    """
    sources = [source for source in sku.supplier_skus.all() if source.is_active]
    cost_state = verification_state(sku.cost_price, sku.cost_currency, sku.cost_verified_at, now=now)
    positive_sources = [
        source for source in sources
        if source.purchase_price is not None
        and source.purchase_price > 0
        and str(source.currency or "").strip()
    ]
    source_states = [
        verification_state(source.purchase_price, source.currency, source.purchase_price_verified_at, now=now)
        for source in positive_sources
    ]

    codes = []
    if not str(sku.sales_model or "").strip():
        codes.append("missing_sales_model")
    if not sources:
        codes.append("missing_supplier_source")
    if cost_state == "missing" or not positive_sources:
        codes.append("missing_reference_cost")
    if cost_state == "unverified":
        codes.append("cost_unverified")
    elif cost_state == "expired":
        codes.append("cost_expired")
    if "unverified" in source_states:
        codes.append("supplier_price_unverified")
    if "expired" in source_states:
        codes.append("supplier_price_expired")

    return {
        "sku": sku.pk,
        "sku_code": sku.sku,
        "label": sku.sales_model or sku.sku,
        "has_risk": bool(codes),
        "risk_codes": codes,
        "risk_labels": [RISK_LABELS[code] for code in codes],
        "cost_verification_state": cost_state,
        "supplier_source_count": len(sources),
    }


def quote_risk_rows(skus, *, now=None):
    return [quote_risk_row(sku, now=now) for sku in skus]
