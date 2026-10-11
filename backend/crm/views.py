Warning: truncated output (original token count: 34381)
Total output lines: 2407

from .trade_units import amount_expression, trade_values
import csv
import hashlib
import io
import json
import time
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from urllib.request import urlopen

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.db.models import Case, Count, DecimalField, ExpressionWrapper, F, IntegerField, OuterRef, Q, Subquery, Sum, Value, When
from django.db.models.functions import Coalesce, TruncMonth
from django.http import HttpResponse
from django.core import signing
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action, api_view, parser_classes, permission_classes
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from .models import AccessRole, CategoryAttribute, Contact, ContractChangeRequest, Customer, EmployeeProfile, FollowUp, FollowUpAttachment, GoodsReceipt, HSCode, InventoryMovement, OperationLog, Order, OrderItem, OrganizationUnit, PackagingTemplate, PackingPlan, PaymentPlan, Position, Product, ProductCategory, ProductCertificate, ProductParameter, PurchaseOrder, Quote, QuoteImportantNote, RolePermission, Shipment, ShipmentPackage, SKUPackagingProfile, SKU, Supplier, SupplierSKU, Transaction
from .querysets import current_due_follow_ups, prefetch_purchase_related_orders
from .permissions import HSCodeMaintenancePermission, ModuleActionPermission, OrganizationOverviewPermission, PermissionAdminOnly, QuoteExportPermission, _profile_for, effective_permission_matrix, has_all_permissions, is_permission_admin, user_can
from .sales_scope import allowed_employee_ids, data_scope_display, effective_data_scope, employee_profile_for, scope_customer_queryset, scope_customer_related_queryset
from .quote_numbers import allocate_revision_quote_no
from .quote_export import QuoteExportError, build_pi_export_payload
from .quote_snapshots import create_quote_items
from .serializers import certificate_expiry, AccessRoleSerializer, CancellationInputSerializer, CategoryAttributeSerializer, ContactSerializer, ContractChangeRequestSerializer, CustomerSerializer, EmployeeProfileSerializer, FollowUpAttachmentSerializer, FollowUpSerializer, GoodsReceiptSerializer, HSCodeSerializer, InventoryMovementReversalInputSerializer, InventoryMovementSerializer, OperationLogSerializer, OrderItemSerializer, OrderSerializer, OrganizationUnitSerializer, PackagingTemplateSerializer, PackingPlanSerializer, PaymentPlanSerializer, PositionSerializer, ProductCategorySerializer, ProductCertificateSerializer, ProductParameterSerializer, ProductSerializer, PurchaseOrderSerializer, ReceiptInputSerializer, ReceiptReversalInputSerializer, QuoteAvailabilityPreviewInputSerializer, QuoteImportantNoteSerializer, QuoteSerializer, RolePermissionSerializer, ShipmentInputSerializer, ShipmentPackageSerializer, ShipmentReversalInputSerializer, TransactionVoidInputSerializer, SKUPackagingProfileSerializer, SKUSerializer, SKUVersionSerializer, SupplierPaymentInputSerializer, SupplierSerializer, SupplierSKUSerializer, TransactionSerializer, next_product_code
from .serializers import ProcurementDraftInputSerializer
from .audit import AuditTrailMixin, record_operation, snapshot
from .services.finance import allocate_advance, approve_contract_change, reject_contract_change, record_contract_payment, record_transaction, void_transaction
from .services.fulfillment import bulk_sku_metrics, confirm_shipment, order_item_metrics, record_receipt, record_supplier_payment, reverse_manual_inventory_movement, reverse_receipt as reverse_receipt_service, reverse_shipment as reverse_shipment_service
from .services.order_lifecycle import cancel_order, complete_order, confirm_order, start_order_production
from .services.packaging import copy_estimated_to_actual, generate_packing_plan, packaging_summary
from .services.purchase_lifecycle import cancel_purchase_order, place_purchase_order
from .services.procurement import build_procurement_plan, create_purchase_drafts, draft_procurement_quantities
from .services.sku_plans import apply_category_attribute_reorder, preview_category_attribute_reorder
from .services.sku_schema import (
    UNFROZEN_CATEGORY_HIERARCHY_MESSAGE,
    UNFROZEN_SCHEMA_MESSAGE,
    unfrozen_products_using_category_scope,
    unfrozen_schema_error,
)
from .services.sales_model_prefix import apply_sales_model_prefix, preview_sales_model_prefix
from .sku_identity import normalize_abbreviation_key
from .sales_model_defaults import DEFAULT_SALES_MODEL_ABBREVIATIONS

MONEY = DecimalField(max_digits=20, decimal_places=2)
USD_CNY_REFERENCE_CACHE = {"expires_at": 0, "payload": None}


@api_view(["GET"])
def usd_cny_reference_rate(request):
    """Return a short-lived, display-only USD/CNY market reference rate."""
    now = time.monotonic()
    cached = USD_CNY_REFERENCE_CACHE["payload"]
    if cached and now < USD_CNY_REFERENCE_CACHE["expires_at"]:
        return Response({**cached, "cached": True})
    try:
        with urlopen("https://api.frankfurter.dev/v2/rate/USD/CNY", timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
        rate = Decimal(str(data["rate"]))
        payload = {"base": "USD", "quote": "CNY", "rate": str(rate), "date": data["date"], "source": "Frankfurter"}
        USD_CNY_REFERENCE_CACHE.update({"payload": payload, "expires_at": now + 300})
        return Response(payload)
    except (KeyError, ValueError, OSError, json.JSONDecodeError):
        if cached:
            return Response({**cached, "cached": True, "stale": True})
        return Response({"detail": "暂时无法获取 USD/CNY 参考汇率。"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class OperationLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OperationLogSerializer
    queryset = OperationLog.objects.select_related("operator", "content_type")
    permission_classes = [ModuleActionPermission]
    search_fields = ["entity", "entity_label", "object_id", "object_label", "action_label", "operator__username"]
    ordering_fields = ["created_at", "entity", "action"]

    def get_queryset(self):
        qs = super().get_queryset()
        entity = self.request.query_params.get("entity")
        object_id = self.request.query_params.get("object_id")
        if entity:
            qs = qs.filter(entity=entity)
        if object_id:
            qs = qs.filter(object_id=str(object_id))
        return qs


class OrganizationUnitViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    serializer_class = OrganizationUnitSerializer
    queryset = OrganizationUnit.objects.select_related("parent").prefetch_related("positions").annotate(employee_count=Count("employees"))
    search_fields = ["name", "code"]


class PositionViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    serializer_class = PositionSerializer
    queryset = Position.objects.select_related("unit")
    search_fields = ["name", "code", "unit__name"]


class SupplierViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    serializer_class = SupplierSerializer
    queryset = Supplier.objects.prefetch_related("purchase_orders")
    search_fields = ["name", "code", "country", "main_products", "contact_name", "phone", "email", "store_url", "payment_terms"]

    @action(detail=True, methods=["get"], url_path="supplier-skus")
    def supplier_skus(self, request, pk=None):
        supplier = self.get_object()
        rows = supplier.supplier_skus.select_related("sku", "sku__product").order_by("sku__sku", "id")
        return Response(SupplierSKUSerializer(rows, many=True).data)


class SupplierSKUViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    serializer_class = SupplierSKUSerializer
    queryset = SupplierSKU.objects.select_related("supplier", "sku", "sku__product").prefetch_related("purchase_items", "inventory_movements")
    search_fields = [
        "supplier_sku_code", "supplier_model", "supplier_product_name", "supplier_barcode",
        "supplier__name", "sku__sku", "sku__sales_model", "sku__display_name_cn", "sku__product__name",
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("sku"):
            qs = qs.filter(sku_id=self.request.query_params["sku"])
        if self.request.query_params.get("supplier"):
            qs = qs.filter(supplier_id=self.request.query_params["supplier"])
        for parameter, field in [("is_active", "is_active"), ("is_preferred", "is_preferred")]:
            raw = self.request.query_params.get(parameter)
            if raw is not None:
                qs = qs.filter(**{field: str(raw).lower() in {"1", "true", "yes"}})
        return qs

    @action(detail=True, methods=["post"], url_path="set-preferred")
    def set_preferred(self, request, pk=None):
        from .services.supplier_sku import set_preferred_supplier_sku

        source = self.get_object()
        before = snapshot(source)
        instance = set_preferred_supplier_sku(source)
        record_operation(request=request, instance=instance, action="custom", action_label="设为首选供应商来源", before=before, metadata={"supplier_id": instance.supplier_id, "sku_id": instance.sku_id})
        return Response(self.get_serializer(instance).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.purchase_items.exists() or instance.inventory_movements.exists():
            return Response({"detail": "该供应商来源已被采购或入库流水引用，不能删除；请停用。"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response({"detail": "该供应商来源已被业务记录引用，不能删除；请停用。"}, status=status.HTTP_400_BAD_REQUEST)


class PurchaseOrderViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    serializer_class = PurchaseOrderSerializer
    queryset = prefetch_purchase_related_orders(
        PurchaseOrder.objects.select_related("supplier", "order").prefetch_related(
            "items__sku", "items__supplier_sku__supplier", "items__receipts", "transactions"
        )
    )
    search_fields = ["purchase_no", "supplier__name", "order__order_no"]

    def get_queryset(self):
        queryset = super().get_queryset()
        sku_id = self.request.query_params.get("sku")
        if sku_id:
            queryset = queryset.filter(items__sku_id=sku_id).distinct()
        purchase_status = self.request.query_params.get("status")
        if purchase_status:
            queryset = queryset.filter(status=purchase_status)
        if self.request.query_params.get("pending_receipt") == "1":
            queryset = queryset.filter(status__in=["ordered", "partial"])
        return queryset

    def create(self, request, *args, **kwargs):
        if request.data.get("status") not in (None, "", "draft"):
            return Response({"detail": "新建采购单只能保存为草稿，请使用确认下单动作。"}, status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if "status" in request.data:
            return Response({"detail": "采购单状态只能通过确认下单、到货或取消等业务动作变更。"}, status=status.HTTP_400_BAD_REQUEST)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        purchase = self.get_object()
        if purchase.status != "draft":
            return Response({"detail": "正式采购单不能删除，请使用取消采购。"}, status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def place(self, request, pk=None):
        try:
            with transaction.atomic():
                purchase = place_purchase_order(self.get_object())
                record_operation(
                    request=request,
                    instance=purchase,
                    action="custom",
                    action_label="确认采购下单",
                    metadata={"purchase_order_id": purchase.id, "purchase_no": purchase.purchase_no},
                )
        except DjangoValidationError as error:
            return Response({"detail": error.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(purchase).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        input_serializer = CancellationInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                purchase = cancel_purchase_order(self.get_object(), input_serializer.validated_data["reason"])
                record_operation(
                    request=request,
                    instance=purchase,
                    action="custom",
                    action_label="取消采购单",
                    metadata={"reason": purchase.cancellation_reason},
                )
        except DjangoValidationError as error:
            return Response({"detail": error.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(purchase).data)

    @action(detail=True, methods=["post"], url_path="cost-allocation-preview")
    def cost_allocation_preview(self, request, pk=None):
        from .services.purchase_costs import CostInput, preview_costs
        purchase = self.get_object()
        input_serializer = CostInput(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        return Response(preview_costs(purchase, input_serializer.validated_data))

    @action(detail=True, methods=["get", "post"], url_path="cost-allocation")
    def cost_allocation(self, request, pk=None):
        from .services.purchase_costs import CostInput, cost_summary, save_costs
        purchase = self.get_object()
        if request.method == "GET":
            return Response(cost_summary(purchase))
        input_serializer = CostInput(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            before = cost_summary(purchase)
            result = save_costs(purchase, input_serializer.validated_data)
            record_operation(request=request, instance=purchase, action="custom", action_label="采购成本分配", metadata=json.loads(json.dumps({"before_allocation": before, "after_allocation": result}, default=str)))
        return Response(result)

    @action(detail=True, methods=["post"])
    def receive(self, request, pk=None):
        purchase = self.get_object()
        before = snapshot(purchase)
        input_serializer = ReceiptInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        item = purchase.items.filter(pk=input_serializer.validated_data["purchase_item"]).first()
        if item is None:
            return Response({"detail": "到货明细不属于该采购单。"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            receipt = record_receipt(item, input_serializer.validated_data)
        except DjangoValidationError as error:
            return Response({"detail": error.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        record_operation(request=request, instance=purchase, action="custom", action_label="登记采购到货", before=before, metadata={"receipt_id": receipt.id, "quantity": str(receipt.quantity), "inventory_movement_id": receipt.inventory_movement_id})
        return Response({
            "id": receipt.id,
            "purchase_item": receipt.purchase_item_id,
            "quantity": receipt.quantity,
            **{**trade_values(receipt), "trade_unit": receipt.trade_unit_id},
            "is_overage": receipt.is_overage,
            "inventory_movement": receipt.inventory_movement_id,
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path=r"receipts/(?P<receipt_id>[^/.]+)/reverse")
    def reverse_receipt(self, request, pk=None, receipt_id=None):
        purchase = self.get_object()
        receipt = get_object_or_404(GoodsReceipt, pk=receipt_id, purchase_item__purchase_order=purchase)
        input_serializer = ReceiptReversalInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        try:
            receipt = reverse_receipt_service(receipt, input_serializer.validated_data["reason"])
        except DjangoValidationError as error:
            return Response({"detail": error.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        record_operation(
            request=request,
            instance=purchase,
            action="custom",
            action_label="冲销采购入库",
            metadata={
                "receipt_id": receipt.id,
                "reversal_inventory_movement_id": receipt.reversal_inventory_movement_id,
                "reason": receipt.reversal_reason,
            },
        )
        return Response(GoodsReceiptSerializer(receipt).data)

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        input_serializer = SupplierPaymentInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        purchase = self.get_object()
        before = snapshot(purchase)
        try:
            payment = record_contract_payment(purchase, {**input_serializer.validated_data, "category": "供应商付款"})
        except DjangoValidationError as error:
            return Response({"detail": error.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        record_operation(request=request, instance=payment, action="create", action_label="登记供应商付款", metadata={"purchase_order_id": purchase.id, "purchase_no": purchase.purchase_no})
        record_operation(request=request, instance=purchase, action="custom", action_label="采购单付款", before=before, metadata={"transaction_id": payment.id})
        return Response(TransactionSerializer(payment).data, status=status.HTTP_201_CREATED)


class AccessRoleViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    serializer_class = AccessRoleSerializer
    queryset = AccessRole.objects.prefetch_related("permissions").annotate(employee_count=Count("employees", distinct=True)).order_by("priority", "id")
    search_fields = ["name", "code", "description"]
    permission_classes = [ModuleActionPermission, PermissionAdminOnly]

    @action(detail=True, methods=["post"], url_path="permission-matrix")
    @transaction.atomic
    def permission_matrix(self, request, pk=None):
        role = self.get_object()
        if role.code == "superadmin":
            return Response({"detail": "超级管理员权限为系统最高权限，不允许取消。"}, status=status.HTTP_400_BAD_REQUEST)
        rows = request.data.get("permissions")
        if not isinstance(rows, list):
            return Response({"detail": "权限矩阵格式不正确。"}, status=status.HTTP_400_BAD_REQUEST)

        valid_modules = dict(RolePermission.MODULE_CHOICES)
        submitted = set()
        for row in rows:
            module = row.get("module")
            if module not in valid_modules or module in submitted:
                return Response({"detail": f"无效或重复的功能模块：{module}"}, status=status.HTTP_400_BAD_REQUEST)
            submitted.add(module)
            RolePermission.objects.update_or_create(role=role, module=module, defaults={
                "can_view": bool(row.get("can_view")), "can_create": bool(row.get("can_create")),
                "can_update": bool(row.get("can_update")), "can_delete": bool(row.get("can_delete")),
                "can_export": bool(row.get("can_export")), "can_import": bool(row.get("can_import")),
            })
        RolePermission.objects.filter(role=role).exclude(module__in=submitted).delete()
        refreshed = AccessRole.objects.prefetch_related("permissions").annotate(employee_count=Count("employees", distinct=True)).get(pk=role.pk)
        return Response(AccessRoleSerializer(refreshed).data)


class RolePermissionViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    serializer_class = RolePermissionSerializer
    queryset = RolePermission.objects.select_related("role")
    permission_classes = [ModuleActionPermission, PermissionAdminOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(role_id=self.request.query_params["role"]) if self.request.query_params.get("role") else qs


class EmployeeProfileViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    serializer_class = EmployeeProfileSerializer
    queryset = EmployeeProfile.objects.select_related("user", "unit", "position").prefetch_related("roles")
    search_fields = ["display_name", "user__username", "unit__name", "position__name"]


@api_view(["GET"])
@permission_classes([OrganizationOverviewPermission])
def organization_overview(request):
    from django.conf import settings
    units = OrganizationUnit.objects.select_related("parent").prefetch_related("positions").annotate(employee_count=Count("employees"))
    roles = AccessRole.objects.prefetch_related("permissions").annotate(employee_count=Count("employees", distinct=True)).order_by("priority", "id")
    return Response({
        "units": OrganizationUnitSerializer(units, many=True).data,
        "roles": AccessRoleSerializer(roles, many=True).data,
        "summary": {
            "departments": units.filter(type="department").count(),
            "positions": Position.objects.filter(active=True).count(),
            "roles": roles.filter(active=True).count(),
            "members": EmployeeProfile.objects.filter(active=True).count(),
        },
        "modules": [{"code": code, "name": name} for code, name in RolePermission.MODULE_CHOICES],
        "enforcement": settings.RBAC_ENFORCEMENT,
        "configuration_mode": not settings.RBAC_ENFORCEMENT,
    })


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def current_operator(request):
    from django.conf import settings
    from .permissions import development_superadmin_enabled

    matrix = effective_permission_matrix(request.user)
    complete = has_all_permissions(request.user)
    can_manage = is_permission_admin(request.user)
    permission_payload = {
        module: {action: bool(value) for action, value in actions.items()}
        for module, actions in matrix.items()
    }

    if development_superadmin_enabled():
        profile = employee_profile_for(request.user) or _profile_for(request.user)
        name = (profile.display_name if profile else request.user.get_full_name() or request.user.username) if request.user.is_authenticated else settings.DEFAULT_OPERATOR_NAME
        return Response({"name": name, "role": "超级管理员", "authenticated": request.user.is_authenticated,
                         "development_superadmin": True, "rbac_enforcement": settings.RBAC_ENFORCEMENT,
                         "has_all_permissions": True, "can_manage_permissions": True, "permissions": permission_payload,
                         "data_scope": "all", "data_scope_display": "全部数据",
                         "employee_profile_id": profile.pk if profile else None, "unit_id": profile.unit_id if profile else None,
                         "unit_name": profile.unit.name if profile else "", "can_manage_hs_codes": True,
                         "audit_log_enabled": bool(request.user.is_authenticated and settings.AUDIT_LOG_ENABLED)})

    if request.user.is_authenticated:
        profile = _profile_for(request.user)
        name = profile.display_name if profile else request.user.get_full_name() or request.user.username
        roles = list(profile.roles.filter(active=True).values_list("name", flat=True)) if profile and profile.active else []
        role = "超级管理员" if request.user.is_superuser else "、".join(roles) or "未分配角色"
        scope = effective_data_scope(request.user)
        return Response({"name": name, "role": role, "authenticated": True, "development_superadmin": False,
                         "rbac_enforcement": settings.RBAC_ENFORCEMENT, "has_all_permissions": complete,
                         "can_manage_permissions": can_manage, "permissions": permission_payload,
                         "data_scope": scope, "data_scope_display": data_scope_display(scope),
                         "employee_profile_id": profile.pk if profile and profile.active else None,
                         "unit_id": profile.unit_id if profile and profile.active else None,
                         "unit_name": profile.unit.name if profile and profile.active else "",
                         "can_manage_hs_codes": can_manage, "audit_log_enabled": settings.AUDIT_LOG_ENABLED})
    return Response({"name": "未登录", "role": "未登录", "authenticated": False, "development_superadmin": False,
                     "rbac_enforcement": settings.RBAC_ENFORCEMENT, "has_all_permissions": complete,
                     "can_manage_permissions": False, "permissions": permission_payload,
                     "data_scope": "none", "data_scope_display": "未分配数据范围",
                     "employee_profile_id": None, "unit_id": None, "unit_name": "",
                     "can_manage_hs_codes": False, "audit_log_enabled": False})


class CustomerViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    search_fields = ["name", "code", "country", "owner", "source"]
    ordering_fields = ["name", "created_at", "updated_at", "next_follow_up"]

    def get_queryset(self):
        formal_statuses = ["confirmed", "production", "shipped", "completed"]
        item_amount = OrderItem.objects.filter(order_id=OuterRef("pk")).values("order_id").annotate(
            total=Sum(amount_expression("")),
        ).values("total")
        approved_changes = ContractChangeRequest.objects.filter(
            order_id=OuterRef("pk"), status="approved",
        ).values("order_id").annotate(total=Sum("amount_delta")).values("total")
        formal_orders = Order.objects.filter(customer_id=OuterRef("pk"), status__in=formal_statuses).annotate(
            item_amount=Coalesce(Subquery(item_amount, output_field=MONEY), Decimal("0"), output_field=MONEY),
            approved_change_amount=Coalesce(Subquery(approved_changes, output_field=MONEY), Decimal("0"), output_field=MONEY),
        ).annotate(
            sales_rmb=ExpressionWrapper(
                (F("item_amount") + F("shipping_fee") - F("discount") + F("approved_change_amount")) * F("exchange_rate"),
                output_field=MONEY,
            ),
        )
        sales = formal_orders.values("customer_id").annotate(total=Sum("sales_rmb")).values("total")
        order_count = Order.objects.filter(customer_id=OuterRef("pk"), status__in=formal_statuses).values("customer_id").annotate(total=Count("id")).values("total")
        contact_count = Contact.objects.filter(customer=OuterRef("pk")).values("customer").annotate(total=Count("id")).values("total")
        queryset = Customer.objects.annotate(
            contact_count=Coalesce(Subquery(contact_count, output_field=IntegerField()), 0),
            order_count=Coalesce(Subquery(order_count, output_field=IntegerField()), 0),
            sales_amount=Coalesce(Subquery(sales, output_field=MONEY), Decimal("0"), output_field=MONEY),
        )
        return scope_customer_queryset(queryset, self.request.user).order_by("-updated_at")

    @action(detail=False, methods=["get"], url_path="owner-options")
    def owner_options(self, request):
        employees = EmployeeProfile.objects.filter(pk__in=allowed_employee_ids(request.user), active=True).select_related("unit")
        return Response([{"id": employee.pk, "display_name": employee.display_name, "unit_name": employee.unit.name, "label": f"{employee.display_name} · {employee.unit.name}"} for employee in employees])

    @action(detail=False, methods=["get"], url_path="next-code")
    def next_code(self, request):
        from .models import CustomerCodeSequence
        from .serializers import customer_sequence_suffix

        sequence = CustomerCodeSequence.objects.filter(pk=1).first()
        next_value = (sequence.last_value if sequence else -1) + 1
        return Response({"code": f"{timezone.localdate():%Y%m%d}{customer_sequence_suffix(next_value)}"})

    @action(detail=False, methods=["get"])
    def sources(self, request):
        values = scope_customer_queryset(Customer.objects.all(), request.user).exclude(source="").values_list("source", flat=True).distinct().order_by("source")
        return Response([{"value": value, "label": value} for value in values])

    @action(detail=True, methods=["get"])
    def insights(self, request, pk=None):
        customer = self.get_object()
        year = timezone.localdate().year
        formal_statuses = ["confirmed", "production", "shipped", "completed"]
        yearly = []
        for target in [year - 1, year]:
            orders = list(customer.orders.filter(status__in=formal_statuses, order_date__year=target).prefetch_related("items", "contract_changes"))
            yearly.append({
                "year": target,
                "orders": len(orders),
                "sales": sum((order.total_amount * order.exchange_rate for order in orders), Decimal("0")),
            })
        products = OrderItem.objects.filter(order__customer=customer, order__status__in=formal_statuses).values(
            "sku__product__id", "sku__product__name"
        ).annotate(
            sales=Sum(ExpressionWrapper(amount_expression("") * F("order__exchange_rate"), output_field=MONEY)),
            quantity=Sum("quantity"),
        ).order_by("-sales")[:10]
        return Response({
            "customer": CustomerSerializer(customer).data,
            "yearly": yearly,
            "top_products": list(products),
            "recent_orders": OrderSerializer(customer.orders.exclude(status="cancelled").order_by("-order_date", "-id").prefetch_related("items__sku__product")[:5], many=True).data,
            "recent_follow_ups": FollowUpSerializer(customer.follow_ups.select_related("contact")[:5], many=True).data,
        })

    def destroy(self, request, *args, **kwargs):
        customer = self.get_object()
        if customer.follow_ups.exists() or customer.quotes.exists() or customer.orders.exists() or customer.transactions.exists():
            return Response({"detail": "该客户已有业务历史，不能删除；请保留客户档案。"}, status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)


class ContactViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    queryset = Contact.objects.select_related("customer")
    serializer_class = ContactSerializer
    search_fields = ["name", "email", "phone", "customer__name"]

    def get_queryset(self):
        qs = scope_customer_related_queryset(super().get_queryset(), self.request.user)
        return qs.filter(customer_id=self.request.query_params["customer"]) if self.request.query_params.get("customer") else qs

    def destroy(self, request, *args, **kwargs):
        contact = self.get_object()
        if contact.follow_ups.exists():
            return Response({"detail": "该联系人已有跟进历史，不能删除。"}, status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)


class FollowUpViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    queryset = FollowUp.objects.select_related("customer", "contact").prefetch_related("attachments")
    serializer_class = FollowUpSerializer
    search_fields = ["subject", "content", "customer__name", "owner"]
    ordering_fields = ["followed_at", "next_follow_up", "created_at"]

    @action(detail=False, methods=["get"])
    def methods(self, request):
        builtins = [{"value": value, "label": label} for value, label in FollowUp.TYPE_CHOICES]
        builtin_values = {item["value"] for item in builtins}
        custom = FollowUp.objects.exclude(type="").values_list("type", flat=True).distinct().order_by("type")
        return Response(builtins + [{"value": value, "label": value} for value in custom if value not in builtin_values])

    def get_queryset(self):
        qs = scope_customer_related_queryset(super().get_queryset(), self.request.user)
        if self.request.query_params.get("customer"):
            qs = qs.filter(customer_id=self.request.query_params["customer"])
        if self.request.query_params.get("due") == "true":
            qs = current_due_follow_ups(qs, today=timezone.localdate())
        return qs

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser], url_path="attachments")
    def upload_attachments(self, request, pk=None):
        follow_up = self.get_object()
        uploads = request.FILES.getlist("files") or request.FILES.getlist("file")
        if not uploads:
            return Response({"detail": "请选择要上传的附件。"}, status=status.HTTP_400_BAD_REQUEST)
        max_size = 20 * 1024 * 1024
        if any(upload.size > max_size for upload in uploads):
            return Response({"detail": "单个附件不能超过 20 MB。"}, status=status.HTTP_400_BAD_REQUEST)
        attachments = []
        for upload in uploads:
            attachment = FollowUpAttachment(follow_up=follow_up, file=upload, name=upload.name[:255], content_type=upload.content_type or "", size=upload.size)
            attachment.save()
            attachments.append(attachment)
        record_operation(request=request, instance=follow_up, action="custom", action_label="上传跟进附件", metadata={"attachment_ids": [attachment.id for attachment in attachments], "file_names": [attachment.name for attachment in attachments]})
        return Response(FollowUpAttachmentSerializer(attachments, many=True, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path=r"attachments/(?P<attachment_id>[^/.]+)")
    def delete_attachment(self, request, pk=None, attachment_id=None):
        follow_up = self.get_object()
        attachment = get_object_or_404(FollowUpAttachment, pk=attachment_id, follow_up=follow_up)
        attachment_name = attachment.name
        attachment.file.delete(save=False)
        attachment.delete()
        record_operation(request=request, instance=follow_up, action="custom", action_label="删除跟进附件", metadata={"attachment_id": attachment_id, "file_name": attachment_name})
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductCategoryViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    serializer_class = ProductCategorySerializer
    queryset = ProductCategory.objects.select_related("parent").prefetch_related("attributes", "parent__attributes", "parent__parent__attributes").annotate(product_count=Count("products", distinct=True), child_count=Count("children", distinct=True))
    search_fields = ["name"]

    @action(detail=False, methods=["get"])
    def tree(self, request):
        return Response(self.get_serializer(self.get_queryset().order_by("parent_id", "sort_order", "id"), many=True).data)

    def destroy(self, request, *args, **kwargs):
        category = self.get_object()
        if category.children.exists() or category.products.exists() or category.secondary_products.exists():
            return Response(
                {"detail": "该分类仍有子分类或关联产品，不能删除；请先调整产品分类关系。"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=["post"])
    @transaction.atomic
    def reorder(self, request):
        category = get_object_or_404(ProductCategory.objects.select_for_update(), pk=request.data.get("id"))
        before = snapshot(category)
        parent_id = request.data.get("parent") or None
        new_parent = get_object_or_404(ProductCategory, pk=parent_id) if parent_id else None
        cursor = new_parent
        while cursor:
            if cursor.pk == category.pk:
                return Response({"detail": "不能把分类移动到自身或其子分类下。"}, status=status.HTTP_400_BAD_REQUEST)
            cursor = cursor.parent
        old_parent_id = category.parent_id
        new_parent_id = new_parent.pk if new_parent else None
        if old_parent_id != new_parent_id:
            unsafe_products = unfrozen_products_using_category_scope(category)
            if unsafe_products:
                return Response(
                    unfrozen_schema_error(unsafe_products, UNFROZEN_CATEGORY_HIERARCHY_MESSAGE),
                    status=status.HTTP_400_BAD_REQUEST,
                )
        category.parent = new_parent
        category.save(update_fields=["parent", "updated_at"])
        siblings = list(ProductCategory.objects.filter(parent=new_parent).exclude(pk=category.pk).order_by("sort_order", "id"))
        index = max(0, min(int(request.data.get("index", len(siblings))), len(siblings)))
        siblings.insert(index, category)
        for order, sibling in enumerate(siblings):
            ProductCategory.objects.filter(pk=sibling.pk).update(sort_order=order)
        if old_parent_id != new_parent_id:
            for order, sibling in enumerate(ProductCategory.objects.filter(parent_id=old_parent_id).order_by("sort_order", "id")):
                ProductCategory.objects.filter(pk=sibling.pk).update(sort_order=order)
        record_operation(request=request, instance=category, action="custom", action_label="调整产品分类顺序", before=before, metadata={"parent_id": parent_id, "index": index})
        return Response({"detail": "分类位置已更新。"})


class CategoryAttributeViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    serializer_class = CategoryAttributeSerializer
    queryset = CategoryAttribute.objects.select_related("category")

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(category_id=self.request.query_params["category"]) if self.request.query_params.get("category") else qs

    def destroy(self, request, *args, **kwargs):
        attribute = self.get_object()
        unsafe_products = unfrozen_products_using_category_scope(attribute.category)
        if unsafe_products:
            return Response(
                unfrozen_schema_error(unsafe_products, UNFROZEN_SCHEMA_MESSAGE),
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=["post"])
    @transaction.atomic
    def reorder(self, request):
        category = get_object_or_404(ProductCategory, pk=request.data.get("category"))
        before = {"attribute_ids": list(category.attributes.order_by("sort_order", "id").values_list("id", flat=True))}
        ids = request.data.get("ids")
        if not isinstance(ids, list):
            return Response({"detail": "ids 必须为属性 ID 数组。"}, status=status.HTTP_400_BAD_REQUEST)
        attributes = list(CategoryAttribute.objects.filter(category=category).order_by("sort_order", "id"))
        existing_ids = {attribute.id for attribute in attributes}
        if set(ids) != existing_ids or len(ids) != len(existing_ids):
            return Response({"detail": "排序内容与当前分类属性不一致。"}, status=status.HTTP_400_BAD_REQUEST)
        if request.data.get("preview"):
            return Response(preview_category_attribute_reorder(category, ids))
        before_order = before["attribute_ids"]
        for order, attribute_id in enumerate(ids):
            CategoryAttribute.objects.filter(pk=attribute_id).update(sort_order=order)
        result = apply_category_attribute_reorder(category, ids)
        record_operation(request=request, instance=category, action="custom", action_label="调整分类属性顺序并刷新 SKU", before={"attribute_ids": before_order}, after={"attribute_ids": ids, "affected_skus": result["affected_skus"]})
        return Response({"detail": "属性排序已更新，SKU 名称和 Sales Model 已刷新。", **result})


class ProductViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    queryset = Product.objects.select_related("category", "hs_code").annotate(
        sku_count=Count("skus", distinct=True),
        parameter_count=Count("parameters", distinct=True),
        certificate_count=Count("certificates", distinct=True),
    )
    search_fields = ["name", "name_en", "code", "hs_code__code", "category__name"]

    def get_queryset(self):
        queryset = super().get_queryset()
        category_id = self.request.query_params.get("category")
        if category_id:
            queryset = queryset.filter(Q(category_id=category_id) | Q(additional_categories__id=category_id)).distinct()
        return queryset

    @action(detail=False, methods=["get"], url_path="next-code")
    def next_code(self, request):
        return Response({"code": next_product_code()})

    @action(detail=True, methods=["post"], url_path="sales-model-prefix-preview")
    def sales_model_prefix_preview(self, request, pk=None):
        product = self.get_object()
        return Response(preview_sales_model_prefix(product, request.data.get("sales_model_prefix")))

    @action(detail=True, methods=["post"], url_path="sales-model-prefix-apply")
    def sales_model_prefix_apply(self, request, pk=None):
        product = self.get_object()
        result = apply_sales_model_prefix(
            product.pk,
            request.data.get("sales_model_prefix"),
            request.data.get("baseline"),
        )
        record_operation(
            request=request,
            instance=Product.objects.get(pk=product.pk),
            action="custom",
            action_label="确认变更 Sales Model Prefix",
            before={"sales_model_prefix": result["old_prefix"]},
            after={"sales_model_prefix": result["new_prefix"]},
            metadata={"affected_sku_ids": [row["sku_id"] for row in result["affected_skus"]]},
        )
        return Response(result)

    @action(detail=True, methods=["get"])
    def customers(self, request, pk=None):
        rows = OrderItem.objects.filter(
            sku__product=self.get_object(),
            order__status__in=["confirmed", "production", "shipped", "completed"],
        ).values(
            "order__customer__id", "order__customer__name", "order__customer__country"
        ).annotate(
            sales=Sum(ExpressionWrapper(amount_expression("") * F("order__exchange_rate"), output_field=MONEY)),
            order_count=Count("order", distinct=True), quantity=Sum("quantity"),
        ).order_by("-sales")
        return Response(list(rows))

    def destroy(self, request, *args, **kwargs):
        product = self.get_object()
        if product.skus.exists():
            return Response({"detail": "该产品已存在 SKU，不能物理删除。请将产品设为停产并停用相关 SKU。"}, status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)


class HSCodeViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    serializer_class = HSCodeSerializer
    permission_classes = [HSCodeMaintenancePermission]
    queryset = HSCode.objects.annotate(product_count=Count("products", distinct=True))
    search_fields = ["code", "de…12381 tokens truncated…rue).data,
            "shipments": [{
                "id": shipment.id, "shipment_no": shipment.shipment_no,
                "shipment_date": shipment.shipment_date, "status": shipment.status,
                "reversed_at": shipment.reversed_at, "reversal_reason": shipment.reversal_reason,
                "has_overage": any(line.is_overage for line in shipment.items.all()),
                "items": [{
                    "id": line.id, "sku": line.sku_id,
                    "sku_code": (line.inventory_movement.sku_code_snapshot if line.inventory_movement else "") or line.order_item.sku_code_snapshot or line.sku.sku,
                    "display_name": (line.inventory_movement.display_name_snapshot if line.inventory_movement else "") or line.order_item.display_name_snapshot or line.sku.display_name_cn,
                    "base_unit": (line.trade_snapshot or {}).get("base_unit") or line.sku.unit,
                    "quantity": line.quantity,
                    "is_overage": line.is_overage,
                    "inventory_movement": line.inventory_movement_id,
                    "reversal_inventory_movement": line.reversal_inventory_movement_id,
                } for line in shipment.items.all()],
            } for shipment in shipments],
        })

    @action(detail=True, methods=["get"], url_path="procurement-plan")
    def procurement_plan(self, request, pk=None):
        return Response(build_procurement_plan(self.get_object()))

    @action(detail=True, methods=["post"], url_path="generate-purchase-drafts")
    def generate_purchase_drafts(self, request, pk=None):
        input_serializer = ProcurementDraftInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        try:
            purchases = create_purchase_drafts(self.get_object(), input_serializer.validated_data)
            for purchase in purchases:
                record_operation(
                    request=request,
                    instance=purchase,
                    action="custom",
                    action_label="由销售订单生成采购草稿",
                    metadata={"order_id": purchase.order_id, "order_no": purchase.order.order_no},
                )
        except DjangoValidationError as error:
            return Response({"detail": error.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        purchase_ids = [purchase.pk for purchase in purchases]
        serialized_purchases = prefetch_purchase_related_orders(
            PurchaseOrder.objects.filter(pk__in=purchase_ids)
            .select_related("supplier", "order")
            .prefetch_related("items__sku", "items__receipts", "transactions")
        )
        return Response({
            "created_count": len(purchases),
            "purchase_orders": PurchaseOrderSerializer(serialized_purchases, many=True).data,
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"], url_path="packing-plan")
    def packing_plan(self, request, pk=None):
        order = self.get_object()
        if request.method == "POST":
            plan = generate_packing_plan(order)
            record_operation(request=request, instance=order, action="custom", action_label="生成订单装箱方案", metadata={"packing_plan_id": plan.id})
            return Response(PackingPlanSerializer(plan).data)
        plan = getattr(order, "packing_plan", None)
        return Response(PackingPlanSerializer(plan).data if plan else {"detail": "尚未生成预计装箱。"}, status=status.HTTP_200_OK if plan else status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=["post"])
    def ship(self, request, pk=None):
        input_serializer = ShipmentInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        try:
            shipment = confirm_shipment(self.get_object(), input_serializer.validated_data)
        except DjangoValidationError as error:
            return Response({"detail": error.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        record_operation(request=request, instance=self.get_object(), action="custom", action_label="确认订单发货", metadata={"shipment_id": shipment.id, "shipment_no": shipment.shipment_no})
        return Response({"id": shipment.id, "shipment_no": shipment.shipment_no, "status": shipment.status}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def workbench(self, request, pk=None):
        order = self.get_object()
        from .models import AdvanceAllocation
        advance_allocations = [{"id": row.pk, "transaction_no": row.advance.transaction_no,
            "transaction_date": row.advance.transaction_date, "amount": row.amount,
            "currency": row.plan.currency, "is_active": row.is_active}
            for row in AdvanceAllocation.objects.filter(plan__order=order).select_related("advance", "plan")]
        items = list(order.items.all())
        payments = list(order.transactions.all())
        plans = list(order.payment_plans.all())
        expenses = [row for row in payments if row.direction == "expense" and row.kind not in {"supplier_payment", "refund", "unallocated_advance", "unallocated_payment"} and row.status == "confirmed"]
        inventory = list(InventoryMovement.objects.filter(Q(order=order) | Q(related_orders=order)).distinct().select_related("sku__product"))
        ordered_quantity = sum((item.quantity for item in items), Decimal("0"))
        shipped_quantity = sum((order_item_metrics(item)["shipped_quantity"] for item in items), Decimal("0"))
        paid_amount = order.paid_amount
        planned_receivable = sum((plan.planned_amount for plan in plans if plan.status != "cancelled"), Decimal("0"))
        from .services.profit import order_profit_summary
        profit_summary = order_profit_summary(order)
        return Response({
            "order": OrderSerializer(order).data,
            "source_quote": QuoteSerializer(order.quote).data if order.quote else None,
            "items": OrderItemSerializer(items, many=True).data,
            "payments": TransactionSerializer(payments, many=True).data,
            "advance_allocations": advance_allocations,
            "plans": PaymentPlanSerializer(plans, many=True).data,
            "inventory": InventoryMovementSerializer(inventory, many=True).data,
            "payment_summary": {
                "paid_amount": paid_amount,
                "balance_amount": order.outstanding_amount,
                "planned_amount": planned_receivable,
            },
            "expense_summary": {"expense_rmb": profit_summary["expense_rmb"]},
            "profit_summary": profit_summary,
            "fulfillment_summary": {
                "ordered_quantity": ordered_quantity,
                "shipped_quantity": shipped_quantity,
                "remaining_quantity": ordered_quantity - shipped_quantity,
            },
        })


@api_view(["GET"])
def finance_dashboard(request):
    today = timezone.localdate()
    try:
        start = date.fromisoformat(request.query_params.get("date_from") or today.replace(day=1).isoformat())
        end = date.fromisoformat(request.query_params.get("date_to") or today.isoformat())
        if start > end:
            raise ValueError
    except ValueError:
        return Response({"detail": "请填写有效日期，开始日期不能晚于结束日期。"}, status=400)
    plans = PaymentPlan.objects.select_related("order__customer", "purchase_order__supplier").filter(status="open").exclude(order__status__in=["draft", "cancelled"]).exclude(purchase_order__status__in=["draft", "cancelled"])
    receivables = plans.filter(direction="receivable")
    payables = plans.filter(direction="payable")
    remaining = lambda rows: sum((row.remaining_amount * (row.order.exchange_rate if row.order_id else row.purchase_order.exchange_rate) for row in rows), Decimal("0"))
    from .services.profit import order_profit_summary
    period_orders = Order.objects.exclude(status__in=["draft", "cancelled"]).filter(order_date__range=(start, end)).prefetch_related("items", "contract_changes", "purchase_cost_allocations", "transactions")
    profits = [order_profit_summary(order) for order in period_orders]
    sales_rmb = sum((row["sales_rmb"] for row in profits), Decimal("0"))
    purchase_cost_rmb = sum((row["purchase_cost_rmb"] for row in profits), Decimal("0"))
    order_expense_rmb = sum((row["expense_rmb"] for row in profits), Decimal("0"))
    estimated_profit_rmb = sum((row["estimated_profit_rmb"] for row in profits), Decimal("0"))
    cash = Transaction.objects.filter(status="confirmed", transaction_date__range=(start, end))
    income, expense = Decimal("0"), Decimal("0")
    categories, monthly = {}, {}
    for row in cash:
        value = row.rmb_amount or row.amount * row.exchange_rate
        if row.direction == "income":
            income += value
        else:
            expense += value
        key = (row.direction, row.category)
        categories[key] = categories.get(key, Decimal("0")) + value
        month = row.transaction_date.strftime("%Y-%m")
        bucket = monthly.setdefault(month, {"month": month, "income": Decimal("0"), "expense": Decimal("0")})
        bucket[row.direction] += value
    advances = Transaction.objects.filter(status="confirmed", kind__in=["unallocated_advance", "unallocated_payment"])
    unallocated = lambda direction: sum(((row.amount - row.allocated_amount) * row.exchange_rate for row in advances if row.direction == direction), Decimal("0"))
    due_items = [
        {
            "id": row.id, "direction": row.direction, "contract_no": row.order.order_no if row.order_id else row.purchase_order.purchase_no,
            "order": row.order_id, "purchase_order": row.purchase_order_id,
            "counterparty_name": row.order.customer.name if row.order_id else row.purchase_order.supplier.name,
            "due_date": row.due_date, "remaining_amount": row.remaining_amount, "currency": row.currency,
        }
        for row in plans.filter(due_date__isnull=False, due_date__lte=today).order_by("due_date")[:12]
    ]
    return Response({"metrics": {
        "receivable_count": receivables.count(), "receivable_rmb": remaining(receivables),
        "payable_count": payables.count(), "payable_rmb": remaining(payables), "sales_rmb": sales_rmb, "monthly_sales_rmb": sales_rmb,
        "purchase_cost_rmb": purchase_cost_rmb, "order_expense_rmb": order_expense_rmb, "estimated_profit_rmb": estimated_profit_rmb,
        "income_rmb": income, "expense_rmb": expense, "net_cash_rmb": income - expense,
        "advance_receipt_rmb": unallocated("income"), "advance_payment_rmb": unallocated("expense"),
    }, "period": {"date_from": start, "date_to": end}, "due_items": due_items,
        "categories": [{"direction": key[0], "category": key[1], "amount": value} for key, value in sorted(categories.items())],
        "monthly_cash": [{**monthly[key], "net": monthly[key]["income"] - monthly[key]["expense"]} for key in sorted(monthly)]})


class TransactionViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    queryset = Transaction.objects.select_related("customer", "order", "supplier", "purchase_order").prefetch_related("allocations__plan__order", "allocations__plan__purchase_order")
    search_fields = ["transaction_no", "category", "customer__name", "supplier__name", "order__order_no", "purchase_order__purchase_no", "reference"]
    ordering_fields = ["transaction_date", "amount", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("customer"):
            qs = qs.filter(customer_id=self.request.query_params["customer"])
        if self.request.query_params.get("order"):
            qs = qs.filter(order_id=self.request.query_params["order"])
        for key in ("supplier", "purchase_order", "status", "direction", "kind"):
            if self.request.query_params.get(key):
                qs = qs.filter(**{key: self.request.query_params[key]})
        for key, lookup in (("date_from", "transaction_date__gte"), ("date_to", "transaction_date__lte")):
            if self.request.query_params.get(key):
                qs = qs.filter(**{lookup: self.request.query_params[key]})
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            row = record_transaction(serializer.validated_data.copy())
        except DjangoValidationError as error:
            return Response({"detail": error.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        record_operation(request=request, instance=row, action="create", action_label="登记财务流水")
        return Response(self.get_serializer(row).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        return Response({"detail": "财务流水保留原始记录，请作废后重记。"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        return Response({"detail": "财务流水不能删除，请使用作废保留记录。"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def void(self, request, pk=None):
        source = self.get_object()
        input_serializer = TransactionVoidInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        before = snapshot(source)
        try:
            row = void_transaction(source, input_serializer.validated_data["reason"])
        except DjangoValidationError as error:
            return Response({"detail": error.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        split_ids = []
        frontier = [row.pk]
        while frontier:
            child_ids = list(Transaction.objects.filter(split_from_id__in=frontier).values_list("pk", flat=True))
            split_ids.extend(child_ids)
            frontier = child_ids
        record_operation(
            request=request,
            instance=row,
            action="custom",
            action_label="作废财务流水",
            before=before,
            metadata={"transaction_id": row.id, "reason": row.void_reason, "split_transaction_ids": split_ids},
        )
        return Response(self.get_serializer(row).data)

    @action(detail=True, methods=["post"])
    def allocate(self, request, pk=None):
        from rest_framework import serializers as drf_serializers
        plan_id = drf_serializers.IntegerField(min_value=1).run_validation(request.data.get("plan"))
        amount = drf_serializers.DecimalField(max_digits=14, decimal_places=4, min_value=Decimal("0.0001")).run_validation(request.data.get("amount"))
        plan = get_object_or_404(PaymentPlan, pk=plan_id)
        try:
            source = self.get_object()
            plan = allocate_advance(source, plan, amount)
        except DjangoValidationError as error:
            return Response({"detail": error.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        record_operation(request=request, instance=plan, action="custom", action_label="核销预收预付", metadata={"transaction_id": source.id, "amount": str(request.data.get("amount") or "")})
        return Response(PaymentPlanSerializer(plan).data)


class InventoryMovementViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    manual_types = {"adjust_in", "adjust_out", "sample_out", "return_in", "transfer_in", "transfer_out", "production_in", "production_out", "other_in", "other_out"}
    serializer_class = InventoryMovementSerializer
    queryset = InventoryMovement.objects.select_related("sku__product", "order")
    search_fields = ["movement_no", "sku__sku", "sku__product__name", "order__order_no", "warehouse", "reference"]
    ordering_fields = ["movement_date", "quantity", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("sku"):
            qs = qs.filter(sku_id=self.request.query_params["sku"])
        if self.request.query_params.get("product"):
            qs = qs.filter(sku__product_id=self.request.query_params["product"])
        if self.request.query_params.get("order"):
            qs = qs.filter(Q(order_id=self.request.query_params["order"]) | Q(related_orders__id=self.request.query_params["order"])).distinct()
        return qs

    def create(self, request, *args, **kwargs):
        if request.data.get("type") not in self.manual_types:
            return Response({"detail": "手工库存流水类型不受支持，请选择入库或出库类型。"}, status=status.HTTP_400_BAD_REQUEST)
        payload = request.data.copy()
        payload["source_type"] = "manual"
        payload["is_automatic"] = False
        serializer = self.get_serializer(data=payload)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def batch(self, request):
        items = request.data.get("items") or []
        if not items:
            return Response({"detail": "请至少选择一个 SKU 并填写数量。"}, status=status.HTTP_400_BAD_REQUEST)
        if request.data.get("type") not in self.manual_types:
            return Response({"detail": "手工库存流水类型不受支持，请选择入库或出库类型。"}, status=status.HTTP_400_BAD_REQUEST)
        common = {key: value for key, value in request.data.items() if key != "items"}
        serializers_to_save = []
        for item in items:
            payload = {**common, **item, "source_type": "manual", "is_automatic": False}
            if payload.get("type") not in self.manual_types:
                return Response({"detail": "批量明细包含不支持的库存类型。"}, status=status.HTTP_400_BAD_REQUEST)
            serializer = self.get_serializer(data=payload)
            serializer.is_valid(raise_exception=True)
            serializers_to_save.append(serializer)
        with transaction.atomic():
            records = [serializer.save() for serializer in serializers_to_save]
        for row in records:
            record_operation(request=request, instance=row, action="create", action_label="批量登记库存流水")
        return Response(self.get_serializer(records, many=True).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        movement = self.get_object()
        if movement.is_automatic:
            return Response({"detail": "系统自动生成的库存流水不能修改。"}, status=status.HTTP_400_BAD_REQUEST)
        if InventoryMovement.objects.filter(source_type="reversal", source_no=movement.movement_no).exists():
            return Response({"detail": "已冲销的库存流水不能修改。"}, status=status.HTTP_400_BAD_REQUEST)
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def reverse(self, request, pk=None):
        input_serializer = InventoryMovementReversalInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        original = self.get_object()
        try:
            reversal = reverse_manual_inventory_movement(original, input_serializer.validated_data["reason"])
        except DjangoValidationError as error:
            return Response({"detail": error.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        record_operation(
            request=request,
            instance=original,
            action="custom",
            action_label="冲销库存流水",
            metadata={"reversal_movement_id": reversal.id, "reversal_movement_no": reversal.movement_no, "reason": input_serializer.validated_data["reason"]},
        )
        record_operation(request=request, instance=reversal, action="create", action_label="生成库存冲销流水", metadata={"source_movement_no": original.movement_no})
        return Response(self.get_serializer(reversal).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        self.get_object()
        return Response({"detail": "库存流水属于库存审计记录，不能直接删除，请使用冲销。"}, status=status.HTTP_400_BAD_REQUEST)


class PaymentPlanViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    serializer_class = PaymentPlanSerializer
    queryset = PaymentPlan.objects.select_related("order__customer", "purchase_order__supplier")
    search_fields = [
        "order__order_no",
        "order__customer__name",
        "purchase_order__purchase_no",
        "purchase_order__supplier__name",
    ]
    ordering_fields = ["due_date", "planned_amount", "created_at"]

    def _date_filter(self, key):
        value = self.request.query_params.get(key)
        if not value:
            return None
        try:
            parsed = date.fromisoformat(value)
        except (TypeError, ValueError):
            raise DRFValidationError({key: "日期格式无效，请使用 YYYY-MM-DD。"})
        if parsed.isoformat() != value:
            raise DRFValidationError({key: "日期格式无效，请使用 YYYY-MM-DD。"})
        return parsed

    def get_queryset(self):
        qs = super().get_queryset()
        for key in ("direction", "order", "purchase_order", "status"):
            if self.request.query_params.get(key):
                qs = qs.filter(**{f"{key}_id" if key in {"order", "purchase_order"} else key: self.request.query_params[key]})
        if self.request.query_params.get("overdue") == "true":
            qs = qs.filter(status="open", due_date__lt=timezone.localdate())
        due_from = self._date_filter("due_from")
        due_to = self._date_filter("due_to")
        if due_from and due_to and due_from > due_to:
            raise DRFValidationError({"due_from": "不能晚于 due_to。"})
        if due_from:
            qs = qs.filter(due_date__gte=due_from)
        if due_to:
            qs = qs.filter(due_date__lte=due_to)
        return qs

    @action(detail=True, methods=["post"])
    def settle(self, request, pk=None):
        plan = self.get_object()
        payload = {**request.data, "plan": plan.pk,
            "currency": request.data.get("currency", plan.currency),
            "exchange_rate": request.data.get("exchange_rate", (plan.order or plan.purchase_order).exchange_rate),
            "direction": "income" if plan.order_id else "expense",
            "kind": "customer_receipt" if plan.order_id else "supplier_payment",
            "category": request.data.get("category") or ("客户收款" if plan.order_id else "供应商付款")}
        input_serializer = TransactionSerializer(data=payload)
        input_serializer.is_valid(raise_exception=True)
        try:
            row = record_transaction(input_serializer.validated_data)
        except DjangoValidationError as error:
            return Response({"detail": error.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        record_operation(request=request, instance=row, action="create", action_label="结算付款计划", metadata={"payment_plan_id": plan.id})
        return Response(TransactionSerializer(row).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        return Response({"detail": "收付款计划保留合同依据，可修改未核销计划的金额、日期和备注，不支持直接删除。"}, status=status.HTTP_400_BAD_REQUEST)


class ContractChangeRequestViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    serializer_class = ContractChangeRequestSerializer
    queryset = ContractChangeRequest.objects.select_related("order", "purchase_order")

    def get_queryset(self):
        queryset = super().get_queryset()
        sales_changes = scope_customer_related_queryset(queryset.filter(order__isnull=False), self.request.user, relation="order__customer")
        purchase_changes = queryset.filter(purchase_order__isnull=False)
        queryset = sales_changes | purchase_changes
        if self.request.query_params.get("order"):
            queryset = queryset.filter(order_id=self.request.query_params["order"])
        if self.request.query_params.get("purchase_order"):
            queryset = queryset.filter(purchase_order_id=self.request.query_params["purchase_order"])
        return queryset

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        try:
            request_item = self.get_object()
            plan = approve_contract_change(request_item)
        except DjangoValidationError as error:
            return Response({"detail": error.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        record_operation(request=request, instance=request_item, action="custom", action_label="审批合同变更", metadata={"payment_plan_id": plan.id})
        return Response(PaymentPlanSerializer(plan).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        try:
            request_item = reject_contract_change(self.get_object())
        except DjangoValidationError as error:
            return Response({"detail": error.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        record_operation(request=request, instance=request_item, action="custom", action_label="拒绝合同变更")
        return Response(self.get_serializer(request_item).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status != "pending":
            return Response({"detail": "已处理的合同变更必须保留历史记录，不能删除。"}, status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)



@api_view(["GET"])
def dashboard(request):
    today = timezone.localdate()
    year_start = date(today.year, 1, 1)
    last_year_start = date(today.year - 1, 1, 1)
    last_year_same_day = date(today.year - 1, today.month, min(today.day, 28 if today.month == 2 else today.day))
    formal_statuses = ["confirmed", "production", "shipped", "completed"]
    scoped_customers = scope_customer_queryset(Customer.objects.all(), request.user)
    valid_orders = scope_customer_related_queryset(Order.objects.filter(status__in=formal_statuses), request.user)
    def sales_between(start, end):
        return sum(
            (order.total_amount * order.exchange_rate for order in valid_orders.filter(order_date__range=(start, end)).prefetch_related("items", "contract_changes")),
            Decimal("0"),
        )

    monthly_rows = defaultdict(lambda: {"sales": Decimal("0"), "orders": 0})
    customer_rows = defaultdict(lambda: {"sales": Decimal("0"), "orders": 0, "name": "", "country": ""})
    for order in valid_orders.filter(order_date__gte=last_year_start).select_related("customer").prefetch_related("items", "contract_changes"):
        amount = order.total_amount * order.exchange_rate
        month = order.order_date.strftime("%Y-%m")
        monthly_rows[month]["sales"] += amount
        monthly_rows[month]["orders"] += 1
        if order.order_date >= year_start:
            customer = customer_rows[order.customer_id]
            customer["sales"] += amount
            customer["orders"] += 1
            customer["name"], customer["country"] = order.customer.name, order.customer.country
    monthly = [{"month": month, **values} for month, values in sorted(monthly_rows.items())]
    # Product-category sales deliberately remain item-only: contract adjustments have no SKU/category allocation.
    categories = OrderItem.objects.filter(order__in=valid_orders, order__order_date__gte=year_start).values(
        "sku__product__category__name"
    ).annotate(sales=Sum(ExpressionWrapper(amount_expression("") * F("order__exchange_rate"), output_field=MONEY)), quantity=Sum("quantity")).order_by("-sales")[:8]
    top_customers = [
        {"id": customer_id, **values}
        for customer_id, values in sorted(customer_rows.items(), key=lambda row: row[1]["sales"], reverse=True)[:6]
    ]
    income = Transaction.objects.filter(direction="income", status="confirmed", transaction_date__gte=year_start).aggregate(
        v=Coalesce(Sum(ExpressionWrapper(F("amount") * F("exchange_rate"), output_field=MONEY)), Decimal("0"), output_field=MONEY)
    )["v"]
    expense = Transaction.objects.filter(direction="expense", status="confirmed", transaction_date__gte=year_start).aggregate(
        v=Coalesce(Sum(ExpressionWrapper(F("amount") * F("exchange_rate"), output_field=MONEY)), Decimal("0"), output_field=MONEY)
    )["v"]
    due_follow_ups = scope_customer_related_queryset(current_due_follow_ups(today=today), request.user).select_related("customer", "contact").prefetch_related("attachments")
    certificates = ProductCertificate.objects.filter(expires_on__lte=today + timedelta(days=90)).select_related("product")
    certificate_alerts = [
        {"id": c.id, "product_id": c.product_id, "product_name": c.product.name,
         "certificate_name": c.name, "certificate_no": c.certificate_no, "expires_on": c.expires_on,
         **certificate_expiry(c.expires_on, today)}
        for c in certificates.order_by("expires_on", "id")[:5]
    ]
    return Response({
        "certificate_alerts": certificate_alerts,
        "summary": {
            "certificate_attention": certificates.count(),
            "certificate_expired": certificates.filter(expires_on__lt=today).count(),
            "certificate_expiring": certificates.filter(expires_on__gte=today).count(),
            "sales_ytd": sales_between(year_start, today),
            "sales_last_ytd": sales_between(last_year_start, last_year_same_day),
            "orders_ytd": valid_orders.filter(order_date__gte=year_start).count(),
            "active_customers": Customer.objects.filter(status__in=["customer", "company"]).count(),
            "receipts_rmb": income,
            "payments_rmb": expense,
            "follow_ups_due": due_follow_ups.count(),
        },
        "monthly_sales": monthly,
        "category_sales": list(categories),
        "top_customers": list(top_customers),
        "recent_orders": OrderSerializer(valid_orders.prefetch_related("items__sku__product")[:5], many=True).data,
        "due_follow_ups": FollowUpSerializer(due_follow_ups[:5], many=True).data,
    })


IMPORT_FIELDS = {
    "customers": ["code", "name", "country", "source", "website", "address", "notes"],
    "products": ["code", "name", "sales_model_prefix", "category", "description", "status"],
    "skus": ["sku", "product_code", "specification", "unit", "cost_price", "default_price", "currency"],
    "transactions": ["transaction_no", "transaction_date", "direction", "category", "amount", "currency", "exchange_rate", "customer_code", "order_no", "payment_method", "reference", "notes"],
}
IMPORT_REQUIRED_FIELDS = {
    "customers": {"code", "name"},
    "products": {"code", "name"},
    "skus": {"sku", "product_code"},
    "transactions": {"transaction_no", "transaction_date", "direction", "category", "amount"},
}
IMPORT_KEY_FIELDS = {"customers": "code", "products": "code", "skus": "sku", "transactions": "transaction_no"}
IMPORT_PREVIEW_SALT = "crm.import.preview"
IMPORT_PREVIEW_MAX_AGE_SECONDS = 30 * 60
ORDER_IMPORT_DISABLED_MESSAGE = "正式订单导入暂未开放，请通过订单业务流程创建；避免绕过报价、库存预留和收款计划。"


@api_view(["GET"])
def import_templates(request):
    return Response(IMPORT_FIELDS)


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def import_csv(request):
    """Legacy endpoint is intentionally preview-only; it must never write data."""
    return _import_csv_preview_request(request)


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def import_csv_preview(request):
    return _import_csv_preview_request(request)


def _import_csv_preview_request(request):
    entity = request.data.get("entity")
    upload = request.FILES.get("file")
    try:
        rows, digest = _read_import_csv(entity, upload)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    preview_state = _import_state(entity, rows)
    preview = _preview_import(entity, rows, user=request.user)
    if not preview["errors"]:
        preview["preview_token"] = signing.dumps({"entity": entity, "sha256": digest, "state": preview_state}, salt=IMPORT_PREVIEW_SALT)
    return Response(preview)


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def import_csv_execute(request):
    entity = request.data.get("entity")
    upload = request.FILES.get("file")
    token = request.data.get("preview_token")
    try:
        rows, digest = _read_import_csv(entity, upload)
        signed = signing.loads(token or "", salt=IMPORT_PREVIEW_SALT, max_age=IMPORT_PREVIEW_MAX_AGE_SECONDS)
    except signing.SignatureExpired:
        return Response({"detail": "预览已过期，请重新预览后再导入。"}, status=status.HTTP_400_BAD_REQUEST)
    except signing.BadSignature:
        return Response({"detail": "预览凭证无效，请重新预览后再导入。"}, status=status.HTTP_400_BAD_REQUEST)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    if signed.get("entity") != entity or signed.get("sha256") != digest:
        return Response({"detail": "文件或数据类型已变化，请重新预览后再导入。"}, status=status.HTTP_400_BAD_REQUEST)
    if signed.get("state") != _import_state(entity, rows):
        return Response({"detail": "数据状态已发生变化，请重新预览后再导入。"}, status=status.HTTP_400_BAD_REQUEST)

    # Run the exact write path once in a transaction that is rolled back. This
    # detects concurrent changes after preview without leaving any side effects.
    validation = _preview_import(entity, rows, user=request.user)
    if validation["errors"]:
        return Response({"detail": "数据状态已变化，请重新预览后再导入。", "errors": validation["errors"]}, status=status.HTTP_400_BAD_REQUEST)
    try:
        with transaction.atomic():
            if signed.get("state") != _import_state(entity, rows, lock=True):
                return Response({"detail": "数据状态已发生变化，请重新预览后再导入。"}, status=status.HTTP_400_BAD_REQUEST)
            created, updated = _apply_import_rows(entity, rows, user=request.user)
    except Exception:
        return Response({"detail": "数据状态已变化，请重新预览后再导入。"}, status=status.HTTP_400_BAD_REQUEST)
    return Response({"total": len(rows), "created": created, "updated": updated})


def _import_state(entity, rows, lock=False):
    model = {"customers": Customer, "products": Product, "skus": SKU, "transactions": Transaction}[entity]
    key = IMPORT_KEY_FIELDS[entity]
    targets = model.objects.filter(**{f"{key}__in": [row.get(key, "") for row in rows]})
    if lock:
        targets = targets.select_for_update()
    records = {getattr(record, key): record for record in targets}
    state = []
    for row in rows:
        business_key = row.get(key, "")
        record = records.get(business_key)
        entry = {"business_key": business_key, "action": "update" if record else "create"}
        if record:
            entry["id"] = record.pk
            entry["updated_at"] = record.updated_at.isoformat()
            # Include concrete values as well: QuerySet.update can bypass auto_now.
            values = {field.attname: str(getattr(record, field.attname)) for field in model._meta.concrete_fields}
            entry["version"] = hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()
        state.append(entry)
    return state


def _read_import_csv(entity, upload):
    if entity == "orders":
        raise ValueError(ORDER_IMPORT_DISABLED_MESSAGE)
    if entity not in IMPORT_FIELDS or not upload:
        raise ValueError("请选择有效的数据类型和 CSV 文件。")
    raw = upload.read()
    if not raw:
        raise ValueError("CSV 文件为空。")
    try:
        text = raw.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            raise ValueError("CSV 缺少表头。")
        headers = {str(field or "").strip() for field in reader.fieldnames}
        missing = IMPORT_REQUIRED_FIELDS[entity] - headers
        if missing:
            raise ValueError(f"CSV 缺少必要字段：{'、'.join(sorted(missing))}。")
        rows = [{str(key or "").strip(): (value or "").strip() for key, value in row.items()} for row in reader]
    except UnicodeDecodeError as exc:
        raise ValueError("CSV 文件无法读取，请使用 UTF-8 或 UTF-8 BOM 编码。") from exc
    except csv.Error as exc:
        raise ValueError("CSV 文件格式无效。") from exc
    if not rows:
        raise ValueError("CSV 没有数据行。")
    if len(rows) > 5000:
        raise ValueError("CSV 最多允许 5000 行数据。")
    key = IMPORT_KEY_FIELDS[entity]
    duplicates = _duplicate_key_errors(rows, key)
    if duplicates:
        # File-level duplicate errors are returned by the preview with row data.
        for row, message in duplicates:
            rows[row - 2]["__import_error__"] = message
    return rows, hashlib.sha256(raw).hexdigest()


def _duplicate_key_errors(rows, key):
    seen, errors = {}, []
    for index, row in enumerate(rows, start=2):
        value = row.get(key, "").strip()
        if not value:
            continue
        if value in seen:
            errors.append((index, f"文件内业务主键 {key} 重复：{value}（首次出现在第 {seen[value]} 行）。"))
        else:
            seen[value] = index
    return errors


def _preview_import(entity, rows, user=None):
    created = updated = 0
    errors = []
    with transaction.atomic():
        for index, row in enumerate(rows, start=2):
            try:
                if row.get("__import_error__"):
                    raise ValueError(row["__import_error__"])
                with transaction.atomic():
                    was_created = _import_row(entity, row, user=user)
                created += int(was_created)
                updated += int(not was_created)
            except Exception as exc:
                errors.append({"row": index, "message": _import_error_message(exc), "key": row.get(IMPORT_KEY_FIELDS[entity], "")})
        transaction.set_rollback(True)
    return {"total": len(rows), "created": created, "updated": updated, "errors": errors}


def _apply_import_rows(entity, rows, user=None):
    created = updated = 0
    for row in rows:
        was_created = _import_row(entity, row, user=user)
        created += int(was_created)
        updated += int(not was_created)
    return created, updated


def _import_error_message(exc):
    if isinstance(exc, DRFValidationError):
        return _flatten_import_validation_error(exc.detail)
    if isinstance(exc, DjangoValidationError):
        return "；".join(exc.messages)
    return str(exc)


def _flatten_import_validation_error(detail):
    if isinstance(detail, dict):
        return "；".join(_flatten_import_validation_error(item) for item in detail.values())
    if isinstance(detail, (list, tuple)):
        return "；".join(_flatten_import_validation_error(item) for item in detail)
    return str(detail)


def _decimal(value, default="0"):
    try:
        return Decimal(value or default)
    except InvalidOperation as exc:
        raise ValueError(f"无效金额：{value}") from exc


def _import_row(entity, row, user=None):
    if entity == "orders":
        raise ValueError(ORDER_IMPORT_DISABLED_MESSAGE)
    if entity == "customers":
        instance = Customer.objects.filter(code=row["code"]).first()
        if instance and user is not None and not scope_customer_queryset(Customer.objects.filter(pk=instance.pk), user).exists():
            raise DjangoValidationError("该客户不在当前账号的数据范围内。")
        fields = ("name", "country", "source", "website", "address", "notes")
        payload = {field: row.get(field, "") for field in fields}
        serializer = CustomerSerializer(
            instance, data=payload, partial=bool(instance),
            context={"allow_import_without_contacts": True, "allow_import_code": True, "user": user},
        )
        serializer.is_valid(raise_exception=True)
        if instance:
            serializer.save()
            return False
        serializer.save(imported_code=row["code"])
        return True
    if entity == "products":
        category = None
        if row.get("category"):
            category = ProductCategory.objects.filter(name=row["category"]).first()
            if not category:
                raise ValueError("产品分类不存在，请先建立分类。")
        instance = Product.objects.filter(code=row["code"]).first()
        payload = {
            "name": row.get("name", ""), "category": category.pk if category else None,
            "description": row.get("description", ""), "status": row.get("status") or "active",
        }
        if row.get("sales_model_prefix"):
            payload["sales_model_prefix"] = row["sales_model_prefix"]
        serializer = ProductSerializer(instance, data=payload, partial=bool(instance), context={"allow_import_code": True})
        serializer.is_valid(raise_exception=True)
        if instance:
            serializer.save()
            return False
        serializer.save(imported_code=row["code"])
        return True
    if entity == "skus":
        product = Product.objects.get(code=row["product_code"])
        instance = SKU.objects.filter(sku=row["sku"]).first()
        payload = {
            "product": product.pk, "specification": row.get("specification", ""),
            "unit": row.get("unit") or "pcs", "cost_price": _decimal(row.get("cost_price")),
            "default_price": _decimal(row.get("default_price")), "currency": row.get("currency") or "USD",
        }
        serializer = SKUSerializer(instance, data=payload, partial=bool(instance))
        serializer.is_valid(raise_exception=True)
        if instance:
            serializer.save()
            return False
        serializer.save(sku=row["sku"])
        return True
    customer = Customer.objects.filter(code=row.get("customer_code")).first() if row.get("customer_code") else None
    order = Order.objects.filter(order_no=row.get("order_no")).first() if row.get("order_no") else None
    defaults = {"transaction_date": row["transaction_date"], "direction": row["direction"], "category": row["category"], "amount": _decimal(row["amount"]), "currency": row.get("currency") or "USD", "exchange_rate": _decimal(row.get("exchange_rate"), "1"), "customer": customer or (order.customer if order else None), "order": order, "payment_method": row.get("payment_method", ""), "reference": row.get("reference", ""), "notes": row.get("notes", "")}
    if Transaction.objects.filter(transaction_no=row["transaction_no"]).exists():
        raise DjangoValidationError("该流水号已存在，不能通过导入覆盖财务记录。")
    if row.get("customer_code") and not customer or row.get("order_no") and not order:
        raise DjangoValidationError("流水关联的客户或订单不存在。")
    if order and defaults["direction"] == "income":
        defaults["kind"] = "customer_receipt"
    payload = {**defaults, "transaction_no": row["transaction_no"], "customer": defaults["customer"].pk if defaults["customer"] else None, "order": order.pk if order else None}
    serializer = TransactionSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    record_transaction(serializer.validated_data)
    return True

