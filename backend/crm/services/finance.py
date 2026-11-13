from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction

from django.utils import timezone
from crm.money import LEGACY_AMOUNT_CALCULATION_VERSION, money
from crm.models import AdvanceAllocation, ContractChangeRequest, FinancePlanWriteoff, FinancePlanWriteoffCorrection, FinanceReceiptAdjustment, FinanceVoucher, Order, PaymentPlan, PurchaseOrder, Transaction
from crm.finance_scope import require_finance_permission, scope_plan_queryset, scope_transaction_queryset, validate_finance_relations
from crm.services import cash_events as cash
from crm.services.historical import reject_historical, reject_unlinked_historical_finance, is_historical, has_verified_history_balance


def positive_decimal(value, label):
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number <= 0:
            raise ValueError
        return number
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError(f"{label}必须是大于零的有效数字。")


def _writeoff_total(plan):
    written = plan.finance_writeoffs.aggregate(total=models.Sum("amount"))["total"] or Decimal("0")
    corrected = FinancePlanWriteoffCorrection.objects.filter(writeoff__plan=plan).aggregate(total=models.Sum("amount"))["total"] or Decimal("0")
    return written - corrected


def _writeoff_total_for_source(source):
    written = FinancePlanWriteoff.objects.filter(source_transaction=source).aggregate(total=models.Sum("amount"))["total"] or Decimal("0")
    corrected = FinancePlanWriteoffCorrection.objects.filter(writeoff__source_transaction=source).aggregate(total=models.Sum("amount"))["total"] or Decimal("0")
    return written - corrected


def _sync_plan_status(plan):
    plan.status = "settled" if plan.settled_amount + _writeoff_total(plan) == plan.planned_amount else "open"


@transaction.atomic
def writeoff_receivable(source_transaction, plan, amount, reason, request_key, user, *, nature="rounding", evidence=None, contract_change=None, receipt_context=None):
    """Record an authorized rounding write-off without creating any cash movement."""
    require_finance_permission(user, "finance", "update")
    request_key = str(request_key or "").strip()
    reason = str(reason or "").strip()
    if not request_key or len(request_key) > 128:
        raise ValidationError("本次操作编号无效，请重新打开登记窗口。")
    if len(reason) < 5 or len(reason) > 500:
        raise ValidationError("请填写至少 5 个字的抹零原因。")
    amount = positive_decimal(amount, "抹零金额")
    if amount.quantize(Decimal("0.0001")) != amount or amount >= Decimal("10000000000"):
        raise ValidationError("抹零金额最多保留 4 位小数，且不能超限。")
    amount = amount.quantize(Decimal("0.0001"))
    source = Transaction.objects.select_for_update().filter(pk=source_transaction.pk).first()
    locked_plan = PaymentPlan.objects.select_for_update().filter(pk=plan.pk).first()
    if source is None or locked_plan is None:
        raise ValidationError("原收款或应收计划不存在。")
    if not scope_transaction_queryset(Transaction.objects.filter(pk=source.pk), user).exists():
        raise ValidationError("原收款不在当前账号的数据范围内。")
    if not scope_plan_queryset(PaymentPlan.objects.filter(pk=locked_plan.pk), user).exists():
        raise ValidationError("应收计划不在当前账号的数据范围内。")
    validate_finance_relations({"plan": locked_plan, "customer": source.customer}, user)
    actor = cash.actor(user, "writeoff_receivable")
    if nature not in {"rounding", "discount", "other"}:
        raise ValidationError("非现金抵减性质无效。")
    if nature != "rounding":
        if evidence is None or contract_change is not None:
            raise ValidationError("非现金抵减须关联凭证；已修订订单不能再次抵减。")
        from .finance_closeout import voucher
        FinanceVoucher.objects.select_for_update().filter(pk=evidence.pk).first()
        evidence = voucher(evidence.pk, scope="transaction")
        if (evidence.bank_sources or evidence.receipt_refunds.exists() or evidence.plan_writeoffs.exclude(source_transaction=source).exists() or evidence.transactions.exclude(pk=source.pk).exists()
                or evidence.receipt_adjustments.exclude(transaction_id=source.pk).exists()):
            raise ValidationError("抵减凭证已绑定其他资金来源。")
    payload = {"source": source.pk, "plan": locked_plan.pk, "amount": str(amount), "reason": reason, "actor": actor}
    if nature != "rounding" or evidence or contract_change:
        payload.update(nature=nature, evidence=getattr(evidence, "pk", None), contract_change=getattr(contract_change, "pk", None))
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
    existing = FinancePlanWriteoff.objects.filter(request_key=request_key).first()
    if existing:
        if existing.request_hash != fingerprint:
            raise cash.CashConflict("本次操作编号已用于其他抹零内容。")
        return existing, False
    if source.status != "confirmed" or source.direction != "income" or source.kind not in {"customer_receipt", "unallocated_advance"}:
        raise ValidationError("抹零只能关联已确认的客户收款或预收款。")
    if locked_plan.direction != "receivable" or not locked_plan.order_id or locked_plan.status != "open":
        raise ValidationError("抹零只能用于有效销售订单的未结应收计划。")
    order = locked_plan.order
    if order.status in {"draft", "cancelled"} or source.customer_id != order.customer_id or source.currency != locked_plan.currency:
        raise ValidationError("原收款与应收计划的客户、币种或订单状态不匹配。")
    if nature != "rounding" and FinancePlanWriteoff.objects.filter(plan=locked_plan, evidence=evidence, nature=nature).exists():
        raise ValidationError("该凭证已用于此计划的同类扣减，不能重复抵减。")
    if nature == "discount" and order.discount > 0:
        recorded = FinanceReceiptAdjustment.objects.filter(order=order, nature="discount", handling="already_in_order").aggregate(total=models.Sum("amount"))["total"] or Decimal("0")
        if recorded < order.discount:
            raise ValidationError("订单已有优惠，请先核实已计入订单的金额，避免重复抵减。")
    linked = source.plan_id == locked_plan.pk or AdvanceAllocation.objects.filter(
        advance=source, plan=locked_plan, is_active=True,
    ).exists()
    if receipt_context:
        if (nature not in {"discount", "other"} or evidence is None or receipt_context != {
            "transaction": source.pk, "plan": locked_plan.pk, "amount": amount, "nature": nature,
            "reason": reason, "evidence": evidence.pk, "contract_change": getattr(contract_change, "pk", None),
        }):
            raise ValidationError("收款抵减记录与核销依据不一致。")
        linked = True
    if not linked:
        raise ValidationError("抹零须关联本笔收款已核销的订单计划。")
    if amount > locked_plan.remaining_amount:
        raise ValidationError("抹零金额不能超过订单尚欠金额。")
    try:
        with transaction.atomic():
            row = FinancePlanWriteoff.objects.create(
                source_transaction=source, plan=locked_plan, amount=amount,
                reason=reason, request_key=request_key, request_hash=fingerprint,
                confirmed_actor=actor, nature=nature, evidence=evidence, contract_change=contract_change,
            )
    except IntegrityError:
        existing = FinancePlanWriteoff.objects.filter(request_key=request_key).first()
        if existing is None:
            raise
        if existing.request_hash != fingerprint:
            raise cash.CashConflict("本次操作编号已用于其他抹零内容。")
        return existing, False
    _sync_plan_status(locked_plan)
    locked_plan.save(update_fields=["status", "updated_at"])
    return row, True


@transaction.atomic
def correct_receivable_writeoff(source_transaction, writeoff, amount, reason, request_key, user):
    """Reverse some or all of a write-off without deleting its original audit record."""
    require_finance_permission(user, "finance", "update")
    request_key = str(request_key or "").strip()
    reason = str(reason or "").strip()
    if not request_key or len(request_key) > 128:
        raise ValidationError("本次更正编号无效，请重新打开登记窗口。")
    if len(reason) < 5 or len(reason) > 500:
        raise ValidationError("请填写至少 5 个字的更正原因。")
    amount = positive_decimal(amount, "更正金额")
    if amount.quantize(Decimal("0.0001")) != amount or amount >= Decimal("10000000000"):
        raise ValidationError("更正金额最多保留 4 位小数且不能超限。")
    original = FinancePlanWriteoff.objects.select_for_update().select_related("plan", "source_transaction").filter(pk=writeoff.pk).first()
    if original is None:
        raise ValidationError("原抹零记录不存在。")
    source = Transaction.objects.select_for_update().filter(pk=source_transaction.pk).first()
    if source is None or original.source_transaction_id != source.pk:
        raise ValidationError("原抹零记录不属于当前收款流水。")
    plan = PaymentPlan.objects.select_for_update().filter(pk=original.plan_id).first()
    if plan is None:
        raise ValidationError("原应收计划不存在。")
    if not scope_transaction_queryset(Transaction.objects.filter(pk=original.source_transaction_id), user).exists():
        raise ValidationError("原收款不在当前账号的数据范围内。")
    if not scope_plan_queryset(PaymentPlan.objects.filter(pk=plan.pk), user).exists():
        raise ValidationError("应收计划不在当前账号的数据范围内。")
    actor = cash.actor(user, "correct_receivable_writeoff")
    payload = {"writeoff": original.pk, "amount": str(amount), "reason": reason, "actor": actor}
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
    existing = FinancePlanWriteoffCorrection.objects.filter(request_key=request_key).first()
    if existing:
        if existing.request_hash != fingerprint:
            raise cash.CashConflict("本次更正编号已用于其他内容。")
        return existing, False
    corrected = original.corrections.aggregate(total=models.Sum("amount"))["total"] or Decimal("0")
    if amount > original.amount - corrected:
        raise ValidationError("更正金额不能超过该抹零记录尚未更正的金额。")
    try:
        with transaction.atomic():
            correction = FinancePlanWriteoffCorrection.objects.create(
                writeoff=original, amount=amount, reason=reason, request_key=request_key,
                request_hash=fingerprint, actor=actor,
            )
    except IntegrityError:
        existing = FinancePlanWriteoffCorrection.objects.filter(request_key=request_key).first()
        if existing is None:
            raise
        if existing.request_hash != fingerprint:
            raise cash.CashConflict("本次更正编号已用于其他内容。")
        return existing, False
    _sync_plan_status(plan)
    plan.save(update_fields=["status", "updated_at"])
    return correction, True


def _transaction_no(prefix="FIN"):
    return f"{prefix}-{uuid4().hex[:16].upper()}"


def _receipt_fee_fields(payload, amount):
    kind, direction = payload.get("kind"), payload.get("direction")
    if kind not in {"customer_receipt", "unallocated_advance"} or direction != "income":
        if any(payload.get(field) not in (None, "", Decimal("0")) for field in ("bank_fee_amount", "fee_responsibility", "fee_reason", "fee_evidence")):
            raise ValidationError("客户汇款扣费仅支持登记在客户收款或未分配预收款上。")
        return Decimal("0")
    from crm.models import FinanceVoucher
    remitted = positive_decimal(payload.get("remittance_amount", amount), "客户汇款金额")
    try:
        fee = Decimal(str(payload.get("bank_fee_amount") or "0"))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError("收款扣费金额无效。")
    responsibility = payload.get("fee_responsibility", "")
    reason = str(payload.get("fee_reason") or "").strip()
    evidence = payload.get("fee_evidence")
    if not fee.is_finite() or fee < 0 or remitted - amount != fee:
        raise ValidationError("客户汇款额减银行实际到账额必须等于扣费金额。")
    if fee > 0:
        if responsibility not in {"company", "customer", "unknown"} or len(reason) < 5:
            raise ValidationError("有银行扣费时，请记录承担方和扣费依据。")
        if evidence is not None and not isinstance(evidence, FinanceVoucher):
            evidence = FinanceVoucher.objects.filter(pk=evidence).first()
        if evidence is None:
            raise ValidationError("有银行扣费时，请上传并关联收款凭证。")
        from .finance_closeout import voucher
        FinanceVoucher.objects.select_for_update().filter(pk=evidence.pk).first()
        evidence = voucher(evidence.pk, scope="transaction")
        if evidence.bank_sources or evidence.receipt_refunds.exists():
            raise ValidationError("收款凭证不能绑定其他银行事件来源。")
        split_from = payload.get("split_from")
        root_id = (split_from.pk if hasattr(split_from, "pk") else split_from) or None
        if root_id:
            root = Transaction.objects.filter(pk=root_id).values_list("split_from_id", flat=True).first()
            root_id = root or root_id
            family_ids = {root_id, *Transaction.objects.filter(split_from_id=root_id).values_list("pk", flat=True)}
        else:
            family_ids = set()
        if evidence.transactions.exclude(pk__in=family_ids).exists():
            raise ValidationError("收款凭证已绑定其他收款来源。")
    elif responsibility or reason or evidence:
        raise ValidationError("没有扣费时无需填写扣费承担方、依据或凭证。")
    payload.update(remittance_amount=remitted, bank_fee_amount=fee, fee_responsibility=responsibility,
        fee_reason=reason, fee_evidence=evidence)
    return fee if responsibility == "company" else Decimal("0")


def _contract_amount(contract):
    return contract.total_amount


@transaction.atomic
def install_history_opening_plans(contract, user):
    """Install reviewed unpaid balances without creating historical cash transactions."""
    from . import finance_closeout
    finance_closeout.access(user, "create")
    contract = contract.__class__.objects.select_for_update().get(pk=contract.pk)
    if not is_historical(contract) or not has_verified_history_balance(contract):
        raise ValidationError("只有已审批的历史合同余额可以建立承接计划。")
    link = contract.history_balance
    specs = link.balance_snapshot.get("plans", [])
    if not isinstance(specs, list) or len(specs) > 100:
        raise ValidationError("历史未结计划格式无效。")
    relation = {"order": contract} if isinstance(contract, Order) else {"purchase_order": contract}
    if PaymentPlan.objects.filter(**relation).exists() or Transaction.objects.filter(**relation).exists():
        raise ValidationError("历史合同已有计划或资金流水，不能重复承接余额。")
    amounts = [positive_decimal(spec.get("amount"), "未结金额") for spec in specs]
    if sum(amounts, Decimal("0")) != link.opening_balance:
        raise ValidationError("历史未结明细与审核余额不一致。")
    direction = "receivable" if isinstance(contract, Order) else "payable"
    rows = []
    for spec, amount in zip(specs, amounts):
        row = PaymentPlan(**relation, direction=direction, currency=contract.currency, due_date=spec.get("due_date") or None,
            planned_amount=amount, settled_amount=0, notes=spec["note"])
        row.full_clean()
        row.save()
        finance_closeout.audit(row, user, "建立历史未结计划")
        rows.append(row)
    return rows


@transaction.atomic
def ensure_default_payment_plans(contract, deposit_ratio=None):
    contract = contract.__class__.objects.select_for_update().get(pk=contract.pk)
    if has_verified_history_balance(contract) or hasattr(contract, "history_continuation"):
        return list(contract.payment_plans.order_by("id"))
    reject_historical(contract, "生成收付款计划")
    if contract.status in {"draft", "cancelled"}:
        return []
    is_order = contract.__class__.__name__ == "Order"
    if not is_order:
        from crm.payment_terms import validate_payment_terms
        relation = {"purchase_order": contract}
        existing = PaymentPlan.objects.filter(**relation).order_by("id")
        if existing.exists():
            return list(existing)
        # Supplier-level fixed rules are archived configuration only.  A PO
        # gets payable plans only from its own saved, negotiated snapshot.
        if isinstance(contract, PurchaseOrder) and not contract.payment_terms_snapshot:
            return []
        terms = validate_payment_terms(contract.payment_terms_snapshot)
        total = _contract_amount(contract)
        if total <= 0:
            return []
        remaining = total
        rows = []
        for index, stage in enumerate(terms):
            amount = remaining if index == len(terms) - 1 else min(remaining, (total * Decimal(stage["ratio"])).quantize(Decimal("0.0001")))
            remaining -= amount
            if amount <= 0:
                continue
            basis_date = getattr(contract, stage["due_basis"], None) if stage["due_basis"] != "no_date" else None
            due_date = basis_date + timedelta(days=stage["offset_days"]) if basis_date else None
            rows.append(PaymentPlan.objects.create(**relation, direction="payable", currency=contract.currency,
                due_date=due_date, planned_amount=amount, notes=stage["label"]))
        return rows
    if deposit_ratio is None:
        deposit_ratio = contract.quote.deposit_ratio if is_order and contract.quote_id else Decimal("0.30")
    deposit_ratio = Decimal(str(deposit_ratio))
    if not Decimal("0") <= deposit_ratio <= Decimal("1"):
        raise ValidationError("定金比例必须在 0 到 1 之间。")
    relation = {"order": contract} if is_order else {"purchase_order": contract}
    direction = "receivable" if is_order else "payable"
    if PaymentPlan.objects.filter(**relation).exists():
        return list(PaymentPlan.objects.filter(**relation).order_by("id"))
    total = _contract_amount(contract)
    if total <= 0:
        return []
    deposit = (total * Decimal(str(deposit_ratio))).quantize(Decimal("0.0001"))
    balance = total - deposit
    rows = [PaymentPlan.objects.create(**relation, direction=direction, currency=contract.currency,
        due_date=due_date, planned_amount=amount, notes=notes)
        for amount, due_date, notes in [(deposit, contract.order_date, "默认预付款/定金"),
            (balance, contract.expected_ship_date if is_order else contract.expected_arrival_date, "默认尾款")]
        if amount > 0]
    return rows


def _receipt_amount(value, currency, label):
    try:
        if isinstance(value, (bool, float)):
            raise ValidationError("金额必须以精确十进制值提供。")
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError(f"{label}必须是有效十进制金额。")
    try:
        return cash.money(number.normalize(), currency)
    except Exception as error:
        if getattr(error, "detail", None):
            raise ValidationError(f"{label}无效：{error.detail}")
        raise


def _receipt_adjustment_input(rows, currency, *, customer, order, plans, request_user):
    if not isinstance(rows, list) or len(rows) > 100:
        raise ValidationError("扣减明细最多登记100条。")
    try:
        evidence_ids = sorted({int(row["evidence"]) for row in rows if isinstance(row, dict) and row.get("evidence") not in (None, "")})
    except (TypeError, ValueError):
        raise ValidationError("扣减凭证无效。")
    list(FinanceVoucher.objects.select_for_update().filter(pk__in=evidence_ids).order_by("pk"))
    normalized = []
    applied_evidence = set()
    for index, raw in enumerate(rows):
        allowed = {"nature", "amount", "handling", "reason", "evidence", "plan", "contract_change"}
        if not isinstance(raw, dict) or set(raw) - allowed:
            raise ValidationError("扣减明细字段无效，请核对后重试。")
        nature, handling = raw.get("nature"), raw.get("handling")
        reason = str(raw.get("reason") or "").strip()
        if nature not in {"discount", "bank_fee", "pending_difference", "other"} or len(reason) < 3 or len(reason) > 500:
            raise ValidationError("每条扣减明细都要选择性质并填写处理原因。")
        if handling == "applied" and len(reason) < 5:
            raise ValidationError("抵减应收的依据说明至少填写5个字。")
        amount = _receipt_amount(raw.get("amount"), currency, "扣减金额")
        if handling not in {"company", "customer", "pending", "applied", "already_in_order"}:
            raise ValidationError("扣减处理方式无效。")
        plan = None
        if raw.get("plan") not in (None, ""):
            try:
                plan_id = int(raw["plan"])
            except (TypeError, ValueError):
                raise ValidationError("扣减明细关联的应收计划无效。")
            plan = next((row for row in plans if row.pk == plan_id), None)
            if plan is None:
                plan = PaymentPlan.objects.select_for_update().filter(pk=plan_id).first()
            if (plan is None or plan.direction != "receivable" or not plan.order_id or plan.currency != currency or plan.order.customer_id != customer.pk
                    or plan.status != "open" or plan.order.status in {"draft", "cancelled"}):
                raise ValidationError("扣减明细只能关联同一客户、同一币种的有效应收计划。")
            if request_user:
                validate_finance_relations({"customer": customer, "plan": plan}, request_user)
            reject_unlinked_historical_finance(plan.order, "登记收款扣减")
        evidence = None
        if raw.get("evidence") not in (None, ""):
            try:
                evidence_id = int(raw["evidence"])
            except (TypeError, ValueError):
                raise ValidationError("扣减凭证无效。")
            evidence = FinanceVoucher.objects.select_for_update().filter(pk=evidence_id, scope="transaction").first()
            if evidence is None:
                raise ValidationError("扣减凭证不存在或不是收款凭证。")
            from .finance_closeout import voucher
            evidence = voucher(evidence.pk, scope="transaction")
            if evidence.bank_sources or evidence.receipt_refunds.exists() or evidence.plan_writeoffs.exists() or evidence.transactions.exists() or evidence.receipt_adjustments.exists():
                raise ValidationError("扣减凭证已绑定其他资金来源，请核对后重试。")
        change = None
        if raw.get("contract_change") not in (None, ""):
            try:
                change_id = int(raw["contract_change"])
            except (TypeError, ValueError):
                raise ValidationError("订单修订依据无效。")
            change = ContractChangeRequest.objects.select_for_update().filter(pk=change_id).first()
            if change is None or change.order_id is None or change.order.customer_id != customer.pk:
                raise ValidationError("订单修订依据不存在或不属于当前客户。")
            if request_user:
                validate_finance_relations({"customer": customer, "order": change.order}, request_user)
            if nature != "discount":
                raise ValidationError("只有优惠减免可以关联订单金额修订。")
        if nature == "bank_fee":
            if handling not in {"company", "customer", "pending"} or evidence is None:
                raise ValidationError("银行手续费须选择承担方并关联银行扣费凭证。")
        elif nature == "pending_difference":
            if handling != "pending":
                raise ValidationError("待核实差额不能用于核销应收。")
        elif nature == "discount":
            if handling == "applied":
                if plan is None or evidence is None or change is not None:
                    raise ValidationError("新优惠抵减应收须关联应收计划和凭证；已修订订单请标记为已计入订单金额。")
                target_order = plan.order
                previously_noted = FinanceReceiptAdjustment.objects.filter(
                    order=target_order, nature="discount", handling="already_in_order",
                ).aggregate(total=models.Sum("amount"))["total"] or Decimal("0")
                previously_noted += sum((row["amount"] for row in normalized if row["nature"] == "discount"
                                         and row["handling"] == "already_in_order"
                                         and ((row["plan"] and row["plan"].order_id == target_order.pk)
                                              or (not row["plan"] and (row["contract_change"].order_id if row["contract_change"] else getattr(order, "pk", None)) == target_order.pk))), Decimal("0"))
                if target_order.discount > previously_noted:
                    raise ValidationError("该订单已有优惠金额，请先标记已计入订单金额的部分，避免重复抵减应收。")
                if FinanceReceiptAdjustment.objects.filter(
                    order=target_order, nature="discount", handling="already_in_order", evidence=evidence,
                ).exists() or any(
                    row["nature"] == "discount" and row["handling"] == "already_in_order"
                    and row["evidence"] == evidence
                    and ((row["plan"] and row["plan"].order_id == target_order.pk)
                         or (not row["plan"] and (row["contract_change"].order_id if row["contract_change"] else getattr(order, "pk", None)) == target_order.pk))
                    for row in normalized
                ):
                    raise ValidationError("同一凭证已用于记录订单优惠，不能再次抵减应收。")
            elif handling == "already_in_order":
                target_order = plan.order if plan else order
                if target_order is None and change is not None:
                    target_order = change.order
                if target_order is None:
                    raise ValidationError("已计入订单金额的优惠必须关联订单。")
                if change is not None:
                    if change.status != "approved" or change.order_id != target_order.pk or change.amount_delta >= 0:
                        raise ValidationError("订单修订依据须为已确认的同订单金额调减。")
                    basis_total = -change.amount_delta
                    recorded = change.receipt_adjustments.filter(nature="discount", handling="already_in_order").aggregate(total=models.Sum("amount"))["total"] or Decimal("0")
                else:
                    basis_total = target_order.discount
                    recorded = FinanceReceiptAdjustment.objects.filter(
                        order=target_order, nature="discount", handling="already_in_order", contract_change__isnull=True,
                    ).aggregate(total=models.Sum("amount"))["total"] or Decimal("0")
                if amount > max(basis_total - recorded, Decimal("0")):
                    raise ValidationError("订单已包含的优惠金额不足以支持本条记录，不能重复抵减应收。")
                plan = plan or next((row for row in plans if row.order_id == target_order.pk), None)
            elif handling != "pending":
                raise ValidationError("优惠只能待核实、按订单已有优惠登记，或凭依据授权抵减应收。")
        elif nature == "other":
            if handling == "applied":
                if plan is None or evidence is None:
                    raise ValidationError("其他扣减抵减应收须关联应收计划和凭证。")
                if FinancePlanWriteoff.objects.filter(plan=plan, evidence=evidence, nature="other").exists():
                    raise ValidationError("该凭证已用于此应收计划的其他扣减，不能重复抵减。")
            elif handling != "pending":
                raise ValidationError("其他扣减只能待核实或凭据核准后抵减应收。")
        if nature == "discount" and handling == "applied" and FinancePlanWriteoff.objects.filter(
            plan=plan, evidence=evidence, nature="discount",
        ).exists():
            raise ValidationError("该优惠凭证已用于此应收计划，不能重复抵减。")
        if nature in {"discount", "other"} and handling == "applied":
            evidence_key = (plan.pk, nature, evidence.pk)
            if evidence_key in applied_evidence:
                raise ValidationError("同一凭证不能在本次收款中重复抵减同一应收计划。")
            applied_evidence.add(evidence_key)
        normalized.append({"nature": nature, "handling": handling, "amount": amount, "currency": currency,
                           "reason": reason, "plan": plan, "evidence": evidence, "contract_change": change,
                           "index": index})
    return normalized


def _receipt_request_hash(payload, transaction_no, *, customer, order, currency, amount, exchange_rate, reference_missing, actor=None):
    """Fingerprint submitted receipt intent without depending on mutable plan state."""
    def identifier(value, label):
        if value in (None, ""):
            return None
        try:
            return int(value.pk if hasattr(value, "pk") else value)
        except (TypeError, ValueError):
            raise ValidationError(f"{label}无效。")

    def amount_text(value):
        number = _receipt_amount(value, currency, "收款请求金额")
        return format(number.normalize(), "f")

    raw_plans = payload.get("plan_allocations") or []
    if not isinstance(raw_plans, list) or len(raw_plans) > 100:
        raise ValidationError("一笔收款最多分配100个应收计划。")
    plans = []
    for raw in raw_plans:
        if not isinstance(raw, dict) or set(raw) != {"plan", "amount"}:
            raise ValidationError("收款分配明细格式无效。")
        plans.append((identifier(raw["plan"], "应收计划"), amount_text(raw["amount"])))

    raw_adjustments = payload.get("receipt_adjustments") or []
    if not isinstance(raw_adjustments, list) or len(raw_adjustments) > 100:
        raise ValidationError("扣减明细最多登记100条。")
    adjustments = []
    allowed = {"nature", "amount", "handling", "reason", "evidence", "plan", "contract_change"}
    for raw in raw_adjustments:
        if not isinstance(raw, dict) or set(raw) - allowed:
            raise ValidationError("扣减明细字段无效，请核对后重试。")
        adjustments.append({
            "nature": raw.get("nature"), "amount": amount_text(raw.get("amount")),
            "handling": raw.get("handling"), "reason": str(raw.get("reason") or "").strip(),
            "evidence": identifier(raw.get("evidence"), "扣减凭证"),
            "plan": identifier(raw.get("plan"), "应收计划"),
            "contract_change": identifier(raw.get("contract_change"), "订单修订依据"),
            "currency": currency,
        })
    remittance = payload.get("remittance_amount")
    if remittance in (None, ""):
        remittance = amount + sum((
            _receipt_amount(row.get("amount"), currency, "扣减金额")
            for row in raw_adjustments if isinstance(row, dict) and row.get("nature") in {"bank_fee", "pending_difference"}
        ), Decimal("0"))
    else:
        remittance = _receipt_amount(remittance, currency, "客户实际汇款金额")
    rate_text = None if reference_missing else format(Decimal(str(exchange_rate)).normalize(), "f")
    fingerprint = {
        "transaction_no": transaction_no, "customer": customer.pk, "order": order.pk if order else None,
        "amount": format(amount.normalize(), "f"), "remittance_amount": format(remittance.normalize(), "f"),
        "currency": currency, "exchange_rate": rate_text, "plans": plans, "adjustments": adjustments,
        "category": str(payload.get("category") or "客户收款"),
        "payment_method": str(payload.get("payment_method") or ""), "reference": str(payload.get("reference") or ""),
        "notes": str(payload.get("notes") or ""),
        "transaction_date": str(payload.get("transaction_date") or timezone.localdate()),
    }
    if actor is not None:
        fingerprint["actor"] = actor
    return hashlib.sha256(json.dumps(fingerprint, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


@transaction.atomic
def record_customer_receipt(payload, user):
    """Save one actual receipt, its non-cash detail, plan allocations and audit facts atomically."""
    from crm.models import Customer
    from django.db import IntegrityError

    payload = payload.copy()
    require_finance_permission(user, "finance", "update")
    order = payload.get("order")
    customer = payload.get("customer") or (order.customer if order else None)
    if not customer:
        raise ValidationError("客户收款请选择客户；可暂不关联订单。")
    if not isinstance(customer, Customer):
        customer = Customer.objects.filter(pk=customer).first()
    if customer is None or order and order.customer_id != customer.pk:
        raise ValidationError("收款客户与所选订单不一致。")
    if user:
        validate_finance_relations({"customer": customer, "order": order}, user)
    customer = Customer.objects.select_for_update().get(pk=customer.pk)
    if order:
        order = Order.objects.select_for_update().select_related("customer").get(pk=order.pk)
        reject_unlinked_historical_finance(order, "登记客户收款")
        if order.status in {"draft", "cancelled"}:
            raise ValidationError("草稿或已取消订单不能登记收款。")
    currency = payload.get("currency") or (order.currency if order else "USD")
    if order and currency != order.currency:
        raise ValidationError("收款币种必须与订单一致。")
    amount = _receipt_amount(payload.get("amount"), currency, "银行实际到账金额")
    transaction_no = str(payload.get("transaction_no") or "").strip()
    if not transaction_no or len(transaction_no) > 50:
        raise ValidationError("收款流水编号无效。")
    supplied_plans = payload.get("plan_allocations", [])
    raw_adjustments = payload.get("receipt_adjustments", [])
    exchange_rate_value = payload.get("exchange_rate")
    reference_missing = currency != "CNY" and (payload.get("reference_rate_missing") is True or exchange_rate_value in (None, ""))
    exchange_rate = None if reference_missing else Decimal("1") if currency == "CNY" and exchange_rate_value in (None, "") else positive_decimal(exchange_rate_value, "账面参考汇率")
    if currency == "CNY" and exchange_rate != 1:
        raise ValidationError("人民币收款的账面参考汇率必须为1。")
    receipt_actor = cash.actor(user, "record_customer_receipt")
    hash_fields = dict(customer=customer, order=order, currency=currency, amount=amount,
                       exchange_rate=exchange_rate, reference_missing=reference_missing)
    request_hash = _receipt_request_hash(payload, transaction_no, **hash_fields, actor=receipt_actor)
    existing = Transaction.objects.select_for_update().filter(transaction_no=transaction_no).first()
    if existing:
        visible_existing = scope_transaction_queryset(Transaction.objects.filter(pk=existing.pk), user).exists()
        if not visible_existing:
            raise cash.CashConflict("收款保存冲突，请按原流水编号核对后再试。")
        if existing.kind == "customer_receipt":
            if existing.request_hash == request_hash:
                return existing, False
            if existing.request_hash == _receipt_request_hash(payload, transaction_no, **hash_fields):
                from crm.models import OperationLog
                user_id = receipt_actor.get("user_id")
                audited = user_id is not None and OperationLog.objects.filter(
                    entity="crm.transaction", object_id=str(existing.pk), action="create",
                    action_label="登记财务流水", operator_id=user_id,
                ).exists()
                if audited or existing.receipt_adjustments.filter(actor=receipt_actor).exists():
                    return existing, False
        raise cash.CashConflict("收款流水编号已被其他内容使用，请按原编号核对。")
    plans = []
    requested_allocations = []
    if not isinstance(supplied_plans, list) or len(supplied_plans) > 100:
        raise ValidationError("一笔收款最多分配100个应收计划。")
    seen_plan_ids = set()
    for raw in supplied_plans:
        if not isinstance(raw, dict) or set(raw) != {"plan", "amount"}:
            raise ValidationError("收款分配明细格式无效。")
        try:
            plan_id = int(raw["plan"])
        except (TypeError, ValueError):
            raise ValidationError("收款分配的应收计划无效。")
        if plan_id in seen_plan_ids:
            raise ValidationError("同一应收计划不能重复分配，请合并金额。")
        seen_plan_ids.add(plan_id)
        # PaymentPlan.order is nullable for payable plans. Limit the lock to
        # the plan row so PostgreSQL does not attempt FOR UPDATE on the
        # nullable side of the joined order relation.
        plan = PaymentPlan.objects.select_for_update(of=("self",)).select_related("order").filter(pk=plan_id).first()
        if plan is None:
            raise ValidationError("收款分配的应收计划不存在。")
        if plan.direction != "receivable" or not plan.order_id or plan.order.customer_id != customer.pk or plan.currency != currency:
            raise ValidationError("收款只能分配给同一客户、同一币种的销售订单应收计划。")
        reject_unlinked_historical_finance(plan.order, "登记收款分配")
        if plan.status != "open" or plan.order.status in {"draft", "cancelled"}:
            raise ValidationError("收款只能分配给有效订单的待结应收计划。")
        value = _receipt_amount(raw["amount"], currency, "核销金额")
        plans.append(plan)
        requested_allocations.append((plan, value))
    if order and not plans:
        ensure_default_payment_plans(order)
        plans = list(order.payment_plans.select_for_update().filter(direction="receivable", status="open").order_by("due_date", "pk"))
    adjustments = _receipt_adjustment_input(raw_adjustments, currency, customer=customer, order=order, plans=plans, request_user=user)
    for adjustment in adjustments:
        if adjustment["plan"] and adjustment["plan"] not in plans:
            plans.append(adjustment["plan"])
    fees = sum((row["amount"] for row in adjustments if row["nature"] == "bank_fee"), Decimal("0"))
    uncertain_difference = sum((row["amount"] for row in adjustments if row["nature"] == "pending_difference"), Decimal("0"))
    remitted = payload.get("remittance_amount")
    remitted = amount + fees + uncertain_difference if remitted in (None, "") else _receipt_amount(remitted, currency, "客户实际汇款金额")
    if remitted < amount or remitted - amount != fees + uncertain_difference:
        raise ValidationError("客户汇款额减银行实际到账额，必须与银行手续费和待核实差额明细合计一致。")
    company_fees = sum((row["amount"] for row in adjustments if row["nature"] == "bank_fee" and row["handling"] == "company"), Decimal("0"))
    settlement_capacity = amount + company_fees
    applied_adjustments = [row for row in adjustments if row["handling"] == "applied"]
    # Validate non-cash adjustments before creating any rows. They are applied
    # inside the same transaction as the receipt and allocation below.
    for row in applied_adjustments:
        plan = row["plan"]
        if plan is None or row["amount"] > plan.remaining_amount:
            raise ValidationError("核准扣减金额不能超过该应收计划剩余金额。")
        writeoff_key = f"{payload.get('transaction_no') or 'NEW'}-{row['index']}"
        if len(writeoff_key) > 128:
            raise ValidationError("收款编号过长，不能生成安全的扣减明细编号。")
    responsibilities = {row["handling"] for row in adjustments if row["nature"] == "bank_fee"}
    fee_responsibility = next(iter(responsibilities)) if len(responsibilities) == 1 else "mixed" if responsibilities else ""
    fee_lines = [row for row in adjustments if row["nature"] == "bank_fee"]
    fee_reason = "；".join(row["reason"] for row in fee_lines)
    fee_evidence = fee_lines[0]["evidence"] if len(fee_lines) == 1 else None
    actor = receipt_actor
    try:
        with transaction.atomic():
            row = Transaction.objects.create(
                transaction_no=transaction_no, transaction_date=payload.get("transaction_date") or timezone.localdate(),
                direction="income", kind="customer_receipt", category=payload.get("category") or "客户收款",
                amount=amount, currency=currency, exchange_rate=exchange_rate,
                rmb_amount=Decimal("0") if reference_missing else (amount * exchange_rate).quantize(Decimal("0.0001")),
                reference_rate_missing=reference_missing, remittance_amount=remitted, bank_fee_amount=fees,
                fee_responsibility=fee_responsibility, fee_reason=fee_reason, fee_evidence=fee_evidence,
                customer=customer, order=None, status="confirmed", allocated_amount=Decimal("0"),
                settlement_amount=Decimal("0"), request_hash=request_hash,
                payment_method=payload.get("payment_method") or "", reference=payload.get("reference") or "",
                notes=payload.get("notes") or "",
            )
            for adjustment in adjustments:
                writeoff = None
                if adjustment["handling"] == "applied":
                    plan = adjustment["plan"]
                    nature = "discount" if adjustment["nature"] == "discount" else "other"
                    writeoff, _ = writeoff_receivable(
                        row, plan, adjustment["amount"], adjustment["reason"],
                        f"{transaction_no}-{adjustment['index']}", user,
                        nature=nature, evidence=adjustment["evidence"], contract_change=adjustment["contract_change"],
                        receipt_context={
                            "transaction": row.pk, "plan": plan.pk, "amount": adjustment["amount"],
                            "nature": nature, "reason": adjustment["reason"],
                            "evidence": getattr(adjustment["evidence"], "pk", None),
                            "contract_change": getattr(adjustment["contract_change"], "pk", None),
                        },
                    )
                FinanceReceiptAdjustment.objects.create(
                    transaction=row, order=(adjustment["plan"].order if adjustment["plan"] else order or (adjustment["contract_change"].order if adjustment["contract_change"] else None)),
                    plan=adjustment["plan"], nature=adjustment["nature"],
                    handling=adjustment["handling"], amount=adjustment["amount"], currency=currency,
                    reason=adjustment["reason"], evidence=adjustment["evidence"],
                    contract_change=adjustment["contract_change"], writeoff=writeoff, actor=actor,
                )
            if not requested_allocations and plans:
                remaining = settlement_capacity
                for plan in plans:
                    if remaining <= 0:
                        break
                    applied = min(remaining, plan.remaining_amount)
                    if applied > 0:
                        requested_allocations.append((plan, applied))
                        remaining -= applied
            if sum((value for _, value in requested_allocations), Decimal("0")) > settlement_capacity:
                raise ValidationError("应收核销金额不能超过实际到账和我方承担手续费的合计。")
            if any(value > plan.remaining_amount for plan, value in requested_allocations):
                raise ValidationError("应收核销金额超过订单剩余应收。")
            for plan, value in requested_allocations:
                allocate_advance(row, plan, value)
            row.refresh_from_db()
            row.settlement_amount = row.allocated_amount
            row.save(update_fields=["settlement_amount", "updated_at"])
    except IntegrityError:
        existing = Transaction.objects.filter(transaction_no=transaction_no).first()
        if existing and existing.kind == "customer_receipt" and existing.request_hash == request_hash:
            return existing, False
        raise cash.CashConflict("收款保存冲突，请按原流水编号核对后再重试。")
    return row, True


@transaction.atomic
def record_transaction(payload):
    payload = payload.copy()
    if payload.get("replaces"):
        from .cash_events import guard_replacement
        guard_replacement(payload["replaces"])
    plan = payload.pop("plan", None)
    plan_chunk = bool(payload.pop("_plan_chunk", False))
    requested_settlement = payload.pop("_settlement_amount", None)
    allow_unplanned_contract_payment = payload.pop("_allow_unplanned_contract_payment", False)
    amount = positive_decimal(payload.get("amount"), "收付款金额")
    kind = payload.get("kind", "other")
    direction = payload.get("direction")
    company_fee_credit = _receipt_fee_fields(payload, amount)
    # Transaction status is controlled by this service; callers cannot override it.
    payload.pop("status", None)
    payload.pop("allocated_amount", None)
    payload.pop("rmb_amount", None)
    if amount <= 0:
        raise ValidationError("收付款金额必须大于零。")
    # Keep this guard at the service boundary as well as in the serializer.
    # Imports, jobs, and direct service callers must not turn a historical
    # analysis record into any kind of linked cash fact.
    linked_order = payload.get("order")
    linked_purchase = payload.get("purchase_order")
    for contract in (linked_order, linked_purchase):
        if is_historical(contract) and (not plan or not has_verified_history_balance(contract)):
            reject_historical(contract, "登记关联资金流水")
    if plan:
        plan = PaymentPlan.objects.select_for_update().get(pk=plan.pk)
        if plan.order_id:
            contract = Order.objects.select_for_update().select_related("customer").get(pk=plan.order_id)
            plan.order = contract
        elif plan.purchase_order_id:
            contract = PurchaseOrder.objects.select_for_update().select_related("supplier").get(pk=plan.purchase_order_id)
            plan.purchase_order = contract
        else:
            raise ValidationError("收付款计划必须关联销售订单或采购单。")
        if plan.status != "open":
            raise ValidationError("只能核销待结清的收付款计划。")
        if payload.get("currency", plan.currency) != plan.currency:
            raise ValidationError("实际收付款币种必须与计划原币一致。")
        contract = plan.order or plan.purchase_order
        reject_unlinked_historical_finance(contract, "登记关联资金流水")
        if contract.status in {"draft", "cancelled"}:
            raise ValidationError("草稿或已取消合同不能登记收付款。")
        expected = {"order": plan.order, "purchase_order": plan.purchase_order,
            "customer": plan.order.customer if plan.order_id else None,
            "supplier": plan.purchase_order.supplier if plan.purchase_order_id else None,
            "direction": "income" if plan.order_id else "expense",
            "kind": "customer_receipt" if plan.order_id else "supplier_payment"}
        for key, value in expected.items():
            if payload.get(key) is not None and payload[key] != value:
                raise ValidationError("收付款方向、往来方及合同必须与核销计划一致。")
        payload.update(expected)
        payload["currency"] = plan.currency
        payload.setdefault("exchange_rate", contract.exchange_rate)
        remaining = plan.remaining_amount
        if remaining <= 0:
            raise ValidationError("该计划已无待结余额，请核对计划状态。")
        if kind == "customer_receipt" and not plan_chunk:
            return record_contract_payment(plan.order, {**payload, "amount": amount, "_preferred_plan": plan.pk})
        settlement_request = positive_decimal(requested_settlement, "本笔核销金额") if requested_settlement is not None else amount
        applied_amount = min(settlement_request, remaining)
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
        order, purchase = payload.get("order"), payload.get("purchase_order")
        kind = payload.get("kind", "other")
        if kind in {"customer_receipt", "supplier_payment"}:
            contract = order if kind == "customer_receipt" else purchase
            if not contract:
                raise ValidationError("客户收款必须关联销售订单，供应商付款必须关联采购单。")
            reject_unlinked_historical_finance(contract, "登记收付款")
            if not allow_unplanned_contract_payment:
                return record_contract_payment(contract, payload)
            payload.update({
                "order": contract if kind == "customer_receipt" else None,
                "purchase_order": contract if kind == "supplier_payment" else None,
                "customer": contract.customer if kind == "customer_receipt" else None,
                "supplier": contract.supplier if kind == "supplier_payment" else None,
                "direction": "income" if kind == "customer_receipt" else "expense",
                "kind": kind,
            })
        if kind in {"refund", "supplier_refund"}:
            contract = order if kind == "refund" else purchase
            if not contract:
                raise ValidationError("客户退款必须关联销售订单，供应商退款必须关联采购单。")
            reject_unlinked_historical_finance(contract, "登记退款")
            return record_contract_refund(contract, payload)
    exchange_rate = positive_decimal(payload.get("exchange_rate", 1), "汇率")
    if payload.get("currency") == "CNY" and exchange_rate != 1:
        raise ValidationError("人民币流水汇率必须为 1。")
    payload["exchange_rate"] = exchange_rate
    applied_cash = min(amount, applied_amount)
    if applied_amount > applied_cash and (kind != "customer_receipt" or company_fee_credit < applied_amount - applied_cash):
        raise ValidationError("核销金额不能超过实际收款；超额部分须有凭证齐全的我方承担手续费。")
    payload.setdefault("rmb_amount", (applied_cash * exchange_rate).quantize(Decimal("0.0001")))
    payload.pop("amount", None)
    row = Transaction.objects.create(
        transaction_no=payload.pop("transaction_no", None) or _transaction_no(),
        transaction_date=payload.pop("transaction_date", None) or timezone.localdate(),
        amount=applied_cash,
        settlement_amount=applied_amount if plan and payload.get("kind") not in {"refund", "supplier_refund"} else Decimal("0"),
        status="confirmed",
        plan=plan,
        **payload,
    )
    if plan:
        plan.settled_amount += applied_amount
        _sync_plan_status(plan)
        plan.save(update_fields=["settled_amount", "status", "updated_at"])
        excess = amount - applied_cash
        if excess > 0:
            Transaction.objects.create(
                transaction_no=_transaction_no("ADV"), transaction_date=row.transaction_date,
                direction=row.direction,
                kind="unallocated_advance" if row.direction == "income" else "unallocated_payment",
                category="未分配预收款" if row.direction == "income" else "未分配预付款",
                amount=excess, currency=row.currency, exchange_rate=exchange_rate,
                rmb_amount=(excess * exchange_rate).quantize(Decimal("0.0001")),
                customer=row.customer, supplier=row.supplier, status="confirmed",
                reference=row.transaction_no, notes="由合同计划超额收付款自动拆分",
                split_from=row, payment_method=row.payment_method,
            )
    return row


@transaction.atomic
def void_transaction(row, reason):
    reason = str(reason or "").strip()
    if not reason:
        raise ValidationError("作废原因不能为空。")

    root = Transaction.objects.select_for_update().get(pk=row.pk)
    if root.split_from_id:
        raise ValidationError("拆分流水必须通过原始流水统一作废。")
    if root.status != "confirmed":
        raise ValidationError("只有已确认流水可以作废。")

    rows = []

    def collect(current):
        current = Transaction.objects.select_for_update().get(pk=current.pk)
        rows.append(current)
        for child in current.split_rows.select_for_update().filter(status="confirmed").order_by("pk"):
            collect(child)

    collect(root)
    root = rows[0]

    if any(_writeoff_total_for_source(current) > 0 for current in rows):
        raise ValidationError("原收款已有授权抹零记录，不能直接作废；请先核实抹零调整。")

    from .cash_events import guard_void
    guard_void(rows)

    plan_deltas = {}
    active_allocations = []
    for current in rows:
        allocations = list(
            AdvanceAllocation.objects.select_for_update()
            .filter(advance=current, is_active=True)
            .order_by("pk")
        )
        allocation_total = sum((allocation.amount for allocation in allocations), Decimal("0"))
        if current.allocated_amount != allocation_total:
            raise ValidationError("该历史预收预付缺少核销明细，请先人工核对，不能直接作废。")
        active_allocations.extend(allocations)
        for allocation in allocations:
            plan_deltas[allocation.plan_id] = plan_deltas.get(allocation.plan_id, Decimal("0")) + allocation.amount
        if current.plan_id:
            settled_delta = current.settlement_amount or current.amount
            delta = -settled_delta if current.kind in {"refund", "supplier_refund"} else settled_delta
            plan_deltas[current.plan_id] = plan_deltas.get(current.plan_id, Decimal("0")) + delta

    plans = {
        plan.pk: plan
        for plan in PaymentPlan.objects.select_for_update()
        .filter(pk__in=plan_deltas)
        .order_by("pk")
    }
    if len(plans) != len(plan_deltas):
        raise ValidationError("关联收付款计划缺失，不能安全作废。")
    for plan_id, delta in plan_deltas.items():
        revised_amount = plans[plan_id].settled_amount - delta
        if revised_amount < 0:
            raise ValidationError("收付款计划已结金额不足，不能安全作废。")
        if revised_amount > plans[plan_id].planned_amount:
            raise ValidationError("收付款计划已结金额超过计划金额，不能安全作废。")

    for plan_id, delta in sorted(plan_deltas.items()):
        plan = plans[plan_id]
        plan.settled_amount -= delta
        _sync_plan_status(plan)
        plan.save(update_fields=["settled_amount", "status", "updated_at"])
    for allocation in active_allocations:
        allocation.is_active = False
        allocation.save(update_fields=["is_active", "updated_at"])

    voided_at = timezone.now()
    for current in rows:
        current.status = "cancelled"
        current.allocated_amount = 0
        current.voided_at = voided_at
        current.void_reason = reason
        current.save(update_fields=["status", "allocated_amount", "voided_at", "void_reason", "updated_at"])
    return root


@transaction.atomic
def allocate_advance(advance, plan, amount):
    advance = Transaction.objects.select_for_update().get(pk=advance.pk)
    plan = PaymentPlan.objects.select_for_update().get(pk=plan.pk)
    if plan.order_id:
        contract = Order.objects.select_for_update().select_related("customer").get(pk=plan.order_id)
        plan.order = contract
    elif plan.purchase_order_id:
        contract = PurchaseOrder.objects.select_for_update().select_related("supplier").get(pk=plan.purchase_order_id)
        plan.purchase_order = contract
    else:
        raise ValidationError("收付款计划必须关联销售订单或采购单。")
    reject_unlinked_historical_finance(plan.order or plan.purchase_order, "分配收付款")
    amount = positive_decimal(amount, "分配金额")
    if advance.kind not in {"unallocated_advance", "unallocated_payment", "customer_receipt"} or advance.status != "confirmed":
        raise ValidationError("只能分配已确认的未分配预收预付。")
    if advance.kind == "customer_receipt" and (advance.order_id or advance.plan_id):
        raise ValidationError("已直接关联应收计划的客户收款不能再次分配。")
    if plan.status != "open" or (plan.order or plan.purchase_order).status in {"draft", "cancelled"}:
        raise ValidationError("只能分配到有效合同的待结清计划。")
    if advance.direction != ("income" if plan.order_id else "expense"):
        raise ValidationError("预收预付方向与计划不匹配。")
    if amount <= 0 or amount > advance.allocation_capacity - advance.allocated_amount:
        raise ValidationError("分配金额不能超过未分配余额。")
    if amount > plan.remaining_amount or advance.currency != plan.currency:
        raise ValidationError("计划余额或币种不匹配。")
    if plan.direction == "receivable" and advance.customer_id != plan.order.customer_id:
        raise ValidationError("预收款只能分配给同一客户的应收计划。")
    if plan.direction == "payable" and advance.supplier_id != plan.purchase_order.supplier_id:
        raise ValidationError("预付款只能分配给同一供应商的应付计划。")
    advance.allocated_amount += amount
    advance.save(update_fields=["allocated_amount", "updated_at"])
    plan.settled_amount += amount
    _sync_plan_status(plan)
    plan.save(update_fields=["settled_amount", "status", "updated_at"])
    cash_used = sum((row.cash_amount if row.cash_amount is not None else row.amount for row in AdvanceAllocation.objects.select_for_update().filter(advance=advance, is_active=True)), Decimal("0"))
    fee_used = sum(AdvanceAllocation.objects.select_for_update().filter(advance=advance, is_active=True).values_list("fee_credit_amount", flat=True), Decimal("0"))
    unallocated_refunds = advance.refunded_cash_amount(unallocated_only=True) + advance.returned_cash_amount(unallocated_only=True)
    cash_part = min(amount, max(advance.amount - cash_used - unallocated_refunds, Decimal("0")))
    fee_part = amount - cash_part
    if fee_part:
        if advance.kind == "customer_receipt":
            if fee_part > advance.allocation_capacity - advance.amount + unallocated_refunds - fee_used:
                raise ValidationError("我方承担的扣费核销额度不足。")
        else:
            if advance.fee_responsibility != "company" or not advance.fee_evidence_id or fee_part > advance.bank_fee_amount - fee_used:
                raise ValidationError("超出实际到账额的核销必须有有效的我方承担手续费凭证及剩余额度。")
            from .finance_closeout import voucher
            proof = voucher(advance.fee_evidence_id, scope="transaction")
            family_root_id = advance.split_from_id or advance.pk
            linked_ids = {family_root_id, *Transaction.objects.filter(split_from_id=family_root_id).values_list("pk", flat=True)}
            if proof.receipt_refunds.exists() or proof.transactions.exclude(pk__in=linked_ids).exists():
                raise ValidationError("收款手续费凭证已绑定其他收款来源。")
    AdvanceAllocation.objects.create(advance=advance, plan=plan, amount=amount, cash_amount=cash_part, fee_credit_amount=fee_part)
    return plan


@transaction.atomic
def record_contract_payment(contract, payload):
    """One cash event may settle several installments; only true excess becomes an advance."""
    payload = payload.copy()
    preferred_plan = payload.pop("_preferred_plan", None)
    contract = contract.__class__.objects.select_for_update().get(pk=contract.pk)
    reject_unlinked_historical_finance(contract, "登记收付款")
    if contract.status in {"draft", "cancelled"}:
        raise ValidationError("草稿或已取消合同不能登记收付款。")
    amount = positive_decimal(payload.get("amount"), "收付款金额")
    if payload.get("currency", contract.currency) != contract.currency:
        raise ValidationError("收付款币种必须与合同一致。")
    ensure_default_payment_plans(contract)
    plans = list(contract.payment_plans.select_for_update().filter(status="open").order_by("due_date", "pk"))
    if preferred_plan is not None:
        if not any(plan.pk == preferred_plan for plan in plans):
            raise ValidationError("所选收款计划已结清或不属于当前订单。")
        plans.sort(key=lambda plan: plan.pk != preferred_plan)
    if not plans:
        if is_historical(contract) or hasattr(contract, "history_continuation"):
            raise ValidationError("历史接续合同没有未结计划；额外款项请登记为未分配预收预付。")
        if isinstance(contract, PurchaseOrder) and not contract.payment_terms_snapshot:
            return record_transaction({
                **payload,
                "purchase_order": contract,
                "supplier": contract.supplier,
                "direction": "expense",
                "kind": "supplier_payment",
                "_allow_unplanned_contract_payment": True,
            })
        raise ValidationError("合同已结清；额外款项请登记为未分配预收预付。")
    is_customer = isinstance(contract, Order)
    fee = Decimal(str(payload.get("bank_fee_amount") or "0")) if is_customer else Decimal("0")
    company_fee = fee if payload.get("fee_responsibility") == "company" else Decimal("0")
    settlement_remaining = amount + company_fee
    cash_remaining = amount
    fee_credit_used = Decimal("0")
    chunks = []
    for plan in plans:
        applied = min(settlement_remaining, plan.remaining_amount)
        if applied <= 0:
            continue
        cash_applied = min(cash_remaining, applied)
        fee_credit = applied - cash_applied
        if fee_credit > 0 and (not is_customer or fee_credit > fee - fee_credit_used):
            raise ValidationError("核销金额超过实际到账，且超额部分没有有效的我方手续费额度。")
        chunks.append({"plan": plan, "settlement": applied, "cash": cash_applied, "fee_credit": fee_credit})
        settlement_remaining -= applied
        cash_remaining -= cash_applied
        fee_credit_used += fee_credit
        if settlement_remaining <= 0:
            break
    if not chunks:
        raise ValidationError("合同没有可核销的收付款计划。")

    fee_recorded = fee_credit_used if is_customer and payload.get("fee_responsibility") == "company" else Decimal("0")
    fee_left = max(fee - fee_recorded, Decimal("0"))
    advance_fee = fee_left if is_customer and payload.get("fee_responsibility") == "company" and cash_remaining > 0 else Decimal("0")
    if fee_left and not advance_fee and payload.get("fee_responsibility") == "company":
        chunks[0]["fee_extra"] = fee_left
    else:
        chunks[0]["fee_extra"] = Decimal("0")

    # A later installment can consist entirely of a company-borne bank fee.
    # Keep that fee on the real receipt and represent the allocation without
    # creating a zero-value cash transaction.
    fee_only = sum((chunk["fee_credit"] for chunk in chunks if not chunk["cash"]), Decimal("0"))
    chunks[0]["fee_extra"] += fee_only

    first = None
    fee_memo_attached = False
    for index, chunk in enumerate(chunks):
        if not chunk["cash"]:
            if first is None or not chunk["fee_credit"]:
                raise ValidationError("手续费核销必须关联实际到账的原收款。")
            AdvanceAllocation.objects.create(advance=first, plan=chunk["plan"], amount=chunk["settlement"],
                cash_amount=Decimal("0"), fee_credit_amount=chunk["fee_credit"])
            first.allocated_amount += chunk["settlement"]
            first.save(update_fields=["allocated_amount", "updated_at"])
            chunk["plan"].settled_amount += chunk["settlement"]
            _sync_plan_status(chunk["plan"])
            chunk["plan"].save(update_fields=["settled_amount", "status", "updated_at"])
            continue
        row_fee = chunk["fee_credit"]
        if index == 0:
            row_fee += chunk["fee_extra"]
        if is_customer and payload.get("fee_responsibility") != "company" and fee > 0 and not fee_memo_attached:
            row_fee += fee
        data = {**payload, "amount": chunk["cash"], "plan": chunk["plan"], "currency": contract.currency,
                "_settlement_amount": chunk["settlement"], "_plan_chunk": True}
        data.setdefault("exchange_rate", contract.exchange_rate)
        if row_fee > 0:
            data.update(remittance_amount=chunk["cash"] + row_fee, bank_fee_amount=row_fee)
            fee_memo_attached = True
        else:
            data.update(remittance_amount=chunk["cash"], bank_fee_amount=Decimal("0"), fee_responsibility="", fee_reason="", fee_evidence=None)
        if first:
            data.pop("transaction_no", None)
            data["split_from"] = first
        row = record_transaction(data)
        first = first or row

    if cash_remaining > 0:
        advance_payload = {**payload, "transaction_no": _transaction_no("ADV"),
            "transaction_date": first.transaction_date, "direction": "income" if is_customer else "expense",
            "kind": "unallocated_advance" if is_customer else "unallocated_payment",
            "category": "未分配预收款" if is_customer else "未分配预付款",
            "amount": cash_remaining, "remittance_amount": cash_remaining + advance_fee,
            "bank_fee_amount": advance_fee, "order": None, "purchase_order": None,
            "plan": None, "split_from": first}
        if not advance_fee:
            advance_payload.update(fee_responsibility="", fee_reason="", fee_evidence=None)
        record_transaction(advance_payload)
    return first


@transaction.atomic
def record_contract_refund(contract, payload):
    """Record a real cash refund by reopening the latest settled installments first."""
    from crm.models import Customer, Supplier
    from .cash_events import guard_refund
    party_model, party_id = (Customer, contract.customer_id) if isinstance(contract, Order) else (Supplier, contract.supplier_id)
    party_model.objects.select_for_update().get(pk=party_id)
    contract = contract.__class__.objects.select_for_update().get(pk=contract.pk)
    reject_unlinked_historical_finance(contract, "登记退款")
    guard_refund(contract)
    is_order = isinstance(contract, Order)
    amount = positive_decimal(payload.get("amount"), "退款金额")
    if payload.get("currency", contract.currency) != contract.currency:
        raise ValidationError("合同收付款及退款币种必须与合同一致。")
    if contract.status in {"draft", "cancelled"}:
        raise ValidationError("草稿或已取消合同不能登记退款。")
    if amount > contract.paid_amount:
        raise ValidationError("退款金额不能超过该订单当前已收金额。" if is_order else "退款金额不能超过该采购单当前已付金额。")

    plans = list(
        contract.payment_plans.select_for_update()
        .exclude(status="cancelled")
        .filter(settled_amount__gt=0)
        .order_by("-due_date", "-pk")
    )
    if not plans:
        raise ValidationError("合同没有可回退的已结收付款计划。")

    exchange_rate = positive_decimal(payload.get("exchange_rate", contract.exchange_rate), "汇率")
    if contract.currency == "CNY" and exchange_rate != 1:
        raise ValidationError("人民币流水汇率必须为 1。")
    remaining = amount
    first = None
    for plan in plans:
        # Only actual cash associated with this plan can be returned. A plan
        # settled entirely by a fee credit has no cash to refund.
        payment_kind = "customer_receipt" if is_order else "supplier_payment"
        refund_kind = "refund" if is_order else "supplier_refund"
        paid_cash = sum(plan.transactions.filter(status="confirmed", kind=payment_kind).values_list("amount", flat=True), Decimal("0"))
        paid_cash += sum((allocation.cash_amount if allocation.cash_amount is not None else allocation.amount
            for allocation in plan.advance_allocations.filter(is_active=True, advance__status="confirmed")), Decimal("0"))
        refunded = sum(plan.transactions.filter(status="confirmed", kind=refund_kind).values_list("amount", flat=True), Decimal("0"))
        applied = min(remaining, plan.settled_amount, max(paid_cash - refunded, Decimal("0")))
        if applied <= 0:
            continue
        row = Transaction.objects.create(
            transaction_no=payload.get("transaction_no") if first is None and payload.get("transaction_no") else _transaction_no(),
            transaction_date=payload.get("transaction_date") or timezone.localdate(),
            direction="expense" if is_order else "income",
            kind="refund" if is_order else "supplier_refund",
            category=payload.get("category") or ("客户退款" if is_order else "供应商退款"),
            amount=applied,
            currency=contract.currency,
            exchange_rate=exchange_rate,
            rmb_amount=(applied * exchange_rate).quantize(Decimal("0.0001")),
            customer=contract.customer if is_order else None,
            supplier=contract.supplier if not is_order else None,
            order=contract if is_order else None,
            purchase_order=contract if not is_order else None,
            plan=plan,
            status="confirmed",
            split_from=first,
            payment_method=payload.get("payment_method", ""),
            reference=payload.get("reference", ""),
            notes=payload.get("notes", ""),
        )
        first = first or row
        plan.settled_amount -= applied
        _sync_plan_status(plan)
        plan.save(update_fields=["settled_amount", "status", "updated_at"])
        remaining -= applied
        if remaining == 0:
            break
    if remaining != 0:
        raise ValidationError("合同已结收付款计划不足，不能安全登记退款。")
    return first


@transaction.atomic
def refund_receipt_cash(source, order, value, reason, evidence_id, user, *, actual_date):
    """Refund traceable, unconverted cash; keep source and allocations immutable."""
    from crm.models import Customer, FinanceReceiptRefund
    if not source.customer_id:
        raise ValidationError("原收款尚未核实客户，不能登记退款。")
    Customer.objects.select_for_update().get(pk=source.customer_id)
    members = cash.family(source)
    for member in members:
        Transaction.objects.select_for_update().get(pk=member.pk)
    source = Transaction.objects.get(pk=source.pk)
    if source.status != "confirmed" or source.direction != "income" or source.kind not in {"customer_receipt", "unallocated_advance"}:
        raise ValidationError("只能从已确认客户收款登记退款。")
    reason = str(reason or "").strip()
    if not 5 <= len(reason) <= 500:
        raise ValidationError("请填写至少 5 个字的退款依据。")
    from .finance_closeout import voucher
    FinanceVoucher.objects.select_for_update().filter(pk=evidence_id).first()
    proof = voucher(evidence_id, scope="transaction")
    if proof.bank_sources or proof.transactions.exists() or proof.receipt_adjustments.exists() or proof.plan_writeoffs.exists() or proof.receipt_refunds.exists():
        raise ValidationError("退款凭证已用于其他业务，请上传本次实际退款凭证。")
    amount = _receipt_amount(value, source.currency, "退款金额")
    if cash.refund_source_uncertainty(source):
        raise ValidationError("原收款有来源不明的历史退款或替代关系，请先核实。")
    if source.cash_source_allocations.filter(event__status="pending").exists():
        raise ValidationError("原收款有待确认银行登记，请先完成或放弃该登记。")
    if amount > cash.refundable_cash(source):
        raise ValidationError("退款超过原收款尚未结汇且尚未退回的实际现金。")
    if order:
        plan_ids = set(source.allocations.filter(is_active=True, plan__order=order).values_list("plan_id", flat=True))
        if source.plan_id and source.plan.order_id == order.pk:
            plan_ids.add(source.plan_id)
        # Match allocation's source → plan → contract lock order, and acquire
        # multiple plan locks by primary key before choosing refund priority.
        plans = list(PaymentPlan.objects.select_for_update().filter(pk__in=plan_ids).order_by("pk"))
        order = Order.objects.select_for_update().get(pk=order.pk)
        reject_unlinked_historical_finance(order, "登记退款")
        cancelled_refund = order.status == "cancelled" and order.total_amount == 0
        if order.customer_id != source.customer_id or order.currency != source.currency or order.status == "draft" or (order.status == "cancelled" and not cancelled_refund):
            raise ValidationError("订单与原收款的客户、币种或状态不匹配。")
        plans.sort(key=lambda plan: (plan.due_date is not None, plan.due_date or date.min, plan.pk), reverse=True)
    else:
        plans = [None]
    remaining, rows = amount, []
    for plan in plans:
        if plan is None:
            eligible = source.unallocated_cash_amount
        else:
            eligible = sum((a.cash_amount if a.cash_amount is not None else a.amount for a in source.allocations.filter(is_active=True, plan=plan)), Decimal("0"))
            if source.plan_id == plan.pk:
                eligible += source.amount
            previous = source.attributed_refunds.filter(refund__status="confirmed", refund__plan=plan).aggregate(total=models.Sum("refund__amount"))["total"] or Decimal("0")
            returned = source.bank_return_allocations.filter(plan=plan).aggregate(total=models.Sum("amount"))["total"] or Decimal("0")
            eligible = min(max(eligible - previous - returned, Decimal("0")), plan.settled_amount)
        applied = min(remaining, eligible)
        if applied <= 0:
            continue
        rate = source.exchange_rate
        refund = Transaction.objects.create(transaction_no=_transaction_no(), transaction_date=actual_date,
            direction="expense", kind="refund", category="客户退款", amount=applied, currency=source.currency,
            exchange_rate=rate, rmb_amount=(applied * rate).quantize(Decimal("0.0001")) if rate else Decimal("0"),
            reference_rate_missing=source.reference_rate_missing or rate is None, customer_id=source.customer_id,
            order=order, plan=plan, status="confirmed", split_from=rows[0][0] if rows else None, notes=reason)
        link = FinanceReceiptRefund.objects.create(source=source, refund=refund, voucher=proof, actor=cash.actor(user, "refund_receipt_cash"))
        if plan:
            plan.settled_amount -= applied
            if cancelled_refund:
                plan.planned_amount = plan.settled_amount
                plan.status = "settled" if plan.settled_amount else "cancelled"
            else:
                _sync_plan_status(plan)
            plan.save(update_fields=["settled_amount", "planned_amount", "status", "updated_at"])
        rows.append((refund, link))
        remaining -= applied
        if not remaining:
            break
    if remaining:
        raise ValidationError("所选订单可退的原收款现金不足；未分配款请单独选择退款。")
    return rows


@transaction.atomic
def approve_contract_change(change):
    change = ContractChangeRequest.objects.select_for_update().get(pk=change.pk)
    if change.order_id:
        contract = Order.objects.select_for_update().get(pk=change.order_id)
        change.order = contract
    elif change.purchase_order_id:
        contract = PurchaseOrder.objects.select_for_update().get(pk=change.purchase_order_id)
        change.purchase_order = contract
    else:
        raise ValidationError("合同变更必须关联销售订单或采购单。")
    if change.status != "pending":
        raise ValidationError("只有待确认变更单可以确认。")
    contract = change.order or change.purchase_order
    if contract is None or contract.status in {"draft", "cancelled"}:
        raise ValidationError("只有有效合同可以确认金额变更。")
    before_total = contract.total_amount
    target_total = before_total + change.amount_delta
    if change.order_id and contract.amount_calculation_version != LEGACY_AMOUNT_CALCULATION_VERSION:
        target_total = money(contract.base_amount + contract.approved_change_amount + change.amount_delta)
    delta = target_total - before_total
    plan = None
    if delta > 0:
        plan = PaymentPlan.objects.create(
            order=change.order,
            purchase_order=change.purchase_order,
            direction="receivable" if change.order_id else "payable",
            due_date=change.due_date,
            planned_amount=delta,
            currency=contract.currency,
            notes=f"变更单 #{change.pk}：{change.notes}",
        )
    elif delta < 0:
        if target_total < contract.paid_amount:
            raise ValidationError("金额调减后不能低于当前已收/已付金额，需先完成退款。")
        remaining_reduction = -delta
        plans = list(contract.payment_plans.select_for_update().exclude(status="cancelled").order_by("-due_date", "-id"))
        if sum((plan.remaining_amount for plan in plans), Decimal("0")) < remaining_reduction:
            raise ValidationError("金额调减超过可减少的未结收付款计划余额。")
        plan = None
        for candidate in plans:
            reduction = min(candidate.remaining_amount, remaining_reduction)
            if reduction <= 0:
                continue
            candidate.planned_amount -= reduction
            if candidate.planned_amount == 0:
                candidate.status = "cancelled"
            else:
                _sync_plan_status(candidate)
            candidate.save(update_fields=["planned_amount", "status", "updated_at"])
            plan = candidate
            remaining_reduction -= reduction
            if remaining_reduction == 0:
                break
    change.status = "approved"
    change.save(update_fields=["status", "updated_at"])
    return plan


@transaction.atomic
def reject_contract_change(change):
    change = ContractChangeRequest.objects.select_for_update().get(pk=change.pk)
    if change.status != "pending":
        raise ValidationError("只有待确认变更单可以拒绝。")
    change.status = "rejected"
    change.save(update_fields=["status", "updated_at"])
    return change


def order_receivable_state(order, plans, today=None):
    """Read-only status from effective original-currency plans; never creates plans."""
    today = today or timezone.localdate()
    if order.status in {"draft", "cancelled"}:
        return {"state": order.status, "label": "尚未生效" if order.status == "draft" else "已取消", "overdue_amount": Decimal("0")}
    effective = [p for p in plans if p.direction == "receivable" and p.status != "cancelled"]
    total = sum((p.planned_amount for p in effective), Decimal("0"))
    settled = sum((p.settled_amount + _writeoff_total(p) for p in effective), Decimal("0"))
    balance = sum((p.remaining_amount for p in effective if p.status == "open"), Decimal("0"))
    overdue = sum((p.remaining_amount for p in effective if p.status == "open" and p.remaining_amount > 0 and p.due_date and p.due_date < today), Decimal("0"))
    if not effective:
        state, label = ("zero_contract", "零金额订单，无应收计划") if order.total_amount == 0 else ("no_plans", "无有效应收计划")
    elif balance == 0 and total > 0 and settled == total:
        state, label = "settled", "款项已结清"
    elif balance > 0:
        state, label = ("partial", "部分收款") if settled > 0 else ("pending", "待收款")
    else:
        state, label = "review", "应收计划待核对"
    return {"state": state, "label": label, "overdue_amount": overdue}
