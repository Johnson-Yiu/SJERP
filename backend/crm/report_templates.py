"""Team-owned, validated report query templates.

Templates contain only a report definition.  They never contain a result
snapshot, a business-record export, or a permission bypass.  Every use still
goes through the normal reporting endpoint and current data-scope checks.
"""

import json

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.response import Response

from .audit import record_operation, snapshot
from .models import OperationLog, SharedReportTemplate
from .permissions import ModuleActionPermission, user_can
from .reporting import DIMENSION_MODULES, SOURCE_MODULES, SOURCES
from .finance_scope import require_finance_permission


CONFIG_KEYS = {
    "source", "group_by", "group_by_2", "grain", "date_field", "metric",
    "view", "comparison", "title", "filters",
}
ALLOWED_VIEWS = {"bar", "line", "donut", "table"}
ALLOWED_GRAINS = {"day", "week", "month", "quarter", "year"}
ALLOWED_COMPARISONS = {"previous", "year"}
MAX_CONFIG_BYTES = 12000
MAX_FILTERS = 12


class TemplateConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "团队模板已被其他操作更新，请刷新后重试。"
    default_code = "template_conflict"


def _allowed_metrics(source):
    if source == "customers":
        return {"count"}
    if source == "inventory":
        return {"count", "quantity"}
    return {"amount", "count"} if source in {"profit", "cash", "actual_cash"} else {"amount", "count", "quantity"}


def _validate_filter_values(source, filters):
    if filters is None:
        return {}
    if not isinstance(filters, dict):
        raise ValidationError({"config": "filters 必须是对象。"})
    if len(filters) > MAX_FILTERS:
        raise ValidationError({"config": "团队模板最多保存 12 个筛选条件。"})
    spec = SOURCES[source]
    normalized = {}
    for key, value in filters.items():
        if not isinstance(key, str) or not key.startswith("filter_"):
            raise ValidationError({"config": "筛选条件必须使用受支持的 filter_ 维度。"})
        dimension = key[7:]
        if dimension not in spec["dimensions"] or dimension == "time":
            raise ValidationError({"config": f"筛选维度 {dimension or key} 不适用于当前报表来源。"})
        if isinstance(value, (dict, list, tuple, bool)) or value is None:
            raise ValidationError({"config": "筛选值必须是单个文本或数字。"})
        normalized[key] = str(value)[:200]
    return normalized


def validate_template_config(raw_config, user=None, require_permissions=True):
    """Validate and normalize the reusable report definition whitelist."""
    if not isinstance(raw_config, dict):
        raise ValidationError({"config": "团队模板配置必须是对象。"})
    unknown = set(raw_config) - CONFIG_KEYS
    if unknown:
        raise ValidationError({"config": f"配置包含不支持的字段：{'、'.join(sorted(unknown))}。"})
    source = raw_config.get("source")
    if source not in SOURCES:
        raise ValidationError({"config": "不支持的报表来源。"})
    spec = SOURCES[source]
    group = raw_config.get("group_by")
    group_2 = raw_config.get("group_by_2") or ""
    if group not in spec["dimensions"]:
        raise ValidationError({"config": "第一统计维度不适用于当前报表来源。"})
    if group_2 and (group_2 not in spec["dimensions"] or group_2 == group):
        raise ValidationError({"config": "第二统计维度不适用于当前报表来源，或与第一维度重复。"})
    if group_2 and group == "time" and group_2 == "time":
        raise ValidationError({"config": "不能同时按两个时间维度分组。"})
    date_field = raw_config.get("date_field")
    if date_field not in spec.get("dates", {}):
        raise ValidationError({"config": "日期口径不适用于当前报表来源。"})
    grain = raw_config.get("grain", "month")
    if grain not in ALLOWED_GRAINS:
        raise ValidationError({"config": "时间粒度不受支持。"})
    metric = raw_config.get("metric", "amount")
    if metric not in _allowed_metrics(source):
        raise ValidationError({"config": "指标不适用于当前报表来源。"})
    view = raw_config.get("view", "bar")
    if view not in ALLOWED_VIEWS:
        raise ValidationError({"config": "图表类型不受支持。"})
    if group_2 and view == "line":
        raise ValidationError({"config": "两级分组不能使用时间趋势折线图，请选择条形图、环形图或数据表。"})
    comparison = raw_config.get("comparison", "previous")
    if comparison not in ALLOWED_COMPARISONS:
        raise ValidationError({"config": "比较方式不受支持。"})
    title = str(raw_config.get("title") or spec["label"]).strip()
    if not title or len(title) > 80:
        raise ValidationError({"config": "图表名称不能为空且最多 80 个字符。"})
    filters = _validate_filter_values(source, raw_config.get("filters", {}))
    normalized = {
        "source": source, "group_by": group, "group_by_2": group_2,
        "grain": grain, "date_field": date_field, "metric": metric,
        "view": view, "title": title, "comparison": comparison,
        "filters": filters,
    }
    if len(json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))) > MAX_CONFIG_BYTES:
        raise ValidationError({"config": "团队模板配置过大。"})
    if require_permissions:
        require_finance_permission(user, "reports", "view")
        for module in SOURCE_MODULES[source]:
            require_finance_permission(user, module, "view")
        for dimension in {group, *(d for d in [group_2] if d), *(key[7:] for key in filters)}:
            module = DIMENSION_MODULES.get(dimension)
            if module:
                require_finance_permission(user, module, "view")
    return normalized


def template_config_is_usable(template, user):
    try:
        validate_template_config(template.config, user=user, require_permissions=True)
    except (ValidationError, PermissionDenied):
        return False
    return True


def template_is_usable(template, user):
    return bool(template.published) and template_config_is_usable(template, user)


def visible_template_ids(queryset, user, include_drafts=False):
    return [
        template.pk for template in queryset
        if (include_drafts or template.published) and template_config_is_usable(template, user)
    ]


class SharedReportTemplateSerializer(serializers.ModelSerializer):
    creator_name = serializers.SerializerMethodField()
    updater_name = serializers.SerializerMethodField()
    can_use = serializers.SerializerMethodField()
    can_manage = serializers.SerializerMethodField()

    class Meta:
        model = SharedReportTemplate
        fields = [
            "id", "name", "description", "config", "published", "published_at",
            "config_version", "created_by", "creator_name", "updated_by", "updater_name",
            "created_at", "updated_at", "can_use", "can_manage",
        ]
        read_only_fields = [
            "id", "published", "published_at", "config_version", "created_by", "updated_by",
            "creator_name", "updater_name", "created_at", "updated_at", "can_use", "can_manage",
        ]

    def get_creator_name(self, obj):
        return obj.created_by.get_username() if obj.created_by else "系统"

    def get_updater_name(self, obj):
        return obj.updated_by.get_username() if obj.updated_by else "系统"

    def get_can_use(self, obj):
        return template_is_usable(obj, self.context["request"].user)

    def get_can_manage(self, obj):
        return user_can(self.context["request"].user, "reports", "update")


class SharedReportTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = SharedReportTemplateSerializer
    queryset = SharedReportTemplate.objects.select_related("created_by", "updated_by")
    permission_classes = [ModuleActionPermission]
    permission_module = "reports"

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        if user_can(user, "reports", "update"):
            candidates = queryset
        elif user_can(user, "reports", "create"):
            candidates = queryset.filter(Q(published=True) | Q(created_by=user))
        else:
            candidates = queryset.filter(published=True)
        return candidates.filter(pk__in=visible_template_ids(candidates, user, include_drafts=True))

    def _expected_version(self, request, instance):
        raw = request.data.get("config_version") or request.headers.get("If-Match")
        if raw in (None, ""):
            raise ValidationError({"config_version": "修改团队模板前必须提供配置版本。"})
        try:
            expected = int(str(raw).strip('"'))
        except (TypeError, ValueError):
            raise ValidationError({"config_version": "配置版本无效。"})
        if expected != instance.config_version:
            raise TemplateConflict()
        return expected

    def perform_create(self, serializer):
        config = validate_template_config(serializer.validated_data.get("config"), self.request.user)
        instance = serializer.save(created_by=self.request.user, updated_by=self.request.user, config=config)
        record_operation(
            request=self.request, instance=instance, action="create", action_label="创建团队共享模板",
            metadata={"config_version": instance.config_version},
        )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        current = self.get_object()
        instance = type(current).objects.select_for_update().get(pk=current.pk)
        self._expected_version(request, instance)
        payload = request.data.copy()
        payload["config"] = payload.get("config", instance.config)
        serializer = self.get_serializer(instance, data=payload, partial=partial)
        serializer.is_valid(raise_exception=True)
        before = snapshot(instance)
        config = validate_template_config(serializer.validated_data.get("config"), request.user)
        updated = serializer.save(updated_by=request.user, config=config, config_version=instance.config_version + 1)
        record_operation(
            request=request, instance=updated, action="update", action_label="修改团队共享模板",
            before=before, metadata={"config_version": updated.config_version},
        )
        return Response(self.get_serializer(updated).data)

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        current = self.get_object()
        instance = type(current).objects.select_for_update().get(pk=current.pk)
        self._expected_version(request, instance)
        config = validate_template_config(instance.config, request.user)
        before = snapshot(instance)
        instance.config = config
        instance.published = True
        instance.published_at = instance.published_at or timezone.now()
        instance.updated_by = request.user
        instance.save(update_fields=["config", "published", "published_at", "updated_by", "updated_at"])
        record_operation(
            request=request, instance=instance, action="custom", action_label="发布团队共享模板",
            before=before, metadata={"config_version": instance.config_version, "published": True},
        )
        return Response(self.get_serializer(instance).data)

    @transaction.atomic
    @action(detail=True, methods=["post"])
    def unpublish(self, request, pk=None):
        current = self.get_object()
        instance = type(current).objects.select_for_update().get(pk=current.pk)
        self._expected_version(request, instance)
        before = snapshot(instance)
        instance.published = False
        instance.published_at = None
        instance.updated_by = request.user
        instance.save(update_fields=["published", "published_at", "updated_by", "updated_at"])
        record_operation(
            request=request, instance=instance, action="custom", action_label="取消发布团队共享模板",
            before=before, metadata={"config_version": instance.config_version, "published": False},
        )
        return Response(self.get_serializer(instance).data)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        current = self.get_object()
        instance = type(current).objects.select_for_update().get(pk=current.pk)
        self._expected_version(request, instance)
        before = snapshot(instance)
        record_operation(
            request=request, instance=instance, action="delete", action_label="删除团队共享模板",
            before=before, after={}, metadata={"config_version": before.get("config_version", 1)},
        )
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        if not user_can(request.user, "reports", "update"):
            raise PermissionDenied("只有具备报表管理权限的人员可以查看团队模板操作记录。")
        instance = self.get_object()
        logs = OperationLog.objects.filter(entity="crm.sharedreporttemplate", object_id=str(instance.pk)).select_related("operator")
        from .serializers import OperationLogSerializer
        return Response(OperationLogSerializer(logs[:50], many=True, context={"request": request}).data)
