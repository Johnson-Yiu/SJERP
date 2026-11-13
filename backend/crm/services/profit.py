"""Shared operational profit estimate; intentionally not an accounting net-profit calculation."""
from decimal import Decimal

from django.db.models import Q
from crm.models import AdvanceAllocation, FinancePlanWriteoff, FinancePlanWriteoffCorrection, Transaction
from .purchase_costs import IncompletePurchaseCost, order_purchase_cost_components


def order_profit_summary(order):
    cost_issue = None
    try:
        purchase_base_rmb, purchase_contract_change_rmb, purchase_additional_rmb = order_purchase_cost_components(order)
    except IncompletePurchaseCost as error:
        purchase_base_rmb = purchase_contract_change_rmb = purchase_additional_rmb = None
        cost_issue = str(error.detail[0])
    missing_rate = Q(reference_rate_missing=True) | Q(exchange_rate__isnull=True)
    expense_rows = order.transactions.filter(status="confirmed", direction="expense").exclude(
        kind__in=["supplier_payment", "refund", "unallocated_advance", "unallocated_payment"])
    direct_fee_rows = order.transactions.filter(status="confirmed", direction="income", fee_responsibility="company", bank_fee_amount__gt=0)
    allocation_rows = AdvanceAllocation.objects.filter(plan__order=order, is_active=True, advance__status="confirmed", advance__fee_responsibility__in=["company", "mixed"], fee_credit_amount__gt=0).exclude(advance__kind="customer_receipt", advance__order=order)
    reference_incomplete = (expense_rows.filter(missing_rate).exists() or direct_fee_rows.filter(missing_rate).exists()
        or allocation_rows.filter(Q(advance__reference_rate_missing=True) | Q(advance__exchange_rate__isnull=True)).exists())
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
        plan__order=order, is_active=True, advance__status="confirmed", advance__fee_responsibility__in=["company", "mixed"],
    ).exclude(advance__kind="customer_receipt", advance__order=order).select_related("advance") if row.advance.exchange_rate is not None and not row.advance.reference_rate_missing), Decimal("0"))
    expense_rmb += direct_fees + allocated_fees
    writeoffs = FinancePlanWriteoff.objects.filter(plan__order=order, source_transaction__status="confirmed")
    reduction = sum(writeoffs.values_list("amount", flat=True), Decimal("0"))
    reduction -= sum(FinancePlanWriteoffCorrection.objects.filter(writeoff__in=writeoffs).values_list("amount", flat=True), Decimal("0"))
    receivable_reduction_rmb = reduction * order.exchange_rate
    sales_rmb = order.total_amount * order.exchange_rate
    purchase_cost_rmb = None if cost_issue else purchase_base_rmb + purchase_contract_change_rmb + purchase_additional_rmb
    estimated_profit_rmb = None if cost_issue else sales_rmb - purchase_cost_rmb - expense_rmb - receivable_reduction_rmb
    return {
        "sales_rmb": sales_rmb, "purchase_base_rmb": purchase_base_rmb,
        "purchase_contract_change_rmb": purchase_contract_change_rmb,
        "purchase_additional_rmb": purchase_additional_rmb, "purchase_cost_rmb": purchase_cost_rmb,
        "order_expense_rmb": expense_rmb, "expense_rmb": expense_rmb,
        "receipt_bank_fee_rmb": direct_fees + allocated_fees,
        "receivable_reduction_rmb": receivable_reduction_rmb,
        "cost_incomplete": cost_issue is not None, "cost_issue": cost_issue,
        "reference_incomplete": reference_incomplete,
        "estimated_profit_rmb": estimated_profit_rmb,
        "estimated_gross_profit_rmb": estimated_profit_rmb,
        "estimated_margin_percent": None if cost_issue else (estimated_profit_rmb / sales_rmb * Decimal("100") if sales_rmb else Decimal("0")),
    }
