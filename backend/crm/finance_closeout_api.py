"""Private, permission-controlled account-ledger workflows."""
import csv
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.db.models import Q, Sum
from django.http import FileResponse, HttpResponse
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.response import Response

from .models import (FinanceAccount, FinanceAccountMapping, FinanceClassification, FinanceFact,
    FinanceHistoricalTransfer, FinanceInstruction, FinanceReview, FinanceTransferMatch, FinanceVoucher, Order, RmbCashEvent)
from .permissions import user_can
from .reporting import safe_csv
from .services import finance_closeout as ledger
from .upload_handlers import CsvImportSizeLimitUploadHandler


class VoucherTooLarge(APIException):
    status_code = 413
    default_detail = "凭证超过10MB，未保存文件。"


class FinanceVoucherUploadHandler(CsvImportSizeLimitUploadHandler):
    def __init__(self, request):
        super().__init__(request)
        self.enabled = True
        self.limit = 10 * 1024 * 1024


def actor_name(actor):
    if not isinstance(actor, dict) or actor.get("kind") != "authenticated_user":
        return "开发身份（非正式审批人）" if actor else "尚未复核"
    user = get_user_model().objects.filter(pk=actor.get("user_id")).first()
    return (user.get_full_name() or user.get_username()) if user else "已停用或不存在的账号"


def fact_label(fact):
    reference = "手工登记" if fact.source_system == "manual" and fact.source_key == fact.instruction.request_key else fact.source_key
    return f"{fact.actual_date} · {fact.account.name} · {'流入' if fact.direction == 'income' else '流出'} ¥{fact.amount} · {reference}"


def bank_label(event, user):
    if not ledger.cash.visible(event, user):
        return "银行记录不可查看"
    return f"{event.bank_date} · {event.rmb_account} · {'流入' if event.direction == 'income' else '流出'} ¥{event.bank_net_amount} · {event.bank_reference or '银行参考号未提供'} · {event.event_no}"


def instruction_data(obj):
    return {"id": obj.pk, "kind": obj.kind, "status": obj.status, "payload": obj.payload,
        "created_actor": obj.created_actor, "approved_actor": obj.approved_actor,
        "created_actor_name": actor_name(obj.created_actor), "approved_actor_name": actor_name(obj.approved_actor),
        "created_at": obj.created_at, "approved_at": obj.approved_at, "replaces": obj.replaces_id}


def fact_data(obj, matched=None):
    superseded = ledger.corrected_ids()[0]
    if matched is None:
        matched = set(superseded)
        for out, inc in FinanceTransferMatch.objects.values_list("outgoing_id", "incoming_id"):
            matched.update((out, inc))
        for out, inc in FinanceHistoricalTransfer.objects.values_list("outgoing_fact_id", "incoming_fact_id"):
            matched.update(value for value in (out, inc) if value is not None)
    classification = obj.classifications.order_by("pk").last()
    return {"id": obj.pk, "account": obj.account_id, "account_name": obj.account.name,
        "account_type": obj.account.account_type, "instruction": obj.instruction_id,
        "actual_date": obj.actual_date, "amount": str(obj.amount), "direction": obj.direction,
        "nature": classification.nature if classification else obj.nature, "kind": obj.kind,
        "refund_excess_amount": str(obj.excess_amount),
        "unallocated_amount": str(obj.amount - sum((Decimal(a["amount"]) for a in obj.instruction.payload["allocations"]), Decimal("0"))) if obj.kind == "refund_payment" else "0.00",
        "voucher": obj.voucher_id, "voucher_sha256": obj.voucher.sha256,
        "source_system": obj.source_system, "source_key": obj.source_key, "parent": obj.parent_id, "legacy_parent": obj.legacy_parent_id,
        "source_reference": "" if obj.source_system == "manual" and obj.source_key == obj.instruction.request_key else obj.source_key,
        "actor": obj.actor, "created_at": obj.created_at,
        "company_flow_included": obj.kind != "opening" and obj.amount != 0 and obj.pk not in (matched or set()),
        "flow_exclusion_reason": "opening" if obj.kind == "opening" else "superseded" if obj.pk in superseded else "zero_correction" if obj.amount == 0 else "internal_principal" if obj.pk in matched else "",
        "classifications": [{"nature": c.nature, "reason": c.reason, "actor": c.actor, "created_at": c.created_at} for c in obj.classifications.order_by("pk")]}


def flow_rows(user, start, end):
    ledger.access(user)
    matched = set()
    matched.update(ledger.corrected_ids()[0])
    for out, inc in FinanceTransferMatch.objects.values_list("outgoing_id", "incoming_id"):
        matched.update((out, inc))
    for out, inc in FinanceHistoricalTransfer.objects.values_list("outgoing_fact_id", "incoming_fact_id"):
        matched.update(value for value in (out, inc) if value is not None)
    return [fact_data(f, matched) for f in FinanceFact.objects.select_related("account", "voucher").filter(actual_date__range=(start, end)).order_by("actual_date", "pk")]


class FinanceCloseoutViewSet(viewsets.ViewSet):
    permission_action_map = {
        "preview": "view", "accounts": "create", "vouchers": "create", "instructions": "create",
    }

    @property
    def permission_module(self):
        request = getattr(self, "request", None)
        # Match the existing CSV contract (finance OR reports export). The
        # ordinary ledger.access() checks still require global finance and
        # transaction read scope before any data is returned.
        if (getattr(self, "action", None) == "facts" and request is not None
                and request.query_params.get("export") == "csv"
                and not user_can(request.user, "finance", "export")
                and user_can(request.user, "reports", "export")):
            return "reports"
        return "finance"

    def initialize_request(self, request, *args, **kwargs):
        path = request.path.rstrip("/")
        suffix = kwargs.get("format")
        if suffix and path.endswith("." + suffix):
            path = path[:-(len(suffix) + 1)]
        if request.method == "POST" and path.endswith("/finance-ledger/vouchers"):
            request.upload_handlers.insert(0, FinanceVoucherUploadHandler(request))
        return super().initialize_request(request, *args, **kwargs)

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.method == "POST" and not isinstance(request.data, dict):
            raise ValidationError("资金操作需要对象格式。")
        operation = "view" if request.method in {"GET", "HEAD", "OPTIONS"} or self.action == "preview" else "create" if self.action in {"accounts", "vouchers", "instructions"} else "update"
        ledger.access(request.user, operation)

    def handle_exception(self, exc):
        if isinstance(exc, ObjectDoesNotExist):
            exc = NotFound("资金记录不存在。")
        elif isinstance(exc, IntegrityError):
            exc = ledger.cash.CashConflict("资金记录冲突，请按原请求核对。")
        return super().handle_exception(exc)

    def list(self, request, format=None):
        end = ledger.iso(request.query_params.get("date_to") or timezone.localdate().isoformat())
        accounts = []
        for obj in FinanceAccount.objects.order_by("pk"):
            calculated, _ = ledger.balance(obj, end, request.user)
            accounts.append({"id": obj.pk, "code": obj.code, "name": obj.name,
                "account_type": obj.account_type, "ownership": obj.ownership, "ownership_reason": obj.ownership_reason,
                "currency": obj.currency, "balance": str(calculated) if calculated is not None else None,
                "is_active": obj.is_active})
        reviews = []
        for r in FinanceReview.objects.select_related("account").order_by("pk"):
            _, fingerprint = ledger.balance(r.account, r.date_to, request.user)
            reviews.append({"id": r.pk, "account": r.account_id, "date_from": r.date_from, "date_to": r.date_to,
                "statement_balance": str(r.statement_balance), "calculated_balance": str(r.calculated_balance),
                "difference": str(r.difference), "voucher": r.voucher_id, "reason": r.reason,
                "actor": r.actor, "created_at": r.created_at,
                "actor_name": actor_name(r.actor),
                "status": "needs_review" if fingerprint != r.fingerprint else "completed" if r.completed else "difference_pending"})
        transfers = [{"id": row.pk, "outgoing_id": row.outgoing_id, "incoming_id": row.incoming_id, "reason": row.reason, "actor": row.actor,
            "outgoing_label": fact_label(row.outgoing), "incoming_label": fact_label(row.incoming)} for row in FinanceTransferMatch.objects.select_related("outgoing__account", "outgoing__instruction", "incoming__account", "incoming__instruction")]
        historical_transfers = []
        for row in FinanceHistoricalTransfer.objects.select_related("outgoing_fact__account", "outgoing_fact__instruction", "incoming_fact__account", "incoming_fact__instruction", "outgoing_legacy", "incoming_legacy"):
            historical_transfers.append({"id": row.pk, "reason": row.reason, "actor": row.actor,
                "outgoing_fact_id": row.outgoing_fact_id, "incoming_fact_id": row.incoming_fact_id,
                "outgoing_legacy_id": row.outgoing_legacy_id, "incoming_legacy_id": row.incoming_legacy_id,
                "outgoing_voucher_id": row.outgoing_voucher_id, "incoming_voucher_id": row.incoming_voucher_id,
                "outgoing_label": bank_label(row.outgoing_legacy, request.user) if row.outgoing_legacy_id else fact_label(row.outgoing_fact),
                "incoming_label": bank_label(row.incoming_legacy, request.user) if row.incoming_legacy_id else fact_label(row.incoming_fact)})
        mapped_codes = set(FinanceAccountMapping.objects.values_list("legacy_code", flat=True))
        legacy_codes = {event.rmb_account for event in RmbCashEvent.objects.order_by("pk") if event.rmb_account not in mapped_codes and ledger.cash.visible(event, request.user)}
        legacy_names = {account.code: account.name for account in FinanceAccount.objects.filter(code__in=legacy_codes)}
        legacy_accounts = [{"code": code, "name": legacy_names.get(code) or code} for code in sorted(legacy_codes)]
        return Response({"accounts": accounts, "instructions": [instruction_data(i) for i in FinanceInstruction.objects.order_by("-pk")],
            "vouchers": [{"id": v.pk, "name": v.original_name, "sha256": v.sha256, "size": v.size} for v in FinanceVoucher.objects.filter(scope="account").order_by("-pk")],
            "reviews": reviews, "mappings": list(FinanceAccountMapping.objects.values("id", "legacy_code", "account_id", "reason", "actor")),
            "transfers": transfers, "historical_transfers": historical_transfers, "legacy_accounts": legacy_accounts})

    @action(detail=False, methods=["post"])
    def accounts(self, request, format=None):
        obj = ledger.create_account(request.data, request.user)
        return Response({"id": obj.pk}, status=201)

    @action(detail=False, methods=["post"])
    def verify_account(self, request, format=None):
        obj = ledger.verify_account(request.data, request.user)
        return Response({"id": obj.pk, "ownership": obj.ownership})

    @action(detail=False, methods=["post"])
    def mappings(self, request, format=None):
        obj = ledger.map_account(request.data, request.user)
        return Response({"id": obj.pk}, status=201)

    @action(detail=False, methods=["post"])
    def vouchers(self, request, format=None):
        files = request.FILES
        if getattr(request._request, "_csv_import_upload_limit_exceeded", None):
            raise VoucherTooLarge()
        if set(files) != {"file"} or len(files.getlist("file")) != 1:
            raise ValidationError("每次只上传一份凭证。")
        obj = ledger.upload(files.get("file"), request.user)
        return Response({"id": obj.pk, "sha256": obj.sha256, "size": obj.size}, status=201)

    @action(detail=False, methods=["get"], url_path="voucher-download")
    def voucher_download(self, request, format=None):
        obj = ledger.voucher(request.query_params.get("id"))
        response = FileResponse(obj.file.open("rb"), as_attachment=True, filename=obj.original_name, content_type="application/octet-stream")
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response

    @action(detail=False, methods=["post"])
    def preview(self, request, format=None):
        p = ledger.normalize(request.data, request.user)
        return Response({"payload": p, "duplicate_candidates": ledger.duplicate_candidates(p, request.user), "written": False})

    @action(detail=False, methods=["get"])
    def choices(self, request, format=None):
        """Search by business references; identifiers stay inside option values."""
        kind = request.query_params.get("type", "")
        query = request.query_params.get("q", "").strip()[:100]
        direction = request.query_params.get("direction", "")
        if direction not in {"", "income", "expense"}:
            raise ValidationError("资金方向无效。")
        items = []
        if kind in {"fact", "transfer_fact", "transfer_any"}:
            facts = FinanceFact.objects.select_related("account", "instruction").order_by("-actual_date", "-pk")
            if direction:
                facts = facts.filter(direction=direction)
            if query:
                facts = facts.filter(Q(source_key__icontains=query) | Q(account__name__icontains=query))
            for fact in facts[:30]:
                label = fact_label(fact)
                items.append({"value": f"fact:{fact.pk}" if kind == "transfer_any" else fact.pk, "label": label})
        if kind in {"event", "transfer_any"}:
            events = RmbCashEvent.objects.filter(status="confirmed").order_by("-bank_date", "-pk")
            if direction:
                events = events.filter(direction=direction)
            if query:
                events = events.filter(Q(event_no__icontains=query) | Q(bank_reference__icontains=query) | Q(rmb_account__icontains=query))
            for event in events[:100]:
                if ledger.cash.visible(event, request.user):
                    label = bank_label(event, request.user)
                    items.append({"value": f"legacy:{event.pk}" if kind == "transfer_any" else event.pk, "label": label})
                    if len(items) >= 60:
                        break
        if kind == "order":
            orders = Order.objects.select_related("customer").order_by("-order_date", "-pk")
            if query:
                orders = orders.filter(Q(order_no__icontains=query) | Q(customer__name__icontains=query))
            for order in orders[:30]:
                items.append({"value": order.pk, "label": f"{order.order_no} · {order.order_date} · {order.customer.name} · {order.currency} · {order.get_status_display()}"})
        if kind in {"approval", "replacement"}:
            instructions = FinanceInstruction.objects.order_by("-created_at", "-pk")
            instructions = instructions.filter(kind="refund_approval", status="approved") if kind == "approval" else instructions.filter(status__in=("cancelled", "failed"))
            for obj in instructions[:100]:
                p = obj.payload
                reference = "手工登记" if p.get("source_system") == "manual" and p.get("source_key") == obj.request_key else p.get("source_key", "")
                label = f"{reference} · {p.get('actual_date', '')} · ¥{p.get('amount', '')} · {obj.reason}"
                if not query or query.lower() in label.lower():
                    items.append({"value": obj.pk, "label": label})
                    if len(items) >= 30:
                        break
        if kind not in {"fact", "transfer_fact", "transfer_any", "event", "order", "approval", "replacement"}:
            raise ValidationError("选择类型无效。")
        return Response({"items": items})

    @action(detail=False, methods=["get"], url_path="bank-return-options")
    def bank_return_options(self, request, format=None):
        from .finance_scope import scope_plan_queryset
        from .models import AdvanceAllocation, FinanceBankFactMatch, FinanceBankReturnAllocation, PaymentPlan
        event_id, fact_id = request.query_params.get("event"), request.query_params.get("fact")
        if bool(event_id) == bool(fact_id):
            raise ValidationError("请选择一条原银行记录。")
        if fact_id:
            fact = FinanceFact.objects.get(pk=ledger.pk(fact_id))
            match = FinanceBankFactMatch.objects.filter(fact=fact).select_related("event").first()
            event = match.event if match else None
        else:
            event = ledger.cash.get_event(request.user, pk=ledger.pk(event_id))
        if event is None:
            return Response({"supported": False, "reason": "原账户事实没有关联银行来源；请先核实来源。", "items": []})
        if event.status != "confirmed" or not ledger.cash.visible(event, request.user):
            raise NotFound("原银行记录不存在或不可访问。")
        if event.kind != "cny_direct" or event.currency != "CNY":
            return Response({"supported": False, "reason": "外币结汇退回的原币关系待核实，不能直接按人民币恢复订单。", "items": []})
        items = []
        for allocation in event.sources.select_related("source__plan__order", "source__plan__purchase_order").order_by("source_id"):
            source = allocation.source
            if not ledger.cash.source_visible(source, request.user):
                continue
            returned = FinanceBankReturnAllocation.objects.filter(source=source).filter(
                Q(fact__legacy_parent=event) | Q(fact__parent__bank_event_match__event=event)).aggregate(total=Sum("amount"))["total"] or Decimal("0")
            event_remaining = max(allocation.amount - returned, Decimal("0"))
            plans = {row.plan_id: row.plan for row in AdvanceAllocation.objects.filter(advance=source, is_active=True).select_related("plan__order", "plan__purchase_order")}
            if source.plan_id:
                plans[source.plan_id] = source.plan
            visible = set(scope_plan_queryset(PaymentPlan.objects.filter(pk__in=plans), request.user).values_list("pk", flat=True)) if plans else set()
            for plan_id, plan in plans.items():
                if plan_id not in visible:
                    continue
                paid = sum((row.cash_amount if row.cash_amount is not None else row.amount for row in AdvanceAllocation.objects.filter(advance=source, plan=plan, is_active=True)), Decimal("0"))
                if source.plan_id == plan_id:
                    paid += source.amount
                refunded = source.attributed_refunds.filter(refund__status="confirmed", refund__plan=plan).aggregate(total=Sum("refund__amount"))["total"] or Decimal("0")
                already = source.bank_return_allocations.filter(plan=plan).aggregate(total=Sum("amount"))["total"] or Decimal("0")
                remaining = min(event_remaining, max(paid - refunded - already, Decimal("0")), plan.settled_amount)
                if remaining > 0:
                    contract = plan.order.order_no if plan.order_id else plan.purchase_order.purchase_no
                    items.append({"source": source.pk, "plan": plan.pk, "remaining": str(remaining), "label": f"{source.transaction_no} · {contract} · 尚可退回 CNY {remaining}"})
            unallocated = min(event_remaining, source.unallocated_cash_amount if not source.plan_id else Decimal("0"))
            if unallocated > 0:
                items.append({"source": source.pk, "plan": None, "remaining": str(unallocated), "label": f"{source.transaction_no} · 未分配现金 · 尚可退回 CNY {unallocated}"})
        return Response({"supported": True, "items": items})

    @action(detail=False, methods=["post"])
    def instructions(self, request, format=None):
        obj, created = ledger.submit(request.data, request.user)
        return Response(instruction_data(obj), status=201 if created else 200)

    @action(detail=False, methods=["post"])
    def approve(self, request, format=None):
        return Response(instruction_data(ledger.approve(request.data.get("id"), request.user)))

    @action(detail=False, methods=["post"])
    def cancel(self, request, format=None):
        return Response(instruction_data(ledger.cancel(request.data.get("id"), request.user, request.data.get("reason"))))

    @action(detail=False, methods=["post"])
    def fail(self, request, format=None):
        return Response(instruction_data(ledger.fail(request.data.get("id"), request.user, request.data.get("reason"), request.data.get("no_debit_confirmed"))))

    @action(detail=False, methods=["post"], url_path="post", url_name="post")
    def execute(self, request, format=None):
        obj = ledger.post(request.data.get("id"), request.user, voucher_checked=request.data.get("voucher_checked"))
        return Response(fact_data(obj))

    @action(detail=False, methods=["post"])
    def transfers(self, request, format=None):
        historical = any(":" in str(request.data.get(key, "")) for key in ("outgoing", "incoming"))
        obj = ledger.match_historical_transfer(request.data, request.user) if historical else ledger.match_transfer(request.data, request.user)
        return Response({"id": obj.pk}, status=201)

    @action(detail=False, methods=["post"])
    def classifications(self, request, format=None):
        obj = ledger.classify(request.data, request.user)
        return Response({"id": obj.pk}, status=201)

    @action(detail=False, methods=["post"])
    def reviews(self, request, format=None):
        obj = ledger.reconcile(request.data, request.user)
        return Response({"id": obj.pk, "difference": str(obj.difference)}, status=201)

    @action(detail=False, methods=["get"])
    def fact_detail(self, request, format=None):
        return Response(fact_data(FinanceFact.objects.select_related("account", "voucher").get(pk=ledger.pk(request.query_params.get("id")))))

    @action(detail=False, methods=["get"])
    def facts(self, request, format=None):
        start, end = ledger.iso(request.query_params.get("date_from", "1900-01-01")), ledger.iso(request.query_params.get("date_to", "2099-12-31"))
        if start > end:
            raise ledger.ValidationError("日期范围无效。")
        rows = flow_rows(request.user, start, end)
        total = {"inflow": Decimal("0"), "outflow": Decimal("0")}
        for row in rows:
            if row["company_flow_included"]:
                total["inflow" if row["direction"] == "income" else "outflow"] += Decimal(row["amount"])
        total["net"] = total["inflow"] - total["outflow"]
        if request.query_params.get("export") == "csv":
            if not (user_can(request.user, "finance", "export") or user_can(request.user, "reports", "export")):
                raise ledger.PermissionDenied("没有资金导出权限。")
            response = HttpResponse(content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = 'attachment; filename="account-cash-facts.csv"'
            response.write("\ufeff")
            writer = csv.writer(response)
            keys = ["id", "account_name", "account_type", "actual_date", "kind", "nature", "direction", "amount", "refund_excess_amount", "unallocated_amount", "company_flow_included", "source_system", "source_key", "voucher_sha256"]
            writer.writerow(keys)
            for row in rows:
                writer.writerow([safe_csv(row[k]) for k in keys])
            return response
        return Response({"basis": "verified_account_cash_v1", "facts": rows, "totals": {k: str(v) for k, v in total.items()},
            "note": "仅已核实自有账户事实；基准不计流入，已核实内部本金不计公司毛流量，账户明细保留实际变动。"})
