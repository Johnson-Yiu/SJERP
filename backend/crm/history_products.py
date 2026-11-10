import json
from collections import defaultdict
from decimal import Decimal
from hashlib import sha256

from django.core import signing
from django.db import transaction
from rest_framework.exceptions import ValidationError

from .history_product_models import ArchivedHistoryLine, HistoryProductLink, HistoryProductLinkRequest, HistoryProductRule
from .models import HistoryTakeoverEvent, HistoryTakeoverGroup, HistoryTakeoverHandoff, HistoryTakeoverSourceRecord, OrderItem, PurchaseOrderItem, SKU

ARCHIVED = "crm.ArchivedHistoryLine"
LEGACY_MODELS = {"crm.OrderItem": OrderItem, "crm.PurchaseOrderItem": PurchaseOrderItem}
SOURCE_MODELS = (ARCHIVED, *LEGACY_MODELS)
PREVIEW_SALT = "history-product-link-v1"


def document_lines(document):
    if document.historical_only:
        return [*document.items.all(), *document.archived_lines.all()]
    return document.items.all()


def source_line(source):
    model = ArchivedHistoryLine if source.target_model == ARCHIVED else LEGACY_MODELS.get(source.target_model)
    if model is None:
        return None
    related = ("order", "purchase_order") if model is ArchivedHistoryLine else (
        "order" if model is OrderItem else "purchase_order", "sku__product",
    )
    return model.objects.select_related(*related).filter(pk=source.target_id).first()


def sku_summary(sku):
    return {
        "id": sku.pk, "code": sku.sku, "name": sku.display_name_cn or sku.product.name,
        "unit": sku.unit, "specification": sku.specification, "parameters": sku.parameter_values,
        "active": sku.active,
    } if sku else None


def link_state(source, line):
    link = getattr(source, "product_link", None) if source else None
    if link:
        return link.sku, link.version, "review" if link.needs_review else "linked" if link.sku_id else "pending"
    sku = None if isinstance(line, ArchivedHistoryLine) else line.sku
    return sku, 0, "linked" if sku else "pending"


def source_fields(source, line):
    if isinstance(line, ArchivedHistoryLine):
        return line.facts
    snapshot = source.source_snapshot.get("source", {}) if source else {}
    return {
        "sku_code": line.sku_code_snapshot,
        "sku_name_snapshot": line.display_name_snapshot,
        "description_snapshot": line.description_snapshot,
        "base_unit_snapshot": line.trade_snapshot.get("base_unit", getattr(line, "unit_snapshot", "")),
        "unit_snapshot": getattr(line, "unit_snapshot", "") or line.trade_snapshot.get("unit", ""),
        "product_category_snapshot": line.product_category_name_snapshot,
        **snapshot,
    }


def line_summary(source, line, *, include_sku=True):
    facts = source_fields(source, line)
    sku, version, state = link_state(source, line) if include_sku else (None, 0, None)
    document = getattr(line, "order", None) or line.purchase_order
    return {
        "id": source.pk if source else None,
        "source_system": source.source_system if source else "",
        "source_number": source.source_record_id if source else "",
        "batch": source.group.source_group_id if source else "",
        "group": source.group_id if source else None,
        "application": source.group.application_id if source else None,
        "kind": "sales" if hasattr(document, "order_no") else "purchase",
        "order_number": getattr(document, "order_no", None) or document.purchase_no,
        "date": document.order_date.isoformat(),
        "code": facts.get("sku_code") or "",
        "name": facts.get("sku_name_snapshot") or "",
        "specification": facts.get("specification_snapshot") or "",
        "description": facts.get("description_snapshot") or "",
        "category": facts.get("product_category_snapshot") or "",
        "category_reference": getattr(line, "product_category_reference_snapshot", ""),
        "trade_quantity": str(line.trade_quantity) if line.trade_quantity is not None else None,
        "trade_unit_price": str(line.trade_unit_price) if line.trade_unit_price is not None else None,
        "trade_unit": facts.get("trade_unit_snapshot") or "",
        "unit_price": str(line.unit_price),
        "unit": facts.get("base_unit_snapshot") or "",
        "quantity": str(line.quantity),
        "amount": str(line.amount),
        "currency": document.currency,
        "sku": sku_summary(sku),
        "status": state,
        "version": version,
    }


def document_product_rows(document, *, include_sku=True, include_source=True):
    lines = list(document_lines(document))
    legacy_model = "crm.OrderItem" if hasattr(document, "order_no") else "crm.PurchaseOrderItem"
    pairs = [(ARCHIVED if isinstance(line, ArchivedHistoryLine) else legacy_model, line.pk) for line in lines]
    sources = {}
    if include_source or include_sku:
        for source in HistoryTakeoverSourceRecord.objects.filter(
            target_model__in=(ARCHIVED, legacy_model), target_id__in=[pk for _, pk in pairs],
        ).select_related("group", "product_link__sku__product"):
            sources[(source.target_model, source.target_id)] = source
    rows = [line_summary(sources.get(key), line, include_sku=include_sku) for key, line in zip(pairs, lines)]
    if not include_sku:
        for row in rows:
            for key in ("code", "name", "specification", "description", "category", "category_reference"):
                row[key] = ""
    if not include_source:
        for row in rows:
            for key in ("id", "application", "group", "source_number", "source_system", "batch", "version"):
                row.pop(key)
    return rows


def rule_key(source_system, record_type, code, specification, unit):
    values = [str(value or "").strip() for value in (source_system, record_type, code, specification, unit)]
    if not all(values):
        return None
    return sha256(json.dumps(values, ensure_ascii=False).encode()).hexdigest()


def specification_matches(sku, unit, specification):
    if not unit or sku.unit != unit:
        return False
    specification = str(specification or "").strip()
    current = sku.specification.strip()
    if not current and sku.parameter_values:
        current = " · ".join(f"{key}：{value}" for key, value in sorted(sku.parameter_values.items()))
    return not current or specification == current


def _preview_rows(sources, target, operation):
    rows, conflicts = [], []
    for source in sources:
        line = source_line(source)
        if not line:
            conflicts.append({"source_number": source.source_record_id, "reason": "原明细已不可用。"})
            continue
        row = line_summary(source, line)
        if operation == "link" and row["sku"] and row["sku"]["id"] != target.pk:
            conflicts.append({**row, "reason": "已有其他关联，请使用修改关联。"})
        elif operation in {"change", "unlink"} and not row["sku"]:
            conflicts.append({**row, "reason": "该明细当前没有关联。"})
        elif target and not specification_matches(target, row["unit"], row["specification"]):
            conflicts.append({**row, "reason": "基础单位或规格资料不足或不一致，请先标记待核实。"})
        else:
            rows.append(row)
    return rows, conflicts


def _target(target_id, *, lock=False):
    if target_id is None:
        return None
    qs = SKU.objects.select_related("product")
    if lock:
        qs = qs.select_for_update(of=("self",))
    sku = qs.filter(pk=target_id, active=True).first()
    if not sku:
        raise ValidationError("目标 SKU 已停用、不可见或不存在。")
    return sku


def preview_links(sources, user, ids, operation, target_id, reason, save_rule=False):
    if operation not in {"link", "change", "unlink", "review"}:
        raise ValidationError("请选择关联操作。")
    if operation in {"link", "change"} and target_id is None:
        raise ValidationError("请选择正式 SKU。")
    if operation in {"unlink", "review"} and target_id is not None:
        raise ValidationError("此操作无需选择 SKU。")
    if operation in {"change", "unlink", "review"} and not reason:
        raise ValidationError("请填写原因。")
    selected = list(sources.filter(pk__in=ids).order_by("pk"))
    if len(selected) != len(ids):
        raise ValidationError("部分历史明细已不可见或不存在。")
    target = _target(target_id)
    rows, conflicts = _preview_rows(selected, target, operation)
    if save_rule:
        if not target:
            raise ValidationError("请选择要保存为候选的 SKU。")
        for source, row in zip(selected, rows):
            if not rule_key(source.source_system, source.record_type, row["code"], row["specification"], row["unit"]):
                conflicts.append({**row, "reason": "保存候选规则须有原编码、规格和单位。"})
    if conflicts:
        return {"conflicts": conflicts}
    quantities, amounts = defaultdict(Decimal), defaultdict(Decimal)
    for row in rows:
        quantities[row["unit"]] += Decimal(row["quantity"])
        amounts[row["currency"]] += Decimal(row["amount"])
    preview = {
        "user": user.pk, "operation": operation, "target": sku_summary(target), "reason": reason,
        "rows": rows, "save_rule": save_rule,
    }
    return {
        "rows": rows, "count": len(rows), "quantities": quantities, "amounts": amounts,
        "target": preview["target"], "token": signing.dumps(preview, salt=PREVIEW_SALT, compress=True),
    }


@transaction.atomic
def apply_links(sources, user, token):
    try:
        preview = signing.loads(token, salt=PREVIEW_SALT)
        if preview["user"] != user.pk:
            raise signing.BadSignature
    except signing.BadSignature as exc:
        raise ValidationError("关联预览无效，请重新预览。") from exc
    digest = sha256(token.encode()).hexdigest()
    expected = {row["id"]: row for row in preview["rows"]}
    # Match the lock order used by fulfillment: groups, source identities, SKUs.
    group_ids = sources.filter(pk__in=expected).values_list("group_id", flat=True)
    list(HistoryTakeoverGroup.objects.select_for_update().filter(pk__in=group_ids).order_by("pk").values_list("pk", flat=True))
    locked = list(HistoryTakeoverSourceRecord.objects.select_for_update().filter(pk__in=expected, group_id__in=group_ids).order_by("pk"))
    selected = list(sources.filter(pk__in=[row.pk for row in locked]).order_by("pk"))
    if len(selected) != len(expected):
        return {"conflicts": [{"reason": "部分来源已不可见，请重新预览。"}]}
    saved = HistoryProductLinkRequest.objects.filter(pk=digest).first()
    if saved:
        return saved.result
    try:
        signing.loads(token, salt=PREVIEW_SALT, max_age=900)
    except signing.SignatureExpired as exc:
        raise ValidationError("关联预览已过期，请重新预览。") from exc

    operation, old_target = preview["operation"], preview["target"]
    target = _target(old_target["id"], lock=True) if old_target else None
    if sku_summary(target) != old_target:
        return {"conflicts": [{"reason": "目标 SKU 资料已变化，请重新预览。"}]}
    rows, conflicts = _preview_rows(selected, target, operation)
    conflicts.extend({**row, "reason": "原关联或来源资料已变化。"} for row in rows if row != expected[row["id"]])
    if conflicts:
        return {"conflicts": conflicts}

    count = 0
    changed_sources = defaultdict(set)
    for source, row in zip(selected, rows):
        before = row["sku"]["id"] if row["sku"] else None
        after = target.pk if target else before if operation == "review" else None
        needs_review = operation == "review"
        saved_rule = False
        if preview["save_rule"]:
            key = rule_key(source.source_system, source.record_type, row["code"], row["specification"], row["unit"])
            rule, saved_rule = HistoryProductRule.objects.get_or_create(
                scope_key=key, defaults={"confirmed_source": source, "sku": target},
            )
            if rule.sku_id != target.pk:
                raise ValidationError("此来源已有不同的候选规则，请取消保存候选后重新预览。")
        if before == after and needs_review == (row["status"] == "review") and not saved_rule:
            continue
        version = row["version"] + 1
        changed_sources[source.group_id].add(source.pk)
        HistoryProductLink.objects.update_or_create(
            source=source, defaults={"sku_id": after, "version": version, "needs_review": needs_review},
        )
        HistoryTakeoverEvent.objects.create(
            application_id=source.group.application_id, group_id=source.group_id,
            event_type="history_product_linked", actor=user,
            actor_label=user.get_full_name() or user.get_username(),
            details={
                "source_id": source.pk, "source_system": source.source_system,
                "source_number": source.source_record_id, "before": before, "after": after,
                "operation": operation, "reason": preview["reason"], "version": version, "request": digest, "saved_candidate_rule": saved_rule,
            },
        )
        count += 1
    for group_id, source_ids in changed_sources.items():
        handoff = HistoryTakeoverHandoff.objects.filter(
            group_id=group_id, kind="fulfillment", status__in=("pending_review", "approved"),
        ).first()
        if handoff and any(
            line["source_id"] in source_ids
            for document in handoff.payload.get("operational_proposal", {}).get("normalized", [])
            for line in document["lines"]
        ):
            handoff.status = "needs_reapproval"
            handoff.save(update_fields=["status"])
            HistoryTakeoverGroup.objects.filter(pk=group_id).update(fulfillment_handoff_status="needs_reapproval")
    result = {"updated": count}
    HistoryProductLinkRequest.objects.create(pk=digest, result=result)
    return result
