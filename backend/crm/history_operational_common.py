"""Check operational handoffs against both archived and original source rows."""

from rest_framework.exceptions import ValidationError

from crm.history_takeover import _record_source_id


def verified_original(group, source, sheet):
    originals = [item for item in group.source_rows.get(sheet, [])
                 if _record_source_id(sheet, item.get("data", {})) == source.source_record_id]
    if len(originals) != 1 or originals[0].get("data") != source.source_snapshot.get("source"):
        raise ValidationError("来源记录与申请原文不一致，请通过更正流程重新审核。")
    expected = dict(originals[0]["data"])
    prefix = f"{sheet}:{originals[0]['row']}:"
    for key, value in (group.resolution_map or {}).items():
        if key.startswith(prefix):
            expected[key[len(prefix):]] = str(value).strip()
    resolved = source.source_snapshot.get("resolved", {})
    if expected != resolved:
        raise ValidationError("来源主档映射与已核实记录不一致，请重新审核。")
    return resolved


def verified_source(group, handoff, source, sheet, payload_key):
    resolved = verified_original(group, source, sheet)
    archived = [item for item in handoff.payload.get(payload_key, [])
                if _record_source_id(sheet, item) == source.source_record_id]
    if len(archived) != 1 or archived[0] != resolved:
        raise ValidationError("来源记录与已归档资料不一致，请通过更正流程重新审核。")
    return resolved
