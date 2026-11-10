"""Reviewed opening counts, without replaying historical stock movements."""

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from crm.finance_scope import require_finance_permission
from crm.history_takeover import _event, _json_hash, actor_snapshot
from crm.history_operational_common import verified_source
from crm.history_products import sku_summary
from crm.models import (HistoryInventoryBaseline, HistoryInventoryBaselineReversal,
    HistoryTakeoverGroup, HistoryTakeoverHandoff, InventoryMovement, InventoryReservation, SKU)


def _access(user, action):
    if not user or not user.is_authenticated:
        raise ValidationError("库存基准操作需要已认证的操作人。")
    require_finance_permission(user, "inventory", action)
    require_finance_permission(user, "inventory", "view")


def _locked(group_id):
    group = HistoryTakeoverGroup.objects.select_for_update().select_related("application").get(pk=group_id)
    if group.status != "executed" or group.truth_status != "真实" or group.coverage_status != "complete":
        raise ValidationError("只有已审核归档的真实完整关联组可以办理库存基准。")
    return group, HistoryTakeoverHandoff.objects.select_for_update().get(group=group, kind="inventory")


def _cost(value):
    if not isinstance(value, str):
        raise ValidationError("请明确填写单位成本的十进制字符串。")
    try:
        number = Decimal(value)
        if not number.is_finite() or number < 0 or number.as_tuple().exponent < -12 or number >= Decimal("1000000000000"):
            raise ValueError
    except (InvalidOperation, ValueError):
        raise ValidationError("单位成本无效或精度超过12位。")
    return str(number)


def _sources(group):
    return list(group.source_records.filter(record_type="库存盘点").select_related("product_link__sku__product").order_by("pk"))


def _source_identity(source):
    link = getattr(source, "product_link", None)
    return {"version": link.version, "sku_id": link.sku_id, "needs_review": link.needs_review} if link else None


def _fingerprint(group, rows):
    sources = []
    for source in _sources(group):
        entry = {"id": source.pk, "snapshot": source.source_snapshot}
        if identity := _source_identity(source):
            entry["product_link"] = identity
        sources.append(entry)
    return _json_hash({"rows": rows, "sources": sources})


def _resolved_sku(source, row):
    link = getattr(source, "product_link", None)
    if link:
        return link.sku if link.sku_id and not link.needs_review and link.sku.active else None
    return SKU.objects.filter(sku=row.get("sku_code"), active=True).first()


def status(group, user):
    _access(user, "view")
    handoff = group.handoffs.filter(kind="inventory").first()
    if handoff is None:
        return {"status": "not_connected", "sources": []}
    return {"status": handoff.status,
        "proposal": handoff.payload.get("baseline_proposal"),
        "approval": handoff.payload.get("baseline_approval"),
        "sources": [{"source_id": source.pk, "source_record_id": source.source_record_id,
                     "source": source.source_snapshot.get("source", {}),
                     "linked_sku": sku_summary(getattr(getattr(source, "product_link", None), "sku", None)),
                     "link_needs_review": bool(getattr(getattr(source, "product_link", None), "needs_review", False))}
                    for source in _sources(group)],
        "baselines": list(group.inventory_baselines.values("id", "source_id", "sku_id", "quantity", "goods_ownership", "warehouse_type", "warehouse", "lot_reference", "unit_cost", "cost_currency", "reversal__id"))}


@transaction.atomic
def propose(group_id, rows, reason, complete_sku_inventory, user):
    _access(user, "create")
    group, handoff = _locked(group_id)
    if handoff.status in {"posted", "reversed"}:
        raise ValidationError("已启用或撤销的基准不能覆盖；请通过更正流程处理。")
    sources = _sources(group)
    if not sources or not isinstance(rows, list) or len(rows) != len(sources) or complete_sku_inventory is not True:
        raise ValidationError("请核实每个 SKU 的完整盘点范围并逐行填写归属与成本。")
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 500:
        raise ValidationError("请填写盘点及成本核实依据。")
    by_id = {str(source.pk): source for source in sources}
    seen, normalized = set(), []
    for entry in rows:
        if not isinstance(entry, dict) or set(entry) != {"source_id", "goods_ownership", "unit_cost", "cost_currency", "no_lot"}:
            raise ValidationError("盘点映射字段不完整。")
        ident = str(entry["source_id"])
        source = by_id.get(ident)
        if source is None or ident in seen:
            raise ValidationError("盘点来源不存在或重复。")
        seen.add(ident)
        row = verified_source(group, handoff, source, "库存盘点", "count_baselines")
        sku = _resolved_sku(source, row)
        if (row.get("truth_status") != "真实" or row.get("coverage_complete") != "yes" or not row.get("voucher_reference")
                or row.get("warehouse_type") not in {"自有仓", "第三方仓"} or not row.get("warehouse") or not sku
                or row.get("unit_snapshot") != sku.unit):
            raise ValidationError("盘点来源、凭证、仓库、SKU 或基础单位尚未完整核实。")
        if not row.get("lot_reference") and entry["no_lot"] is not True:
            raise ValidationError("没有批次或货位时须明确确认不适用。")
        if row.get("lot_reference") and entry["no_lot"] is True:
            raise ValidationError("来源已有批次或货位，不能同时标记为不适用。")
        if len(str(row["warehouse"])) > 100 or len(str(row.get("lot_reference") or "")) > 160 or len(str(row["voucher_reference"])) > 500:
            raise ValidationError("仓库、批次或凭证引用超出可保存长度。")
        if entry["goods_ownership"] not in {"own", "third_party"}:
            raise ValidationError("须明确货物为自有或第三方所有；仓库归属不能代替货物归属。")
        currency = str(entry["cost_currency"] or "").strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", currency):
            raise ValidationError("须填写三位成本币种。")
        try:
            count = Decimal(str(row["counted_quantity"]))
            count_date = date.fromisoformat(str(row["count_date"]))
            if not count.is_finite() or count < 0 or count.as_tuple().exponent < -2 or count_date > timezone.localdate():
                raise ValueError
        except (KeyError, ValueError, InvalidOperation):
            raise ValidationError("盘点日期或数量无效。")
        normalized.append({"source_id": source.pk, "sku_id": sku.pk, "sku_unit": sku.unit,
            "count_date": count_date.isoformat(), "quantity": str(count),
            "goods_ownership": entry["goods_ownership"], "unit_cost": _cost(entry["unit_cost"]),
            "cost_currency": currency, "no_lot": entry["no_lot"] is True})
    normalized.sort(key=lambda item: item["source_id"])
    sku_dates = {}
    for row in normalized:
        sku_dates.setdefault(row["sku_id"], set()).add(row["count_date"])
    if any(len(values) != 1 for values in sku_dates.values()):
        raise ValidationError("同一 SKU 的盘点基准必须使用同一盘点日期。")
    payload = dict(handoff.payload)
    proposal = {"rows": normalized, "reason": reason.strip(), "maker_id": user.pk, "maker_kind": actor_snapshot(user)[2]}
    proposal["fingerprint"] = _fingerprint(group, proposal)
    if payload.get("baseline_proposal") == proposal and handoff.status in {"pending_review", "approved"}:
        return handoff, True
    payload["baseline_proposal"] = proposal
    payload.pop("baseline_approval", None)
    handoff.payload, handoff.status = payload, "pending_review"
    handoff.save(update_fields=["payload", "status"])
    group.inventory_handoff_status = "pending_review"
    group.save(update_fields=["inventory_handoff_status", "updated_at"])
    _event(group.application, group, "inventory_baseline_proposed", user, {"fingerprint": proposal["fingerprint"], "reason": reason.strip()})
    return handoff, False


@transaction.atomic
def approve(group_id, note, user):
    _access(user, "update")
    group, handoff = _locked(group_id)
    proposal = handoff.payload.get("baseline_proposal")
    if not proposal or handoff.status not in {"pending_review", "approved"}:
        raise ValidationError("请先提交库存基准核实资料。")
    if proposal["maker_id"] == user.pk:
        raise ValidationError("申请人不能复核自己的库存基准。")
    if not isinstance(note, str) or not note.strip():
        raise ValidationError("请填写盘点复核依据。")
    raw = {key: value for key, value in proposal.items() if key != "fingerprint"}
    if _fingerprint(group, raw) != proposal["fingerprint"]:
        raise ValidationError("盘点来源已变化，请重新申请。")
    if handoff.status == "approved":
        return handoff, True
    payload = dict(handoff.payload)
    payload["baseline_approval"] = {"reviewer_id": user.pk, "reviewer_kind": actor_snapshot(user)[2], "note": note.strip(), "fingerprint": proposal["fingerprint"]}
    handoff.payload, handoff.status = payload, "approved"
    handoff.save(update_fields=["payload", "status"])
    group.inventory_handoff_status = "approved"
    group.save(update_fields=["inventory_handoff_status", "updated_at"])
    _event(group.application, group, "inventory_baseline_approved", user, payload["baseline_approval"])
    return handoff, False


@transaction.atomic
def execute(group_id, user):
    _access(user, "update")
    group, handoff = _locked(group_id)
    if handoff.status == "posted":
        return list(group.inventory_baselines.values_list("pk", flat=True)), True
    if handoff.status != "approved":
        raise ValidationError("库存基准必须先经另一名授权人员复核。")
    proposal, approval = handoff.payload["baseline_proposal"], handoff.payload["baseline_approval"]
    raw = {key: value for key, value in proposal.items() if key != "fingerprint"}
    if _fingerprint(group, raw) != proposal["fingerprint"] or approval["fingerprint"] != proposal["fingerprint"]:
        raise ValidationError("来源或复核资料已变化，请重新申请。")
    sku_ids = sorted({row["sku_id"] for row in proposal["rows"]})
    skus = {sku.pk: sku for sku in SKU.objects.select_for_update().filter(pk__in=sku_ids).order_by("pk")}
    if len(skus) != len(sku_ids):
        raise ValidationError("SKU 已不存在，请重新核实。")
    if (InventoryMovement.objects.filter(sku_id__in=sku_ids).exists()
            or InventoryReservation.objects.filter(sku_id__in=sku_ids).exists()
            or HistoryInventoryBaseline.objects.filter(sku_id__in=sku_ids, reversal__isnull=True).exists()):
        raise ValidationError("SKU 已有库存流水、预留或启用基准，不能叠加盘点基准。")
    sources = {source.pk: source for source in _sources(group)}
    created = []
    for row in proposal["rows"]:
        sku, source = skus[row["sku_id"]], sources.get(row["source_id"])
        if not source or not sku.active or sku.unit != row["sku_unit"]:
            raise ValidationError("SKU 或盘点来源已变化，请重新审核。")
        data = verified_source(group, handoff, source, "库存盘点", "count_baselines")
        resolved = _resolved_sku(source, data)
        if resolved is None or resolved.pk != sku.pk:
            raise ValidationError("SKU 或盘点来源已变化，请重新审核。")
        obj = HistoryInventoryBaseline.objects.create(group=group, source=source, sku=sku,
            count_date=row["count_date"], warehouse_type=data["warehouse_type"], warehouse=data["warehouse"],
            lot_reference=data.get("lot_reference") or "", goods_ownership=row["goods_ownership"],
            unit_snapshot=row["sku_unit"], quantity=row["quantity"], unit_cost=row["unit_cost"],
            cost_currency=row["cost_currency"], evidence_reference=data["voucher_reference"],
            approval_snapshot={"proposal": proposal, "approval": approval})
        created.append(obj.pk)
    handoff.status = group.inventory_handoff_status = "posted"
    handoff.save(update_fields=["status"])
    group.save(update_fields=["inventory_handoff_status", "updated_at"])
    _event(group.application, group, "inventory_baseline_posted", user, {"baseline_ids": created, "fingerprint": proposal["fingerprint"]})
    return created, False


@transaction.atomic
def reverse(group_id, reason, user):
    _access(user, "update")
    group, handoff = _locked(group_id)
    if handoff.status == "reversed":
        return True
    if handoff.status != "posted" or not isinstance(reason, str) or not reason.strip():
        raise ValidationError("只有已启用的基准可以填写原因后撤销。")
    baselines = list(group.inventory_baselines.select_related("source").order_by("sku_id", "pk"))
    sku_ids = sorted({item.sku_id for item in baselines})
    list(SKU.objects.select_for_update().filter(pk__in=sku_ids).order_by("pk"))
    if InventoryMovement.objects.filter(sku_id__in=sku_ids).exists() or InventoryReservation.objects.filter(sku_id__in=sku_ids).exists():
        raise ValidationError("基准已有后续库存流水或预留，不能直接撤销；请走审计更正。")
    if any(HistoryInventoryBaselineReversal.objects.filter(baseline=item).exists() for item in baselines):
        raise ValidationError("基准撤销状态不一致，需人工核查。")
    for item in baselines:
        HistoryInventoryBaselineReversal.objects.create(baseline=item, group=group, reason=reason.strip(), actor=user)
    handoff.status = group.inventory_handoff_status = "reversed"
    handoff.save(update_fields=["status"])
    group.save(update_fields=["inventory_handoff_status", "updated_at"])
    _event(group.application, group, "inventory_baseline_reversed", user, {"baseline_ids": [item.pk for item in baselines], "reason": reason.strip()})
    return False
