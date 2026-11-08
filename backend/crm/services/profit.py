"""Shared operational profit estimate; intentionally not an accounting net-profit calculation."""
from decimal import Decimal

from crm.models import Transaction
from .purchase_costs import order_purchase_cost


def order_profit_summary(order):
    purchase_base_rmb, purchase_additional_rmb = order_purchase_cost(order)
    expense_rmb = sum(
        (row.rmb_reference_amount or Decimal("0") for row in order.transactions.filter(
            status="confirmed", direction="expense",
        ).exclude(kind__in=["supplier_payment", "refund", "unallocated_advance", "unallocated_payment"])),
        Decimal("0"),
    )
    sales_rmb = order.total_amount * order.exchange_rate
    purchase_cost_rmb = purchase_base_rmb + purchase_additional_rmb
    estimated_profit_rmb = sales_rmb - purchase_cost_rmb - expense_rmb
    return {
        "sales_rmb": sales_rmb, "purchase_base_rmb": purchase_base_rmb,
        "purchase_additional_rmb": purchase_additional_rmb, "purchase_cost_rmb": purchase_cost_rmb,
        "order_expense_rmb": expense_rmb, "expense_rmb": expense_rmb,
        "estimated_profit_rmb": estimated_profit_rmb,
        "estimated_gross_profit_rmb": estimated_profit_rmb,
        "estimated_margin_percent": (estimated_profit_rmb / sales_rmb * Decimal("100")) if sales_rmb else Decimal("0"),
    }
