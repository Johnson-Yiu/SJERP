"""Private, permission-controlled account-ledger workflows."""
import csv
from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.http import FileResponse, HttpResponse
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.response import Response

from .models import (FinanceAccount, FinanceAccountMapping, FinanceClassification, FinanceFact,
    FinanceHistoricalTransfer, FinanceInstruction, FinanceReview, FinanceTransferMatch, FinanceVoucher)
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


def instruction_data(obj):
    return {"id": obj.pk, "kind": obj.kind, "status": obj.status, "payload": obj.payload,
        "created_actor": obj.created_actor, "approved_actor": obj.approved_actor,
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
    def initialize_request(self, request, *args, **kwargs):
        if request.method == "POST" and request.path.rstrip("/").endswith("/finance-ledger/vouchers"):
            request.upload_handlers.insert(0, FinanceVoucherUploadHandler(request))
        return super().initialize_request(request, *args, **kwargs)

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        operation = "view" if request.method in {"GET", "HEAD", "OPTIONS"} or self.action == "preview" else "create" if self.action in {"accounts", "vouchers", "instructions"} else "update"
        ledger.access(request.user, operation)

    def handle_exception(self, exc):
        if isinstance(exc, ObjectDoesNotExist):
            exc = NotFound("资金记录不存在。")
        elif isinstance(exc, IntegrityError):
            exc = ledger.cash.CashConflict("资金记录冲突，请按原请求核对。")
        return super().handle_exception(exc)

    def list(self, request):
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
                "status": "needs_review" if fingerprint != r.fingerprint else "completed" if r.completed else "difference_pending"})
        return Response({"accounts": accounts, "instructions": [instruction_data(i) for i in FinanceInstruction.objects.order_by("-pk")],
            "vouchers": [{"id": v.pk, "name": v.original_name, "sha256": v.sha256, "size": v.size} for v in FinanceVoucher.objects.filter(scope="account").order_by("-pk")],
            "reviews": reviews, "mappings": list(FinanceAccountMapping.objects.values("id", "legacy_code", "account_id", "reason", "actor")),
            "transfers": list(FinanceTransferMatch.objects.values("id", "outgoing_id", "incoming_id", "reason", "actor")),
            "historical_transfers": list(FinanceHistoricalTransfer.objects.values("id", "outgoing_fact_id", "incoming_fact_id", "outgoing_legacy_id", "incoming_legacy_id", "outgoing_voucher_id", "incoming_voucher_id", "reason", "actor"))})

    @action(detail=False, methods=["post"])
    def accounts(self, request):
        obj = ledger.create_account(request.data, request.user)
        return Response({"id": obj.pk}, status=201)

    @action(detail=False, methods=["post"])
    def verify_account(self, request):
        obj = ledger.verify_account(request.data, request.user)
        return Response({"id": obj.pk, "ownership": obj.ownership})

    @action(detail=False, methods=["post"])
    def mappings(self, request):
        obj = ledger.map_account(request.data, request.user)
        return Response({"id": obj.pk}, status=201)

    @action(detail=False, methods=["post"])
    def vouchers(self, request):
        files = request.FILES
        if getattr(request._request, "_csv_import_upload_limit_exceeded", None):
            raise VoucherTooLarge()
        if set(files) != {"file"} or len(files.getlist("file")) != 1:
            raise ValidationError("每次只上传一份凭证。")
        obj = ledger.upload(files.get("file"), request.user)
        return Response({"id": obj.pk, "sha256": obj.sha256, "size": obj.size}, status=201)

    @action(detail=False, methods=["get"], url_path="voucher-download")
    def voucher_download(self, request):
        obj = ledger.voucher(request.query_params.get("id"))
        response = FileResponse(obj.file.open("rb"), as_attachment=True, filename=obj.original_name, content_type="application/octet-stream")
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response

    @action(detail=False, methods=["post"])
    def preview(self, request):
        p = ledger.normalize(request.data, request.user)
        return Response({"payload": p, "duplicate_candidates": ledger.duplicate_candidates(p, request.user), "written": False})

    @action(detail=False, methods=["post"])
    def instructions(self, request):
        obj, created = ledger.submit(request.data, request.user)
        return Response(instruction_data(obj), status=201 if created else 200)

    @action(detail=False, methods=["post"])
    def approve(self, request):
        return Response(instruction_data(ledger.approve(request.data.get("id"), request.user)))

    @action(detail=False, methods=["post"])
    def cancel(self, request):
        return Response(instruction_data(ledger.cancel(request.data.get("id"), request.user, request.data.get("reason"))))

    @action(detail=False, methods=["post"])
    def fail(self, request):
        return Response(instruction_data(ledger.fail(request.data.get("id"), request.user, request.data.get("reason"), request.data.get("no_debit_confirmed"))))

    @action(detail=False, methods=["post"], url_path="post", url_name="post")
    def execute(self, request):
        obj = ledger.post(request.data.get("id"), request.user, voucher_checked=request.data.get("voucher_checked"))
        return Response(fact_data(obj))

    @action(detail=False, methods=["post"])
    def transfers(self, request):
        historical = any(":" in str(request.data.get(key, "")) for key in ("outgoing", "incoming"))
        obj = ledger.match_historical_transfer(request.data, request.user) if historical else ledger.match_transfer(request.data, request.user)
        return Response({"id": obj.pk}, status=201)

    @action(detail=False, methods=["post"])
    def classifications(self, request):
        obj = ledger.classify(request.data, request.user)
        return Response({"id": obj.pk}, status=201)

    @action(detail=False, methods=["post"])
    def reviews(self, request):
        obj = ledger.reconcile(request.data, request.user)
        return Response({"id": obj.pk, "difference": str(obj.difference)}, status=201)

    @action(detail=False, methods=["get"])
    def fact_detail(self, request):
        return Response(fact_data(FinanceFact.objects.select_related("account", "voucher").get(pk=ledger.pk(request.query_params.get("id")))))

    @action(detail=False, methods=["get"])
    def facts(self, request):
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
