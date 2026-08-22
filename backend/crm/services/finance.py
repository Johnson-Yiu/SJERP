from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import transaction

from crm.models import PaymentPlan, Transaction


def _transaction_no(prefix="FIN"):
    return f"{prefix}-{uuid4().hex[:16].upper()}"


def _contract_amount(contract):
    return contract.total_amount


@transaction.atomic
def ensure_default_payment_plans(contract, deposit_ratio=Decimal("0.30")):
    is_order = contract.__class__.__name__ == "Order"
    relation = {"order": contract} if is_order else {"purchase_order": contract}
    direction = "receivable" if is_order else "payable"
    if PaymentPlan.objects.filter(**relation).exists():
        return list(PaymentPlan.objects.filter(**relation).order_by("id"))
    total = _contract_amount(contract)
    if total <= 0:
        return []
    deposit = (total * Decimal(str(deposit_ratio))).quantize(Decimal("0.01"))
    balance = total - deposit
    rows = [
        PaymentPlan.objects.create(**relation, direction=direction, currency=contract.currency, due_date=contract.order_date, planned_amount=deposit, notes="默认预付款/定金"),
        PaymentPlan.objects.create(**relation, direction=direction, currency=contract.currency, due_date=contract.expected_ship_date if is_order else contract.expected_arrival_date, planned_amount=balance, notes="默认尾款"),
    ]
    return rows


@transaction.atomic
def record_transaction(payload):
    payload = payload.copy()
    plan = payload.pop("plan", None)
    amount = Decimal(str(payload.pop("amount")))
    if amount <= 0:
        raise ValidationError("收付款金额必须大于零。")
    if plan:
        plan = PaymentPlan.objects.select_for_update().select_related("order__customer", "purchase_order__supplier").get(pk=plan.pk)
        if plan.status != "open":
            raise ValidationError("只能核销待结清的收付款计划。")
        if payload.get("currency", plan.currency) != plan.currency:
            raise ValidationError("实际收付款币种必须与计划原币一致。")
        remaining = plan.remaining_amount
        applied_amount = min(amount, remaining)
        if plan.order_id:
            payload.setdefault("order", plan.order)
            payload.setdefault("customer", plan.order.customer)
            payload.setdefault("direction", "income")
            payload.setdefault("kind", "customer_receipt")
        else:
            payload.setdefault("purchase_order", plan.purchase_order)
            payload.setdefault("supplier", plan.purchase_order.supplier)
            payload.setdefault("direction", "expense")
            payload.setdefault("kind", "supplier_payment")
    else:
        applied_amount = amount
    exchange_rate = Decimal(str(payload.get("exchange_rate", 1)))
    payload.setdefault("rmb_amount", (applied_amount * exchange_rate).quantize(Decimal("0.01")))
    row = Transaction.objects.create(
        transaction_no=payload.pop("transaction_no", None) or _transaction_no(),
        transaction_date=payload.pop("transaction_date", None) or date.today(),
        amount=applied_amount,
        status="confirmed",
        plan=plan,
        **payload,
    )
    if plan:
        plan.settled_amount += applied_amount
        plan.status = "settled" if plan.settled_amount == plan.planned_amount else "open"
        plan.save(update_fields=["settled_amount", "status", "updated_at"])
        excess = amount - applied_amount
        if excess > 0:
            Transaction.objects.create(
                transaction_no=_transaction_no("ADV"), transaction_date=row.transaction_date,
                direction=row.direction, kind="unallocated_advance", category="未分配预收预付",
                amount=excess, currency=row.currency, exchange_rate=exchange_rate,
                rmb_amount=(excess * exchange_rate).quantize(Decimal("0.01")),
                customer=row.customer, supplier=row.supplier, status="confirmed",
                reference=row.transaction_no, notes="由合同计划超额收付款自动拆分",
            )
    return row


@transaction.atomic
def void_transaction(row):
    row = Transaction.objects.select_for_update().select_related("plan").get(pk=row.pk)
    if row.status != "confirmed":
        raise ValidationError("只有已确认流水可以作废。")
    if row.plan_id:
        plan = PaymentPlan.objects.select_for_update().get(pk=row.plan_id)
        plan.settled_amount -= row.amount
        plan.status = "open"
        plan.save(update_fields=["settled_amount", "status", "updated_at"])
    row.status = "cancelled"
    row.save(update_fields=["status", "updated_at"])
    return row
