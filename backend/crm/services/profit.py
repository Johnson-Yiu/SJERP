"""Shared operational profit estimate; intentionally not an accounting net-profit calculation."""
from decimal import Decimal

from crm.models import FinancePlanWriteoff, FinanceReceiptAdjustment, Transaction
from .purchase_costs import order_purchase_cost


def order_profit_summary(order):
    purchase_base_rmb, purchase_additional_rmb = order_purchase_cost(order)
    expense_rmb = sum(
        (row.rmb_reference_amount or Decimal("0") for row in order.transactions.filter(
            status="confirmed", direction="expense",
        ).exclude(kind__in=["supplier_payment", "refund", "unallocated_advance", "unallocated_payment"])),
        Decimal("0"),
    )
    receipt_fee_rmb = sum((
        row.amount * row.transaction.exchange_rate
        for row in FinanceReceiptAdjustment.objects.filter(order=order, nature="bank_fee", handling="company", transaction__status="confirmed").select_related("transaction")
        if not row.transaction.reference_rate_missing and row.transaction.exchange_rate is not None
    ), Decimal("0"))
    receivable_reduction_rmb = sum((
        row.amount * order.exchange_rate
        for row in FinancePlanWriteoff.objects.filter(plan__order=order, source_transaction__status="confirmed")
    ), Decimal("0"))
    expense_rmb += receipt_fee_rmb
    sales_rmb = order.total_amount * order.exchange_rate
    purchase_cost_rmb = purchase_base_rmb + purchase_additional_rmb
    estimated_profit_rmb = sales_rmb - purchase_cost_rmb - expense_rmb - receivable_reduction_rmb
    return {
        "sales_rmb": sales_rmb, "purchase_base_rmb": purchase_base_rmb,
        "purchase_additional_rmb": purchase_additional_rmb, "purchase_cost_rmb": purchase_cost_rmb,
        "order_expense_rmb": expense_rmb, "expense_rmb": expense_rmb,
        "receipt_bank_fee_rmb": receipt_fee_rmb, "receivable_reduction_rmb": receivable_reduction_rmb,
        "estimated_profit_rmb": estimated_profit_rmb,
        "estimated_gross_profit_rmb": estimated_profit_rmb,
        "estimated_margin_percent": (estimated_profit_rmb / sales_rmb * Decimal("100")) if sales_rmb else Decimal("0"),
    }
