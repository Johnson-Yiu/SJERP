"""Connect verified historical cash sources to the controlled finance service."""

import hashlib
import json

from django.db import transaction
from rest_framework.exceptions import ValidationError

from crm.history_takeover import _event
from crm.history_operational_common import verified_source
from crm.models import FinanceFact, FinanceInstruction, HistoryTakeoverGroup, HistoryTakeoverHandoff, HistoryTakeoverSourceRecord
from crm.services import finance_closeout


SOURCE_SYSTEM = "HISTORY_TAKEOVER_V1"


def _source_key(source):
    identity = json.dumps([source.source_system, source.record_type, source.source_record_id], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def _locked(group_id, source_id):
    group = HistoryTakeoverGroup.objects.select_for_update().select_related("application").get(pk=group_id)
    if group.status != "executed" or group.truth_status != "真实" or group.coverage_status != "complete":
        raise ValidationError("仅已审核并归档的真实完整关联组可申请资金接续。")
    handoff = HistoryTakeoverHandoff.objects.select_for_update().get(group=group, kind="finance")
    source = HistoryTakeoverSourceRecord.objects.filter(group=group, pk=source_id, record_type="收付款流水").first()
    if source is None:
        raise ValidationError("该关联组没有指定的历史收付款来源。")
    row = verified_source(group, handoff, source, "收付款流水", "source_transactions")
    if row.get("truth_status") != "真实" or row.get("source_status") != "confirmed" or not row.get("voucher_reference"):
        raise ValidationError("只有已确认且凭证、真实性均已核实的历史资金来源可以接续。")
    return group, handoff, source, row


def _mapping(handoff, source):
    return dict(handoff.payload.get("operational_instructions", {})).get(str(source.pk))


@transaction.atomic
def submit_source(group_id, source_id, data, user, *, replace_id=None):
    group, handoff, source, row = _locked(group_id, source_id)
    allowed = {"account", "voucher", "actual_date", "amount", "reason"}
    if not isinstance(data, dict) or set(data) != allowed:
        raise ValidationError("须明确填写账户、凭证、实际日期、实际人民币金额及核实依据。")
    direction = row.get("direction")
    if direction not in {"income", "expense"}:
        raise ValidationError("历史来源的收支方向不明确。")
    key = _source_key(source)
    old = _mapping(handoff, source)
    previous = FinanceInstruction.objects.filter(pk=old).first() if old else None
    replace = False
    if replace_id is not None:
        replace_id = finance_closeout.pk(replace_id)
        if previous and previous.replaces_id == replace_id:
            pass  # A response was lost after this revision was already saved.
        elif previous and previous.pk == replace_id and previous.status in {"cancelled", "failed"}:
            replace = True
        else:
            raise ValidationError("仅可修订当前已取消或已核实失败的资金指令。")
    request_key = ("history-cash:" + key + ":" + str(previous.pk)) if replace else (previous.request_key if previous else "history-cash:" + key)
    payload = {**data, "request_key": request_key, "source_system": SOURCE_SYSTEM,
               "source_key": key, "kind": "cash", "direction": direction,
               "nature": "unclassified", "truth": "verified", "allocations": []}
    if replace:
        payload["replaces"] = previous.pk
    elif previous and previous.replaces_id:
        payload["replaces"] = previous.replaces_id
    obj, created = finance_closeout.submit(payload, user)
    if old is not None and old != obj.pk and not replace:
        raise ValidationError("历史来源已关联另一条资金指令。")
    if old is None or (replace and old != obj.pk):
        details = dict(handoff.payload)
        mappings = dict(details.get("operational_instructions", {}))
        mappings[str(source.pk)] = obj.pk
        details["operational_instructions"] = mappings
        history = dict(details.get("operational_history", {}))
        history[str(source.pk)] = [*history.get(str(source.pk), []), obj.pk]
        details["operational_history"] = history
        handoff.payload, handoff.status = details, "pending_review"
        handoff.save(update_fields=["payload", "status"])
        group.finance_handoff_status = "pending_review"
        group.save(update_fields=["finance_handoff_status", "updated_at"])
        _event(group.application, group, "finance_instruction_submitted", user,
               {"source_record_id": source.pk, "instruction_id": obj.pk, "source_key": key})
    return obj, created


@transaction.atomic
def advance_source(group_id, source_id, action, user, *, voucher_checked=False, reason="", no_debit_confirmed=False):
    group, handoff, source, _row = _locked(group_id, source_id)
    instruction_id = _mapping(handoff, source)
    if not instruction_id:
        raise ValidationError("请先保存该来源的资金指令。")
    instruction = FinanceInstruction.objects.get(pk=instruction_id)
    if instruction.payload.get("source_system") != SOURCE_SYSTEM or instruction.payload.get("source_key") != _source_key(source):
        raise ValidationError("资金指令与历史来源不匹配。")
    previous_status = instruction.status
    if action == "approve":
        result = finance_closeout.approve(instruction_id, user)
    elif action == "post":
        if instruction.status not in {"approved", "posted"}:
            raise ValidationError("历史资金须由另一名人员复核后才能记账。")
        result = finance_closeout.post(instruction_id, user, voucher_checked=voucher_checked)
    elif action == "cancel":
        result = finance_closeout.cancel(instruction_id, user, reason)
    elif action == "fail":
        result = finance_closeout.fail(instruction_id, user, reason, no_debit_confirmed=no_debit_confirmed)
    else:
        raise ValidationError("不支持的资金接续操作。")
    if previous_status != {"approve": "approved", "post": "posted", "cancel": "cancelled", "fail": "failed"}[action]:
        _event(group.application, group, "finance_instruction_" + action, user,
               {"source_record_id": source.pk, "instruction_id": instruction_id,
                "fact_id": result.pk if action == "post" else None})
    statuses = [FinanceInstruction.objects.filter(pk=value).values_list("status", flat=True).first()
                for value in handoff.payload.get("operational_instructions", {}).values()]
    total = sum(1 for item in group.source_records.filter(record_type="收付款流水")
                if item.source_snapshot.get("resolved", {}).get("source_status") != "cancelled")
    status = "sources_posted" if total and len(statuses) == total and all(value == "posted" for value in statuses) else "pending_review"
    handoff.status = group.finance_handoff_status = status
    handoff.save(update_fields=["status"])
    group.save(update_fields=["finance_handoff_status", "updated_at"])
    return result


def source_status(group, user):
    finance_closeout.access(user)
    handoff = group.handoffs.filter(kind="finance").first()
    if handoff is None:
        return []
    result = []
    for source in group.source_records.filter(record_type="收付款流水").order_by("pk"):
        ident = _mapping(handoff, source)
        instruction = FinanceInstruction.objects.filter(pk=ident).first() if ident else None
        fact = FinanceFact.objects.filter(instruction_id=ident).first() if ident else None
        result.append({"source_id": source.pk, "source_record_id": source.source_record_id,
                       "source": source.source_snapshot.get("resolved", {}),
                       "instruction_id": ident, "status": instruction.status if instruction else "unmapped",
                       "fact_id": fact.pk if fact else None})
    return result
