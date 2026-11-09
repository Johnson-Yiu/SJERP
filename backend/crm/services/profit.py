"""Shared operational profit estimate; intentionally not an accounting net-profit calculation."""
from decimal import Decimal

from crm.models import AdvanceAllocation, FinancePlanWriteoff, FinancePlanWriteoffCorrection, Transaction
from .purchase_costs import order_purchase_cost


def order_profit_summary(order):
    purchase_base_rmb, purchase_additional_rmb = order_purchase_cost(order)
    expense_rmb = sum(
        (row.rmb_reference_amount or Decimal("0") for row in order.transactions.filter(
            status="confirmed", direction="expense",
        ).exclude(kind__in=["supplier_payment", "refund", "unallocated_advance", "unallocated_payment"])),
        Decimal("0"),
    )
    # A company-borne collection fee is an order expense. It is already netted
    # from receipt cash, so never add a separate cash-out transaction.
    direct_fees = sum((row.bank_fee_amount * row.exchange_rate for row in order.transactions.filter(
        status="confirmed", direction="income", fee_responsibility="company", bank_fee_amount__gt=0,
    ) if row.exchange_rate is not None and not row.reference_rate_missing), Decimal("0"))
    allocated_fees = sum((row.fee_credit_amount * row.advance.exchange_rate for row in AdvanceAllocation.objects.filter(
        plan__order=order, is_active=True, advance__status="confirmed", advance__fee_responsibility="company",
    ).exclude(advance__kind="customer_receipt", advance__order=order).select_related("advance") if row.advance.exchange_rate is not None and not row.advance.reference_rate_missing), Decimal("0"))
    expense_rmb += direct_fees + allocated_fees
    writeoffs = FinancePlanWriteoff.objects.filter(plan__order=order, source_transaction__status="confirmed")
    reduction = sum(writeoffs.values_list("amount", flat=True), Decimal("0"))
    reduction -= sum(FinancePlanWriteoffCorrection.objects.filter(writeoff__in=writeoffs).values_list("amount", flat=True), Decimal("0"))
    sales_rmb = (order.total_amount - reduction) * order.exchange_rate
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
