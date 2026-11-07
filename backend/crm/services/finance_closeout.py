"""Controlled account ledger. No legacy order/debt/inventory mutation."""
import hashlib
import json
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from crm.models import (FinanceAccount, FinanceAccountMapping, FinanceClassification,
    FinanceFact, FinanceInstruction, FinanceReview, FinanceTransferMatch, FinanceVoucher,
    FinanceHistoricalTransfer, OperationLog, Order, RmbCashEvent)
from crm.sales_scope import effective_data_scope
from crm.finance_scope import validate_finance_relations
from crm.services import cash_events as cash

NATURES = {"unclassified", "income", "expense", "interest", "loan", "capital", "bank_fee", "commercial_refund", "refund_excess", "internal_principal", "correction"}
KINDS = {"cash", "opening", "correction", "refund_approval", "refund_payment", "bank_return", "refund_return"}
APPROVAL_KINDS = {"opening", "correction", "refund_approval", "refund_payment"}


def access(user, action="view"):
    cash.access(user, action)
    # Unallocated company facts cannot inherit a salesperson's customer scope.
    if effective_data_scope(user) != "all":
        raise PermissionDenied("账户资金需要全局财务数据范围。")


def identity(user, action):
    return cash.actor(user, action)


def audit(instance, user, label, before=None, after=None):
    actor = identity(user, label)
    from crm.audit import snapshot
    before, after = before or {}, after if after is not None else snapshot(instance)
    OperationLog.objects.create(content_type=ContentType.objects.get_for_model(instance),
        object_id=str(instance.pk), entity=instance._meta.label_lower,
        entity_label=str(instance._meta.verbose_name), object_label=str(instance.pk),
        action="custom", action_label=label, operator=user if actor["kind"] == "authenticated_user" else None,
        before_data=before, after_data=after,
        changed_fields=sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k)),
        metadata={"actor": actor, "source": "finance_closeout_v1"})


def text(value, limit=500):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        raise ValidationError("必填文字为空或超出长度。")
    return value.strip()


def pk(value):
    if isinstance(value, bool) or not str(value).isdigit() or not 0 < int(value) < 2**63:
        raise ValidationError("关联标识无效。")
    return int(value)


def iso(value):
    try:
        result = date.fromisoformat(value)
        if result.year < 1900:
            raise ValueError
        return result.isoformat()
    except (TypeError, ValueError):
        raise ValidationError("实际日期无效。")


def amount(value, signed=False):
    if signed:
        if not isinstance(value, str):
            raise ValidationError("金额必须为十进制字符串。")
        try:
            number = Decimal(value)
            if not number.is_finite() or abs(number) >= Decimal("1000000000000") or number.as_tuple().exponent < -2:
                raise ValueError
            return number.quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            raise ValidationError("金额或精度无效。")
    return cash.money(value)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def account(value, lock=False):
    qs = FinanceAccount.objects.select_for_update() if lock else FinanceAccount.objects
    obj = qs.filter(pk=pk(value)).first()
    if obj is None:
        raise NotFound("账户不存在。")
    if not obj.is_active or obj.ownership != "own" or obj.currency != "CNY":
        raise ValidationError("仅可使用已核实的自有人民币账户。")
    return obj


def voucher(value, scope="account"):
    obj = FinanceVoucher.objects.filter(pk=pk(value)).first()
    if obj is None:
        raise NotFound("凭证不存在。")
    if obj.scope != scope:
        raise PermissionDenied("凭证所属业务范围不匹配。")
    hashed, size = hashlib.sha256(), 0
    try:
        with obj.file.open("rb") as source:
            for chunk in iter(lambda: source.read(65536), b""):
                size += len(chunk)
                if size > 10 * 1024 * 1024:
                    raise ValidationError("凭证文件超限。")
                hashed.update(chunk)
    except (OSError, ValueError):
        raise ValidationError("凭证文件不可读取。")
    if size != obj.size or hashed.hexdigest() != obj.sha256:
        raise ValidationError("凭证文件完整性核对失败。")
    return obj


def upload(file, user, bank_sources=None, scope=None):
    if scope is None:
        scope = "bank" if bank_sources is not None else "account"
    if scope not in {"account", "bank", "transaction"} or (bank_sources is not None and scope != "bank"):
        raise ValidationError("凭证用途无效。")
    if bank_sources is None:
        access(user, "create")
    else:
        cash.access(user, "create")
        if not bank_sources or len(bank_sources) > 100:
            raise ValidationError("银行凭证须绑定明确的1至100条来源。")
        from crm.models import Transaction
        bank_sources = sorted({pk(value) for value in bank_sources})
        for ident in bank_sources:
            source = Transaction.objects.filter(pk=ident).first()
            if source is None or not cash.source_visible(source, user):
                raise PermissionDenied("凭证来源不存在或不可访问。")
    if file is None or file.size > 10 * 1024 * 1024 or file.size <= 0:
        raise ValidationError("凭证不能为空且不得超过10MB。")
    data = bytearray()
    for chunk in file.chunks():
        data.extend(chunk)
        if len(data) > 10 * 1024 * 1024:
            raise ValidationError("凭证文件超限。")
    # Serve only as attachment. Reject active HTML/SVG and unknown formats.
    extension = ".pdf" if data.startswith(b"%PDF-") else ".png" if data.startswith(b"\x89PNG\r\n\x1a\n") else ".jpg" if data.startswith(b"\xff\xd8\xff") else None
    if extension is None:
        raise ValidationError("凭证仅支持PDF、PNG或JPEG。")
    obj = FinanceVoucher(original_name=str(file.name).replace("\\", "/").rsplit("/", 1)[-1][:200],
        sha256=hashlib.sha256(data).hexdigest(), size=len(data), actor=identity(user, "upload_voucher"),
        scope=scope, bank_sources=bank_sources or [])
    saved = False
    try:
        with transaction.atomic():
            obj.file.save(uuid.uuid4().hex + extension, ContentFile(bytes(data)), save=False)
            saved = True
            obj.save()
            audit(obj, user, "上传私有资金凭证")
    except Exception:
        if saved:
            obj.file.storage.delete(obj.file.name)
        raise
    return obj


@transaction.atomic
def create_account(data, user):
    access(user, "create")
    if not isinstance(data, dict) or set(data) - {"code", "name", "account_type", "ownership", "ownership_reason"}:
        raise ValidationError("未知账户字段。")
    kind, owner = data.get("account_type"), data.get("ownership", "unverified")
    if not isinstance(kind, str) or not isinstance(owner, str) or kind not in {"bank", "cash"} or owner not in {"own", "external", "unverified"}:
        raise ValidationError("账户类型或归属无效。")
    reason = text(data.get("ownership_reason")) if owner != "unverified" else ""
    code = text(data.get("code"), 40)
    if FinanceAccount.objects.filter(code=code).exists():
        raise ValidationError("账户标识已存在。")
    obj = FinanceAccount.objects.create(code=code, name=text(data.get("name"), 200), account_type=kind,
        ownership=owner, ownership_reason=reason)
    audit(obj, user, "建立资金账户")
    return obj


@transaction.atomic
def verify_account(data, user):
    access(user, "update")
    obj = FinanceAccount.objects.select_for_update().get(pk=pk(data.get("account")))
    if FinanceFact.objects.filter(account=obj).exists() or FinanceAccountMapping.objects.filter(account=obj).exists():
        raise ValidationError("账户已有历史事实或映射，不能改写历史归属。")
    if not isinstance(data.get("ownership"), str) or data.get("ownership") not in {"own", "external"}:
        raise ValidationError("须明确核实为自有或外部账户。")
    before = {"ownership": obj.ownership, "ownership_reason": obj.ownership_reason}
    obj.ownership, obj.ownership_reason = data["ownership"], text(data.get("reason"))
    obj.save(update_fields=["ownership", "ownership_reason", "updated_at"])
    audit(obj, user, "核实账户归属", before=before)
    return obj


@transaction.atomic
def map_account(data, user):
    access(user, "update")
    obj = account(data.get("account"), lock=True)
    if obj.account_type != "bank":
        raise ValidationError("既有银行事实只能映射到明确的银行账户，不能改成现金。")
    code = text(data.get("legacy_code"), 40)
    if FinanceAccountMapping.objects.filter(legacy_code=code).exists():
        raise ValidationError("旧账户已有明确映射，不可覆盖。")
    if not RmbCashEvent.objects.filter(rmb_account=code).exists():
        raise ValidationError("没有对应旧银行账户记录。")
    row = FinanceAccountMapping.objects.create(account=obj, legacy_code=code,
        reason=text(data.get("reason")), actor=identity(user, "map_account"))
    audit(row, user, "核实旧资金账户映射")
    return row


def normalize(data, user=None):
    allowed = {"request_key", "kind", "account", "voucher", "actual_date", "amount", "direction", "nature", "truth",
        "source_system", "source_key", "reason", "parent", "legacy_parent", "approval", "allocations", "excess_reason", "replaces", "duplicate_review_token", "duplicate_review_reason"}
    if not isinstance(data, dict) or set(data) - allowed:
        raise ValidationError("资金承接字段无效。")
    p = dict(data)
    p["request_key"] = text(p.get("request_key"), 128)
    if not isinstance(p.get("kind"), str) or p.get("kind") not in KINDS:
        raise ValidationError("资金操作类型无效。")
    p["reason"] = text(p.get("reason"))
    p["account"] = account(p.get("account")).pk
    p["voucher"] = voucher(p.get("voucher")).pk
    p["actual_date"] = iso(p.get("actual_date"))
    p["amount"] = str(cash.money(p.get("amount"), zero=True) if p["kind"] in {"opening", "correction"} else amount(p.get("amount")))
    if not isinstance(p.get("direction"), str) or p.get("direction") not in {"income", "expense"}:
        raise ValidationError("资金方向无效。")
    p.setdefault("nature", "unclassified")
    if not isinstance(p["nature"], str) or p["nature"] not in NATURES:
        raise ValidationError("资金性质无效。")
    p.setdefault("truth", "needs_verification")
    if not isinstance(p["truth"], str) or p["truth"] not in {"verified", "simulated", "needs_verification"}:
        raise ValidationError("真实性状态无效。")
    p["source_system"] = text(p.get("source_system"), 80)
    p["source_key"] = text(p.get("source_key"), 128)
    for key in ("parent", "legacy_parent", "approval", "replaces"):
        if p.get(key) is not None:
            p[key] = pk(p[key])
    if p.get("parent") and p.get("legacy_parent"):
        raise ValidationError("原事实只可选择一个来源。")
    allocations = p.setdefault("allocations", [])
    if not isinstance(allocations, list) or len(allocations) > 100:
        raise ValidationError("订单分配格式无效。")
    seen, total = set(), Decimal("0")
    for row in allocations:
        if not isinstance(row, dict) or set(row) != {"order", "amount"}:
            raise ValidationError("订单分配仅接受订单和金额。")
        row["order"] = pk(row["order"])
        if row["order"] in seen or not Order.objects.filter(pk=row["order"]).exists():
            raise ValidationError("订单不存在或重复。")
        seen.add(row["order"])
        if user is not None:
            validate_finance_relations({"order": Order.objects.get(pk=row["order"])}, user)
        row["amount"] = str(amount(row["amount"]))
        total += Decimal(row["amount"])
    if total > Decimal(p["amount"]):
        raise ValidationError("订单分配超过本次金额。")
    if p["kind"] == "refund_approval" and not p.get("excess_reason"):
        # Approval may exceed original receipts, but basis must explicitly say why.
        raise ValidationError("商业退款须提供批准及超额性质依据。")
    if p.get("excess_reason"):
        p["excess_reason"] = text(p["excess_reason"])
    for key in ("duplicate_review_token", "duplicate_review_reason"):
        if key in p:
            p[key] = text(p[key])
    return p


@transaction.atomic
def submit(data, user):
    access(user, "create")
    p = normalize(data, user)
    fingerprint = digest(p)
    previous = FinanceInstruction.objects.filter(request_key=p["request_key"]).first()
    if previous:
        if previous.request_hash != fingerprint:
            raise cash.CashConflict()
        return previous, False
    if p.get("replaces"):
        prior = FinanceInstruction.objects.select_for_update().filter(pk=p["replaces"]).first()
        if prior is None or prior.status not in {"cancelled", "failed"}:
            raise ValidationError("修订只能引用已留痕取消的指令。")
    try:
        with transaction.atomic():
            obj = FinanceInstruction.objects.create(request_key=p["request_key"], request_hash=fingerprint,
                payload=p, kind=p["kind"], reason=p["reason"], created_actor=identity(user, "submit"), replaces_id=p.get("replaces"))
    except IntegrityError:
        previous = FinanceInstruction.objects.get(request_key=p["request_key"])
        if previous.request_hash != fingerprint:
            raise cash.CashConflict()
        return previous, False
    audit(obj, user, "发起资金指令")
    return obj, True


@transaction.atomic
def approve(value, user):
    access(user, "update")
    obj = FinanceInstruction.objects.select_for_update().get(pk=pk(value))
    if not user or not user.is_authenticated or obj.created_actor.get("kind") != "authenticated_user":
        raise ValidationError("审批需要两名真实认证人员；开发身份不能代替。")
    if obj.created_actor.get("user_id") == user.pk:
        raise ValidationError("发起人不得审批自己的指令。")
    if obj.status == "approved":
        return obj
    if obj.status != "pending":
        raise ValidationError("仅待复核指令可批准。")
    if obj.payload["truth"] != "verified":
        raise ValidationError("待核实或模拟指令不能批准实际资金。")
    before = {"status": obj.status}
    obj.status, obj.approved_actor, obj.approved_at = "approved", identity(user, "approve"), timezone.now()
    obj.save(update_fields=["status", "approved_actor", "approved_at", "updated_at"])
    audit(obj, user, "复核资金指令", before=before)
    return obj


@transaction.atomic
def cancel(value, user, reason):
    access(user, "update")
    obj = FinanceInstruction.objects.select_for_update().get(pk=pk(value))
    if obj.status not in {"pending", "approved"}:
        raise ValidationError("已记账事实不能取消；请发起更正。")
    before = {"status": obj.status}
    obj.status = "cancelled"
    obj.save(update_fields=["status", "updated_at"])
    audit(obj, user, "取消资金指令", before=before, after={"status": obj.status, "reason": text(reason)})
    return obj


@transaction.atomic
def fail(value, user, reason, no_debit_confirmed=False):
    access(user, "update")
    obj = FinanceInstruction.objects.select_for_update().get(pk=pk(value))
    if obj.status not in {"pending", "approved"} or no_debit_confirmed is not True:
        raise ValidationError("仅明确核实未发生扣款的待处理指令可标记失败；结果未知不能这样处理。")
    before = {"status": obj.status}
    obj.status = "failed"
    obj.save(update_fields=["status", "updated_at"])
    audit(obj, user, "记录未扣款的资金失败", before=before, after={"status": "failed", "reason": text(reason)})
    return obj


def remaining(parent, kinds):
    return parent.amount - (FinanceFact.objects.filter(parent=parent, kind__in=kinds).aggregate(total=Sum("amount"))["total"] or Decimal("0"))


@transaction.atomic
def post(value, user, voucher_checked=False):
    access(user, "update")
    # All writers lock the account first, then instructions/parents; same order
    # for refunds, account reconciliation and opening baselines.
    initial = FinanceInstruction.objects.get(pk=pk(value))
    own = account(initial.payload["account"], lock=True)
    obj = FinanceInstruction.objects.select_for_update().get(pk=initial.pk)
    if obj.status == "posted":
        return FinanceFact.objects.get(instruction=obj)
    if obj.status in {"cancelled", "failed"} or voucher_checked is not True:
        raise ValidationError("须核实凭证且指令未取消。")
    p = obj.payload
    if p.get("source_system") == "HISTORY_TAKEOVER_V1" and obj.status != "approved":
        raise ValidationError("历史资金须由另一名授权人员复核后才能记账。")
    if digest(p) != obj.request_hash:
        raise ValidationError("指令内容完整性异常。")
    if p["truth"] != "verified":
        raise ValidationError("模拟或待核实资料不能计入实际资金。")
    for allocation in p["allocations"]:
        validate_finance_relations({"order": Order.objects.get(pk=allocation["order"])}, user)
    if obj.kind in APPROVAL_KINDS and obj.status != "approved":
        raise ValidationError("此操作须经另一名授权人员复核。")
    if obj.kind == "refund_approval":
        raise ValidationError("批准退款不等于实际扣款；请登记真实扣款。")
    proof = voucher(p["voucher"])
    value = Decimal(p["amount"])
    excess = Decimal("0")
    parent = None
    legacy_parent = None
    if p.get("parent"):
        parent = FinanceFact.objects.select_for_update().filter(pk=p["parent"]).first()
        if parent is None:
            raise ValidationError("原资金事实不存在。")
    if p.get("legacy_parent"):
        legacy_parent = RmbCashEvent.objects.select_for_update().filter(pk=p["legacy_parent"], status="confirmed").first()
        if legacy_parent is None or not cash.visible(legacy_parent, user) or not FinanceAccountMapping.objects.filter(account=own, legacy_code=legacy_parent.rmb_account).exists():
            raise ValidationError("既有银行事实须已确认、可访问且已明确映射到该账户。")
    if obj.kind in {"bank_return", "refund_return"}:
        if (parent and parent.pk in corrected_ids()[0]) or (legacy_parent and legacy_parent.pk in corrected_ids()[1]):
            raise ValidationError("原事实已有更正，退回须依据其有效版本核实。")
        required = "refund_payment" if obj.kind == "refund_return" else None
        if parent is None and legacy_parent is None:
            raise ValidationError("退回必须保留原实际资金关联。")
        if parent is not None and (parent.kind == "opening" or parent.account_id != own.pk or (required and parent.kind != required)):
            raise ValidationError("退回必须关联同一账户的原实际事实。")
        if required and legacy_parent:
            raise ValidationError("退款退回须引用本流程实际退款扣款，旧来源需先核实。")
        original_direction = parent.direction if parent else legacy_parent.direction
        available = remaining(parent, {"bank_return", "refund_return"}) if parent else legacy_parent.bank_net_amount - (FinanceFact.objects.filter(legacy_parent=legacy_parent, kind="bank_return").aggregate(total=Sum("amount"))["total"] or Decimal("0"))
        if p["direction"] == original_direction or value > available:
            raise ValidationError("退回方向错误或累计超过尚未退回金额。")
        if obj.kind == "bank_return" and own.account_type != "bank":
            raise ValidationError("银行退回必须属于银行账户。")
    if obj.kind == "correction" and ((parent is None and legacy_parent is None) or (parent is not None and parent.account_id != own.pk)):
        raise ValidationError("更正须保留同账户原事实关联；来源不明继续待核实。")
    if obj.kind == "correction":
        if parent and (parent.kind in {"opening", "refund_payment"} or FinanceFact.objects.filter(parent=parent).exists() or FinanceTransferMatch.objects.filter(Q(outgoing=parent) | Q(incoming=parent)).exists() or FinanceHistoricalTransfer.objects.filter(Q(outgoing_fact=parent) | Q(incoming_fact=parent)).exists()):
            raise ValidationError("原事实已有后续或本金关联；请先逐项核实依赖，不能覆盖其核实基础。")
        if legacy_parent and (FinanceFact.objects.filter(legacy_parent=legacy_parent).exists() or legacy_parent.pk in historical_transfer_ids()):
            raise ValidationError("既有银行事实已有后续核实记录，不能建立更正分叉。")
        reference_key, reference_id = ("parent", parent.pk) if parent else ("legacy_parent", legacy_parent.pk)
        approval_ids = set(FinanceInstruction.objects.filter(kind="refund_approval", **{f"payload__{reference_key}": reference_id}).values_list("pk", flat=True))
        if any(f.instruction.payload.get("approval") in approval_ids for f in FinanceFact.objects.filter(kind="refund_payment")):
            raise ValidationError("原事实已有实际退款，不能更改退款核实基础。")
    if obj.kind == "refund_payment":
        approval = FinanceInstruction.objects.select_for_update().filter(pk=p.get("approval"), kind="refund_approval", status="approved").first()
        if approval is None or approval.payload["account"] != own.pk or p["direction"] != "expense":
            raise ValidationError("实际退款须关联该账户已批准的退款依据。")
        consumed = sum((f.amount for f in FinanceFact.objects.filter(kind="refund_payment") if f.instruction.payload.get("approval") == approval.pk), Decimal("0"))
        if consumed + value > Decimal(approval.payload["amount"]):
            raise ValidationError("累计退款扣款超过批准金额。")
        original = FinanceFact.objects.select_for_update().filter(pk=approval.payload.get("parent"), direction="income").first()
        legacy_original = RmbCashEvent.objects.select_for_update().filter(pk=approval.payload.get("legacy_parent"), direction="income", status="confirmed").first()
        if original is None and (legacy_original is None or not cash.visible(legacy_original, user) or not FinanceAccountMapping.objects.filter(account=own, legacy_code=legacy_original.rmb_account).exists()):
            raise ValidationError("批准退款尚无明确原收款来源，须先核实。")
        if (original and FinanceFact.objects.filter(parent=original, kind="correction").exists()) or (legacy_original and FinanceFact.objects.filter(legacy_parent=legacy_original, kind="correction").exists()):
            raise ValidationError("批准所依据的原事实已有更正，须依据有效版本重新复核退款。")
        original_amount = original.amount if original else legacy_original.bank_net_amount
        reference_key, reference_id = ("parent", original.pk) if original else ("legacy_parent", legacy_original.pk)
        approvals = set(FinanceInstruction.objects.filter(kind="refund_approval", **{f"payload__{reference_key}": reference_id}).values_list("pk", flat=True))
        original_consumed = sum((f.amount for f in FinanceFact.objects.filter(kind="refund_payment") if f.instruction.payload.get("approval") in approvals), Decimal("0"))
        excess = max(Decimal("0"), original_consumed + value - original_amount) - max(Decimal("0"), original_consumed - original_amount)
        approved_allocations = {a["order"]: Decimal(a["amount"]) for a in approval.payload["allocations"]}
        for allocation in p["allocations"]:
            spent = sum((Decimal(a["amount"]) for f in FinanceFact.objects.filter(kind="refund_payment") if f.instruction.payload.get("approval") == approval.pk for a in f.instruction.payload["allocations"] if a["order"] == allocation["order"]), Decimal("0"))
            if spent + Decimal(allocation["amount"]) > approved_allocations.get(allocation["order"], Decimal("0")):
                raise ValidationError("订单退款分配超过该订单批准额度。")
    opening = FinanceFact.objects.filter(account=own, kind="opening").first()
    if obj.kind == "opening":
        if opening or FinanceFact.objects.filter(account=own, actual_date__lt=p["actual_date"]).exists():
            raise ValidationError("账户已有基准，或基准晚于已有实际事实；请核实启用边界。")
    elif opening and date.fromisoformat(p["actual_date"]) < opening.actual_date:
        raise ValidationError("实际日期早于启用基准，须按历史核实流程处理。")
    if FinanceFact.objects.filter(source_system=p["source_system"], source_key=p["source_key"]).exists():
        raise cash.CashConflict("来源记录已承接，不能使用新请求键重复记账。")
    # Candidate is a warning/refusal, not automatic deduplication. Explicitly
    # approved correction/refund entries still retain their separate identities.
    candidates = duplicate_candidates(p, user)
    if candidates["restricted"]:
        raise cash.CashConflict("存在无权核实的既有银行候选，不能记账。")
    if obj.kind == "cash" and candidates["ids"] and (p.get("duplicate_review_token") != candidates["token"] or not p.get("duplicate_review_reason")):
        raise cash.CashConflict("存在疑似重复事实，须获取当前候选并填写人工核实说明。")
    fact = FinanceFact.objects.create(instruction=obj, account=own, voucher=proof,
        actual_date=p["actual_date"], amount=value, direction=p["direction"], kind=obj.kind,
        nature=p["nature"], truth=p["truth"], source_system=p["source_system"], source_key=p["source_key"],
        parent=parent, legacy_parent=legacy_parent, excess_amount=excess, actor=identity(user, "post"))
    obj.status = "posted"
    obj.save(update_fields=["status", "updated_at"])
    audit(fact, user, "记入实际资金事实")
    return fact


def duplicate_candidates(p, user=None):
    ids = list(FinanceFact.objects.filter(account_id=p["account"], actual_date=p["actual_date"], direction=p["direction"], amount=p["amount"]).order_by("pk").values_list("pk", flat=True))
    codes = FinanceAccountMapping.objects.filter(account_id=p["account"]).values_list("legacy_code", flat=True)
    legacy = list(RmbCashEvent.objects.filter(rmb_account__in=codes, status="confirmed", bank_date=p["actual_date"], direction=p["direction"], bank_net_amount=p["amount"]).order_by("pk"))
    restricted = user is not None and any(not cash.visible(event, user) for event in legacy)
    if restricted:
        return {"ids": [], "token": "", "restricted": True}
    ids.extend(-event.pk for event in legacy)
    return {"ids": ids, "token": digest(ids), "restricted": False}


@transaction.atomic
def match_transfer(data, user):
    access(user, "update")
    ids = sorted({pk(data.get("outgoing")), pk(data.get("incoming"))})
    rows = list(FinanceFact.objects.filter(pk__in=ids).order_by("pk"))
    if len(rows) != 2:
        raise ValidationError("必须指定两笔已存在的实际资金事实。")
    for ident in sorted({r.account_id for r in rows}):
        account(ident, lock=True)
    out = FinanceFact.objects.select_for_update().get(pk=pk(data["outgoing"]))
    inc = FinanceFact.objects.select_for_update().get(pk=pk(data["incoming"]))
    if out.direction != "expense" or inc.direction != "income" or out.account_id == inc.account_id or out.amount != inc.amount:
        raise ValidationError("两端须为不同自有账户、相反方向且本金相等；差额不能当手续费。")
    if out.kind not in {"cash", "correction"} or inc.kind not in {"cash", "correction"} or effective_nature(out) != "internal_principal" or effective_nature(inc) != "internal_principal" or {out.pk, inc.pk} & corrected_ids()[0]:
        raise ValidationError("只可核实明确标记的内部本金事实。")
    if FinanceHistoricalTransfer.objects.filter(Q(outgoing_fact__in=[out, inc]) | Q(incoming_fact__in=[out, inc])).exists():
        raise cash.CashConflict("本金一端已完成历史银行匹配。")
    existing = FinanceTransferMatch.objects.filter(Q(outgoing=out) | Q(incoming=inc)).first()
    if existing:
        if existing.outgoing_id == out.pk and existing.incoming_id == inc.pk:
            return existing
        raise cash.CashConflict("转账一端已经关联。")
    obj = FinanceTransferMatch.objects.create(outgoing=out, incoming=inc, reason=text(data.get("reason")), actor=identity(user, "match_transfer"))
    audit(obj, user, "核实内部转账本金")
    return obj


@transaction.atomic
def classify(data, user):
    access(user, "update")
    fact = FinanceFact.objects.get(pk=pk(data.get("fact")))
    account(fact.account_id, lock=True)
    if fact.pk in corrected_ids()[0]:
        raise ValidationError("此事实已有核实更正，请对有效版本进行分类。")
    if FinanceTransferMatch.objects.filter(Q(outgoing=fact) | Q(incoming=fact)).exists() or FinanceHistoricalTransfer.objects.filter(Q(outgoing_fact=fact) | Q(incoming_fact=fact)).exists():
        raise ValidationError("已核实内部本金不能直接改成其他性质；请保留两端历史并使用受复核的更正事实。")
    nature = data.get("nature")
    if not isinstance(nature, str) or nature not in NATURES or nature == "internal_principal":
        raise ValidationError("性质无效；内部转账本金须由两端核实流程处理。")
    obj = FinanceClassification.objects.create(fact=fact, nature=nature, reason=text(data.get("reason")), actor=identity(user, "classify"))
    audit(obj, user, "核实资金性质")
    return obj


def account_rows(own, end, user=None):
    facts = list(FinanceFact.objects.filter(account=own, actual_date__lte=end).order_by("actual_date", "pk"))
    codes = FinanceAccountMapping.objects.filter(account=own).values_list("legacy_code", flat=True)
    legacy = list(RmbCashEvent.objects.filter(rmb_account__in=codes, status="confirmed", bank_date__lte=end).order_by("bank_date", "pk"))
    if user is not None and any(not cash.visible(event, user) for event in legacy):
        raise PermissionDenied("账户包含无权核实的历史来源，不能返回部分余额。")
    return facts, legacy


def effective_nature(fact):
    """Use the same append-only classification that reporting presents."""
    classification = fact.classifications.order_by("pk").last()
    return classification.nature if classification else fact.nature


def balance(own, end, user=None):
    facts, legacy = account_rows(own, end, user)
    opening = next((f for f in facts if f.kind == "opening"), None)
    if opening is None:
        return None, digest({"facts": [f.pk for f in facts], "legacy": [e.pk for e in legacy]})
    total = Decimal("0")
    included_legacy = [e for e in legacy if e.bank_date >= opening.actual_date]
    superseded, superseded_legacy = corrected_ids()
    for fact in facts:
        if fact.pk not in superseded:
            total += fact.amount if fact.direction == "income" else -fact.amount
    for event in included_legacy:
        if event.pk not in superseded_legacy:
            total += event.bank_net_amount if event.direction == "income" else -event.bank_net_amount
    corrections = list(FinanceFact.objects.filter(account=own, kind="correction").values_list("pk", flat=True))
    classifications = list(FinanceClassification.objects.filter(fact__in=facts).order_by("pk").values_list("pk", flat=True))
    fingerprint = {"facts": [f.pk for f in facts], "legacy": [e.pk for e in included_legacy], "corrections": corrections, "classifications": classifications}
    matches = list(FinanceTransferMatch.objects.filter(Q(outgoing__in=facts) | Q(incoming__in=facts)).order_by("pk").values_list("pk", flat=True))
    historical_matches = list(FinanceHistoricalTransfer.objects.filter(
        Q(outgoing_fact__in=facts) | Q(incoming_fact__in=facts) |
        Q(outgoing_legacy__in=included_legacy) | Q(incoming_legacy__in=included_legacy)
    ).order_by("pk").values_list("pk", flat=True))
    # Leave fingerprints for untouched older reviews byte-compatible. Accounts
    # with newly tracked matches conservatively require another review.
    if matches or historical_matches:
        fingerprint.update(transfer_matches=matches, historical_transfer_matches=historical_matches)
    return total, digest(fingerprint)


def corrected_ids():
    rows = FinanceFact.objects.filter(kind="correction").values_list("parent_id", "legacy_parent_id")
    parent_ids, legacy_ids = set(), set()
    for parent_id, legacy_id in rows:
        if parent_id:
            parent_ids.add(parent_id)
        if legacy_id:
            legacy_ids.add(legacy_id)
    return parent_ids, legacy_ids


def reporting_events(user, start, end):
    """Same verified facts for dashboard, report center, CSV and drilldown."""
    from types import SimpleNamespace
    from rest_framework.exceptions import PermissionDenied
    try:
        access(user)
    except PermissionDenied:
        return []
    matched = set()
    superseded, _ = corrected_ids()
    matched.update(superseded)
    for out, inc in FinanceTransferMatch.objects.values_list("outgoing_id", "incoming_id"):
        matched.update((out, inc))
    for out, inc in FinanceHistoricalTransfer.objects.values_list("outgoing_fact_id", "incoming_fact_id"):
        matched.update(value for value in (out, inc) if value is not None)
    result = []
    for f in FinanceFact.objects.select_related("account").filter(actual_date__range=(start, end)).exclude(kind="opening").exclude(pk__in=matched).exclude(kind="correction", amount=0):
        nature = effective_nature(f)
        result.append(SimpleNamespace(pk=-f.pk, id=-f.pk, event_no=f"ACCOUNT-{f.pk}", kind=nature,
            currency="CNY", amount=f.amount, direction=f.direction, bank_date=f.actual_date,
            bank_net_amount=f.amount, fee_mode="none", fee_amount=Decimal("0"),
            bank_reference=f.source_key, status="confirmed", account_type=f.account.account_type,
            excess_amount=f.excess_amount,
            detail_url=f"/finance-ledger?fact={f.pk}", get_kind_display=lambda n=nature: n))
    return result


def historical_transfer_ids():
    return {value for pair in FinanceHistoricalTransfer.objects.values_list("outgoing_legacy_id", "incoming_legacy_id") for value in pair if value is not None}


@transaction.atomic
def match_historical_transfer(data, user):
    access(user, "update")
    references = []
    for key, direction in (("outgoing", "expense"), ("incoming", "income")):
        raw = text(str(data.get(key)), 60)
        prefix, separator, ident = raw.partition(":")
        if not separator:
            prefix, ident = "fact", raw
        if prefix not in {"fact", "legacy"}:
            raise ValidationError("引用须为fact:编号或legacy:编号。")
        if prefix == "legacy":
            event = cash.get_event(user, pk=pk(ident))
            mapping = FinanceAccountMapping.objects.filter(legacy_code=event.rmb_account).first()
            if mapping is None or event.status != "confirmed":
                raise ValidationError("既有银行事件须已确认并完成明确账户映射。")
            if event.pk in corrected_ids()[1]:
                raise ValidationError("既有银行事实已更正，请使用其有效账户事实版本。")
            own_id, value = mapping.account_id, event.bank_net_amount
        else:
            event = FinanceFact.objects.get(pk=pk(ident))
            own_id, value = event.account_id, event.amount
            if event.kind not in {"cash", "correction"} or effective_nature(event) != "internal_principal" or event.pk in corrected_ids()[0]:
                raise ValidationError("新事实须明确标记为内部本金。")
        if event.direction != direction:
            raise ValidationError("本金两端方向错误。")
        references.append((prefix, event.pk, own_id, value))
    out, inc = references
    if out[2] == inc[2] or out[3] != inc[3] or not any(r[0] == "legacy" for r in references):
        raise ValidationError("历史匹配须含既有银行事件，两端账户不同且本金相同。")
    for ident in sorted({r[2] for r in references}):
        account(ident, lock=True)
    for prefix, ident, _, _ in sorted(references):
        model = RmbCashEvent if prefix == "legacy" else FinanceFact
        locked = model.objects.select_for_update().get(pk=ident)
        # Classification/correction may have committed while this request was
        # waiting for the shared account lock. Validate again under that lock.
        if prefix == "fact" and (effective_nature(locked) != "internal_principal" or ident in corrected_ids()[0]):
            raise ValidationError("新事实须明确标记为内部本金。")
        if prefix == "legacy" and ident in corrected_ids()[1]:
            raise ValidationError("既有银行事实已更正，请使用其有效账户事实版本。")
    values = {"outgoing_" + out[0] + "_id": out[1], "incoming_" + inc[0] + "_id": inc[1]}
    existing = FinanceHistoricalTransfer.objects.filter(**values).first()
    if existing:
        return existing
    for prefix, ident, _, _ in references:
        if prefix == "fact" and FinanceTransferMatch.objects.filter(Q(outgoing_id=ident) | Q(incoming_id=ident)).exists():
            raise cash.CashConflict("新资金事实已完成其他本金匹配。")
        if FinanceHistoricalTransfer.objects.filter(**{"outgoing_" + prefix + "_id": ident}).exists() or FinanceHistoricalTransfer.objects.filter(**{"incoming_" + prefix + "_id": ident}).exists():
            raise cash.CashConflict("该事实已用于其他本金匹配。")
    obj = FinanceHistoricalTransfer.objects.create(**values,
        outgoing_voucher=voucher(data.get("outgoing_voucher")), incoming_voucher=voucher(data.get("incoming_voucher")),
        reason=text(data.get("reason")), actor=identity(user, "match_historical_transfer"))
    audit(obj, user, "核实既有银行内部本金")
    return obj


@transaction.atomic
def reconcile(data, user):
    access(user, "update")
    own = account(data.get("account"), lock=True)
    start, end = iso(data.get("date_from")), iso(data.get("date_to"))
    if start > end:
        raise ValidationError("核对期间无效。")
    proof = voucher(data.get("voucher"))
    calculated, fingerprint = balance(own, end, user)
    if calculated is None:
        raise ValidationError("缺少独立启用基准，不能完成余额核对。")
    stated = amount(data.get("statement_balance"), signed=True)
    difference = stated - calculated
    if data.get("completed") is True and difference != 0:
        raise ValidationError("余额存在差异，不能标记核对完成。")
    obj = FinanceReview.objects.create(account=own, date_from=start, date_to=end, voucher=proof,
        statement_balance=stated, calculated_balance=calculated, difference=difference,
        fingerprint=fingerprint, completed=data.get("completed") is True,
        reason=text(data.get("reason")), actor=identity(user, "reconcile"))
    audit(obj, user, "核对账户余额")
    return obj
