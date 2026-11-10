from io import BytesIO

from django.http import Http404
from django.conf import settings
from django.db import IntegrityError
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .history_import_preflight import (
    HistoryPreflightPermission,
    PreflightInputError,
    _csv_response,
    _read_bounded_upload,
)
from .history_takeover import (
    TakeoverRuleError,
    execute_group,
    resolve_master,
    review_correction,
    review_group,
    submit_correction,
    submit_workbook,
    withdraw_group,
)
from .models import HistoryTakeoverApplication, HistoryTakeoverGroup
from .permissions import is_permission_admin
from . import history_operational_finance, history_operational_inventory, history_operational_contracts
from .history_operational_common import overall_status


class HistoryTakeoverPermission(HistoryPreflightPermission):
    """Require a signed-in user even in the permissive development stage."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and super().has_permission(request, view))


def _application_payload(application, *, include_source=True):
    groups = []
    for group in application.groups.prefetch_related("handoffs", "source_records").order_by("id"):
        item = {
            "id": group.pk,
            "source_group_id": group.source_group_id,
            "source_system": group.source_system,
            "exported_at": group.exported_at,
            "coverage_status": group.coverage_status,
            "truth_status": group.truth_status,
            "evidence_reference": group.evidence_reference,
            "notes": group.notes,
            "status": group.status,
            "review_note": group.review_note,
            "preflight_result": group.preflight_result,
            "remainder_snapshot": group.remainder_snapshot,
            "execution_result": group.execution_result,
            "verified_correction_ids": group.verified_correction_ids,
            "handoffs": {row.kind: {"status": row.status, "payload": row.payload} for row in group.handoffs.all()},
            "source_record_count": group.source_records.count(),
            "finance_handoff_status": group.finance_handoff_status,
            "inventory_handoff_status": group.inventory_handoff_status,
            "fulfillment_handoff_status": group.fulfillment_handoff_status,
            "operational_overall": overall_status(group),
        }
        if include_source:
            item["source_rows"] = group.source_rows
            item["resolution_map"] = group.resolution_map
        groups.append(item)
    return {
        "id": application.pk,
        "source_file_name": application.source_file_name,
        "source_sha256": application.source_sha256,
        "status": application.status,
        "preflight_summary": application.preflight_summary,
        "created_by_label": application.created_by_label,
        "created_actor_kind": application.created_actor_kind,
        "reviewed_by_label": application.reviewed_by_label,
        "reviewed_actor_kind": application.reviewed_actor_kind,
        "submitted_at": application.submitted_at,
        "reviewed_at": application.reviewed_at,
        "groups": groups,
        "events": list(application.events.values("id", "group_id", "event_type", "actor_label", "actor_kind", "details", "created_at").order_by("created_at", "id")),
    }


def _admin_required(request):
    return bool(request.user and request.user.is_authenticated and is_permission_admin(request.user))


def _visible_applications(request):
    applications = HistoryTakeoverApplication.objects.all()
    if not _admin_required(request):
        applications = applications.filter(created_by_id=request.user.pk)
    return applications


def _get_visible_application(request, application_id):
    try:
        return _visible_applications(request).get(pk=application_id)
    except HistoryTakeoverApplication.DoesNotExist as exc:
        raise Http404 from exc


class HistoryTakeoverListCreateView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [HistoryTakeoverPermission]

    def get(self, request):
        rows = _visible_applications(request).order_by("-submitted_at", "-id")[:100]
        return Response({"results": [_application_payload(item, include_source=False) for item in rows]})

    def post(self, request):
        if not request.user or not request.user.is_authenticated:
            return Response({"detail": "请登录后提交历史承接申请。"}, status=401)
        django_request = getattr(request, "_request", request)
        upload = request.FILES.get("file")
        if getattr(django_request, "_csv_import_upload_limit_exceeded", False):
            return Response({"detail": "文件超过大小限制。", "business_write_performed": False}, status=413)
        try:
            data = _read_bounded_upload(upload, settings.CSV_IMPORT_MAX_BYTES)
            application, preflight, reused = submit_workbook(data, getattr(upload, "name", "history.xlsx"), request.user)
        except PreflightInputError as exc:
            return Response({"detail": str(exc), "business_write_performed": False}, status=exc.status_code)
        except (TakeoverRuleError, ValueError) as exc:
            return Response({"detail": str(exc)}, status=400)
        except IntegrityError:
            return Response({"detail": "来源资料已提交或存在重复来源编号，请读取已有申请。"}, status=409)
        if reused and not _admin_required(request) and application.created_by_id != request.user.pk:
            return Response({"detail": "相同来源文件已由其他申请人提交，请联系管理员查询处理状态。"}, status=409)
        payload = _application_payload(application)
        payload["duplicate_submission_reused"] = reused
        payload["preflight_only"] = True
        payload["approval_or_migration"] = False
        payload["preflight_summary"] = preflight["summary"]
        return Response(payload, status=200 if reused else 201)


class HistoryTakeoverTemplateView(APIView):
    permission_classes = [HistoryTakeoverPermission]

    def get(self, request):
        from .history_import_preflight import SHEET_SCHEMAS

        workbook = Workbook()
        instructions = workbook.active
        instructions.title = "使用说明"
        instructions.append(["历史资料承接模板 · v2"])
        instructions.append(["每行注明真实/模拟/待核实；只有真实且凭证、依赖核实通过的关联组可申请执行。"])
        instructions.append(["预检通过不等于审批或执行；历史收付款、履约和盘点只进入待交接区，不生成正式资金或库存流水。"])
        instructions.append(["不得按名称猜测主体，不得自动创建客户、供应商或 SKU。请填写历史快照及原系统编号。"])
        instructions.append(["历史国家/地区和产品主分类须填写发生/确认时的原始快照；缺少证据时留空，统计显示待核实，不从当前主档回填。"])
        instructions.append(["历史商品可先归档。原商品编码可留空，归档后可关联正式 SKU。"])
        for sheet_name, schema in SHEET_SCHEMAS.items():
            sheet = workbook.create_sheet(sheet_name)
            sheet.append([column["label"] for column in schema])
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = f"A1:{get_column_letter(len(schema))}1"
            for index, column in enumerate(schema, start=1):
                sheet.column_dimensions[get_column_letter(index)].width = min(34, max(12, len(column["label"]) * 1.8))
        buffer = BytesIO()
        workbook.save(buffer)
        workbook.close()
        response = HttpResponse(buffer.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = 'attachment; filename="history-takeover-template-v2.xlsx"'
        return response


class HistoryTakeoverDetailView(APIView):
    permission_classes = [HistoryTakeoverPermission]

    def get(self, request, application_id):
        application = _get_visible_application(request, application_id)
        return Response(_application_payload(application))


class HistoryTakeoverReportView(APIView):
    permission_classes = [HistoryTakeoverPermission]

    def get(self, request, application_id):
        application = _get_visible_application(request, application_id)
        results = []
        for group in application.groups.all():
            results.extend(group.preflight_result.get("results", []))
        payload = {"results": results}
        response = _csv_response(payload)
        response["Content-Disposition"] = f'attachment; filename="history-takeover-{application.pk}-review.csv"'
        return response


class HistoryTakeoverGroupActionView(APIView):
    permission_classes = [HistoryTakeoverPermission]

    def post(self, request, application_id, group_id, operation):
        try:
            group = HistoryTakeoverGroup.objects.select_related("application").get(pk=group_id, application_id=application_id)
        except HistoryTakeoverGroup.DoesNotExist as exc:
            raise Http404 from exc

        data = request.data
        try:
            if operation in {"review", "execute", "resolve-master", "correction-review", "finance-status", "finance-preview", "finance-submit", "finance-replace", "finance-approve", "finance-post", "finance-cancel", "finance-fail", "inventory-status", "inventory-propose", "inventory-approve", "inventory-execute", "inventory-reverse", "operational-status", "operational-propose", "operational-approve", "operational-execute", "operational-reverse"} and not _admin_required(request):
                return Response({"detail": "仅管理员可以审核、关联主档或执行历史承接。"}, status=403)
            if operation == "operational-status":
                return Response({**history_operational_contracts.status(group, request.user), "overall": overall_status(group)})
            if operation == "operational-propose":
                obj, replay = history_operational_contracts.propose(group.pk, data, request.user)
                return Response({"status": obj.status, "idempotent_replay": replay})
            if operation == "operational-approve":
                obj, replay = history_operational_contracts.approve(group.pk, data.get("note"), request.user)
                return Response({"status": obj.status, "idempotent_replay": replay})
            if operation == "operational-execute":
                ids, replay = history_operational_contracts.execute(group.pk, request.user)
                return Response({"contract_ids": ids, "idempotent_replay": replay})
            if operation == "operational-reverse":
                replay = history_operational_contracts.reverse(group.pk, data.get("reason"), request.user)
                return Response({"status": "reversed", "idempotent_replay": replay})
            if operation == "inventory-status":
                return Response({**history_operational_inventory.status(group, request.user), "overall": overall_status(group)})
            if operation == "inventory-propose":
                obj, replay = history_operational_inventory.propose(group.pk, data.get("rows"), data.get("reason"), data.get("complete_sku_inventory"), request.user)
                return Response({"status": obj.status, "idempotent_replay": replay})
            if operation == "inventory-approve":
                obj, replay = history_operational_inventory.approve(group.pk, data.get("note"), request.user)
                return Response({"status": obj.status, "idempotent_replay": replay})
            if operation == "inventory-execute":
                ids, replay = history_operational_inventory.execute(group.pk, request.user)
                return Response({"baseline_ids": ids, "idempotent_replay": replay})
            if operation == "inventory-reverse":
                replay = history_operational_inventory.reverse(group.pk, data.get("reason"), request.user)
                return Response({"status": "reversed", "idempotent_replay": replay})
            if operation == "finance-status":
                return Response({"sources": history_operational_finance.source_status(group, request.user), "overall": overall_status(group)})
            if operation == "finance-preview":
                return Response(history_operational_finance.preview_source(group.pk, data.get("source_id"), data.get("mapping"), request.user))
            if operation in {"finance-submit", "finance-replace"}:
                if operation == "finance-replace" and data.get("replaces") is None:
                    return Response({"detail": "请指定需要修订的原资金指令。"}, status=400)
                obj, created = history_operational_finance.submit_source(group.pk, data.get("source_id"), data.get("mapping"), request.user, replace_id=data.get("replaces") if operation == "finance-replace" else None)
                return Response({"instruction_id": obj.pk, "status": obj.status, "created": created}, status=201 if created else 200)
            if operation in {"finance-approve", "finance-post", "finance-cancel", "finance-fail"}:
                action = operation.removeprefix("finance-")
                obj = history_operational_finance.advance_source(group.pk, data.get("source_id"), action, request.user, voucher_checked=data.get("voucher_checked") is True, reason=data.get("reason", ""), no_debit_confirmed=data.get("no_debit_confirmed") is True)
                return Response({"id": obj.pk, "action": action})
            if operation == "review":
                group = review_group(
                    group, request.user, str(data.get("decision") or ""), str(data.get("note") or ""),
                    confirm_manual=data.get("confirm_manual") in (True, "true", "1", 1),
                )
            elif operation == "resolve-master":
                group = resolve_master(
                    group, request.user, sheet=str(data.get("sheet") or ""),
                    row_number=data.get("row"), field=str(data.get("field") or ""),
                    target_code=str(data.get("target_code") or ""), note=str(data.get("note") or ""),
                )
            elif operation == "execute":
                group, reused = execute_group(group, request.user)
                current = next(item for item in _application_payload(group.application)["groups"] if item["id"] == group.pk)
                return Response({"group": current, "idempotent_replay": reused})
            elif operation == "withdraw":
                if not _admin_required(request) and group.application.created_by_id != request.user.pk:
                    return Response({"detail": "仅申请人或管理员可以撤回未执行的关联组。"}, status=403)
                group = withdraw_group(group, request.user, str(data.get("reason") or ""))
            elif operation == "correction":
                if not _admin_required(request) and group.application.created_by_id != request.user.pk:
                    return Response({"detail": "仅申请人或管理员可以提交追溯更正。"}, status=403)
                submit_correction(
                    group, request.user, kind=str(data.get("kind") or "correction"),
                    occurred_at=data.get("occurred_at"), details=data.get("details"),
                    reason=str(data.get("reason") or ""),
                )
            elif operation == "correction-review":
                group = review_correction(
                    group, request.user, event_id=data.get("event_id"),
                    decision=str(data.get("decision") or ""), note=str(data.get("note") or ""),
                )
            else:
                return Response({"detail": "不支持的操作。"}, status=404)
        except (TakeoverRuleError, ValueError, TypeError) as exc:
            return Response({"detail": str(exc)}, status=400)
        except IntegrityError:
            return Response({"detail": "来源记录或执行键已存在；请重新读取承接结果。"}, status=409)
        group_payload = next(
            item for item in _application_payload(group.application)["groups"]
            if item["id"] == group.pk
        )
        return Response({"group": group_payload})
