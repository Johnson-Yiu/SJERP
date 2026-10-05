from .trade_units import amount_expression, trade_values
import csv
import io
import json
import time
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from urllib.request import urlopen

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.db.models import Case, Count, DecimalField, ExpressionWrapper, F, IntegerField, OuterRef, Q, Subquery, Sum, Value, When
from django.db.models.functions import Coalesce, TruncMonth
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action, api_view, parser_classes
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from .models import AccessRole, CategoryAttribute, Contact, ContractChangeRequest, Customer, EmployeeProfile, FollowUp, FollowUpAttachment, GoodsReceipt, HSCode, InventoryMovement, OperationLog, Order, OrderItem, OrganizationUnit, PackagingTemplate, PackingPlan, PaymentPlan, Position, Product, ProductCategory, ProductCertificate, ProductParameter, PurchaseOrder, Quote, QuoteImportantNote, RolePermission, Shipment, ShipmentPackage, SKUPackagingProfile, SKU, Supplier, SupplierSKU, Transaction
from .permissions import HSCodeMaintenancePermission, PermissionAdminOnly, QuoteExportPermission
from .quote_numbers import allocate_revision_quote_no
from .quote_export import QuoteExportError, build_pi_export_payload
from .quote_snapshots import create_quote_items
from .serializers import AccessRoleSerializer, CancellationInputSerializer, CategoryAttributeSerializer, ContactSerializer, ContractChangeRequestSerializer, CustomerSerializer, EmployeeProfileSerializer, FollowUpAttachmentSerializer, FollowUpSerializer, GoodsReceiptSerializer, HSCodeSerializer, InventoryMovementReversalInputSerializer, InventoryMovementSerializer, OperationLogSerializer, OrderItemSerializer, OrderSerializer, OrganizationUnitSerializer, PackagingTemplateSerializer, PackingPlanSerializer, PaymentPlanSerializer, PositionSerializer, ProductCategorySerializer, ProductCertificateSerializer, ProductParameterSerializer, ProductSerializer, PurchaseOrderSerializer, ReceiptInputSerializer, ReceiptReversalInputSerializer, QuoteImportantNoteSerializer, QuoteSerializer, RolePermissionSerializer, ShipmentInputSerializer, ShipmentPackageSerializer, ShipmentReversalInputSerializer, TransactionVoidInputSerializer, SKUPackagingProfileSerializer, SKUSerializer, SKUVersionSerializer, SupplierPaymentInputSerializer, SupplierSerializer, SupplierSKUSerializer, TransactionSerializer, next_product_code
from .serializers import ProcurementDraftInputSerializer
from .audit import AuditTrailMixin, record_operation, snapshot
from .services.finance import allocate_advance, approve_contract_change, reject_contract_change, record_contract_payment, record_transaction, void_transaction
from .services.fulfillment import confirm_shipment, order_item_metrics, record_receipt, record_supplier_payment, reverse_manual_inventory_movement, reverse_receipt as reverse_receipt_service, reverse_shipment as reverse_shipment_service, sku_metrics
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
    permission_classes = [permissions.IsAuthenticated]
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
    queryset = PurchaseOrder.objects.select_related("supplier", "order").prefetch_related("items__sku", "items__supplier_sku__supplier", "items__receipts", "transactions")
    search_fields = ["purchase_no", "supplier__name", "order__order_no"]

    def get_queryset(self):
        queryset = super().get_queryset()
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
    permission_classes = [PermissionAdminOnly]

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
    permission_classes = [PermissionAdminOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(role_id=self.request.query_params["role"]) if self.request.query_params.get("role") else qs


class EmployeeProfileViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    serializer_class = EmployeeProfileSerializer
    queryset = EmployeeProfile.objects.select_related("user", "unit", "position").prefetch_related("roles")
    search_fields = ["display_name", "user__username", "unit__name", "position__name"]


@api_view(["GET"])
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
def current_operator(request):
    from django.conf import settings
    from .permissions import development_superadmin_enabled, is_permission_admin

    if development_superadmin_enabled():
        profile = getattr(request.user, "employee_profile", None)
        name = (profile.display_name if profile else request.user.get_full_name() or request.user.username) if request.user.is_authenticated else settings.DEFAULT_OPERATOR_NAME
        return Response({"name": name, "role": "超级管理员", "authenticated": request.user.is_authenticated,
                         "development_superadmin": True, "has_all_permissions": True, "data_scope": "all", "can_manage_hs_codes": True,
                         "audit_log_enabled": bool(request.user.is_authenticated and settings.AUDIT_LOG_ENABLED)})

    if request.user.is_authenticated:
        profile = getattr(request.user, "employee_profile", None)
        name = profile.display_name if profile else request.user.get_full_name() or request.user.username
        roles = list(profile.roles.values_list("name", flat=True)) if profile else []
        role = "超级管理员" if request.user.is_superuser else "、".join(roles) or "未分配角色"
        return Response({"name": name, "role": role, "authenticated": True, "development_superadmin": False,
                         "has_all_permissions": request.user.is_superuser, "can_manage_hs_codes": is_permission_admin(request.user), "audit_log_enabled": settings.AUDIT_LOG_ENABLED})
    return Response({"name": "未登录", "role": "未登录", "authenticated": False, "development_superadmin": False,
                     "has_all_permissions": False, "can_manage_hs_codes": False, "audit_log_enabled": False})


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
        return Customer.objects.annotate(
            contact_count=Coalesce(Subquery(contact_count, output_field=IntegerField()), 0),
            order_count=Coalesce(Subquery(order_count, output_field=IntegerField()), 0),
            sales_amount=Coalesce(Subquery(sales, output_field=MONEY), Decimal("0"), output_field=MONEY),
        ).order_by("-updated_at")

    @action(detail=False, methods=["get"], url_path="next-code")
    def next_code(self, request):
        from .models import CustomerCodeSequence
        from .serializers import customer_sequence_suffix

        sequence = CustomerCodeSequence.objects.filter(pk=1).first()
        next_value = (sequence.last_value if sequence else -1) + 1
        return Response({"code": f"{timezone.localdate():%Y%m%d}{customer_sequence_suffix(next_value)}"})

    @action(detail=False, methods=["get"])
    def sources(self, request):
        values = Customer.objects.exclude(source="").values_list("source", flat=True).distinct().order_by("source")
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
        qs = super().get_queryset()
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
        qs = super().get_queryset()
        if self.request.query_params.get("customer"):
            qs = qs.filter(customer_id=self.request.query_params["customer"])
        if self.request.query_params.get("due") == "true":
            qs = qs.filter(next_follow_up__lte=timezone.localdate())
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
    search_fields = ["code", "description", "notes"]

    def destroy(self, request, *args, **kwargs):
        if self.get_object().products.exists():
            return Response({"detail": "该编码仍有关联产品，请先解除分配，或将编码停用。"}, status=400)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["put"], url_path="assign-products")
    @transaction.atomic
    def assign_products(self, request, pk=None):
        hs_code = self.get_object()
        product_ids = request.data.get("product_ids")
        if not isinstance(product_ids, list) or any(not str(value).isdigit() for value in product_ids):
            return Response({"detail": "product_ids 必须为产品 ID 数组。"}, status=status.HTTP_400_BAD_REQUEST)
        normalized_ids = {int(value) for value in product_ids}
        if not hs_code.active and Product.objects.filter(id__in=normalized_ids).exclude(hs_code=hs_code).exists():
            return Response({"detail": "停用编码不能分配给新产品。"}, status=400)
        existing_ids = set(Product.objects.filter(id__in=normalized_ids).values_list("id", flat=True))
        if existing_ids != normalized_ids:
            return Response({"detail": "包含不存在的产品。"}, status=status.HTTP_400_BAD_REQUEST)
        before = {"product_ids": list(hs_code.products.order_by("id").values_list("id", flat=True))}
        Product.objects.filter(hs_code=hs_code).exclude(id__in=normalized_ids).update(hs_code=None)
        Product.objects.filter(id__in=normalized_ids).update(hs_code=hs_code)
        record_operation(request=request, instance=hs_code, action="custom", action_label="分配 HS 编码产品", before=before, after={"product_ids": sorted(normalized_ids)})
        return Response(self.get_serializer(HSCode.objects.annotate(product_count=Count("products", distinct=True)).get(pk=hs_code.pk)).data)


class SKUViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    @action(detail=False, methods=["post"], url_path="batch-create")
    @transaction.atomic
    def batch_create(self, request):
        items = request.data.get("items")
        if not isinstance(items, list) or not 1 <= len(items) <= 1000:
            return Response({"detail": "请选择 1–1000 个实际 SKU 组合。"}, status=400)
        result = []
        for item in items:
            serializer = self.get_serializer(data=item)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()
            record_operation(request=request, instance=instance, action="create", action_label="按需创建 SKU")
            result.append(serializer.data)
        return Response(result, status=201)

    serializer_class = SKUSerializer
    queryset = SKU.objects.select_related("product").prefetch_related("trade_units__supplier").annotate(
        stock_quantity=Coalesce(Sum(Case(
            When(inventory_movements__type__in=["sale_out", "adjust_out", "sample_out", "transfer_out", "production_out", "other_out"], then=-F("inventory_movements__quantity")),
            default=F("inventory_movements__quantity"), output_field=MONEY,
        )), Decimal("0"), output_field=MONEY),
        quote_count=Count("quote_items__quote", distinct=True),
        order_count=Count("order_items__order", distinct=True),
    ).order_by("sku")
    search_fields = ["sku", "display_name_cn", "sales_model", "specification", "description_cn", "description_en", "product__name", "product__name_en", "product__code", "supplier_skus__supplier_model", "supplier_skus__supplier_sku_code", "supplier_skus__supplier_product_name", "supplier_skus__supplier_barcode"]

    def get_queryset(self):
        qs = super().get_queryset()
        # 列表默认隐藏停用 SKU；但 retrieve / update 必须能读取它们，
        # 才能支持管理员重新启用软停用的 SKU。
        if self.action == "list" and self.request.query_params.get("include_inactive") != "1":
            qs = qs.filter(active=True)
        return qs.filter(product_id=self.request.query_params["product"]) if self.request.query_params.get("product") else qs

    def filter_queryset(self, queryset):
        # SearchFilter cannot express historical-version hits without then
        # filtering them away again, so SKU owns this one search contract.
        term = str(self.request.query_params.get("search", "")).strip()
        if not term:
            return super().filter_queryset(queryset)
        return queryset.filter(
            Q(sku__icontains=term) | Q(display_name_cn__icontains=term) |
            Q(sales_model__icontains=term) | Q(specification__icontains=term) |
            Q(description_cn__icontains=term) | Q(description_en__icontains=term) |
            Q(product__name__icontains=term) | Q(product__name_en__icontains=term) | Q(product__code__icontains=term) |
            Q(supplier_skus__supplier_model__icontains=term) | Q(supplier_skus__supplier_sku_code__icontains=term) |
            Q(supplier_skus__supplier_product_name__icontains=term) | Q(supplier_skus__supplier_barcode__icontains=term) |
            Q(versions__sku_code_snapshot__icontains=term) | Q(versions__sales_model_snapshot__icontains=term) |
            Q(versions__display_name_cn_snapshot__icontains=term) | Q(versions__description_cn_snapshot__icontains=term) |
            Q(versions__description_en_snapshot__icontains=term)
        ).distinct()

    def destroy(self, request, *args, **kwargs):
        return Response({"detail": "SKU 不允许物理删除。请将其停用，以保留库存、报价、订单和历史版本记录。"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"])
    def versions(self, request, pk=None):
        return Response(SKUVersionSerializer(self.get_object().versions.select_related("changed_by"), many=True).data)

    @action(detail=True, methods=["get"], url_path="supplier-skus")
    def supplier_skus(self, request, pk=None):
        rows = self.get_object().supplier_skus.select_related("supplier", "sku", "sku__product")
        return Response(SupplierSKUSerializer(rows, many=True).data)

    @action(detail=False, methods=["get"], url_path="sales-model-abbreviations")
    def sales_model_abbreviations(self, request):
        """Return saved parameter abbreviations, scoped strictly to one category."""
        category_id = request.query_params.get("category")
        if not category_id:
            return Response({"detail": "category 为必填参数。"}, status=status.HTTP_400_BAD_REQUEST)
        category = get_object_or_404(ProductCategory, pk=category_id)
        prefix = f"{category.id}:"
        suggestions = {}
        skus = SKU.objects.filter(
            Q(product__category=category) | Q(product__additional_categories=category)
        ).exclude(sales_model_abbreviations={}).order_by("id").distinct()
        for sku in skus:
            for stored_key, stored_value in (sku.sales_model_abbreviations or {}).items():
                key = str(stored_key)
                abbreviation = str(stored_value or "").strip().upper()
                if not key.startswith(prefix) or not abbreviation:
                    continue
                try:
                    attribute_key, raw_value = key[len(prefix):].split(":", 1)
                except ValueError:
                    continue
                suggestion_key = normalize_abbreviation_key(f"{category.id}:{attribute_key}:{raw_value}")
                suggestions.setdefault(suggestion_key, abbreviation)
        return Response({"abbreviations": suggestions, "defaults": DEFAULT_SALES_MODEL_ABBREVIATIONS})

    @action(detail=True, methods=["get"], url_path="inventory-detail")
    def inventory_detail(self, request, pk=None):
        sku = self.get_object()
        purchases = PurchaseOrder.objects.filter(items__sku=sku).select_related("supplier", "order").prefetch_related("items__receipts").distinct()
        shipments = Shipment.objects.filter(items__sku=sku).select_related("order__customer").prefetch_related("items").distinct()
        orders = Order.objects.filter(items__sku=sku).select_related("customer").prefetch_related("items", "items__shipment_items").distinct()
        movements = InventoryMovement.objects.filter(sku=sku).select_related("order").order_by("-movement_date", "-created_at")
        return Response({
            "sku": SKUSerializer(sku).data,
            "movements": InventoryMovementSerializer(movements, many=True).data,
            "purchases": [{
                "id": purchase.id, "purchase_no": purchase.purchase_no, "supplier_name": purchase.supplier.name,
                "order_no": purchase.order.order_no if purchase.order_id else "", "order_date": purchase.order_date,
                "status": purchase.status, "status_display": purchase.get_status_display(),
                "quantity": sum((item.quantity for item in purchase.items.filter(sku=sku)), Decimal("0")),
                "received_quantity": sum((item.received_quantity for item in purchase.items.filter(sku=sku)), Decimal("0")),
            } for purchase in purchases],
            "shipments": [{
                "id": shipment.id, "shipment_no": shipment.shipment_no, "shipment_date": shipment.shipment_date,
                "order_no": shipment.order.order_no, "customer_name": shipment.order.customer.name,
                "status": shipment.status, "status_display": shipment.get_status_display(),
                "quantity": sum((item.quantity for item in shipment.items.filter(sku=sku)), Decimal("0")),
            } for shipment in shipments],
            "orders": [{
                "id": order.id, "order_no": order.order_no, "customer_name": order.customer.name,
                "order_date": order.order_date, "status": order.status, "status_display": order.get_status_display(),
                "quantity": sum((item.quantity for item in order.items.filter(sku=sku)), Decimal("0")),
                "shipped_quantity": sum((
                    shipment_item.quantity for item in order.items.filter(sku=sku)
                    for shipment_item in item.shipment_items.filter(shipment__status="confirmed")
                ), Decimal("0")),
            } for order in orders],
        })

    @action(detail=True, methods=["get"])
    def thumbnail(self, request, pk=None):
        from .services.sku_images import thumbnail_response
        return thumbnail_response(self.get_object().image, request)

    @action(detail=True, methods=["post", "delete"], parser_classes=[MultiPartParser, FormParser])
    def image(self, request, pk=None):
        sku = self.get_object()
        if request.method == "DELETE":
            before = snapshot(sku)
            if sku.image:
                sku.image.delete(save=False)
            sku.image = ""
            sku.save(update_fields=["image"])
            record_operation(request=request, instance=sku, action="custom", action_label="删除 SKU 图片", before=before)
            return Response(self.get_serializer(sku).data)

        upload = request.FILES.get("image")
        allowed_mime_types = {"image/gif", "image/jpeg", "image/png", "image/webp"}
        if upload is None:
            return Response({"image": "请上传图片文件。"}, status=status.HTTP_400_BAD_REQUEST)
        if upload.content_type not in allowed_mime_types:
            return Response({"image": "仅支持 GIF、JPEG、PNG 或 WebP 图片。"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(sku, data={"image": upload}, partial=True)
        serializer.is_valid(raise_exception=True)
        before = snapshot(sku)
        serializer.save()
        record_operation(request=request, instance=sku, action="custom", action_label="上传 SKU 图片", before=before)
        return Response(serializer.data)

    @action(detail=True, methods=["get", "put"], url_path="packaging")
    def packaging(self, request, pk=None):
        sku = self.get_object()
        if request.method == "GET":
            try:
                profile = sku.packaging_profile
                return Response({"profile": SKUPackagingProfileSerializer(profile).data, "effective": packaging_summary(sku)})
            except SKUPackagingProfile.DoesNotExist:
                return Response({"profile": None, "effective": packaging_summary(sku)})
        with transaction.atomic():
            profile, created = SKUPackagingProfile.objects.get_or_create(sku=sku)
            if not created:
                profile = SKUPackagingProfile.objects.select_for_update().get(pk=profile.pk)
            before = snapshot(profile)
            serializer = SKUPackagingProfileSerializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            profile = serializer.save()
            if request.data.get("verify"):
                # Verification is deliberately recorded only after the final
                # effective values have been saved.
                profile.verified_at = timezone.now()
                profile.verified_by = request.user if request.user.is_authenticated else None
                profile.save(update_fields=["verified_at", "verified_by", "updated_at"])
            record_operation(request=request, instance=profile, action="create" if created else "update", action_label="保存 SKU 包装配置", before=before, metadata={"sku_id": sku.id, "verified": bool(request.data.get("verify"))})
        return Response({"profile": SKUPackagingProfileSerializer(profile).data, "effective": packaging_summary(sku)})


class PackagingTemplateViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    serializer_class = PackagingTemplateSerializer
    queryset = PackagingTemplate.objects.select_related("supplier").prefetch_related("sku_profiles")
    search_fields = ["code", "name", "supplier__name", "description"]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.sku_profiles.exists():
            return Response(
                {"detail": "该包装模板仍被 SKU 使用，不能删除；请先更换关联 SKU 的包装模板，或将模板停用。"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response({"detail": "该包装模板已被业务记录引用，不能删除；请将模板停用。"}, status=status.HTTP_400_BAD_REQUEST)


class SKUPackagingProfileViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    serializer_class = SKUPackagingProfileSerializer
    queryset = SKUPackagingProfile.objects.select_related("sku__product", "packaging_template")
    search_fields = ["sku__sku", "sku__product__name", "packaging_template__code"]

    def get_queryset(self):
        qs = super().get_queryset()
        status_value = self.request.query_params.get("status")
        if status_value:
            # Status is resolved, so only use this broad DB filter then resolve in list below.
            if status_value == "NOT_CONFIGURED": return qs.none()
        return qs


class ShipmentViewSet(AuditTrailMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.Serializer  # read endpoints below use explicit responses
    queryset = Shipment.objects.select_related("order").prefetch_related("packages__items__sku")

    @action(detail=True, methods=["post"], url_path="reverse")
    def reverse(self, request, pk=None):
        shipment = self.get_object()
        input_serializer = ShipmentReversalInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        try:
            shipment = reverse_shipment_service(shipment, input_serializer.validated_data["reason"])
        except DjangoValidationError as error:
            return Response({"detail": error.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        reversal_ids = list(shipment.items.values_list("reversal_inventory_movement_id", flat=True))
        record_operation(
            request=request,
            instance=shipment.order,
            action="custom",
            action_label="冲销销售发货",
            metadata={
                "shipment_id": shipment.id,
                "reversal_inventory_movement_id": reversal_ids[0] if len(reversal_ids) == 1 else reversal_ids,
                "reversal_inventory_movement_ids": reversal_ids,
                "reason": shipment.reversal_reason,
            },
        )
        return Response({
            "id": shipment.id,
            "shipment_no": shipment.shipment_no,
            "status": shipment.status,
            "reversed_at": shipment.reversed_at,
            "reversal_reason": shipment.reversal_reason,
            "reversal_inventory_movement_ids": reversal_ids,
        })

    @action(detail=True, methods=["get", "post"], url_path="packages")
    def packages(self, request, pk=None):
        shipment = self.get_object()
        if request.method == "GET":
            return Response(ShipmentPackageSerializer(shipment.packages.prefetch_related("items__sku"), many=True).data)
        serializer = ShipmentPackageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        package = serializer.save(shipment=shipment)
        record_operation(request=request, instance=shipment, action="custom", action_label="新增装箱明细", metadata={"package_id": package.id})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path=r"packages/(?P<package_id>[^/.]+)")
    def update_package(self, request, pk=None, package_id=None):
        shipment = self.get_object()
        package = get_object_or_404(ShipmentPackage, pk=package_id, shipment=shipment)
        before = snapshot(package)
        serializer = ShipmentPackageSerializer(package, data=request.data)
        serializer.is_valid(raise_exception=True); serializer.save()
        record_operation(request=request, instance=shipment, action="custom", action_label="修改装箱明细", before={"package": before}, metadata={"package_id": package.id})
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="copy-estimated-packing")
    def copy_estimated_packing(self, request, pk=None):
        shipment = self.get_object()
        plan = getattr(shipment.order, "packing_plan", None)
        if not plan: return Response({"detail": "该订单尚未生成预计装箱。"}, status=status.HTTP_400_BAD_REQUEST)
        copy_estimated_to_actual(shipment, plan)
        record_operation(request=request, instance=shipment, action="custom", action_label="复制预计装箱方案", metadata={"packing_plan_id": plan.id})
        return Response(ShipmentPackageSerializer(shipment.packages.prefetch_related("items__sku"), many=True).data)


class ProductParameterViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    serializer_class = ProductParameterSerializer
    queryset = ProductParameter.objects.select_related("product")
    search_fields = ["product__name", "product__code", "group", "name", "value"]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(product_id=self.request.query_params["product"]) if self.request.query_params.get("product") else qs


class ProductCertificateViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    serializer_class = ProductCertificateSerializer
    queryset = ProductCertificate.objects.select_related("product")
    search_fields = ["product__name", "name", "certificate_no", "issuer"]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(product_id=self.request.query_params["product"]) if self.request.query_params.get("product") else qs


class QuoteViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    serializer_class = QuoteSerializer
    queryset = Quote.objects.select_related("customer", "root_quote", "parent_quote").prefetch_related("items__sku__product")
    search_fields = ["quote_no", "customer__name"]
    ordering_fields = ["quote_date", "valid_until", "created_at", "updated_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("customer"):
            qs = qs.filter(customer_id=self.request.query_params["customer"])
        if self.request.query_params.get("status"):
            qs = qs.filter(status=self.request.query_params["status"])
        return qs.order_by("-updated_at", "-id")

    @action(detail=True, methods=["get"])
    def availability(self, request, pk=None):
        quote = self.get_object()
        return Response({"quote": quote.id, "items": [
            {"quote_item": item.id, "sku": item.sku_id,
             "available_quantity": sku_metrics(item.sku)["available_quantity"],
             "reference_lead_time_days": quote.lead_time_days}
            for item in quote.items.select_related("sku")
        ]})

    @action(detail=True, methods=["get", "post"], url_path="packing-plan")
    def packing_plan(self, request, pk=None):
        quote = self.get_object()
        if request.method == "POST":
            plan = generate_packing_plan(quote)
            record_operation(request=request, instance=quote, action="custom", action_label="生成报价装箱方案", metadata={"packing_plan_id": plan.id})
            return Response(PackingPlanSerializer(plan).data)
        plan = getattr(quote, "packing_plan", None)
        return Response(PackingPlanSerializer(plan).data if plan else {"detail": "尚未生成预计装箱。"}, status=status.HTTP_200_OK if plan else status.HTTP_404_NOT_FOUND)

    def update(self, request, *args, **kwargs):
        return Response({"detail": "已保存报价请创建迭代版本"}, status=status.HTTP_400_BAD_REQUEST)

    def _change_status(self, request, quote, target, allowed, label):
        # The action target may have changed after the request was routed.
        # Re-read it under a row lock so exactly one competing transition wins.
        quote = Quote.objects.select_for_update().get(pk=quote.pk)
        if quote.status not in allowed:
            return Response({"detail": "当前报价状态不能执行此操作，请创建修订版重新报价。"}, status=status.HTTP_400_BAD_REQUEST)
        before_status = quote.status
        quote.status = target
        quote.save(update_fields=["status", "updated_at"])
        record_operation(
            request=request,
            instance=quote,
            action="custom",
            action_label=label,
            before={"status": before_status},
            after={"status": target},
        )
        return Response(self.get_serializer(quote).data)

    @action(detail=True, methods=["post"], url_path="mark-sent")
    @transaction.atomic
    def mark_sent(self, request, pk=None):
        return self._change_status(request, self.get_object(), "sent", {"draft"}, "标记报价已发送")

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def accept(self, request, pk=None):
        return self._change_status(request, self.get_object(), "accepted", {"draft", "sent"}, "客户接受报价")

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def reject(self, request, pk=None):
        return self._change_status(request, self.get_object(), "rejected", {"draft", "sent"}, "客户拒绝报价")

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def expire(self, request, pk=None):
        return self._change_status(request, self.get_object(), "expired", {"sent"}, "报价过期")

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "Saved quotations are permanent records and cannot be deleted."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def _root_quote(self, quote):
        return quote.root_quote or quote

    @action(detail=True, methods=["get", "post"], url_path="important-notes")
    def important_notes(self, request, pk=None):
        quote = self.get_object()
        root_quote = self._root_quote(quote)
        notes = QuoteImportantNote.objects.filter(root_quote=root_quote).select_related("source_quote", "created_by", "deactivated_by")
        if request.method == "GET":
            return Response(QuoteImportantNoteSerializer(notes, many=True).data)

        serializer = QuoteImportantNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        creator = request.user if request.user.is_authenticated else None
        note = serializer.save(root_quote=root_quote, source_quote=quote, created_by=creator)
        record_operation(request=request, instance=quote, action="custom", action_label="新增报价重要备注", metadata={"note_id": note.id})
        return Response(QuoteImportantNoteSerializer(note).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path=r"important-notes/(?P<note_id>[^/.]+)/deactivate")
    def deactivate_important_note(self, request, pk=None, note_id=None):
        root_quote = self._root_quote(self.get_object())
        note = get_object_or_404(
            QuoteImportantNote.objects.select_related("source_quote", "created_by", "deactivated_by"),
            pk=note_id,
            root_quote=root_quote,
        )
        if note.is_active:
            note.is_active = False
            note.deactivated_at = timezone.now()
            note.deactivated_by = request.user if request.user.is_authenticated else None
            note.save(update_fields=["is_active", "deactivated_at", "deactivated_by", "updated_at"])
            record_operation(request=request, instance=note.source_quote, action="custom", action_label="停用报价重要备注", metadata={"note_id": note.id})
        return Response(QuoteImportantNoteSerializer(note).data)

    @action(detail=True, methods=["post"], url_path=r"important-notes/(?P<note_id>[^/.]+)/restore")
    def restore_important_note(self, request, pk=None, note_id=None):
        root_quote = self._root_quote(self.get_object())
        note = get_object_or_404(
            QuoteImportantNote.objects.select_related("source_quote", "created_by", "deactivated_by"),
            pk=note_id,
            root_quote=root_quote,
        )
        if not note.is_active:
            note.is_active = True
            note.save(update_fields=["is_active", "updated_at"])
            record_operation(request=request, instance=note.source_quote, action="custom", action_label="恢复报价重要备注", metadata={"note_id": note.id})
        return Response(QuoteImportantNoteSerializer(note).data)

    @action(detail=True, methods=["get"])
    def workbench(self, request, pk=None):
        quote = self.get_object()
        root_quote = self._root_quote(quote)
        revisions = Quote.objects.filter(Q(pk=root_quote.pk) | Q(root_quote=root_quote)).order_by("revision_no", "id")
        orders = Order.objects.filter(quote__in=revisions).select_related("quote", "customer").prefetch_related("items__sku__product", "transactions")
        notes = QuoteImportantNote.objects.filter(root_quote=root_quote).select_related("source_quote", "created_by", "deactivated_by")
        return Response({
            "quote": QuoteSerializer(quote).data,
            "root_quote_no": root_quote.quote_no,
            "revisions": QuoteSerializer(revisions, many=True).data,
            "orders": OrderSerializer(orders, many=True).data,
            "important_notes": QuoteImportantNoteSerializer(notes, many=True).data,
            "order_summary": {"count": orders.count()},
        })

    @action(detail=True, methods=["get"], url_path="order-draft")
    def order_draft(self, request, pk=None):
        quote = self.get_object()
        if quote.status in {"rejected", "expired"}:
            return Response(
                {"detail": "该报价已拒绝或过期，请先创建新的修订版后再转为订单。"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({
            "customer": quote.customer_id,
            "quote": quote.id,
            "order_date": timezone.localdate(),
            "expected_ship_date": None,
            "status": "draft",
            "currency": quote.currency,
            "exchange_rate": quote.exchange_rate,
            "shipping_fee": quote.shipping_fee,
            "discount": quote.discount,
            "notes": quote.notes,
            "items": [
                {
                    "sku": item.sku_id,
                    "sku_code": item.sku_code_snapshot,
                    "sales_model_snapshot": item.sales_model_snapshot,
                    "model": item.sales_model_snapshot,
                    "display_name_snapshot": item.product_name_snapshot,
                    "description_snapshot": item.description,
                    "description": item.description,
                    "unit_snapshot": item.unit_snapshot,
                    **{**trade_values(item), "trade_unit": item.trade_unit_id},
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "cost_price": item.sku.cost_price,
                    "notes": item.notes,
                }
                for item in quote.items.select_related("sku")
            ],
        })

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def revise(self, request, pk=None):
        source = self.get_object()
        revision_summary = str(request.data.get("revision_summary", "")).strip()
        if not revision_summary:
            raise serializers.ValidationError({"revision_summary": "请简要说明本次修改的内容。"})
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        changes = serializer.validated_data.copy()
        item_data = changes.pop("items", None)
        if "customer" in changes and changes["customer"].pk != source.customer_id:
            raise serializers.ValidationError({"customer": "修订版本不能更换客户。"})
        root_quote = source.root_quote or source
        try:
            quote_no, revision_no = allocate_revision_quote_no(source)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(getattr(exc, "message_dict", exc.messages)) from exc
        copied_fields = [
            "customer", "quote_date", "valid_until", "status", "currency", "exchange_rate",
            "shipping_fee", "discount", "notes", "recipient_name", "buyer_address",
            "buyer_email", "buyer_phone", "lead_time_days", "deposit_ratio", "trading_terms",
            "shipping_details", "buyer_company_name",
        ]
        quote_values = {field: getattr(source, field) for field in copied_fields}
        quote_values.update(changes)
        quote_values["status"] = "draft"
        revision = Quote.objects.create(
            quote_no=quote_no,
            root_quote=root_quote,
            parent_quote=source,
            revision_no=revision_no,
            revision_summary=revision_summary,
            **quote_values,
        )
        if item_data is None:
            source_items = list(source.items.select_related("sku__product"))
            item_data = [
                {
                    "sku": item.sku,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "description": item.description,
                    "notes": item.notes,
                    **trade_values(item),
                }
                for item in source_items
            ]
            create_quote_items(revision, item_data, source_items=source_items)
        else:
            create_quote_items(revision, item_data)
        record_operation(request=request, instance=revision, action="create", action_label="创建报价迭代版本", metadata={"parent_quote_id": source.id, "revision_summary": revision_summary})
        record_operation(request=request, instance=source, action="custom", action_label="创建报价迭代版本", metadata={"revision_id": revision.id, "revision_summary": revision_summary})
        return Response(self.get_serializer(revision).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="pi-data")
    def pi_data(self, request, pk=None):
        quote = self.get_object()
        products = []
        subtotal = Decimal("0")
        for item in quote.items.all():
            amount = item.amount
            subtotal += amount
            products.append({
                # ``sku`` remains the legacy/internal field for old clients;
                # customer-facing callers must use ``model``.
                "sku": item.sku_code_snapshot,
                "sku_code": item.sku_code_snapshot,
                "model": item.sales_model_snapshot,
                "sales_model": item.sales_model_snapshot,
                "product_name": item.product_name_snapshot,
                "display_name": item.product_name_snapshot,
                "description": item.description + (f"\n{item.trade_snapshot['name']}: 1 {item.trade_snapshot['unit']} = {item.trade_snapshot['factor']} {item.trade_snapshot['base_unit']}; Total {item.quantity} {item.trade_snapshot['base_unit']}" if item.trade_unit_id else ""),
                "quantity": item.trade_quantity if item.trade_unit_id else item.quantity,
                "base_quantity": item.quantity,
                "trade_snapshot": item.trade_snapshot,
                "unit_price": item.trade_unit_price if item.trade_unit_id else item.unit_price,
                "amount": amount,
                "unit": item.trade_snapshot.get("unit", item.unit_snapshot),
                "image_url": request.build_absolute_uri(item.image_snapshot.url) if item.image_snapshot else "",
            })
        total_amount = quote.total_amount
        deposit_amount = (total_amount * quote.deposit_ratio).quantize(Decimal("0.01"))
        return Response({
            "invoice_no": quote.quote_no,
            "buyer": {
                "company_name": quote.buyer_company_name,
                "name": quote.recipient_name,
                "address": quote.buyer_address,
                "email": quote.buyer_email,
                "phone": quote.buyer_phone,
            },
            "terms": {
                "quote_date": quote.quote_date,
                "valid_until": quote.valid_until,
                "lead_time_days": quote.lead_time_days,
                "trading_terms": quote.trading_terms,
                "shipping_details": quote.shipping_details,
                "notes": quote.notes,
            },
            "totals": {
                "currency": quote.currency,
                "subtotal": subtotal,
                "shipping_fee": quote.shipping_fee,
                "discount": quote.discount,
                "total_amount": total_amount,
            },
            "payment_splits": {
                "deposit_ratio": quote.deposit_ratio,
                "deposit_amount": deposit_amount,
                "balance_ratio": Decimal("1") - quote.deposit_ratio,
                "balance_amount": total_amount - deposit_amount,
            },
            "products": products,
        })

    @action(detail=True, methods=["get"], permission_classes=[QuoteExportPermission])
    def export(self, request, pk=None):
        quote = self.get_object()
        try:
            content = build_pi_export_payload(quote)
        except QuoteExportError:
            return Response(
                {"detail": "PI workbook generation failed."},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        response = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{quote.quote_no}.xlsx"'
        return response


class OrderViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    queryset = Order.objects.select_related("customer", "quote").prefetch_related("items__sku__product", "items__supplier_sku__supplier", "transactions")
    search_fields = ["order_no", "customer__name"]
    ordering_fields = ["order_date", "expected_ship_date", "created_at"]

    def create(self, request, *args, **kwargs):
        if request.data.get("status") not in (None, "", "draft"):
            return Response({"detail": "新建订单只能保存为草稿，请使用确认订单动作。"}, status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if "status" in request.data:
            return Response({"detail": "订单状态只能通过确认、开始生产、发货、完成或取消等业务动作变更。"}, status=status.HTTP_400_BAD_REQUEST)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        order = self.get_object()
        if order.status != "draft":
            return Response({"detail": "正式订单不能删除，请使用取消订单。"}, status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        try:
            with transaction.atomic():
                order = confirm_order(self.get_object())
                record_operation(
                    request=request,
                    instance=order,
                    action="custom",
                    action_label="确认销售订单",
                    metadata={
                        "quote_id": order.quote_id,
                        "quote_no": order.quote.quote_no if order.quote_id else "",
                    },
                )
        except DjangoValidationError as error:
            return Response({"detail": error.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=["post"], url_path="start-production")
    def start_production(self, request, pk=None):
        try:
            with transaction.atomic():
                order = start_order_production(self.get_object())
                record_operation(request=request, instance=order, action="custom", action_label="开始订单生产")
        except DjangoValidationError as error:
            return Response({"detail": error.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        try:
            with transaction.atomic():
                order = complete_order(self.get_object())
                record_operation(request=request, instance=order, action="custom", action_label="完成销售订单")
        except DjangoValidationError as error:
            return Response({"detail": error.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        input_serializer = CancellationInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                order = cancel_order(self.get_object(), input_serializer.validated_data["reason"])
                record_operation(
                    request=request,
                    instance=order,
                    action="custom",
                    action_label="取消销售订单",
                    metadata={"reason": order.cancellation_reason},
                )
        except DjangoValidationError as error:
            return Response({"detail": error.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(order).data)

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("customer"):
            qs = qs.filter(customer_id=self.request.query_params["customer"])
        if self.request.query_params.get("quote"):
            qs = qs.filter(quote_id=self.request.query_params["quote"])
        if self.request.query_params.get("product"):
            qs = qs.filter(items__sku__product_id=self.request.query_params["product"]).distinct()
        if self.request.query_params.get("sku"):
            qs = qs.filter(items__sku_id=self.request.query_params["sku"]).distinct()
        if self.request.query_params.get("status"):
            qs = qs.filter(status=self.request.query_params["status"])
        todo = self.request.query_params.get("todo")
        if todo == "unshipped":
            qs = qs.filter(status__in=["confirmed", "production"])
        elif todo == "due":
            qs = qs.filter(
                status__in=["confirmed", "production"],
                expected_ship_date__isnull=False,
                expected_ship_date__lte=timezone.localdate(),
            )
        return qs

    @action(detail=True, methods=["get"])
    def fulfillment(self, request, pk=None):
        order = self.get_object()
        draft_quantities = draft_procurement_quantities(order)
        rows = []
        for item in order.items.select_related("sku"):
            metrics = order_item_metrics(item)
            rows.append({
                "id": item.id, "sku": item.sku_id, "sku_code": item.sku_code_snapshot or item.sku.sku,
                "base_unit": item.trade_snapshot.get("base_unit", item.unit_snapshot or item.sku.unit),
                "sales_model": item.sales_model_snapshot,
                "display_name": item.display_name_snapshot,
                "quantity": item.quantity, "allocated_quantity": metrics["allocated_quantity"],
                "to_procure_quantity": metrics["to_procure_quantity"],
                "draft_procurement_quantity": draft_quantities[item.id],
                "draftable_quantity": max(Decimal("0"), metrics["to_procure_quantity"] - draft_quantities[item.id]),
                "purchased_quantity": metrics["purchased_quantity"],
                "in_transit_quantity": metrics["in_transit_quantity"],
                "arrived_quantity": metrics["received_quantity"],
                "shipped_quantity": metrics["shipped_quantity"],
                "unshipped_quantity": metrics["unshipped_quantity"],
                "supplier_sku": item.supplier_sku_id,
                "supplier_name": item.supplier_name_snapshot,
                "supplier_model": item.supplier_model_snapshot,
                "supplier_sku_code": item.supplier_sku_code_snapshot,
            })
        purchase_orders = PurchaseOrder.objects.filter(items__cost_allocations__target_type="order", items__cost_allocations__order=order).distinct().select_related("supplier").prefetch_related("items__receipts")
        shipments = Shipment.objects.filter(order=order).prefetch_related("items__sku")
        return Response({
            "order": OrderSerializer(order).data,
            "items": rows,
            "purchase_orders": PurchaseOrderSerializer(purchase_orders, many=True).data,
            "shipments": [{
                "id": shipment.id, "shipment_no": shipment.shipment_no,
                "shipment_date": shipment.shipment_date, "status": shipment.status,
                "reversed_at": shipment.reversed_at, "reversal_reason": shipment.reversal_reason,
                "has_overage": any(line.is_overage for line in shipment.items.all()),
                "items": [{
                    "id": line.id, "sku_code": line.sku.sku, "quantity": line.quantity,
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
        return Response({
            "created_count": len(purchases),
            "purchase_orders": PurchaseOrderSerializer(purchases, many=True).data,
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
    valid_orders = Order.objects.filter(status__in=formal_statuses)
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
    categories = OrderItem.objects.filter(order__status__in=formal_statuses, order__order_date__gte=year_start).values(
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
    return Response({
        "summary": {
            "sales_ytd": sales_between(year_start, today),
            "sales_last_ytd": sales_between(last_year_start, last_year_same_day),
            "orders_ytd": valid_orders.filter(order_date__gte=year_start).count(),
            "active_customers": Customer.objects.filter(status__in=["customer", "company"]).count(),
            "receipts_rmb": income,
            "payments_rmb": expense,
            "follow_ups_due": Customer.objects.filter(next_follow_up__isnull=False, next_follow_up__lte=today).count(),
        },
        "monthly_sales": monthly,
        "category_sales": list(categories),
        "top_customers": list(top_customers),
        "recent_orders": OrderSerializer(valid_orders.prefetch_related("items__sku__product")[:5], many=True).data,
        "due_follow_ups": FollowUpSerializer(
            FollowUp.objects.annotate(
                latest_for_customer_id=Subquery(
                    FollowUp.objects.filter(customer_id=OuterRef("customer_id"))
                    .order_by("-followed_at", "-id")
                    .values("id")[:1]
                )
            )
            .filter(id=F("latest_for_customer_id"), next_follow_up__lte=today)
            .select_related("customer", "contact")
            .prefetch_related("attachments")
            .order_by("next_follow_up", "id")[:5],
            many=True,
        ).data,
    })


IMPORT_FIELDS = {
    "customers": ["code", "name", "country", "source", "owner", "website", "address", "notes"],
    "products": ["code", "name", "sales_model_prefix", "category", "description", "status"],
    "skus": ["sku", "product_code", "specification", "unit", "cost_price", "default_price", "currency"],
    "transactions": ["transaction_no", "transaction_date", "direction", "category", "amount", "currency", "exchange_rate", "customer_code", "order_no", "payment_method", "reference", "notes"],
}
ORDER_IMPORT_DISABLED_MESSAGE = "正式订单导入暂未开放，请通过订单业务流程创建；避免绕过报价、库存预留和收款计划。"


@api_view(["GET"])
def import_templates(request):
    return Response(IMPORT_FIELDS)


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def import_csv(request):
    entity = request.data.get("entity")
    upload = request.FILES.get("file")
    if entity == "orders":
        return Response({"detail": ORDER_IMPORT_DISABLED_MESSAGE}, status=status.HTTP_400_BAD_REQUEST)
    if entity not in IMPORT_FIELDS or not upload:
        return Response({"detail": "请选择有效的数据类型和 CSV 文件。"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        text = upload.read().decode("utf-8-sig")
        rows = list(csv.DictReader(io.StringIO(text)))
    except (UnicodeDecodeError, csv.Error):
        return Response({"detail": "CSV 文件无法读取，请使用 UTF-8 编码。"}, status=status.HTTP_400_BAD_REQUEST)

    created, updated, errors = 0, 0, []
    for index, row in enumerate(rows, start=2):
        try:
            with transaction.atomic():
                was_created = _import_row(entity, {k: (v or "").strip() for k, v in row.items()})
                created += int(was_created)
                updated += int(not was_created)
        except Exception as exc:
            errors.append({"row": index, "message": str(exc)})
    return Response({"total": len(rows), "created": created, "updated": updated, "errors": errors})


def _decimal(value, default="0"):
    try:
        return Decimal(value or default)
    except InvalidOperation as exc:
        raise ValueError(f"无效金额：{value}") from exc


def _import_row(entity, row):
    if entity == "orders":
        raise ValueError(ORDER_IMPORT_DISABLED_MESSAGE)
    if entity == "customers":
        instance = Customer.objects.filter(code=row["code"]).first()
        fields = ("name", "country", "source", "owner", "website", "address", "notes")
        payload = {field: row.get(field, "") for field in fields}
        serializer = CustomerSerializer(
            instance, data=payload, partial=bool(instance),
            context={"allow_import_without_contacts": True, "allow_import_code": True},
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
