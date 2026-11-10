import csv

from django.db.models import Q
from django.http import HttpResponse
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from .history_products import SOURCE_MODELS, apply_links, filter_source_lines, line_summary, load_source_lines, preview_links, sku_summary
from .history_takeover_api import HistoryTakeoverPermission, _visible_applications
from .models import HistoryTakeoverSourceRecord, SKU
from .permissions import user_can
from .reporting import safe_csv


class PreviewInput(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField(min_value=1), min_length=1, max_length=100)
    operation = serializers.ChoiceField(choices=["link", "change", "unlink", "review"])
    target = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    reason = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    verified_specification = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    save_rule = serializers.BooleanField(default=False)


class SubmitInput(serializers.Serializer):
    token = serializers.CharField(max_length=250000)


class QueryInput(serializers.Serializer):
    q = serializers.CharField(max_length=200, required=False, allow_blank=True)
    source = serializers.CharField(max_length=160, required=False, allow_blank=True)
    batch = serializers.CharField(max_length=120, required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=["pending", "linked", "review"], required=False, allow_blank=True)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    target = serializers.CharField(max_length=80, required=False, allow_blank=True)
    page = serializers.IntegerField(min_value=1, default=1)


class HistoryProductsView(APIView):
    permission_classes = [HistoryTakeoverPermission]

    def sources(self, request):
        if not user_can(request.user, "skus", "view"):
            raise PermissionDenied("你没有查看 SKU 的权限。")
        source_types = Q(target_model__in=SOURCE_MODELS)
        if user_can(request.user, "inventory", "view"):
            source_types |= Q(record_type="库存盘点", target_model="")
        return HistoryTakeoverSourceRecord.objects.filter(
            group__application__in=_visible_applications(request),
            group__status="executed",
        ).filter(source_types).select_related("group", "product_link__sku__product")

    def get(self, request, operation="list"):
        sources = self.sources(request)
        query = QueryInput(data=request.query_params)
        query.is_valid(raise_exception=True)
        filters = query.validated_data
        term = filters.get("q", "")
        if operation == "targets":
            skus = SKU.objects.filter(active=True).select_related("product")
            if term:
                skus = skus.filter(Q(sku__icontains=term) | Q(display_name_cn__icontains=term) | Q(product__name__icontains=term))
            return Response([sku_summary(sku) for sku in skus.order_by("sku")[:40]])
        if filters.get("source"):
            sources = sources.filter(source_system__icontains=filters["source"])
        if filters.get("batch"):
            sources = sources.filter(group__source_group_id__icontains=filters["batch"])
        sources = filter_source_lines(sources, filters).order_by("-pk")
        count = None
        if operation != "export":
            count = sources.count()
            offset = (filters["page"] - 1) * 50
            sources = sources[offset:offset + 50]
        sources = list(sources)
        lines = load_source_lines(sources)
        rows = [line_summary(source, lines.get((source.target_model, source.target_id))) for source in sources]
        if operation == "export":
            return self.export(rows)
        return Response({"count": count, "results": rows})

    def export(self, rows):
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="history-products.csv"'
        response.write("\ufeff")
        writer = csv.writer(response)
        writer.writerow(["统计口径", "来源", "批次", "原订单", "原明细", "日期", "原编码", "历史商品", "历史规格",
                         "历史分类", "数量", "单位", "商品金额", "币种", "关联状态", "正式 SKU", "当前 SKU 名称"])
        states = {"pending": "待关联", "linked": "已关联", "review": "待核实"}
        for row in rows:
            sku = row["sku"] or {}
            writer.writerow([safe_csv(value) for value in [
                "历史原文明细", row["source_system"], row["batch"], row["order_number"], row["source_number"],
                row["date"], row["code"], row["name"], row["specification"], row["category"], row["quantity"],
                row["unit"], row["amount"], row["currency"], states[row["status"]], sku.get("code", ""), sku.get("name", ""),
            ]])
        return response

    def post(self, request, operation):
        sources = self.sources(request)
        from .history_takeover_api import _admin_required
        if not _admin_required(request):
            raise PermissionDenied("只有管理员可以修改历史商品关联。")
        if operation == "preview":
            payload = PreviewInput(data=request.data)
            payload.is_valid(raise_exception=True)
            data = payload.validated_data
            result = preview_links(sources, request.user, sorted(set(data["ids"])), data["operation"], data.get("target"), data.get("reason", ""), data["save_rule"], data.get("verified_specification", ""))
        elif operation == "apply":
            payload = SubmitInput(data=request.data)
            payload.is_valid(raise_exception=True)
            result = apply_links(sources, request.user, payload.validated_data["token"])
        else:
            from django.http import Http404
            raise Http404
        return Response(result, status=409 if result.get("conflicts") else 200)
