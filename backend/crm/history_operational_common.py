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


def overall_status(group):
    """Derive, rather than persist, whether every applicable handoff is connected."""
    from crm.models import FinanceFact, FinanceInstruction

    if group.status != "executed":
        return {"state": "not_archived", "components": {}}
    handoffs = {row.kind: row for row in group.handoffs.all()}
    sources = list(group.source_records.all())
    # Cancelled source facts are retained in the archive, never posted again.
    # Pending or unknown sources remain required and therefore prevent completion.
    cash = [row for row in sources if row.record_type == "收付款流水" and row.source_snapshot.get("resolved", {}).get("source_status") != "cancelled"]
    stock = [row for row in sources if row.record_type == "库存盘点"]
    documents = [row for row in sources if row.record_type in {"销售订单", "采购订单"}]
    components = {}
    if cash:
        finance = handoffs.get("finance")
        mapping = (finance.payload if finance else {}).get("operational_instructions", {})
        values = []
        for source in cash:
            instruction = FinanceInstruction.objects.filter(pk=mapping.get(str(source.pk))).first()
            if not instruction:
                values.append("missing")
            elif instruction.status == "posted" and FinanceFact.objects.filter(instruction=instruction).exists():
                values.append("connected")
            elif instruction.status == "approved":
                values.append("ready")
            elif instruction.status == "pending":
                values.append("review")
            else:
                values.append("missing")
        components["finance"] = "connected" if all(value == "connected" for value in values) else "ready" if all(value in {"ready", "connected"} for value in values) else "review" if "review" in values else "missing"
    if stock:
        inventory = handoffs.get("inventory")
        actual = group.inventory_baselines.filter(reversal__isnull=True).count()
        components["inventory"] = "connected" if inventory and inventory.status == "posted" and actual == len(stock) else "ready" if inventory and inventory.status == "approved" else "review" if inventory and inventory.status == "pending_review" else "missing"
    if documents:
        fulfillment = handoffs.get("fulfillment")
        links = list(group.operational_contracts.select_related("continuation_order", "continuation_purchase"))
        if fulfillment and fulfillment.status == "drafts_created" and len(links) == len(documents):
            cancelled = any((link.continuation_order_id and link.continuation_order.status == "cancelled") or (link.continuation_purchase_id and link.continuation_purchase.status == "cancelled") for link in links)
            active = all((not link.continuation_order_id or link.continuation_order.status in {"confirmed", "production", "shipped", "completed"}) and (not link.continuation_purchase_id or link.continuation_purchase.status in {"ordered", "partial", "completed"}) for link in links)
            components["fulfillment"] = "connected" if active else "missing" if cancelled else "ready"
        else:
            components["fulfillment"] = "ready" if fulfillment and fulfillment.status == "approved" else "review" if fulfillment and fulfillment.status == "pending_review" else "missing"
    values = list(components.values())
    if values and all(value == "connected" for value in values):
        state = "connected"
    elif values and all(value in {"ready", "connected"} for value in values):
        state = "ready"
    elif "review" in values:
        state = "pending_review"
    else:
        state = "archived"
    return {"state": state, "components": components}
