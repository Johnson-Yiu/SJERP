"""Shared commercial money rounding rules.

Formal documents display and settle each line at currency-cent precision.
Keeping this rule in one small helper prevents model/API/export drift while
leaving the stored high-precision unit prices unchanged.
"""

from decimal import Decimal, ROUND_HALF_UP


MONEY_QUANTUM = Decimal("0.01")


def money(value):
    """Round one commercial amount to cents with the documented rule."""
    return Decimal(value or 0).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def document_total(lines, *, shipping_fee=0, discount=0):
    """Calculate a document total from displayed, per-line money amounts."""
    subtotal = sum((money(line.amount) for line in lines), Decimal("0.00"))
    return money(subtotal + money(shipping_fee) - money(discount))
