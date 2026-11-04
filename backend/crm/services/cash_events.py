"""Bank voucher facts, independent of debt settlement and reference reporting."""
import hashlib
import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.conf import settings
from django.db import IntegrityError, connection, transaction
from django.db.models import Sum, Q
from django.utils import timezone
from rest_framework.exceptions import APIException, NotFound, ValidationError

from crm.finance_scope import require_finance_permission, scope_transaction_queryset, validate_finance_relations
from crm.audit import snapshot
from crm.models import CashDuplicateReview, CashSourceAllocation, Customer, RmbCashEvent, Supplier, Transaction
from crm.permissions import development_superadmin_enabled


class CashConflict(APIException):
    status_code = 409
    default_detail = "请求键内容冲突或资金来源已被占用，请按原请求键核查。"


UNITS = {c: Decimal("0.01") for c in ("CNY", "USD", "EUR", "GBP", "HKD", "AUD")}
UNITS["JPY"] = Decimal("1")
ACTIVE = ("pending", "confirmed")


def audit_cash_event(event, user, label, before=None):
    """Financial facts always append audit, including explicitly labelled dev identity."""
    from crm.services.finance_closeout import audit
    audit(event, user, label, before=before)


def money(value, currency="CNY", *, zero=False, rate=False):
    """Validate bank input; explicit rounding only canonicalizes valid precision."""
    if currency not in UNITS or isinstance(value, (bool, float)):
        raise ValidationError("币种未配置或金额必须为精确十进制字符串。")
    try:
        n = Decimal(str(value))
        unit = Decimal("0.000001") if rate else UNITS[currency]
        if not n.is_finite() or n < 0 or (n == 0 and not zero) or n >= Decimal("1000000000000"):
            raise ValueError
        rounded = n.quantize(unit, rounding=ROUND_HALF_UP)
        if n.as_tuple().exponent < unit.as_tuple().exponent or n != rounded:
            raise ValueError
        return rounded
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError("金额或汇率非有限正数、超限或超过币种允许精度。")


def access(user, action="view"):
    require_finance_permission(user, "finance", action)
    require_finance_permission(user, "finance", "view")
    require_finance_permission(user, "transactions", "view")


def actor(user, operation):
    if user and user.is_authenticated:
        return {"kind": "authenticated_user", "action": operation, "user_id": user.pk}
    if development_superadmin_enabled():
        return {"kind": "development_superadmin", "action": operation, "note": "开发身份，非正式员工审批"}
    raise ValidationError("无法识别操作身份。")


def source_visible(row, user):
    try:
        for member in family(row):
            if not scope_transaction_queryset(Transaction.objects.filter(pk=member.pk), user).exists():
                return False
            validate_finance_relations({}, user, instance=member)
    except (APIException, Transaction.DoesNotExist):
        return False
    return True


def source_snapshot(row):
    return {k: str(getattr(row, k)) if k in {"amount", "exchange_rate", "rmb_amount"} else getattr(row, k)
            for k in ("id", "transaction_no", "amount", "currency", "direction", "kind", "split_from_id", "customer_id", "supplier_id", "order_id", "purchase_order_id", "plan_id", "exchange_rate", "rmb_amount")}


def visible(event, user):
    if event.fee_for_id and not visible(event.fee_for, user):
        return False
    for a in event.sources.select_related("source"):
        if not source_visible(a.source, user):
            return False
        # Nulling/reassigning historical ownership must not expose the snapshot.
        for key in ("customer_id", "supplier_id", "order_id", "purchase_order_id", "plan_id"):
            if a.source_snapshot[key] != getattr(a.source, key):
                return False
    return event.sources.exists()


def get_event(user, **lookup):
    access(user)
    if "pk" in lookup and (not str(lookup["pk"]).isdigit() or len(str(lookup["pk"])) > 19 or not 0 < int(lookup["pk"]) <= 9223372036854775807):
        raise NotFound("资金记录不存在或不可访问。")
    obj = RmbCashEvent.objects.filter(**lookup).first()
    if obj is None or not visible(obj, user):
        raise NotFound("资金记录不存在或不可访问。")
    return obj


def family(row):
    seen = set()
    while row.split_from_id:
        if row.pk in seen:
            raise ValidationError("历史拆分关系异常，需人工核对。")
        seen.add(row.pk)
        row = Transaction.objects.get(pk=row.split_from_id)
    result, pending = [], [row]
    while pending:
        node = pending.pop(0)
        if node.pk in {r.pk for r in result}:
            raise ValidationError("历史拆分关系异常。")
        result.append(node)
        pending[0:0] = list(node.split_rows.order_by("pk"))
    return result


def parties(row):
    """Legacy rows may identify a party only via their contract or plan."""
    customers, suppliers = set(), set()
    if row.customer_id:
        customers.add(row.customer_id)
    if row.supplier_id:
        suppliers.add(row.supplier_id)
    contracts = [row.order, row.purchase_order]
    if row.plan_id:
        contracts.extend([row.plan.order, row.plan.purchase_order])
    for contract in contracts:
        if contract is not None:
            if hasattr(contract, "customer_id"):
                customers.add(contract.customer_id)
            else:
                suppliers.add(contract.supplier_id)
    return customers, suppliers


def uncertainty(row):
    if row.kind in {"refund", "supplier_refund", "exchange_difference"}:
        return "退款/汇兑差额来源尚未明确，不能自动确认资金事实。"
    related = Q(pk__in=[])
    customers, suppliers = parties(row)
    if len(customers) > 1 or len(suppliers) > 1:
        return "来源往来方关联不一致，需核对。"
    if customers:
        related |= (Q(customer_id__in=customers) | Q(order__customer_id__in=customers) | Q(plan__order__customer_id__in=customers)) & Q(kind="refund")
    if suppliers:
        related |= (Q(supplier_id__in=suppliers) | Q(purchase_order__supplier_id__in=suppliers) | Q(plan__purchase_order__supplier_id__in=suppliers)) & Q(kind="supplier_refund")
    if Transaction.objects.filter(related, currency=row.currency).exists():
        return "同往来方同币种存在来源未明确的退款，资金可用量待核对。"
    members = family(row)
    if any(r.replaces_id for r in members) or Transaction.objects.filter(replaces_id__in=[r.pk for r in members]).exists():
        return "来源有历史替代关系，资金待核对。"
    return None


def available(row):
    used = row.cash_source_allocations.filter(event__status="confirmed").aggregate(n=Sum("amount"))["n"] or Decimal("0")
    return row.amount - used


def normalize(payload):
    if not isinstance(payload, dict):
        raise ValidationError("需要资金事件对象。")
    fields = {"event_no", "request_key", "kind", "currency", "direction", "bank_date", "bank_net_amount", "fee_mode", "fee_amount", "source_account", "rmb_account", "bank_reference", "bank_counterparty", "bank_summary", "bank_transaction_id", "evidence_reference", "evidence_sha256", "evidence_note", "quoted_rate", "sources", "fee_for", "correction_of", "private_voucher"}
    if set(payload) - fields:
        raise ValidationError("存在未支持的字段，不接受银行登录凭据或推测的资金更正。")
    if payload.get("correction_of") is not None:
        raise ValidationError("请使用账户资金更正流程保留原事实；不能直接覆盖银行事件或释放来源。")
    p = {}
    if payload.get("private_voucher") is not None:
        from crm.services.finance_closeout import pk
        p["private_voucher"] = pk(payload["private_voucher"])
    lengths = {"event_no": 64, "request_key": 128, "source_account": 40, "rmb_account": 40, "bank_reference": 120, "evidence_reference": 200, "evidence_sha256": 64, "evidence_note": 500}
    for k, maximum in lengths.items():
        value = payload.get(k, "")
        if not isinstance(value, str) or len(value.strip()) > maximum:
            raise ValidationError(f"{k}格式或长度无效。")
        p[k] = value.strip()
    # Preserve the original hash for retries of requests made before these
    # optional fields existed; absence is different from a newly supplied value.
    for k, maximum in (("bank_counterparty", 200), ("bank_summary", 500), ("bank_transaction_id", 120)):
        if k in payload:
            value = payload[k]
            if not isinstance(value, str) or len(value.strip()) > maximum:
                raise ValidationError(f"{k}格式或长度无效。")
            if value.strip():
                p[k] = value.strip()
    for k in ("event_no", "request_key", "source_account", "rmb_account"):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", p[k]):
            raise ValidationError(f"{k}必须为受控编号。")
    p["evidence_sha256"] = p["evidence_sha256"].lower()
    if not p["bank_reference"]:
        raise ValidationError("必须提供银行参考号。")
    p["kind"] = payload.get("kind")
    p["currency"] = payload.get("currency")
    p["direction"] = payload.get("direction")
    if not all(isinstance(p[k], str) for k in ("kind", "currency", "direction")):
        raise ValidationError("资金类型、方向和币种必须为字符串。")
    if p["kind"] not in {"fx_settlement", "cny_direct", "bank_fee"} or p["currency"] not in UNITS or p["direction"] not in {"income", "expense"}:
        raise ValidationError("资金类型、方向或币种无效。")
    if p["kind"] == "fx_settlement":
        if p["currency"] == "CNY" or p["direction"] != "income":
            raise ValidationError("结汇仅支持外币来源转人民币流入。")
    elif p["currency"] != "CNY":
        raise ValidationError("直接资金及独立扣费仅支持CNY。")
    if p["kind"] == "bank_fee" and p["direction"] != "expense":
        raise ValidationError("独立银行手续费必须为实际扣款。")
    try:
        p["bank_date"] = date.fromisoformat(payload.get("bank_date", "")).isoformat()
    except (TypeError, ValueError):
        raise ValidationError("必须提供银行实际入账/扣款日期。")
    p["bank_net_amount"] = str(money(payload.get("bank_net_amount")))
    p["fee_mode"] = payload.get("fee_mode", "none")
    p["fee_amount"] = str(money(payload.get("fee_amount", "0"), zero=True))
    if not isinstance(p["fee_mode"], str) or p["fee_mode"] not in {"none", "included"} or (p["fee_mode"] == "none" and Decimal(p["fee_amount"]) != 0):
        raise ValidationError("独立扣费须单独事件和银行依据，不能作为含扣费重复扣减。")
    if p["fee_mode"] == "included" and (p["kind"] != "fx_settlement" or Decimal(p["fee_amount"]) <= 0):
        raise ValidationError("含扣费只作结汇净额的说明。")
    p["quoted_rate"] = None if payload.get("quoted_rate") is None else str(money(payload["quoted_rate"], rate=True))
    if p["currency"] == "CNY" and p["quoted_rate"] is not None and Decimal(p["quoted_rate"]) != 1:
        raise ValidationError("CNY对人民币报价汇率只能为1或不提供；不得覆盖银行净额。")
    p["fee_for"] = payload.get("fee_for")
    if p["fee_for"] is not None and (type(p["fee_for"]) is not int or not 0 < p["fee_for"] <= 9223372036854775807 or p["kind"] != "bank_fee"):
        raise ValidationError("费用关联无效。")
    sources = payload.get("sources")
    if not isinstance(sources, list) or not 1 <= len(sources) <= 100:
        raise ValidationError("需要1至100条明确来源。")
    p["sources"] = []
    seen = set()
    for s in sources:
        if not isinstance(s, dict) or set(s) != {"transaction_id", "amount", "verified"} or s.get("verified") is not True or type(s.get("transaction_id")) is not int or not 0 < s["transaction_id"] <= 9223372036854775807 or s["transaction_id"] in seen:
            raise ValidationError("来源须逐条人工核实且不可重复列出。")
        seen.add(s["transaction_id"])
        p["sources"].append({"transaction_id": s["transaction_id"], "amount": str(money(s.get("amount"), p["currency"])), "verified": True})
    p["sources"].sort(key=lambda s: s["transaction_id"])
    total = sum((Decimal(s["amount"]) for s in p["sources"]), Decimal("0"))
    money(total, p["currency"])
    if p["currency"] == "CNY" and total != Decimal(p["bank_net_amount"]):
        raise ValidationError("CNY直接收付必须与分配的银行净额精确一致。")
    return p


def validate_sources(p, user, *, confirmation=False):
    rows = []
    for s in p["sources"]:
        row = Transaction.objects.filter(pk=s["transaction_id"]).first()
        if row is None or not source_visible(row, user):
            raise NotFound("资金来源不存在或不可访问。")
        if row.status != "confirmed" or row.currency != p["currency"] or row.direction != p["direction"]:
            raise ValidationError("来源状态、币种或方向不一致。")
        error = uncertainty(row)
        if error:
            raise ValidationError(error)
        if p["kind"] == "bank_fee" and row.kind != "bank_fee":
            raise ValidationError("单独扣费必须引用独立银行手续费流水及凭证。")
        if p["kind"] != "bank_fee" and row.kind == "bank_fee":
            raise ValidationError("银行手续费应作为独立扣费事件。")
        members = family(row)
        if any(r.currency != row.currency or r.direction != row.direction or r.status != "confirmed" for r in members):
            raise ValidationError("来源家族状态、币种或方向不一致，需核对。")
        if Decimal(s["amount"]) > available(row):
            raise CashConflict("来源额度不足或已确认，不能重复结汇。")
        rows.append(row)
    if p["fee_for"]:
        parent = get_event(user, pk=p["fee_for"])
        if parent.status != "confirmed" or parent.kind != "fx_settlement" or parent.fee_mode != "none" or parent.rmb_account != p["rmb_account"]:
            raise ValidationError("仅可关联无含扣费的已确认结汇；费用账户必须一致。")
    if confirmation:
        accounts = getattr(settings, "RMB_CASH_ACCOUNT_IDS", ())
        if p["source_account"] not in accounts or p["rmb_account"] not in accounts:
            raise ValidationError("银行账户受控标识未配置，不能确认。")
        if not p["evidence_reference"] or not p["evidence_note"] or not re.fullmatch(r"[a-fA-F0-9]{64}", p["evidence_sha256"]):
            raise ValidationError("必须提供银行凭证引用、SHA256及人工核实说明。")
    return rows


def duplicate_candidates(p, user, *, exclude_id=None):
    """Conservative bank-side core; blank optional evidence never proves difference."""
    core = Q(rmb_account=p["rmb_account"], bank_date=p["bank_date"], direction=p["direction"],
             bank_net_amount=p["bank_net_amount"])
    bank_id = p.get("bank_transaction_id", "")
    if bank_id:
        core |= Q(rmb_account=p["rmb_account"], bank_transaction_id=bank_id)
    qs = RmbCashEvent.objects.filter(core, status="confirmed")
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    events = list(qs.order_by("pk"))
    hidden = any(not visible(event, user) for event in events)
    ids = [event.pk for event in events]
    token = hashlib.sha256(json.dumps(ids, separators=(",", ":")).encode()).hexdigest()
    return {"token": token, "restricted": hidden, "count": len(events),
            "items": [] if hidden else [{"id": event.pk, "event_no": event.event_no,
                "bank_reference": event.bank_reference, "bank_counterparty": event.bank_counterparty,
                "bank_summary": event.bank_summary, "bank_transaction_id": event.bank_transaction_id}
                for event in events]}


def lock_bank_fact(p):
    # The lock domain is deliberately broader than optional bank evidence, so
    # missing/different text cannot let concurrent candidates pass each other.
    if connection.vendor == "postgresql":
        core = json.dumps([p["rmb_account"], str(p["bank_date"]), p["direction"],
                           str(Decimal(p["bank_net_amount"]).quantize(Decimal("0.01")))], separators=(",", ":"))
        key = int.from_bytes(hashlib.sha256(core.encode()).digest()[:8], "big", signed=True)
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [key])
            if p.get("bank_transaction_id"):
                identifier = json.dumps(["bank-id", p["rmb_account"], p["bank_transaction_id"]], separators=(",", ":"))
                identifier_key = int.from_bytes(hashlib.sha256(identifier.encode()).digest()[:8], "big", signed=True)
                cursor.execute("SELECT pg_advisory_xact_lock(%s)", [identifier_key])
    elif connection.vendor != "sqlite":
        raise ValidationError("当前数据库不支持银行事实并发锁，不能确认。")


@transaction.atomic
def register_event(payload, user):
    access(user, "create")
    p = normalize(payload)
    digest = hashlib.sha256(json.dumps(p, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    existing = RmbCashEvent.objects.filter(request_key=p["request_key"]).first()
    if existing:
        if not visible(existing, user):
            raise NotFound("资金记录不存在或不可访问。")
        if existing.request_hash != digest:
            raise CashConflict()
        return existing, False
    rows = validate_sources(p, user)
    values = {k: v for k, v in p.items() if k not in {"sources", "fee_for", "private_voucher"}}
    values.update(request_hash=digest, request_payload=p, amount=sum((Decimal(s["amount"]) for s in p["sources"]), Decimal("0")), created_actor=actor(user, "register"), fee_for_id=p["fee_for"])
    try:
        with transaction.atomic():
            event = RmbCashEvent.objects.create(**values)
            for s, row in zip(p["sources"], rows):
                CashSourceAllocation.objects.create(event=event, source=row, amount=s["amount"], currency=p["currency"], source_snapshot=source_snapshot(row))
    except IntegrityError:
        existing = RmbCashEvent.objects.filter(request_key=p["request_key"]).first()
        if existing and visible(existing, user) and existing.request_hash == digest:
            return existing, False
        raise CashConflict()
    event.refresh_from_db()
    if p.get("private_voucher"):
        from crm.services.bank_vouchers import bind
        bind(event, p["private_voucher"], user, operation="create")
    audit_cash_event(event, user, "登记银行资金事件")
    return event, True


@transaction.atomic
def confirm_event(event_id, user, *, voucher_checked=False, duplicate_token=None, duplicate_reason=None):
    access(user, "update")
    event = get_event(user, pk=event_id)
    p = event.request_payload
    lock_bank_fact(p)
    rows = [a.source for a in event.sources.select_related("source").order_by("source_id")]
    # Shared lock domain with refunds. No guesses about which customer's cash a
    # refund consumed; unrelated parties/currencies retain their normal paths.
    for index, model in enumerate((Customer, Supplier)):
        ids = set().union(*(parties(r)[index] for r in rows))
        list(model.objects.select_for_update().filter(pk__in=sorted(ids)).order_by("pk"))
    roots = {family(r)[0].pk for r in rows}
    for root in sorted(roots):
        # Same parent-first order as void_transaction; serialize the whole family.
        for member in family(Transaction.objects.get(pk=root)):
            Transaction.objects.select_for_update().get(pk=member.pk)
    event = RmbCashEvent.objects.select_for_update().get(pk=event.pk)
    if not visible(event, user):
        raise NotFound("资金记录不存在或不可访问。")
    if event.status == "confirmed":
        return event
    if event.status != "pending" or voucher_checked is not True:
        raise ValidationError("只有待确认事件可由人工核实银行凭证后确认。")
    validate_sources(p, user, confirmation=True)
    from crm.services.bank_vouchers import require_verified_file
    require_verified_file(event, user)
    candidates = duplicate_candidates(p, user, exclude_id=event.pk)
    if candidates["restricted"]:
        raise CashConflict("存在无权查看的疑似重复资金记录，请联系有权人员核对。")
    if candidates["count"]:
        if duplicate_token != candidates["token"] or not isinstance(duplicate_reason, str) or not 1 <= len(duplicate_reason.strip()) <= 500:
            raise CashConflict("存在疑似重复资金记录，请重新核对并填写放行说明。")
        CashDuplicateReview.objects.create(event=event, candidate_ids=[c["id"] for c in candidates["items"]],
                                           reason=duplicate_reason.strip(), actor=actor(user, "release_duplicate_candidate"))
    for a in event.sources.select_related("source"):
        if a.source_snapshot != source_snapshot(a.source):
            raise ValidationError("来源快照已变化，请核查原流水；不能覆盖旧证据。")
    before = snapshot(event)
    event.status = "confirmed"
    event.confirmed_at = timezone.now()
    event.confirmed_actor = actor(user, "confirm_bank_voucher")
    event.save(update_fields=["status", "confirmed_at", "confirmed_actor", "updated_at"])
    audit_cash_event(event, user, "确认银行资金事件", before=before)
    return event


@transaction.atomic
def cancel_pending(event_id, user, reason):
    access(user, "update")
    event = get_event(user, pk=event_id)
    event = RmbCashEvent.objects.select_for_update().get(pk=event.pk)
    if event.status != "pending" or not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 500:
        raise ValidationError("仅可有理由地放弃未确认草稿，已确认银行事实不可作废或释放来源。")
    before = snapshot(event)
    event.status = "cancelled"
    event.cancelled_reason = reason.strip()
    event.confirmed_actor = actor(user, "cancel_pending")
    event.save(update_fields=["status", "cancelled_reason", "confirmed_actor", "updated_at"])
    audit_cash_event(event, user, "放弃银行资金草稿", before=before)
    return event


def guard_void(rows, operation="作废"):
    if CashSourceAllocation.objects.filter(source_id__in=[r.pk for r in rows], event__status__in=ACTIVE).exists():
        raise ValidationError(f"来源有关联待确认/已确认银行资金事件，不能直接{operation}。未确认草稿可留痕放弃；已确认事实请走账户资金更正，不能自动释放来源。")


def guard_replacement(row):
    for member in family(row):
        Transaction.objects.select_for_update().get(pk=member.pk)
    guard_void(family(row), "替代")


def guard_refund(contract):
    """Caller locks party before contract, shared with bank confirmation."""
    if hasattr(contract, "customer_id"):
        relation = Q(source__customer_id=contract.customer_id) | Q(source__order__customer_id=contract.customer_id) | Q(source__plan__order__customer_id=contract.customer_id)
    else:
        relation = Q(source__supplier_id=contract.supplier_id) | Q(source__purchase_order__supplier_id=contract.supplier_id) | Q(source__plan__purchase_order__supplier_id=contract.supplier_id)
    if CashSourceAllocation.objects.filter(relation, source__currency=contract.currency, event__status__in=ACTIVE).exists():
        raise ValidationError("该往来方同币种资金已有银行事件，退款来源未明确，不能自动释放或推测使用额度。")
