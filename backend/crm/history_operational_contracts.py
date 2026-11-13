"""Reviewed residual-contract and unpaid-balance handoff for archived history."""

from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from crm.document_numbers import allocate_order_no, allocate_purchase_no
from crm.finance_scope import require_finance_permission
from crm.history_operational_common import verified_original, verified_source
from crm.history_takeover import _build_remainder, _event, _json_hash, _json_safe, actor_snapshot
from crm.history_products import link_specification_is_current, link_state, source_line
from crm.models import (HistoryOperationalContract, HistoryTakeoverGroup, HistoryTakeoverHandoff,
    Order, OrderItem, PurchaseOrder, PurchaseOrderItem, SKU, Supplier, SupplierSKU)
from crm.services.finance import install_history_opening_plans


def _access(user, action):
    if not user or not user.is_authenticated:
        raise ValidationError("历史接续需要已认证的操作人。")
    for module in ("orders", "purchases", "finance"):
        require_finance_permission(user, module, "view")
        require_finance_permission(user, module, action)
    require_finance_permission(user, "transactions", "view")


def _locked(group_id):
    group = HistoryTakeoverGroup.objects.select_for_update().select_related("application").get(pk=group_id)
    if group.status != "executed" or group.truth_status != "真实" or group.coverage_status != "complete":
        raise ValidationError("只有已审核归档的真实完整关联组可以办理业务接续。")
    handoff = HistoryTakeoverHandoff.objects.select_for_update().get(group=group, kind="fulfillment")
    return group, handoff


def _amount(value, *, places=4, digits=14):
    if not isinstance(value, str):
        raise ValidationError("金额须明确填写为十进制字符串。")
    try:
        result = Decimal(value)
        if not result.is_finite() or result < 0 or result.as_tuple().exponent < -places or result >= Decimal(10) ** (digits - places):
            raise ValueError
        return result
    except (InvalidOperation, ValueError):
        raise ValidationError("金额无效、超限或小数位数过多。")


def _date(value, *, optional=False):
    if optional and not value:
        return None
    try:
        parsed = date.fromisoformat(value)
    except (ValueError, TypeError):
        raise ValidationError("日期格式无效。")
    return parsed.isoformat()


def _source_data(group, handoff):
    records = list(group.source_records.order_by("pk"))
    rows, by_id = {}, {}
    finance = group.handoffs.get(kind="finance")
    for record in records:
        sheet = record.record_type
        if sheet == "履约记录":
            data = verified_source(group, handoff, record, sheet, "source_events")
        elif sheet == "收付款计划":
            data = verified_source(group, finance, record, sheet, "payment_plans")
        elif sheet == "收付款流水":
            data = verified_source(group, finance, record, sheet, "source_transactions")
        else:
            data = verified_original(group, record, sheet)
        by_id[record.pk] = (record, data)
        rows.setdefault(sheet, []).append({"data": data})
    remainder = _json_safe(_build_remainder(rows))
    if remainder != group.remainder_snapshot or remainder != handoff.payload.get("remainder_snapshot"):
        raise ValidationError("已归档履约事实或剩余数量发生变化，请通过更正流程重新审核。")
    return by_id, remainder


def status(group, user):
    _access(user, "view")
    handoff = group.handoffs.filter(kind="fulfillment").first()
    if handoff is None:
        return {"status": "not_connected", "contracts": [], "links": []}
    by_id, remainder = _source_data(group, handoff)
    docs = []
    for record, row in by_id.values():
        if record.record_type not in {"销售订单", "采购订单"}:
            continue
        parent_key = "source_order_id" if record.record_type == "销售订单" else "source_purchase_id"
        plans = [{"source_id": item.pk, "source_record_id": item.source_record_id, "source": data}
                 for item, data in by_id.values() if item.record_type == "收付款计划" and str(data.get(parent_key) or "") == record.source_record_id]
        lines = []
        for line, data, quantity in _line_records(record, by_id, remainder):
            archived_line = source_line(line)
            sku, _, link_status = link_state(line, archived_line) if archived_line else (None, 0, "pending")
            if link_status != "linked" or (sku and not sku.active):
                sku = None
            candidates = []
            if record.record_type == "采购订单" and sku:
                supplier_id = PurchaseOrder.objects.filter(pk=record.target_id).values_list("supplier_id", flat=True).first()
                candidates = list(SupplierSKU.objects.filter(sku=sku, supplier_id=supplier_id, is_active=True).values("id", "supplier_sku_code", "supplier_model", "moq"))
            lines.append({"source_id": line.pk, "source_record_id": line.source_record_id, "source": data,
                "remaining_quantity": str(quantity), "sku_link_confirmed": bool(sku), "linked_sku_id": sku.pk if sku else None, "linked_sku_code": sku.sku if sku else "", "sku_currency": sku.currency if sku else "", "sku_cost_currency": (sku.cost_currency or "") if sku else "", "supplier_sources": candidates})
        docs.append({"source_id": record.pk, "source_record_id": record.source_record_id, "record_type": record.record_type,
                     "source": row, "plans": plans, "remaining_lines": lines})
    links = []
    for link in group.operational_contracts.select_related("archived_order", "archived_purchase", "continuation_order", "continuation_purchase"):
        archived = link.archived_order or link.archived_purchase
        continuation = link.continuation_order or link.continuation_purchase
        links.append({"id": link.pk, "source_id": link.source_id, "balance_mode": link.balance_mode,
            "record_type": "销售订单" if link.archived_order_id else "采购订单",
            "opening_balance": str(link.opening_balance), "currency": link.currency,
            "archived_id": archived.pk, "archived_no": archived.order_no if link.archived_order_id else archived.purchase_no,
            "outstanding_balance": str(archived.outstanding_amount if link.archived_order_id else archived.unpaid_amount),
            "plans": list(archived.payment_plans.values("id", "direction", "due_date", "planned_amount", "settled_amount", "status", "notes")),
            "continuation_id": continuation.pk if continuation else None,
            "continuation_no": (continuation.order_no if link.continuation_order_id else continuation.purchase_no) if continuation else None,
            "continuation_status": continuation.status if continuation else "no_remaining", "line_links": link.line_links})
    return {"status": handoff.status, "proposal": handoff.payload.get("operational_proposal"),
            "approval": handoff.payload.get("operational_approval"), "contracts": docs, "links": links}


def _plans(source, data, options, by_id, mode, evidence):
    parent_field = "source_order_id" if source.record_type == "销售订单" else "source_purchase_id"
    direction = "receivable" if source.record_type == "销售订单" else "payable"
    matching = [(record, row) for record, row in by_id.values() if record.record_type == "收付款计划" and str(row.get(parent_field) or "") == source.source_record_id]
    specs = []
    if mode == "balance_only":
        if options.get("plan_source_ids"):
            raise ValidationError("余额承接与逐笔计划承接须分别选择。")
        balance = _amount(options.get("balance_amount"))
        if balance:
            specs.append({"amount": str(balance), "due_date": _date(options.get("due_date"), optional=True),
                          "note": f"历史余额承接：{source.source_record_id}；依据：{evidence}"})
        return balance, specs, []
    if mode != "itemized" or not matching:
        raise ValidationError("逐笔承接需要完整的历史收付款计划；否则请明确选择余额承接。")
    ids = options.get("plan_source_ids")
    if not isinstance(ids, list) or len(ids) != len(matching) or {str(value) for value in ids} != {str(record.pk) for record, _ in matching}:
        raise ValidationError("逐笔承接必须核对该合同的全部来源计划。")
    for record, row in matching:
        if row.get("truth_status") != "真实" or row.get("settlement_detail_complete") != "yes" or not row.get("voucher_reference") or row.get("direction") != direction or row.get("currency") != data.get("currency"):
            raise ValidationError("收付款计划的真实性、明细、方向、币种或凭证尚未核实。")
        planned, settled = _amount(str(row.get("planned_amount"))), _amount(str(row.get("settled_amount")))
        state = row.get("lifecycle_state")
        if settled > planned or state not in {"open", "settled", "cancelled"} or (state == "settled" and settled != planned) or (state == "open" and settled >= planned):
            raise ValidationError("来源付款计划状态与金额不一致。")
        kinds = {"customer_receipt": 1, "refund": -1} if direction == "receivable" else {"supplier_payment": 1, "supplier_refund": -1}
        transactions = [item for item, tx in by_id.values() if item.record_type == "收付款流水" and str(tx.get("source_plan_id") or "") == record.source_record_id]
        confirmed = Decimal("0")
        for item in transactions:
            tx = by_id[item.pk][1]
            if tx.get("source_status") == "confirmed" and tx.get("kind") in kinds:
                if tx.get("truth_status") != "真实" or not tx.get("voucher_reference") or tx.get("currency") != row.get("currency"):
                    raise ValidationError("计划关联的已确认收付款流水未完整核实。")
                confirmed += _amount(str(tx.get("amount"))) * kinds[tx["kind"]]
        if confirmed != settled:
            raise ValidationError("来源计划已核销金额与已确认关联流水不一致。")
        if state == "open":
            specs.append({"amount": str(planned - settled), "due_date": _date(row.get("due_date"), optional=True),
                          "note": f"历史逐笔未结计划：{record.source_record_id}；依据：{row['voucher_reference']}"})
    return sum((Decimal(item["amount"]) for item in specs), Decimal("0")), specs, [record.pk for record, _ in matching]


def _line_records(source, by_id, remainder):
    sales = source.record_type == "销售订单"
    sheet, parent_key = ("销售明细", "source_order_id") if sales else ("采购明细", "source_purchase_id")
    summary_key = "sales_orders" if sales else "purchase_orders"
    summary = next((item for item in remainder[summary_key] if item["source_record_id"] == source.source_record_id), None)
    if summary is None:
        raise ValidationError("找不到历史订单剩余数量快照。")
    remaining = {line["source_line_id"]: Decimal(line["remaining_quantity_base"]) for line in summary["lines"]}
    return [(record, row, remaining[str(row["source_line_id"])]) for record, row in by_id.values()
            if record.record_type == sheet and str(row.get(parent_key) or "") == source.source_record_id
            and remaining.get(str(row.get("source_line_id") or ""), Decimal("0")) > 0]


def _snapshot(group, options, by_id, remainder):
    docs = [(record, data) for record, data in by_id.values() if record.record_type in {"销售订单", "采购订单"}]
    if not isinstance(options, list) or len(options) != len(docs) or {str(row.get("source_id")) for row in options if isinstance(row, dict)} != {str(record.pk) for record, _ in docs}:
        raise ValidationError("关联组中的每个销售及采购合同都必须明确核对。")
    inputs = {str(row["source_id"]): row for row in options}
    output = []
    for source, data in docs:
        item = inputs[str(source.pk)]
        evidence = str(item.get("evidence_reference") or "").strip()
        if not evidence or len(evidence) > 500:
            raise ValidationError("每个合同须填写未结余额核实依据。")
        if HistoryOperationalContract.objects.filter(source=source).exists():
            raise ValidationError("该历史合同已接续。")
        archived = Order.objects.filter(pk=source.target_id, historical_only=True, status="historical").first() if source.record_type == "销售订单" else PurchaseOrder.objects.filter(pk=source.target_id, historical_only=True, status="historical").first()
        original_no = data.get("order_no") if source.record_type == "销售订单" else data.get("purchase_no")
        if not archived or (archived.order_no if source.record_type == "销售订单" else archived.purchase_no) != original_no or archived.currency != data.get("currency") or archived.exchange_rate != Decimal(str(data.get("exchange_rate"))):
            raise ValidationError("历史合同原单或币种已变化。")
        party_name = archived.customer_name_snapshot if source.record_type == "销售订单" else archived.supplier_name_snapshot
        if party_name != (data.get("customer_name_snapshot") if source.record_type == "销售订单" else data.get("supplier_name_snapshot")):
            raise ValidationError("历史合同主体快照已变化。")
        if archived.payment_plans.exists() or archived.transactions.exists():
            raise ValidationError("历史合同已有资金计划或流水，不能重复承接。")
        mode = item.get("balance_mode")
        balance, plans, plan_ids = _plans(source, data, item, by_id, mode, evidence)
        lines = _line_records(source, by_id, remainder)
        if lines and source.record_type == "采购订单" and not archived.supplier.is_active:
            raise ValidationError("历史供应商已停用，不能建立正式采购接续草稿。")
        supplied_lines = item.get("line_options", [])
        if not isinstance(supplied_lines, list):
            raise ValidationError("订单明细映射格式无效。")
        options_by_line = {str(row.get("source_id")): row for row in supplied_lines if isinstance(row, dict)}
        if len(supplied_lines) != len(lines) or len(options_by_line) != len(lines) or set(options_by_line) != {str(line.pk) for line, _, _ in lines}:
            raise ValidationError("每条有剩余数量的订单明细都需要明确核对。")
        line_details = []
        targets = set()
        for line, row, quantity in lines:
            saved = source_line(line)
            parent_id = getattr(saved, "order_id", None) if source.record_type == "销售订单" else getattr(saved, "purchase_order_id", None)
            if not saved or parent_id != archived.pk:
                raise ValidationError("历史明细已变化，无法接续。")
            sku, link_version, link_status = link_state(line, saved)
            if not sku or link_status != "linked":
                raise ValidationError("历史商品尚未关联已核实的正式 SKU，无法接续。")
            if not sku.active or sku.unit != row.get("base_unit_snapshot") or saved.quantity != Decimal(str(row["quantity_base"])) or saved.unit_price != Decimal(str(row["unit_price"])):
                raise ValidationError("历史明细、SKU、单位或价格已变化，不能自动接续。")
            if not link_version and sku.sku != row.get("sku_code"):
                raise ValidationError("旧历史商品的 SKU 编码已变化，请先核实关联。")
            opt = options_by_line[str(line.pk)]
            trade_quantity = None
            if row.get("trade_quantity") not in (None, ""):
                factor = Decimal(str(row.get("trade_factor_snapshot") or "0"))
                if factor <= 0 or row.get("trade_unit_price") in (None, ""):
                    raise ValidationError("历史交易单位换算或价格不完整。")
                trade_quantity = quantity / factor
                if trade_quantity.quantize(Decimal("0.01")) != trade_quantity or (row.get("allow_fraction_snapshot") is False and trade_quantity != trade_quantity.to_integral_value()):
                    raise ValidationError("剩余数量无法按已核实的交易单位准确表达。")
            detail = {"source_id": line.pk, "sku_id": sku.pk, "sku_unit": sku.unit, "quantity": str(quantity), "trade_quantity": str(trade_quantity) if trade_quantity is not None else None,
                "archived_signature": _json_hash({"sku": sku.pk, "quantity": saved.quantity, "price": saved.unit_price, "trade_quantity": saved.trade_quantity, "trade_price": saved.trade_unit_price, "trade_snapshot": saved.trade_snapshot, "name": saved.display_name_snapshot, "description": saved.description_snapshot, "sales_model": saved.sales_model_snapshot})}
            if link_version:
                if not link_specification_is_current(
                    line, sku, row.get("base_unit_snapshot"), row.get("specification_snapshot"), link_version,
                ):
                    raise ValidationError("正式 SKU 的规格已变化，请重新核实历史商品关联。")
                detail["link_version"] = link_version
                detail["sku_specification"] = sku.specification
                detail["sku_parameters"] = sku.parameter_values
            if source.record_type == "销售订单":
                cost = _amount(opt.get("unit_cost"), places=4, digits=14)
                cost_currency = str(opt.get("cost_currency") or "").strip().upper()
                if not str(opt.get("cost_evidence") or "").strip() or len(cost_currency) != 3 or not cost_currency.isascii() or not cost_currency.isalpha():
                    raise ValidationError("销售接续明细须明确核实 SKU 成本、币种和依据。")
                detail.update({"unit_cost": str(cost), "cost_currency": cost_currency, "cost_verification": "current", "cost_evidence": str(opt["cost_evidence"]).strip()})
            else:
                supplier_id = opt.get("supplier_sku_id")
                supplier_sku = SupplierSKU.objects.filter(pk=supplier_id, sku=sku, supplier=archived.supplier, is_active=True).first() if supplier_id else None
                if supplier_id and not supplier_sku:
                    raise ValidationError("采购来源必须匹配当前供应商和 SKU 且处于启用状态。")
                if not supplier_sku and (SupplierSKU.objects.filter(sku=sku, supplier=archived.supplier, is_active=True).exists() or not str(opt.get("manual_reason") or "").strip()):
                    raise ValidationError("请明确选择已有供货档案；无档案时须填写手工来源依据。")
                target = opt.get("target")
                sales_source = opt.get("sales_source_id")
                if target not in {"inventory", "order"} or (target == "order") != bool(sales_source):
                    raise ValidationError("采购明细须明确选择库存或接续销售订单归属。")
                if target == "order":
                    candidate = by_id.get(int(sales_source))
                    if not candidate or candidate[0].record_type != "销售订单" or not any(
                        linked and state == "linked" and linked.pk == sku.pk
                        for sales_line, _, _ in _line_records(candidate[0], by_id, remainder)
                        if (original_line := source_line(sales_line)) is not None
                        for linked, _, state in [link_state(sales_line, original_line)]
                    ):
                        raise ValidationError("采购归属的销售订单或 SKU 不匹配。")
                targets.add((target, int(sales_source) if sales_source else None))
                detail.update({"supplier_sku_id": supplier_sku.pk if supplier_sku else None,
                    "supplier_signature": [supplier_sku.supplier_id, supplier_sku.sku_id, str(supplier_sku.moq), supplier_sku.is_active] if supplier_sku else None,
                    "manual_reason": str(opt.get("manual_reason") or "").strip(), "target": target, "sales_source_id": int(sales_source) if sales_source else None})
            line_details.append(detail)
        if len(targets) > 1:
            raise ValidationError("同一接续采购单的初始归属须一致；复杂分配请在采购草稿中使用正式成本分配。")
        adjustments = None
        if lines and source.record_type == "销售订单":
            shipping = _amount(item.get("remaining_shipping_fee"))
            discount = _amount(item.get("remaining_discount"))
            amount_evidence = str(item.get("amount_evidence") or "").strip()
            if not amount_evidence:
                raise ValidationError("须明确核实剩余运费、折扣及其依据。")
            merchandise = Decimal("0")
            for line in line_details:
                source_row = by_id[line["source_id"]][1]
                merchandise += (Decimal(line["trade_quantity"]) * Decimal(str(source_row["trade_unit_price"]))
                    if line["trade_quantity"] is not None else Decimal(line["quantity"]) * Decimal(str(source_row["unit_price"])))
            if discount > merchandise + shipping:
                raise ValidationError("剩余折扣不能超过剩余货值及运费。")
            adjustments = {"shipping": str(shipping), "discount": str(discount), "evidence": amount_evidence}
        if lines and source.record_type == "采购订单":
            no_costs = item.get("no_additional_costs") is True
            costs_pending = item.get("additional_costs_pending") is True
            if no_costs == costs_pending or not str(item.get("costs_evidence") or "").strip():
                raise ValidationError("请明确选择无额外公共费用，或在采购草稿中登记公共费用，并填写核实依据。")
            adjustments = {"no_additional_costs": no_costs, "additional_costs_pending": costs_pending, "evidence": str(item["costs_evidence"]).strip()}
        output.append({"source_id": source.pk, "record_type": source.record_type, "archived_id": archived.pk,
            "balance_mode": mode, "balance_amount": str(balance), "evidence_reference": evidence,
            "plan_source_ids": plan_ids, "plans": plans, "lines": line_details, "adjustments": adjustments})
    return sorted(output, key=lambda item: (item["record_type"] != "销售订单", item["source_id"]))


def _proposal_data(group, handoff, data, user):
    if not isinstance(data, dict) or set(data) != {"cutover_date", "reason", "contracts"}:
        raise ValidationError("请填写启用日期、核实依据及全部合同映射。")
    cutover = _date(data["cutover_date"])
    if date.fromisoformat(cutover) > timezone.localdate():
        raise ValidationError("启用日期不能晚于今天。")
    reason = str(data.get("reason") or "").strip()
    if not reason or len(reason) > 500:
        raise ValidationError("请填写不超过500字的接续核实依据。")
    by_id, remainder = _source_data(group, handoff)
    date_fields = {"销售订单": "order_date", "采购订单": "order_date", "履约记录": "event_date", "收付款流水": "transaction_date", "库存盘点": "count_date"}
    for record, row in by_id.values():
        field = date_fields.get(record.record_type)
        if field and row.get(field) and _date(str(row[field])) > cutover:
            raise ValidationError("存在晚于启用日期的历史事实，请核实时间边界。")
    if group.exported_at and group.exported_at.isoformat() > cutover:
        raise ValidationError("启用日期不能早于来源导出日期。")
    normalized = _snapshot(group, data["contracts"], by_id, remainder)
    if not normalized:
        raise ValidationError("关联组没有可接续的销售或采购合同。")
    return {"cutover_date": cutover, "reason": reason, "contracts": data["contracts"], "normalized": normalized,
            "sources_hash": _json_hash({str(pk): row for pk, (_record, row) in by_id.items()}),
            "remainder_hash": _json_hash(remainder), "maker_id": user.pk, "maker_kind": actor_snapshot(user)[2]}


@transaction.atomic
def propose(group_id, data, user):
    _access(user, "create")
    group, handoff = _locked(group_id)
    if handoff.status in {"drafts_created", "reversed"}:
        raise ValidationError("已建立接续单据，不能覆盖原接续记录。")
    proposal = _proposal_data(group, handoff, data, user)
    proposal["fingerprint"] = _json_hash(proposal)
    payload = dict(handoff.payload)
    if payload.get("operational_proposal") == proposal and handoff.status in {"pending_review", "approved"}:
        return handoff, True
    payload["operational_proposal"] = proposal
    payload.pop("operational_approval", None)
    handoff.payload, handoff.status = payload, "pending_review"
    handoff.save(update_fields=["payload", "status"])
    group.fulfillment_handoff_status = "pending_review"
    group.save(update_fields=["fulfillment_handoff_status", "updated_at"])
    _event(group.application, group, "operational_contract_proposed", user, {"fingerprint": proposal["fingerprint"], "reason": proposal["reason"]})
    return handoff, False


def _revalidate(group, handoff, user):
    proposal = handoff.payload.get("operational_proposal")
    if not proposal:
        raise ValidationError("请先保存业务接续申请。")
    request = {"cutover_date": proposal["cutover_date"], "reason": proposal["reason"], "contracts": proposal["contracts"]}
    maker = get_user_model().objects.filter(pk=proposal["maker_id"]).first()
    if maker is None:
        raise ValidationError("接续申请人不存在。")
    current = _proposal_data(group, handoff, request, maker)
    if _json_hash(current) != proposal["fingerprint"]:
        raise ValidationError("来源、余额、成本或主档已变化，请重新申请并复核。")
    return proposal


@transaction.atomic
def approve(group_id, note, user):
    _access(user, "update")
    group, handoff = _locked(group_id)
    if handoff.status not in {"pending_review", "approved"}:
        raise ValidationError("请先提交业务接续申请。")
    proposal = _revalidate(group, handoff, user)
    if proposal["maker_id"] == user.pk:
        raise ValidationError("申请人不能复核自己的接续申请。")
    if not isinstance(note, str) or not note.strip():
        raise ValidationError("请填写业务和余额复核依据。")
    if handoff.status == "approved":
        return handoff, True
    payload = dict(handoff.payload)
    payload["operational_approval"] = {"reviewer_id": user.pk, "reviewer_kind": actor_snapshot(user)[2], "note": note.strip(), "fingerprint": proposal["fingerprint"]}
    handoff.payload, handoff.status = payload, "approved"
    handoff.save(update_fields=["payload", "status"])
    group.fulfillment_handoff_status = "approved"
    group.save(update_fields=["fulfillment_handoff_status", "updated_at"])
    _event(group.application, group, "operational_contract_approved", user, payload["operational_approval"])
    return handoff, False


def _create_sales_draft(original, data, lines, by_id, number, cutover, adjustments):
    order = Order.objects.create(order_no=number, customer=original.customer, quote=None,
        customer_name_snapshot=original.customer_name_snapshot, customer_country_snapshot=original.customer_country_snapshot,
        customer_address_snapshot=original.customer_address_snapshot, customer_contact_name_snapshot=original.customer_contact_name_snapshot,
        customer_phone_snapshot=original.customer_phone_snapshot, customer_email_snapshot=original.customer_email_snapshot,
        order_date=cutover, status="draft", currency=original.currency, exchange_rate=original.exchange_rate,
        shipping_fee=adjustments["shipping"], discount=adjustments["discount"], notes=f"历史订单 {original.order_no} 的剩余履约接续；原合同及余额另行保留。")
    links = []
    for line in lines:
        source, row = by_id[line["source_id"]]
        old = source_line(source)
        trade_snapshot = old.trade_snapshot
        if line["trade_quantity"] is not None:
            trade_snapshot = {
                **trade_snapshot,
                "factor": str(row["trade_factor_snapshot"]),
                "allow_fraction": row["allow_fraction_snapshot"],
            }
        new = OrderItem(order=order, sku_id=line["sku_id"], quantity=line["quantity"], unit_price=old.unit_price,
            cost_price=line["unit_cost"], cost_currency_snapshot=line["cost_currency"], cost_verification_snapshot=line.get("cost_verification", "current"), sales_model_snapshot=old.sales_model_snapshot,
            display_name_snapshot=old.display_name_snapshot, description_snapshot=old.description_snapshot, unit_snapshot=old.unit_snapshot,
            trade_snapshot=trade_snapshot, trade_quantity=line["trade_quantity"], trade_unit_price=old.trade_unit_price if line["trade_quantity"] is not None else None,
            notes=f"接续历史明细 {source.source_record_id}"[:200])
        new.save(preserve_cost_snapshot=True)
        links.append({"source_id": source.pk, "archived_item_id": old.pk, "continuation_item_id": new.pk,
            "quantity": line["quantity"], "unit_cost": line["unit_cost"], "cost_verification": new.cost_verification_snapshot, "cost_evidence": line["cost_evidence"], "cost_currency": line["cost_currency"]})
    return order, links


def _create_purchase_draft(original, lines, by_id, number, cutover, sales_orders):
    target = lines[0] if lines else None
    sales_order = sales_orders.get(target["sales_source_id"]) if target and target["target"] == "order" else None
    if target and target["target"] == "order" and sales_order is None:
        raise ValidationError("采购归属的销售接续单不存在或没有剩余履约。")
    purchase = PurchaseOrder.objects.create(purchase_no=number, supplier=original.supplier, order=sales_order,
        supplier_name_snapshot=original.supplier_name_snapshot, supplier_address_snapshot=original.supplier_address_snapshot,
        supplier_contact_name_snapshot=original.supplier_contact_name_snapshot, supplier_phone_snapshot=original.supplier_phone_snapshot,
        supplier_email_snapshot=original.supplier_email_snapshot, order_date=cutover, status="draft", history_finance_mode=True,
        currency=original.currency, exchange_rate=original.exchange_rate, payment_terms_snapshot=[],
        notes=f"历史采购单 {original.purchase_no} 的剩余履约接续；原合同及余额另行保留。")
    links = []
    for line in lines:
        source, _row = by_id[line["source_id"]]
        old = source_line(source)
        new = PurchaseOrderItem.objects.create(purchase_order=purchase, sku_id=line["sku_id"], supplier_sku_id=line["supplier_sku_id"],
            quantity=line["quantity"], unit_price=old.unit_price,
            sales_model_snapshot=old.sales_model_snapshot, display_name_snapshot=old.display_name_snapshot,
            description_snapshot=old.description_snapshot, supplier_name_snapshot=_row.get("supplier_name_snapshot") or "",
            supplier_model_snapshot=_row.get("supplier_model_snapshot") or "", supplier_sku_code_snapshot=_row.get("supplier_sku_code_snapshot") or "",
            trade_snapshot=old.trade_snapshot, trade_quantity=line["trade_quantity"], trade_unit_price=old.trade_unit_price if line["trade_quantity"] is not None else None)
        links.append({"source_id": source.pk, "archived_item_id": old.pk, "continuation_item_id": new.pk,
            "quantity": line["quantity"], "supplier_sku_id": line["supplier_sku_id"], "manual_reason": line["manual_reason"],
            "target": line["target"], "sales_source_id": line["sales_source_id"]})
    return purchase, links


@transaction.atomic
def execute(group_id, user):
    _access(user, "update")
    group, handoff = _locked(group_id)
    if handoff.status == "drafts_created":
        return list(group.operational_contracts.values_list("pk", flat=True)), True
    if handoff.status != "approved":
        raise ValidationError("业务接续须经另一名授权人员复核。")
    proposal = _revalidate(group, handoff, user)
    approval = handoff.payload.get("operational_approval") or {}
    if approval.get("fingerprint") != proposal["fingerprint"]:
        raise ValidationError("接续复核与当前申请不一致。")
    # Allocate numbers before SKU locks, matching ordinary document creation's lock order.
    numbers = {item["source_id"]: (allocate_order_no() if item["record_type"] == "销售订单" else allocate_purchase_no())
               for item in proposal["normalized"] if item["lines"]}
    list(group.source_records.select_for_update().order_by("pk").values_list("pk", flat=True))
    sales_ids = sorted(item["archived_id"] for item in proposal["normalized"] if item["record_type"] == "销售订单")
    purchase_ids = sorted(item["archived_id"] for item in proposal["normalized"] if item["record_type"] == "采购订单")
    list(Order.objects.select_for_update().filter(pk__in=sales_ids).order_by("pk"))
    purchases = list(PurchaseOrder.objects.select_for_update().filter(pk__in=purchase_ids).order_by("pk"))
    list(Supplier.objects.select_for_update().filter(pk__in=sorted({item.supplier_id for item in purchases})).order_by("pk"))
    sku_ids = sorted({line["sku_id"] for item in proposal["normalized"] for line in item["lines"]})
    list(SKU.objects.select_for_update().filter(pk__in=sku_ids).order_by("pk"))
    proposal = _revalidate(group, handoff, user)
    by_id, _remainder = _source_data(group, handoff)
    sales_orders, created_links, plan_ids = {}, [], []
    for item in proposal["normalized"]:
        source, data = by_id[item["source_id"]]
        original = Order.objects.get(pk=item["archived_id"]) if item["record_type"] == "销售订单" else PurchaseOrder.objects.get(pk=item["archived_id"])
        continuation, lines = None, []
        if item["lines"] and item["record_type"] == "销售订单":
            continuation, lines = _create_sales_draft(original, data, item["lines"], by_id, numbers[source.pk], proposal["cutover_date"], item["adjustments"])
            sales_orders[source.pk] = continuation
        elif item["lines"]:
            continuation, lines = _create_purchase_draft(original, item["lines"], by_id, numbers[source.pk], proposal["cutover_date"], sales_orders)
        sales = item["record_type"] == "销售订单"
        link = HistoryOperationalContract.objects.create(group=group, source=source,
            archived_order=original if sales else None, archived_purchase=None if sales else original,
            settlement_order=original if sales else None, settlement_purchase=None if sales else original,
            continuation_order=continuation if sales else None, continuation_purchase=None if sales else continuation,
            cutover_date=proposal["cutover_date"], balance_mode=item["balance_mode"], opening_balance=item["balance_amount"],
            currency=original.currency, evidence_reference=item["evidence_reference"], source_snapshot=source.source_snapshot,
            line_links=lines, balance_snapshot={"mode": item["balance_mode"], "plans": item["plans"], "plan_source_ids": item["plan_source_ids"]},
            approval_snapshot={"proposal_fingerprint": proposal["fingerprint"], "approval": approval, "maker_id": proposal["maker_id"], "maker_kind": proposal["maker_kind"], "adjustments": item["adjustments"]})
        created_links.append(link.pk)
        plan_ids.extend(plan.pk for plan in install_history_opening_plans(original, user))
    handoff.status = group.fulfillment_handoff_status = "drafts_created"
    handoff.save(update_fields=["status"])
    group.save(update_fields=["fulfillment_handoff_status", "updated_at"])
    _event(group.application, group, "operational_contracts_created", user,
        {"contract_links": created_links, "opening_plan_ids": plan_ids, "fingerprint": proposal["fingerprint"]})
    return created_links, False


@transaction.atomic
def reverse(group_id, reason, user):
    """Cancel unused continuation drafts and opening plans without deleting evidence."""
    from crm.services import finance_closeout
    from crm.services.order_lifecycle import cancel_order
    from crm.services.purchase_lifecycle import cancel_purchase_order

    _access(user, "update")
    group, handoff = _locked(group_id)
    if handoff.status == "reversed":
        return True
    if handoff.status != "drafts_created" or not isinstance(reason, str) or not reason.strip():
        raise ValidationError("只有已建立的接续草稿可以填写原因后撤销。")
    links = list(group.operational_contracts.select_related("archived_order", "archived_purchase", "continuation_order", "continuation_purchase").order_by("pk"))
    if not links:
        raise ValidationError("接续关联缺失，不能撤销。")
    purchase_ids = sorted({pk for link in links for pk in (link.archived_purchase_id, link.continuation_purchase_id) if pk})
    order_ids = sorted({pk for link in links for pk in (link.archived_order_id, link.continuation_order_id) if pk})
    list(PurchaseOrder.objects.select_for_update().filter(pk__in=purchase_ids).order_by("pk"))
    list(Order.objects.select_for_update().filter(pk__in=order_ids).order_by("pk"))
    for link in links:
        continuation = link.continuation_order or link.continuation_purchase
        original = link.archived_order or link.archived_purchase
        if continuation:
            continuation.refresh_from_db()
        if continuation and continuation.status != "draft":
            raise ValidationError("接续单已进入正式业务，不能直接撤销；请走审计更正。")
        if original.transactions.exists() or original.payment_plans.filter(settled_amount__gt=0).exists():
            raise ValidationError("未结计划已有后续资金业务，不能直接撤销；请走审计更正。")
        for plan in original.payment_plans.select_for_update():
            if plan.advance_allocations.filter(is_active=True).exists() or plan.status != "open":
                raise ValidationError("未结计划状态已变化，不能直接撤销。")
    # Purchases can refer to sales drafts, so cancel purchases first.
    for link in links:
        if link.continuation_purchase:
            cancel_purchase_order(link.continuation_purchase, reason.strip())
    for link in links:
        if link.continuation_order:
            cancel_order(link.continuation_order, reason.strip())
        original = link.archived_order or link.archived_purchase
        for plan in original.payment_plans.select_for_update():
            plan.status = "cancelled"
            plan.save(update_fields=["status", "updated_at"])
            finance_closeout.audit(plan, user, "撤销历史未结接续")
    handoff.status = group.fulfillment_handoff_status = "reversed"
    handoff.save(update_fields=["status"])
    group.save(update_fields=["fulfillment_handoff_status", "updated_at"])
    _event(group.application, group, "operational_contracts_reversed", user,
        {"contract_links": [link.pk for link in links], "reason": reason.strip()})
    return False
