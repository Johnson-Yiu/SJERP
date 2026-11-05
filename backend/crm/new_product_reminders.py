"""Customer-follow-up requirements with mandatory atomic history and optimistic locking."""
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.response import Response
from .models import NewProductReminder, OperationLog
from .audit import snapshot
from .permissions import ModuleActionPermission, development_superadmin_enabled, user_can, action_for_request
from .sales_scope import scope_customer_related_queryset, customer_in_scope


class Conflict(APIException):
    status_code = 409
    default_detail = "记录已变更，请重新打开后再操作。"


def actor(request):
    if development_superadmin_enabled():
        return "开发超级管理员（非实名员工）"
    return f"账号:{request.user.pk} / {request.user.get_username()}"


class ReminderSerializer(serializers.ModelSerializer):
    requirement = serializers.CharField(max_length=12000)
    specification = serializers.CharField(max_length=12000, allow_blank=True, required=False)
    other_requirements = serializers.CharField(max_length=12000, allow_blank=True, required=False)
    tag = serializers.CharField(read_only=True, default="新品提醒")
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    class Meta:
        model = NewProductReminder
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at", "created_by", "voided_at", "voided_by", "void_reason", "version", "request_key")

    def validate(self, attrs):
        request = self.context["request"]
        permitted = {"customer", "follow_up", "contact", "product", "requirement", "specification", "other_requirements", "version", "request_key"}
        if set(self.initial_data) - permitted:
            raise ValidationError("包含不可修改的字段。")
        customer = attrs.get("customer", getattr(self.instance, "customer", None))
        if not customer or not customer_in_scope(customer.pk, request.user):
            raise PermissionDenied("客户不在当前数据范围内。")
        if self.instance and any(key in attrs and attrs[key] != getattr(self.instance, key) for key in ("customer", "follow_up")):
            raise ValidationError("所属客户和来源跟进不可更改。")
        for field, module in (("contact", "contacts"), ("product", "products"), ("follow_up", "followups")):
            obj = attrs.get(field, getattr(self.instance, field, None))
            if field in attrs and not user_can(request.user, module, "view"):
                raise PermissionDenied("没有查看关联资料的权限。")
            if obj and field in {"contact", "follow_up"} and obj.customer_id != customer.pk:
                raise ValidationError({field: "关联记录不属于当前客户。"})
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for field, module in (("contact", "contacts"), ("product", "products")):
            if not user_can(self.context["request"].user, module, "view"):
                data[field] = None
        return data


def write_history(request, obj, kind, before):
    # Mandatory even when optional legacy development auditing is disabled.
    # Development actors remain explicitly non-personal, including authenticated sessions.
    OperationLog.objects.create(content_type=ContentType.objects.get_for_model(obj),
        object_id=str(obj.pk), entity=obj._meta.label_lower, entity_label="新品提醒",
        object_label=obj.requirement[:300], action=kind, action_label={"create":"创建新品提醒", "update":"修改新品提醒", "custom":"作废新品提醒"}[kind],
        operator=None if development_superadmin_enabled() else request.user,
        before_data=before, after_data=snapshot(obj), metadata={"actor": actor(request)},
        request_method=request.method, request_path=request.path[:500])


class ReminderViewSet(viewsets.ModelViewSet):
    queryset = NewProductReminder.objects.select_related("customer", "follow_up", "contact", "product")
    serializer_class = ReminderSerializer
    permission_classes = [ModuleActionPermission]
    permission_module = "followups"
    http_method_names = ["get", "post", "patch", "head", "options"]
    search_fields = ["requirement", "specification", "other_requirements", "customer__name"]
    ordering_fields = ["created_at", "id"]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not user_can(request.user, "customers", "view") or not user_can(request.user, "followups", action_for_request(request, self)):
            raise PermissionDenied("需要客户查看及跟进操作权限。")

    def get_queryset(self):
        qs = scope_customer_related_queryset(super().get_queryset(), self.request.user)
        if self.action == "list":
            state = self.request.query_params.get("state", "active")
            if state not in {"active", "void", "all"}:
                raise ValidationError("无效的状态筛选。")
            if state != "all":
                qs = qs.filter(voided_at__isnull=state == "active")
            tag = self.request.query_params.get("tag", "")
            if tag and tag not in {"新品提醒", "new-product-reminder"}:
                qs = qs.none()
            if self.request.query_params.get("customer"):
                customer_id = serializers.IntegerField(min_value=1).run_validation(self.request.query_params["customer"])
                qs = qs.filter(customer_id=customer_id)
        return qs

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        key = serializers.UUIDField().run_validation(request.data.get("request_key"))
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Unique request key serializes concurrent duplicate submissions on PostgreSQL.
        obj, created = NewProductReminder.objects.get_or_create(request_key=key,
            defaults={**serializer.validated_data, "created_by": actor(request)})
        if not created:
            if not self.get_queryset().filter(pk=obj.pk).exists():
                raise Conflict()
            if any(getattr(obj, field) != value for field, value in serializer.validated_data.items()):
                raise Conflict("同一提交标识不能用于不同内容。")
        else:
            write_history(request, obj, "create", {})
        return Response(self.get_serializer(obj).data, status=201 if created else 200)

    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        obj = self.get_object()
        expected = serializers.IntegerField(min_value=1).run_validation(request.data.get("version"))
        if obj.voided_at or obj.version != expected:
            raise Conflict()
        serializer = self.get_serializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        before = snapshot(obj)
        if not NewProductReminder.objects.filter(pk=obj.pk, version=expected, voided_at__isnull=True).update(version=expected + 1):
            raise Conflict()
        obj = serializer.save(version=expected + 1)
        write_history(request, obj, "update", before)
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def void(self, request, pk=None):
        obj = self.get_object()
        if set(request.data) - {"version", "reason"}:
            raise ValidationError("包含不支持的字段。")
        expected = serializers.IntegerField(min_value=1).run_validation(request.data.get("version"))
        reason = serializers.CharField(max_length=4000).run_validation(request.data.get("reason"))
        before = snapshot(obj)
        if not NewProductReminder.objects.filter(pk=obj.pk, version=expected, voided_at__isnull=True).update(version=expected+1, voided_at=timezone.now(), voided_by=actor(request), void_reason=reason, updated_at=timezone.now()):
            raise Conflict()
        obj.refresh_from_db()
        write_history(request, obj, "custom", before)
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        obj = self.get_object()
        rows = OperationLog.objects.filter(entity=obj._meta.label_lower, object_id=str(obj.pk)).order_by("id")
        result = list(rows.values("id", "created_at", "action_label", "metadata", "before_data", "after_data"))
        for row in result:
            for snapshot_key in ("before_data", "after_data"):
                for field, module in (("contact", "contacts"), ("product", "products")):
                    if not user_can(request.user, module, "view"):
                        row[snapshot_key].pop(field, None)
        return Response(result)
