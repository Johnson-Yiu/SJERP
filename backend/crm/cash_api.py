"""Minimal bank-fact API. No legacy dashboard/report source changes."""
from decimal import Decimal, ROUND_HALF_UP

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from .models import FinanceBankVoucherBinding, RmbCashEvent, Transaction
from .services import cash_events as cash


class CashEventPermission(BasePermission):
    def has_permission(self, request, view):
        operation = "create" if view.action == "create" else "update" if view.action in {"confirm", "cancel"} else "view"
        cash.access(request.user, operation)
        return True


def event_data(event):
    allocations = list(event.sources.order_by("source_id"))
    reference = sum((a.amount * Decimal(a.source_snapshot["exchange_rate"]) for a in allocations), Decimal("0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    binding = FinanceBankVoucherBinding.objects.filter(event=event).select_related("voucher").first()
    return {
        "private_voucher": binding.voucher_id if binding else None,
        "private_voucher_sha256": binding.voucher.sha256 if binding else None,
        "evidence_basis": "file_bound_v1" if binding else "historical_manual_reference_only",
        "id": event.pk, "event_no": event.event_no, "request_key": event.request_key,
        "kind": event.kind, "currency": event.currency, "amount": str(event.amount),
        "direction": event.direction, "bank_date": event.bank_date,
        "bank_net_amount": str(event.bank_net_amount), "fee_mode": event.fee_mode,
        "bank_currency": "CNY", "fee_currency": "CNY",
        "fee_amount": str(event.fee_amount), "source_account": event.source_account,
        "rmb_account": event.rmb_account, "bank_reference": event.bank_reference,
        "bank_counterparty": event.bank_counterparty, "bank_summary": event.bank_summary,
        "bank_transaction_id": event.bank_transaction_id,
        "evidence_reference": event.evidence_reference, "evidence_sha256": event.evidence_sha256,
        "evidence_note": event.evidence_note, "quoted_rate": str(event.quoted_rate) if event.quoted_rate is not None else None,
        "status": event.status, "confirmed_at": event.confirmed_at, "created_at": event.created_at,
        "created_actor": event.created_actor,
        "confirmed_actor": event.confirmed_actor if event.status == "confirmed" else {},
        "cancelled_actor": event.confirmed_actor if event.status == "cancelled" else {},
        "cancelled_reason": event.cancelled_reason, "correction_of": event.correction_of_id, "fee_for": event.fee_for_id,
        "sources": [{"transaction_id": a.source_id, "amount": str(a.amount), "currency": a.currency, "snapshot": a.source_snapshot} for a in allocations],
        "reference_amount": str(reference),
        "net_minus_reference_information_only": str((event.bank_net_amount - reference).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "basis": "bank_voucher_manual_v1", "coverage_since": None,
        "note": "仅人工凭证确认事实；含扣费不再次扣减净额，参考差异不计汇兑损益，未启用全量实际资金统计或账户余额。",
    }


class RmbCashEventViewSet(viewsets.ViewSet):
    permission_classes = [CashEventPermission]

    def initialize_request(self, request, *args, **kwargs):
        if request.method == "POST" and request.path.rstrip("/").endswith("/rmb-cash-events/voucher-upload"):
            from .finance_closeout_api import FinanceVoucherUploadHandler
            request.upload_handlers.insert(0, FinanceVoucherUploadHandler(request))
        return super().initialize_request(request, *args, **kwargs)

    @action(detail=False, methods=["post"], url_path="voucher-upload")
    def voucher_upload(self, request):
        import json
        from .finance_closeout_api import VoucherTooLarge
        from .services.finance_closeout import upload
        cash.access(request.user, "create")
        files = request.FILES
        if getattr(request._request, "_csv_import_upload_limit_exceeded", None):
            raise VoucherTooLarge()
        try:
            sources = json.loads(request.data.get("sources", "[]"))
        except (ValueError, TypeError):
            raise ValidationError("来源列表无效。")
        if not isinstance(sources, list) or len(files.getlist("file")) != 1:
            raise ValidationError("须上传一份文件并明确来源列表。")
        obj = upload(files.get("file"), request.user, bank_sources=sources)
        return Response({"id": obj.pk, "sha256": obj.sha256, "size": obj.size}, status=201)

    @action(detail=True, methods=["post"], url_path="bind-voucher")
    def bind_voucher(self, request, pk=None):
        from .services.bank_vouchers import bind
        bind(cash.get_event(request.user, pk=pk), request.data.get("private_voucher"), request.user)
        return Response(event_data(cash.get_event(request.user, pk=pk)))

    @action(detail=True, methods=["get"], url_path="voucher-download")
    def voucher_download(self, request, pk=None):
        from django.http import FileResponse
        from .services.bank_vouchers import require_verified_file
        obj = require_verified_file(cash.get_event(request.user, pk=pk), request.user)
        response = FileResponse(obj.file.open("rb"), as_attachment=True, filename=obj.original_name, content_type="application/octet-stream")
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response

    def list(self, request):
        cash.access(request.user)
        # Whole batch visibility: neither its total nor its bank reference leaks.
        events = [e for e in RmbCashEvent.objects.all() if cash.visible(e, request.user)]
        return Response({"results": [event_data(e) for e in events], "coverage_since": None, "note": "人工凭证事件列表，不代表全部银行资金。"})

    def retrieve(self, request, pk=None):
        return Response(event_data(cash.get_event(request.user, pk=pk)))

    def create(self, request):
        event, created = cash.register_event(request.data, request.user)
        return Response(event_data(event), status=201 if created else 200)

    @action(detail=False, methods=["get"], url_path="by-request-key")
    def by_request_key(self, request):
        return Response(event_data(cash.get_event(request.user, request_key=request.query_params.get("request_key", ""))))

    @action(detail=False, methods=["post"])
    def preview(self, request):
        cash.access(request.user)
        p = cash.normalize(request.data)
        rows = cash.validate_sources(p, request.user)
        return Response({"payload": p, "source_total": str(sum((Decimal(s["amount"]) for s in p["sources"]), Decimal("0"))),
                         "bank_net_amount": p["bank_net_amount"], "confirmed": False,
                         "duplicate_candidates": cash.duplicate_candidates(p, request.user),
                         "sources": [{"id": r.pk, "remaining_candidate_amount": str(cash.available(r)), "manual_verification_required": True} for r in rows],
                         "note": "只读预览不占用额度，不替代银行凭证确认。"})

    @action(detail=False, methods=["get"])
    def sources(self, request):
        cash.access(request.user)
        currency = request.query_params.get("currency")
        if currency and currency not in cash.UNITS:
            raise ValidationError("币种未配置。")
        rows = Transaction.objects.filter(status="confirmed").order_by("pk")
        if currency:
            rows = rows.filter(currency=currency)
        result = []
        for row in rows:
            if not cash.source_visible(row, request.user):
                continue
            error = cash.uncertainty(row)
            if row.currency not in cash.UNITS:
                error = "币种未配置。"
            result.append({"id": row.pk, "transaction_no": row.transaction_no,
                           "currency": row.currency, "direction": row.direction, "amount": str(row.amount),
                           "family_root": cash.family(row)[0].pk,
                           "remaining_candidate_amount": None if error else str(cash.available(row)),
                           "manual_verification_required": True, "blocked_reason": error})
        return Response({"results": result, "note": "按具体现金行计量；根行不是家族总额。核销不扣减结汇额度，候选额度不代表银行余额。"})

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        if not isinstance(request.data, dict) or set(request.data) - {"voucher_checked", "duplicate_token", "duplicate_reason"} or "voucher_checked" not in request.data:
            raise ValidationError("确认不可覆盖草稿金额或凭证。")
        return Response(event_data(cash.confirm_event(pk, request.user, voucher_checked=request.data.get("voucher_checked"),
            duplicate_token=request.data.get("duplicate_token"), duplicate_reason=request.data.get("duplicate_reason"))))

    @action(detail=True, methods=["get"], url_path="duplicate-candidates")
    def duplicate_candidates(self, request, pk=None):
        event = cash.get_event(request.user, pk=pk)
        return Response(cash.duplicate_candidates(event.request_payload, request.user, exclude_id=event.pk))

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        if not isinstance(request.data, dict) or set(request.data) != {"reason"}:
            raise ValidationError("草稿放弃只接受原因。")
        return Response(event_data(cash.cancel_pending(pk, request.user, request.data.get("reason"))))
