"""Read-only cost provenance inspection; this module never repairs business data."""
from decimal import Decimal

from crm.models import HistoryOperationalContract, HistoryTakeoverHandoff, SKURelationship
from crm.history_takeover import _json_hash


def _cost(value, currency):
    return {"amount": format(Decimal(str(value)).normalize(), "f") if value is not None else None, "currency": currency or None}


def inspect_cost_integrity():
    findings = []
    checked = {"historical_lines": 0, "derived_skus": 0}
    for contract in HistoryOperationalContract.objects.filter(continuation_order__isnull=False).select_related("continuation_order"):
        handoff = HistoryTakeoverHandoff.objects.filter(group_id=contract.group_id, kind="fulfillment").first()
        proposal = (handoff.payload if handoff else {}).get("operational_proposal", {})
        trusted = bool(proposal) and proposal.get("fingerprint") == contract.approval_snapshot.get("proposal_fingerprint") == _json_hash({key: value for key, value in proposal.items() if key != "fingerprint"})
        document = next((row for row in proposal.get("normalized", []) if row.get("source_id") == contract.source_id), {}) if trusted else {}
        approved = {row["source_id"]: row for row in document.get("lines", [])}
        items = {item.pk: item for item in contract.continuation_order.items.all()}
        for link in contract.line_links:
            checked["historical_lines"] += 1
            source = approved.get(link.get("source_id"), {})
            expected = _cost(link.get("unit_cost", source.get("unit_cost")), link.get("cost_currency"))
            item = items.get(link.get("continuation_item_id"))
            current = _cost(item.cost_price, item.cost_currency_snapshot) if item else None
            immutable_conflict = bool(source and (source.get("cost_currency") != link.get("cost_currency") or
                (link.get("unit_cost") is not None and _cost(source.get("unit_cost"), source.get("cost_currency")) != expected)))
            if immutable_conflict or current != expected or not expected["currency"] or expected["amount"] is None:
                findings.append({"kind": "historical_continuation", "contract_id": contract.pk,
                    "source_id": link.get("source_id"), "order_id": contract.continuation_order_id,
                    "item_id": link.get("continuation_item_id"), "expected": expected, "current": current,
                    "status": "confirmed_mismatch" if immutable_conflict else "needs_review",
                    "reason": "批准申请与不可变接续关联记录的成本金额或币种不同" if immutable_conflict else
                        "当前行与来源快照不同或证据不全；需核对后续人工修改及原始创建记录"})
    # A relationship records ancestry, not the chosen cost source or its historical
    # monetary values. Current parent values cannot establish a historic error.
    targets = {}
    for relationship in SKURelationship.objects.select_related("source", "target").order_by("target_id", "source_id"):
        targets.setdefault(relationship.target_id, []).append(relationship)
    for target_id, relationships in targets.items():
        checked["derived_skus"] += 1
        target = relationships[0].target
        current = _cost(target.cost_price, target.cost_currency)
        sources = [{"sku_id": row.source_id, **_cost(row.source.cost_price, row.source.cost_currency)} for row in relationships]
        if not current["currency"] or any(_cost(row.source.cost_price, row.source.cost_currency) != current for row in relationships):
            findings.append({"kind": "derived_sku", "sku_id": target_id, "current": current, "sources": sources,
                "status": "needs_review", "reason": "关系树未冻结当时成本来源；须核对选定来源及生成后的人工修改"})
    return {"read_only": True, "checked": checked, "findings": findings,
        "counts": {status: sum(row["status"] == status for row in findings) for status in ("confirmed_mismatch", "needs_review")}}
