import json
import re
from collections import defaultdict
from decimal import Decimal
from hashlib import sha256

from django.core import signing
from django.db import transaction
from django.db.models import Case, CharField, F, OuterRef, Q, Subquery, Value, When
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast, Coalesce
from rest_framework.exceptions import ValidationError

from .history_product_models import ArchivedHistoryLine, HistoryProductLink, HistoryProductLinkRequest, HistoryProductRule
from .money import LEGACY_AMOUNT_CALCULATION_VERSION, money
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


def load_source_lines(sources):
    lines = {}
    for label, model in ((ARCHIVED, ArchivedHistoryLine), *LEGACY_MODELS.items()):
        ids = [source.target_id for source in sources if source.target_model == label]
        if not ids:
            continue
        related = ("order", "purchase_order") if model is ArchivedHistoryLine else (
            "order" if model is OrderItem else "purchase_order", "sku__product",
        )
        lines.update(((label, row.pk), row) for row in model.objects.select_related(*related).filter(pk__in=ids))
    return lines


def filter_source_lines(sources, filters):
    def field_for_line(archived, sales, purchase):
        return Case(
            When(target_model=ARCHIVED, then=Subquery(ArchivedHistoryLine.objects.filter(pk=OuterRef("target_id")).annotate(value=archived).values("value")[:1])),
            When(target_model="crm.OrderItem", then=Subquery(OrderItem.objects.filter(pk=OuterRef("target_id")).annotate(value=sales).values("value")[:1])),
            When(target_model="crm.PurchaseOrderItem", then=Subquery(PurchaseOrderItem.objects.filter(pk=OuterRef("target_id")).annotate(value=purchase).values("value")[:1])),
            output_field=CharField(),
        )

    order_number = field_for_line(
        Coalesce("order__order_no", "purchase_order__purchase_no"),
        F("order__order_no"), F("purchase_order__purchase_no"),
    )
    sources = sources.alias(history_order=order_number).filter(Q(history_order__isnull=False) | Q(record_type="库存盘点"))

    if filters.get("q"):
        def original_field(archived_key, legacy_field):
            line_value = field_for_line(KeyTextTransform(archived_key, "facts"), F(legacy_field), F(legacy_field))
            return Case(
                When(target_model=ARCHIVED, then=line_value),
                default=Coalesce(KeyTextTransform(archived_key, "source_snapshot__source"), line_value, output_field=CharField()),
                output_field=CharField(),
            )

        code = original_field("sku_code", "sku_code_snapshot")
        name = original_field("sku_name_snapshot", "display_name_snapshot")
        term = filters["q"]
        sources = sources.alias(history_code=code, history_name=name).filter(
            Q(history_code__icontains=term) | Q(history_name__icontains=term)
            | Q(source_record_id__icontains=term) | Q(history_order__icontains=term)
        )

    if filters.get("date_from") or filters.get("date_to"):
        order_date = field_for_line(
            Cast(Coalesce("order__order_date", "purchase_order__order_date"), CharField()),
            Cast("order__order_date", CharField()), Cast("purchase_order__order_date", CharField()),
        )
        sources = sources.alias(history_date=Coalesce(order_date, KeyTextTransform("count_date", "source_snapshot__source"), output_field=CharField()))
        for name, comparison in (("date_from", "gte"), ("date_to", "lte")):
            if filters.get(name):
                sources = sources.filter(**{f"history_date__{comparison}": filters[name].isoformat()})

    if filters.get("target"):
        legacy_sku = field_for_line(Value(None, output_field=CharField()), F("sku__sku"), F("sku__sku"))
        sources = sources.alias(history_sku=Case(
            When(product_link__isnull=False, then=F("product_link__sku__sku")),
            default=legacy_sku, output_field=CharField(),
        )).filter(history_sku__iexact=filters["target"])

    if filters.get("status") == "review":
        return sources.filter(product_link__needs_review=True)
    legacy = Q(product_link__isnull=True, target_model__in=LEGACY_MODELS)
    linked = Q(product_link__needs_review=False, product_link__sku__isnull=False) | legacy
    if filters.get("status") == "linked":
        return sources.filter(linked)
    if filters.get("status") == "pending":
        return sources.exclude(linked | Q(product_link__needs_review=True))
    return sources


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
    sku = None if line is None or isinstance(line, ArchivedHistoryLine) else line.sku
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


def inventory_source_summary(source):
    original = source.source_snapshot.get("source", {})
    sku, version, state = link_state(source, None)
    return {
        "id": source.pk, "source_system": source.source_system, "source_number": source.source_record_id,
        "batch": source.group.source_group_id, "group": source.group_id, "application": source.group.application_id,
        "kind": "inventory", "order_number": "", "date": original.get("count_date") or "",
        "code": original.get("sku_code") or "", "name": original.get("sku_name_snapshot") or "",
        "specification": original.get("specification_snapshot") or "", "description": "",
        "category": "", "category_reference": "", "trade_quantity": None, "trade_unit_price": None,
        "trade_unit": "", "unit_price": "", "unit": original.get("unit_snapshot") or "",
        "quantity": original.get("counted_quantity") or "0", "amount": "", "currency": "",
        "sku": sku_summary(sku), "status": state, "version": version,
    }


def line_summary(source, line, *, include_sku=True):
    if line is None and source and source.record_type == "库存盘点":
        return inventory_source_summary(source)
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
        "amount": str(line.amount if getattr(document, "amount_calculation_version", LEGACY_AMOUNT_CALCULATION_VERSION) == LEGACY_AMOUNT_CALCULATION_VERSION else money(line.amount)),
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


def _normalize_specification(value):
    # Normalize only whitespace before a Latin unit suffix. Preserve case and
    # separators, so e.g. 24 W never matches 24 kW or 24 w.
    return re.sub(r"(?<=\d)[ \t]+(?=(?:kW|W|mA|A|V|Hz|lm|mm|cm|m|kg|g)(?![A-Za-z]))", "", str(value or "").strip())


def specification_matches(sku, unit, specification, verified_specification=""):
    if not unit or sku.unit != unit:
        return False
    original = _normalize_specification(specification)
    if original and verified_specification:
        return False
    candidate = original or _normalize_specification(verified_specification)
    current = sku.specification.strip()
    if not current and sku.parameter_values:
        current = " · ".join(f"{key}：{value}" for key, value in sorted(sku.parameter_values.items()))
    return bool(candidate and current and candidate == _normalize_specification(current))


def link_specification_is_current(source, sku, unit, original_specification, version):
    verified_specification = ""
    if not str(original_specification or "").strip():
        details = HistoryTakeoverEvent.objects.filter(
            group_id=source.group_id, event_type="history_product_linked",
            details__source_id=source.pk, details__after=sku.pk, details__version=version,
        ).values_list("details", flat=True).first()
        verified_specification = (details or {}).get("verified_specification", "")
    return specification_matches(sku, unit, original_specification, verified_specification)


def _preview_rows(sources, target, operation, verified_specification=""):
    rows, conflicts = [], []
    lines = load_source_lines(sources)
    for source in sources:
        line = lines.get((source.target_model, source.target_id))
        if line is None and source.record_type != "库存盘点":
            conflicts.append({"source_number": source.source_record_id, "reason": "原明细已不可用。"})
            continue
        row = line_summary(source, line)
        if source.record_type == "库存盘点" and source.group.inventory_handoff_status in {"posted", "reversed"}:
            conflicts.append({**row, "reason": "已启用或已撤销的库存基准须通过更正流程处理。"})
        elif operation == "link" and row["sku"] and row["sku"]["id"] != target.pk:
            conflicts.append({**row, "reason": "已有其他关联，请使用修改关联。"})
        elif operation in {"change", "unlink"} and not row["sku"]:
            conflicts.append({**row, "reason": "该明细当前没有关联。"})
        elif target and not specification_matches(target, row["unit"], row["specification"], verified_specification):
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


def preview_links(sources, user, ids, operation, target_id, reason, save_rule=False, verified_specification=""):
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
    if verified_specification and (not target or not reason):
        raise ValidationError("人工补核需要填写正式 SKU、核实规格和依据。")
    rows, conflicts = _preview_rows(selected, target, operation, verified_specification)
    if save_rule and not conflicts:
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
        if row["currency"]:
            amounts[row["currency"]] += Decimal(row["amount"])
    preview = {
        "user": user.pk, "operation": operation, "target": sku_summary(target), "reason": reason,
        "rows": rows, "save_rule": save_rule, "verified_specification": verified_specification,
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
    verified_specification = preview.get("verified_specification", "")
    rows, conflicts = _preview_rows(selected, target, operation, verified_specification)
    conflicts.extend({**row, "reason": "原关联或来源资料已变化。"} for row in rows if row != expected[row["id"]])
    if conflicts:
        return {"conflicts": conflicts}

    count = 0
    changed_sources = defaultdict(set)
    changed_inventory_groups = set()
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
        if before == after and needs_review == (row["status"] == "review") and not saved_rule and not verified_specification:
            continue
        version = row["version"] + 1
        if source.record_type == "库存盘点":
            changed_inventory_groups.add(source.group_id)
        else:
            changed_sources[source.group_id].add(source.pk)
        HistoryProductLink.objects.update_or_create(
            source=source, defaults={"sku_id": after, "version": version, "needs_review": needs_review},
        )
        from .history_takeover import _event
        _event(source.group.application, source.group, "history_product_linked", user, {
                "source_id": source.pk, "source_system": source.source_system,
                "source_number": source.source_record_id, "before": before, "after": after,
                "operation": operation, "reason": preview["reason"] or "已核对原规格与基础单位", "version": version, "request": digest,
                "saved_candidate_rule": saved_rule, "before_sku": row["sku"],
                "after_sku": sku_summary(target) if target else row["sku"] if needs_review else None,
                "original_specification": row["specification"], "verified_specification": verified_specification,
            })
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
    for group_id in changed_inventory_groups:
        handoff = HistoryTakeoverHandoff.objects.filter(
            group_id=group_id, kind="inventory", status__in=("pending_review", "approved"),
        ).first()
        if handoff:
            handoff.status = "needs_reapproval"
            handoff.save(update_fields=["status"])
            HistoryTakeoverGroup.objects.filter(pk=group_id).update(inventory_handoff_status="needs_reapproval")
    result = {"updated": count}
    HistoryProductLinkRequest.objects.create(pk=digest, result=result)
    return result
