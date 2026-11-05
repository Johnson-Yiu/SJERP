from .procurement_scope import validate_cost_writes, scoped_cost_summary, require_cost_allocation_updates, require_order_writes
from .finance_scope import scope_transaction_queryset, scope_plan_queryset, validate_finance_relations, require_finance_permission, ContractFinancePermission
from .trade_units import amount_expression, trade_values
import csv
import hashlib
import io
import json
import time
import uuid
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from urllib.request import urlopen

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.db.models import Case, CharField, Count, DecimalField, ExpressionWrapper, F, IntegerField, OuterRef, Q, Subquery, Sum, Value, When
from django.db.models.functions import Coalesce, TruncMonth
from django.db.models.functions import Cast
from django.http import Http404, HttpResponse
from django.core import signing
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action, api_view, parser_classes, permission_classes
from rest_framework.exceptions import NotFound, ValidationError as DRFValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from .models import AccessRole, CategoryAttribute, Contact, ContractChangeRequest, CSVImportBatch, CSVImportPreviewAudit, CSVImportRowAudit, Customer, CustomerSupplierPreference, EmployeeProfile, FollowUp, FollowUpAttachment, GoodsReceipt, HSCode, InventoryMovement, OperationLog, Order, OrderItem, OrganizationUnit, PackagingTemplate, PackingPlan, PaymentPlan, Position, Product, ProductCategory, ProductCertificate, ProductParameter, PurchaseMOQException, PurchaseOrder, Quote, QuoteImportantNote, RolePermission, Shipment, ShipmentPackage, SKUPackagingProfile, SKU, SharedReportTemplate, Supplier, SupplierSKU, Transaction
from .country_registry import CountryResolutionError, country_options as build_country_options, country_stored_values, display_country
from .error_messages import CUSTOMER_NOT_FOUND_MESSAGE
from .money import CURRENT_AMOUNT_CALCULATION_VERSION
from .querysets import current_due_follow_ups, prefetch_purchase_related_orders
from .permissions import HSCodeMaintenancePermission, ModuleActionPermission, OrganizationOverviewPermission, PermissionAdminOnly, QuoteExportPermission, _profile_for, effective_permission_matrix, has_all_permissions, is_permission_admin, user_can
from .sales_scope import allowed_employee_ids, data_scope_display, effective_data_scope, employee_profile_for, scope_customer_queryset, scope_customer_related_queryset
from .quote_numbers import allocate_revision_quote_no
from .quote_export import QuoteExportError, build_pi_export_payload
from .quotation_export_dto import QuotationExportValidationError, build_quotation_export_dto
from .quote_snapshots import create_quote_items
from .serializers import protected_media_url, certificate_expiry, AccessRoleSerializer, CancellationInputSerializer, CategoryAttributeSerializer, ContactSerializer, ContractChangeRequestSerializer, CustomerSerializer, EmployeeProfileSerializer, FollowUpAttachmentSerializer, FollowUpSerializer, GoodsReceiptSerializer, HSCodeSerializer, InventoryMovementReversalInputSerializer, InventoryMovementSerializer, OperationLogSerializer, OrderItemSerializer, OrderSerializer, OrganizationUnitSerializer, PackagingTemplateSerializer, PackingPlanSerializer, PaymentPlanSerializer, PositionSerializer, ProductCategorySerializer, ProductCertificateSerializer, ProductParameterSerializer, ProductSerializer, PurchaseOrderSerializer, ReceiptInputSerializer, ReceiptReversalInputSerializer, QuoteAvailabilityPreviewInputSerializer, QuoteImportantNoteSerializer, QuoteSerializer, RolePermissionSerializer, ShipmentInputSerializer, ShipmentPackageSerializer, ShipmentReversalInputSerializer, TransactionVoidInputSerializer, SKUPackagingProfileSerializer, SKUSerializer, SKUVersionSerializer, SupplierPaymentInputSerializer, SupplierSerializer, SupplierSKUSerializer, TransactionSerializer, next_product_code
from .serializers import ProcurementDraftInputSerializer
from .audit import AuditTrailMixin, record_operation, snapshot
from .services.finance import allocate_advance, approve_contract_change, reject_contract_change, record_contract_payment, record_transaction, void_transaction
from .services.attachments import delete_follow_up_attachment, upload_follow_up_attachments
from .services.fulfillment import (
    begin_fulfillment_idempotency,
    bulk_sku_metrics,
    complete_fulfillment_idempotency,
    confirm_shipment,
    FulfillmentIdempotencyConflict,
    json_safe_fulfillment_response,
    inventory_baseline_expression,
    order_item_metrics,
    record_receipt,
    record_supplier_payment,
    require_fulfillment_idempotency_key,
    reverse_manual_inventory_movement,
    reverse_receipt as reverse_receipt_service,
    reverse_shipment as reverse_shipment_service,
)
from .services.order_lifecycle import cancel_order, complete_order, confirm_order, start_order_production
from .services.packaging import copy_estimated_to_actual, generate_packing_plan, packaging_summary
from .services.packing_list import (
    PackingListExportError,
    XLSX_CONTENT_TYPE,
    render_packing_list_xlsx,
    safe_packing_list_filename,
)
from .services.purchase_lifecycle import PurchaseMOQExceptionRequired, cancel_purchase_order, place_purchase_order
from .services.procurement import build_procurement_plan, create_purchase_drafts, draft_procurement_quantities
from .services.order_quantity_adjustments import QuantityAdjustmentConflict, apply_quantity_adjustment, preview_quantity_adjustment, redact_quantity_adjustment_response, serialize_adjustment
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


def _quantity_adjustment_visibility(user):
    return {
        "include_financial": user_can(user, "finance", "view") and user_can(user, "transactions", "view"),
        "include_procurement": user_can(user, "purchases", "view"),
    }


def _quantity_adjustment_error_message(error, user):
    messages = getattr(error, "messages", None) or [str(error)]
    message = "；".join(str(value) for value in messages)
    if not _quantity_adjustment_visibility(user)["include_financial"] and any(
        term in message for term in ("应收", "已收金额", "订单金额", "未结应收", "退款", "资金")
    ):
        return "数量变更包含受权限保护的财务校验，当前账号不能继续。"
    return messages[0]


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
        entity = (self.request.query_params.get("entity") or "").lower()
        object_id = self.request.query_params.get("object_id")
        if entity:
            qs = qs.filter(entity=entity)
        else:
            return qs.none()
        object_ids = None
        if entity == "crm.customer":
            object_ids = scope_customer_queryset(Customer.objects.all(), self.request.user)
        elif entity == "crm.contact":
            object_ids = scope_customer_related_queryset(Contact.objects.all(), self.request.user)
        elif entity == "crm.followup":
            object_ids = scope_customer_related_queryset(FollowUp.objects.all(), self.request.user)
        elif entity == "crm.quote":
            object_ids = scope_customer_related_queryset(Quote.objects.all(), self.request.user)
        elif entity == "crm.order":
            object_ids = scope_customer_related_queryset(Order.objects.all(), self.request.user)
        elif entity == "crm.shipment":
            if not user_can(self.request.user, "orders", "view"):
                return qs.none()
            object_ids = scope_customer_related_queryset(Shipment.objects.all(), self.request.user, relation="order__customer")
        elif entity == "crm.transaction":
            object_ids = scope_transaction_queryset(Transaction.objects.all(), self.request.user)
        elif entity == "crm.paymentplan":
            object_ids = scope_plan_queryset(PaymentPlan.objects.all(), self.request.user)
        elif entity == "crm.contractchangerequest":
            changes = ContractChangeRequest.objects.none()
            if user_can(self.request.user, "orders", "view"):
                changes = changes | scope_customer_related_queryset(
                    ContractChangeRequest.objects.filter(order__isnull=False), self.request.user, relation="order__customer",
                )
            if user_can(self.request.user, "purchases", "view"):
                changes = changes | ContractChangeRequest.objects.filter(purchase_order__isnull=False)
            object_ids = changes
        elif entity == "crm.sharedreporttemplate":
            if not user_can(self.request.user, "reports", "update"):
                from .report_templates import visible_template_ids
                object_ids = SharedReportTemplate.objects.filter(
                    pk__in=visible_template_ids(SharedReportTemplate.objects.all(), self.request.user),
                )
        elif entity == "crm.customersupplierpreference":
            object_ids = CustomerSupplierPreference.objects.filter(
                customer__in=scope_customer_queryset(Customer.objects.all(), self.request.user),
            )
        if object_ids is not None:
            qs = qs.filter(object_id__in=object_ids.values_list(Cast("pk", output_field=CharField()), flat=True))
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

    def get_queryset(self):
        queryset = super().get_queryset()
        active_only = str(self.request.query_params.get("active_only", "")).lower() in {"1", "true", "yes"}
        if active_only:
            queryset = queryset.filter(is_active=True)
        return queryset

    def _set_active(self, request, pk, is_active):
        with transaction.atomic():
            supplier = get_object_or_404(Supplier.objects.select_for_update(), pk=pk)
            before = snapshot(supplier)
            if supplier.is_active != is_active:
                supplier.is_active = is_active
                supplier.save(update_fields=["is_active", "updated_at"])
            record_operation(
                request=request,
                instance=supplier,
                action="custom",
                action_label="启用供应商" if is_active else "停用供应商",
                before=before,
                metadata={"is_active": is_active},
            )
        return Response(self.get_serializer(supplier).data)

    @action(detail=True, methods=["post"], url_path="deactivate")
    def deactivate(self, request, pk=None):
        return self._set_active(request, pk, False)

    @action(detail=True, methods=["post"], url_path="activate")
    def activate(self, request, pk=None):
        return self._set_active(request, pk, True)

    def destroy(self, request, *args, **kwargs):
        return Response({"detail": "供应商不支持永久删除，请使用停用操作。"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=True, methods=["get"], url_path="supplier-skus")
    def supplier_skus(self, request, pk=None):
        supplier = self.get_object()
        rows = supplier.supplier_skus.select_related("sku", "sku__product").order_by("sku__sku", "id")
        return Response(SupplierSKUSerializer(rows, many=True, context={"request": request}).data)


class SupplierSKUViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    serializer_class = SupplierSKUSerializer
    queryset = SupplierSKU.objects.select_related("supplier", "sku", "sku__product").prefetch_related("purchase_items", "inventory_movements")
    search_fields = [
        "supplier_sku_code", "supplier_model", "supplier_product_name", "supplier_barcode",
        "supplier__name", "sku__sku", "sku__sales_model", "sku__display_name_cn", "sku__product__name",
    ]

    def get_search_fields(self, request):
        fields = list(self.search_fields)
        if not user_can(request.user, "skus", "view"):
            fields = [field for field in fields if not field.startswith("sku__")]
        if not user_can(request.user, "products", "view"):
            fields = [field for field in fields if "product__" not in field]
        return fields

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("sku"):
            require_finance_permission(self.request.user, "skus", "view")
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
            "items__sku", "items__supplier_sku__supplier", "items__receipts", "transactions", "moq_exception__operator"
        )
    )
    search_fields = ["purchase_no", "supplier__name", "visible_order_search"]

    def get_search_fields(self, request):
        fields = list(self.search_fields)
        if not user_can(request.user, "suppliers", "view"):
            fields.remove("supplier__name")
        if not user_can(request.user, "orders", "view"):
            fields.remove("visible_order_search")
        return fields

    def get_queryset(self):
        queryset = super().get_queryset()
        from django.db.models import Case, When, Value, CharField, F
        from .procurement_scope import visible_order_ids
        historical_requested = self.request.query_params.get("status") == "historical"
        if self.action == "list":
            queryset = queryset.filter(historical_only=True, status="historical") if historical_requested else queryset.filter(historical_only=False)
        ids = visible_order_ids(self.request.user, Order.objects.values_list("pk", flat=True))
        queryset = queryset.annotate(visible_order_search=Case(When(order_id__in=ids, then=F("order__order_no")), default=Value(""), output_field=CharField()))
        sku_id = self.request.query_params.get("sku")
        if sku_id:
            require_finance_permission(self.request.user, "skus", "view")
            queryset = queryset.filter(items__sku_id=sku_id).distinct()
        purchase_status = self.request.query_params.get("status")
        if purchase_status:
            queryset = queryset.filter(status=purchase_status)
        if self.request.query_params.get("pending_receipt") == "1":
            queryset = queryset.filter(status__in=["ordered", "partial"])
        return queryset

    def create(self, request, *args, **kwargs):
        if request.data.get("is_historical") or request.data.get("status") == "historical":
            return Response({"detail": "历史采购订单请使用历史订单录入入口。"}, status=status.HTTP_400_BAD_REQUEST)
        if request.data.get("status") not in (None, "", "draft"):
            return Response({"detail": "新建采购单只能保存为草稿，请使用确认下单动作。"}, status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)

    @action(detail=False, methods=["post"], url_path="historical")
    def create_historical(self, request, *args, **kwargs):
        if request.data.get("status") not in (None, "", "historical") or request.data.get("is_historical") not in (None, "", True, "true", "1"):
            return Response({"detail": "历史采购订单必须通过历史录入模式创建。"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data=request.data, context={"request": request, "historical_mode": True})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(self.get_serializer(serializer.instance).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        purchase = self.get_object()
        if purchase.historical_only or purchase.status == "historical":
            return Response({"detail": "历史采购记录不能直接覆盖；请通过受控追溯更正保留原始轨迹。"}, status=status.HTTP_400_BAD_REQUEST)
        if hasattr(purchase, "history_continuation"):
            return Response({"detail": "历史接续采购单不能直接覆盖，请通过正式变更或审计更正处理。"}, status=status.HTTP_400_BAD_REQUEST)
        if "status" in request.data:
            return Response({"detail": "采购单状态只能通过确认下单、到货或取消等业务动作变更。"}, status=status.HTTP_400_BAD_REQUEST)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        purchase = self.get_object()
        if hasattr(purchase, "history_continuation"):
            return Response({"detail": "历史接续采购单必须保留，请使用取消或审计更正。"}, status=status.HTTP_400_BAD_REQUEST)
        if purchase.status != "draft":
            return Response({"detail": "正式采购单不能删除，请使用取消采购。"}, status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def place(self, request, pk=None):
        reason = request.data.get("moq_exception_reason", "")
        try:
            with transaction.atomic():
                purchase = place_purchase_order(self.get_object(), moq_exception_reason=reason, operator=request.user)
                try:
                    exception = purchase.moq_exception
                except PurchaseMOQException.DoesNotExist:
                    exception = None
                record_operation(
                    request=request,
                    instance=purchase,
                    action="custom",
                    action_label="确认采购下单",
                    metadata={
                        "purchase_order_id": purchase.id,
                        "purchase_no": purchase.purchase_no,
                        "moq_exception_id": exception.id if exception else None,
                        "moq_exception_reason": exception.reason if exception else "",
                        "moq_exception_details": exception.details if exception else [],
                    },
                )
        except PurchaseMOQExceptionRequired as error:
            return Response({"code": error.code, "detail": error.messages[0], "exceptions": error.exceptions}, status=status.HTTP_400_BAD_REQUEST)
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
        if purchase.historical_only or purchase.status == "historical":
            return Response({"detail": "历史采购订单仅用于经营分析，不能建立正式成本归属。"}, status=status.HTTP_400_BAD_REQUEST)
        input_serializer = CostInput(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        validate_cost_writes(purchase, request.user, input_serializer.validated_data["allocations"])
        return Response(scoped_cost_summary(preview_costs(purchase, input_serializer.validated_data), request.user))

    @action(detail=True, methods=["get", "post"], url_path="cost-allocation")
    def cost_allocation(self, request, pk=None):
        from .services.purchase_costs import CostInput, cost_summary, save_costs
        purchase = self.get_object()
        if purchase.historical_only or purchase.status == "historical":
            return Response({"detail": "历史采购订单仅用于经营分析，不能建立正式成本归属。"}, status=status.HTTP_400_BAD_REQUEST)
        if request.method == "GET":
            return Response(scoped_cost_summary(cost_summary(purchase), request.user))
        input_serializer = CostInput(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            purchase = PurchaseOrder.objects.select_for_update().get(pk=purchase.pk)
            validate_cost_writes(purchase, request.user, input_serializer.validated_data["allocations"])
            before = cost_summary(purchase)
            result = save_costs(purchase, input_serializer.validated_data)
            audit_before = json.loads(json.dumps({"cost_allocation": before}, default=str))
            audit_after = json.loads(json.dumps({"cost_allocation": result}, default=str))
            record_operation(
                request=request,
                instance=purchase,
                action="custom",
                action_label="采购成本分配",
                before=audit_before,
                after=audit_after,
                metadata={"purchase_no": purchase.purchase_no},
            )
        return Response(scoped_cost_summary(result, request.user))

    @action(detail=False, methods=["get"], url_path="cost-allocation-orders")
    def cost_allocation_orders(self, request):
        """Return only the identifiers needed by the purchasing allocator."""
        require_cost_allocation_updates(request.user)
        search = (request.query_params.get("search") or "").strip()
        orders = Order.objects.exclude(status="cancelled").order_by("order_no")
        if search:
            orders = orders.filter(order_no__icontains=search)
        return Response([
            {
                "id": order.pk,
                "order_no": order.order_no,
                "status": order.status,
                "status_display": order.get_status_display(),
            }
            for order in orders
        ])

    @action(detail=True, methods=["post"])
    def receive(self, request, pk=None):
        require_finance_permission(request.user, "inventory", "create")
        purchase = self.get_object()
        try:
            idempotency_key = require_fulfillment_idempotency_key(request)
        except DjangoValidationError as error:
            return Response({"detail": error.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        input_serializer = ReceiptInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        item = purchase.items.filter(pk=input_serializer.validated_data["purchase_item"]).first()
        if item is None:
            return Response({"detail": "到货明细不属于该采购单。"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            with transaction.atomic():
                idempotency, replay = begin_fulfillment_idempotency(
                    key=idempotency_key,
                    operation="receive",
                    target_id=purchase.pk,
                    payload=input_serializer.validated_data,
                    operator_id=request.user.pk if getattr(request.user, "is_authenticated", False) else None,
                )
                if replay:
                    replay_response = Response(idempotency.response_payload, status=idempotency.response_status)
                    replay_response["Idempotent-Replay"] = "true"
                    return replay_response
                purchase = PurchaseOrder.objects.select_for_update().get(pk=purchase.pk)
                before = snapshot(purchase)
                receipt = record_receipt(item, input_serializer.validated_data)
                response_payload = json_safe_fulfillment_response({
                    "id": receipt.id,
                    "purchase_item": receipt.purchase_item_id,
                    "quantity": receipt.quantity,
                    **{**trade_values(receipt), "trade_unit": receipt.trade_unit_id},
                    "is_overage": receipt.is_overage,
                    "inventory_movement": receipt.inventory_movement_id,
                })
                purchase.refresh_from_db()
                after = snapshot(purchase)
                record_operation(request=request, instance=purchase, action="custom", action_label="登记采购到货", before=before, after=after, metadata={"receipt_id": receipt.id, "quantity": str(receipt.quantity), "inventory_movement_id": receipt.inventory_movement_id})
                complete_fulfillment_idempotency(idempotency, response_payload)
        except FulfillmentIdempotencyConflict as error:
            return Response({"detail": error.messages[0]}, status=status.HTTP_409_CONFLICT)
        except DjangoValidationError as error:
            return Response({"detail": error.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(response_payload, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path=r"receipts/(?P<receipt_id>[^/.]+)/reverse")
    def reverse_receipt(self, request, pk=None, receipt_id=None):
        require_finance_permission(request.user, "inventory", "update")
        purchase = self.get_object()
        receipt = get_object_or_404(GoodsReceipt, pk=receipt_id, purchase_item__purchase_order=purchase)
        input_serializer = ReceiptReversalInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                purchase = PurchaseOrder.objects.select_for_update().get(pk=purchase.pk)
                before = snapshot(purchase)
                receipt = reverse_receipt_service(receipt, input_serializer.validated_data["reason"])
                purchase.refresh_from_db()
                after = snapshot(purchase)
                record_operation(
                    request=request,
                    instance=purchase,
                    action="custom",
                    action_label="冲销采购入库",
                    before=before,
                    after=after,
                    metadata={
                        "receipt_id": receipt.id,
                        "reversal_inventory_movement_id": receipt.reversal_inventory_movement_id,
                        "reason": receipt.reversal_reason,
                    },
                )
        except DjangoValidationError as error:
            return Response({"detail": error.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(GoodsReceiptSerializer(receipt, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def pay(self, request, pk=None):
        require_finance_permission(request.user, "transactions", "create")
        require_finance_permission(request.user, "finance", "update")
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
        return Response(TransactionSerializer(payment, context={"request": request}).data, status=status.HTTP_201_CREATED)


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

    def get_object(self):
        try:
            return super().get_object()
        except Http404 as error:
            # Keep an out-of-scope customer indistinguishable from an unknown
            # customer while avoiding Django's English model-name detail.
            raise NotFound(CUSTOMER_NOT_FOUND_MESSAGE) from error

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
        queryset = scope_customer_queryset(queryset, self.request.user)
        for key in ("status", "country", "owner_profile"):
            value = self.request.query_params.get(key)
            if value:
                if key == "country":
                    try:
                        country_values = country_stored_values(value)
                    except CountryResolutionError:
                        queryset = queryset.filter(country=value)
                    else:
                        country_query = Q()
                        for stored_value in country_values:
                            country_query |= Q(country__iexact=stored_value)
                        queryset = queryset.filter(country_query)
                else:
                    queryset = queryset.filter(**{key: value})
        return queryset.order_by("-updated_at")

    @action(detail=False, methods=["get"], url_path="owner-options")
    def owner_options(self, request):
        employees = EmployeeProfile.objects.filter(pk__in=allowed_employee_ids(request.user), active=True).select_related("unit")
        return Response([{"id": employee.pk, "display_name": employee.display_name, "unit_name": employee.unit.name, "label": f"{employee.display_name} · {employee.unit.name}"} for employee in employees])

    @action(detail=False, methods=["get"], url_path="country-options")
    def country_options(self, request):
        countries = (
            scope_customer_queryset(Customer.objects.all(), request.user)
            .exclude(country="")
            .values_list("country", flat=True)
            .distinct()
            .order_by("country")
        )
        return Response([{"value": country, "label": display_country(country) or country} for country in countries])

    @action(detail=False, methods=["get"], url_path="country-catalog")
    def country_catalog(self, request):
        legacy_countries = (
            scope_customer_queryset(Customer.objects.all(), request.user)
            .exclude(country="")
            .values_list("country", flat=True)
            .distinct()
            .order_by("country")
        )
        return Response(build_country_options(legacy_countries))

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
        can_view_orders = user_can(request.user, "orders", "view")
        can_view_followups = user_can(request.user, "followups", "view")
        can_view_products = user_can(request.user, "products", "view")
        year = timezone.localdate().year
        formal_statuses = ["confirmed", "production", "shipped", "completed"]
        yearly = []
        for target in ([year - 1, year] if can_view_orders else []):
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
            "customer": CustomerSerializer(customer, context={"request": request}).data,
            "yearly": yearly,
            "top_products": list(products) if can_view_orders and can_view_products else [],
            "recent_orders": OrderSerializer(customer.orders.exclude(status="cancelled").order_by("-order_date", "-id").prefetch_related("items__sku__product")[:5], many=True, context={"request": request}).data if can_view_orders else [],
            "recent_follow_ups": FollowUpSerializer(customer.follow_ups.select_related("contact")[:5], many=True, context={"request": request}).data if can_view_followups else [],
        })

    def destroy(self, request, *args, **kwargs):
        customer = self.get_object()
        if customer.new_product_reminders.exists() or customer.follow_ups.exists() or customer.quotes.exists() or customer.orders.exists() or customer.transactions.exists():
            return Response({"detail": "该客户已有业务历史，不能删除；请保留客户档案。"}, status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)


class ContactViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    queryset = Contact.objects.select_related("customer")
    serializer_class = ContactSerializer
    search_fields = ["name", "email", "phone", "customer__name"]

    def get_search_fields(self, request):
        return list(self.search_fields) if user_can(request.user, "customers", "view") else ["name", "email", "phone"]

    def get_queryset(self):
        qs = scope_customer_related_queryset(super().get_queryset(), self.request.user)
        if self.request.query_params.get("customer"):
            require_finance_permission(self.request.user, "customers", "view")
            return qs.filter(customer_id=self.request.query_params["customer"])
        return qs

    def destroy(self, request, *args, **kwargs):
        contact = self.get_object()
        if contact.follow_ups.exists() or contact.newproductreminder_set.exists():
            return Response({"detail": "该联系人已有跟进历史，不能删除。"}, status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)


class FollowUpViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    queryset = FollowUp.objects.select_related("customer", "contact").prefetch_related("attachments")
    serializer_class = FollowUpSerializer
    search_fields = ["subject", "content", "customer__name", "owner"]

    def get_search_fields(self, request):
        fields = list(self.search_fields)
        if not user_can(request.user, "customers", "view"):
            fields.remove("customer__name")
        return fields
    ordering_fields = ["followed_at", "next_follow_up", "created_at"]

    @action(detail=False, methods=["get"])
    def methods(self, request):
        builtins = [{"value": value, "label": label} for value, label in FollowUp.TYPE_CHOICES]
        builtin_values = {item["value"] for item in builtins}
        visible_follow_ups = scope_customer_related_queryset(FollowUp.objects.all(), request.user)
        custom = visible_follow_ups.exclude(type="").values_list("type", flat=True).distinct().order_by("type")
        return Response(builtins + [{"value": value, "label": value} for value in custom if value not in builtin_values])

    @action(detail=False, methods=["get"], url_path="owner-options")
    def owner_options(self, request):
        owners = (
            scope_customer_related_queryset(FollowUp.objects.all(), request.user)
            .exclude(owner="")
            .values_list("owner", flat=True)
            .distinct()
            .order_by("owner")
        )
        return Response([{"value": owner, "label": owner} for owner in owners])

    def get_queryset(self):
        qs = scope_customer_related_queryset(super().get_queryset(), self.request.user)
        if self.request.query_params.get("customer"):
            require_finance_permission(self.request.user, "customers", "view")
            qs = qs.filter(customer_id=self.request.query_params["customer"])
        if self.request.query_params.get("due") == "true":
            qs = current_due_follow_ups(qs, today=timezone.localdate())
        for key in ("type", "owner"):
            value = self.request.query_params.get(key)
            if value:
                qs = qs.filter(**{key: value})
        date_from = self.request.query_params.get("from")
        date_to = self.request.query_params.get("to")
        if date_from:
            qs = qs.filter(followed_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(followed_at__date__lte=date_to)
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
        attachments = upload_follow_up_attachments(
            request=request,
            follow_up=follow_up,
            uploads=uploads,
        )
        return Response(FollowUpAttachmentSerializer(attachments, many=True, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path=r"attachments/(?P<attachment_id>[^/.]+)")
    def delete_attachment(self, request, pk=None, attachment_id=None):
        follow_up = self.get_object()
        attachment = get_object_or_404(FollowUpAttachment, pk=attachment_id, follow_up=follow_up)
        delete_follow_up_attachment(
            request=request,
            follow_up=follow_up,
            attachment=attachment,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def destroy(self, request, *args, **kwargs):
        if self.get_object().new_product_reminders.exists():
            return Response({"detail": "该跟进有关联新品提醒，不能删除。"}, status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)


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

    def get_search_fields(self, request):
        fields = list(self.search_fields)
        if not user_can(request.user, "hs_codes", "view"):
            fields.remove("hs_code__code")
        if not user_can(request.user, "categories", "view"):
            fields.remove("category__name")
        return fields

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
        require_finance_permission(request.user, "orders", "view")
        require_finance_permission(request.user, "customers", "view")
        product = self.get_object()
        scoped_orders = scope_customer_related_queryset(
            Order.objects.filter(status__in=["confirmed", "production", "shipped", "completed"]),
            request.user,
        )
        rows = OrderItem.objects.filter(
            sku__product=product,
            order__in=scoped_orders,
        ).values(
            "order__customer__id", "order__customer__name", "order__customer__country"
        ).annotate(
            sales=Sum(ExpressionWrapper(amount_expression("") * F("order__exchange_rate"), output_field=MONEY)),
            order_count=Count("order", distinct=True), quantity=Sum("quantity"),
        ).order_by("-sales")
        return Response(list(rows))

    def destroy(self, request, *args, **kwargs):
        product = self.get_object()
        if product.skus.exists() or product.newproductreminder_set.exists():
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
    @transaction.atomic
    def perform_create(self, serializer):
        super().perform_create(serializer)

    @transaction.atomic
    def perform_update(self, serializer):
        super().perform_update(serializer)

    @action(detail=False, methods=["post"], url_path="batch-create")
    @transaction.atomic
    def batch_create(self, request):
        items = request.data.get("items")
        if not isinstance(items, list) or not 1 <= len(items) <= 1000:
            return Response({"detail": "请选择 1–1000 个实际 SKU 组合。"}, status=400)
        serializers = [self.get_serializer(data=item) for item in items]
        for serializer in serializers:
            serializer.is_valid(raise_exception=True)
        result = []
        for serializer in serializers:
            instance = serializer.save()
            record_operation(request=request, instance=instance, action="create", action_label="按需创建 SKU")
            result.append(serializer.data)
        return Response(result, status=201)

    serializer_class = SKUSerializer
    queryset = SKU.objects.select_related("product").prefetch_related("trade_units__supplier").annotate(
        stock_quantity=Coalesce(Sum(Case(
            When(inventory_movements__type__in=["sale_out", "adjust_out", "sample_out", "transfer_out", "production_out", "other_out"], then=-F("inventory_movements__quantity")),
            default=F("inventory_movements__quantity"), output_field=MONEY,
        )), Decimal("0"), output_field=MONEY) + inventory_baseline_expression(),
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
        if self.request.query_params.get("product"):
            require_finance_permission(self.request.user, "products", "view")
            return qs.filter(product_id=self.request.query_params["product"])
        return qs

    @action(detail=False, methods=["get"], url_path="inventory-list")
    def inventory_list(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page if page is not None else queryset, many=True)
        inventory_fields = (
            "id", "sku", "display_name_cn", "product_name", "product_code", "unit",
            "stock_quantity", "actual_quantity", "reserved_quantity", "available_quantity",
            "in_transit_quantity", "to_procure_quantity", "has_anomaly",
        )
        rows = [{field: row[field] for field in inventory_fields} for row in serializer.data]
        return self.get_paginated_response(rows) if page is not None else Response(rows)

    def filter_queryset(self, queryset):
        # SearchFilter cannot express historical-version hits without then
        # filtering them away again, so SKU owns this one search contract.
        term = str(self.request.query_params.get("search", "")).strip()
        if not term:
            return super().filter_queryset(queryset)
        conditions = [
            Q(sku__icontains=term), Q(display_name_cn__icontains=term),
            Q(sales_model__icontains=term), Q(specification__icontains=term),
            Q(description_cn__icontains=term), Q(description_en__icontains=term),
            Q(versions__sku_code_snapshot__icontains=term), Q(versions__sales_model_snapshot__icontains=term),
            Q(versions__display_name_cn_snapshot__icontains=term), Q(versions__description_cn_snapshot__icontains=term),
            Q(versions__description_en_snapshot__icontains=term),
        ]
        if user_can(self.request.user, "products", "view"):
            conditions.extend([Q(product__name__icontains=term), Q(product__name_en__icontains=term), Q(product__code__icontains=term)])
        if user_can(self.request.user, "suppliers", "view"):
            conditions.extend([
                Q(supplier_skus__supplier_model__icontains=term), Q(supplier_skus__supplier_sku_code__icontains=term),
                Q(supplier_skus__supplier_product_name__icontains=term), Q(supplier_skus__supplier_barcode__icontains=term),
            ])
        search = conditions[0]
        for condition in conditions[1:]:
            search |= condition
        return queryset.filter(search).distinct()

    def destroy(self, request, *args, **kwargs):
        return Response({"detail": "SKU 不允许物理删除。请将其停用，以保留库存、报价、订单和历史版本记录。"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"])
    def versions(self, request, pk=None):
        return Response(SKUVersionSerializer(self.get_object().versions.select_related("changed_by"), many=True).data)

    @action(detail=True, methods=["get"], url_path="supplier-skus")
    def supplier_skus(self, request, pk=None):
        from rest_framework.exceptions import PermissionDenied
        if not user_can(request.user, "suppliers", "view"):
            raise PermissionDenied("查看供应商来源需要供应商模块权限。")
        rows = self.get_object().supplier_skus.select_related("supplier", "sku", "sku__product")
        return Response(SupplierSKUSerializer(rows, many=True, context={"request": request}).data)

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
        scoped_orders = scope_customer_related_queryset(
            Order.objects.filter(items__sku=sku), request.user,
        )
        shipments = (
            Shipment.objects.filter(items__sku=sku, order__in=scoped_orders)
            .select_related("order__customer").prefetch_related("items").distinct()
        )
        orders = (
            scoped_orders.select_related("customer")
            .prefetch_related("items", "items__shipment_items").distinct()
        )
        movements = InventoryMovement.objects.filter(sku=sku).select_related("order").order_by("-movement_date", "-created_at")
        can_view_orders = user_can(request.user, "orders", "view")
        can_view_customers = user_can(request.user, "customers", "view")
        can_view_purchases = user_can(request.user, "purchases", "view")
        purchase_order_ids = purchases.exclude(order_id=None).values_list("order_id", flat=True)
        visible_purchase_order_ids = set(scope_customer_related_queryset(
            Order.objects.filter(pk__in=purchase_order_ids), request.user,
        ).values_list("pk", flat=True)) if can_view_orders else set()
        return Response({
            "sku": {"id": sku.id, "sku": sku.sku, "display_name_cn": sku.display_name_cn, "unit": sku.unit},
            "movements": InventoryMovementSerializer(movements, many=True, context={"request": request}).data,
            "purchases": [{
                "id": purchase.id, "purchase_no": purchase.purchase_no, "supplier_name": purchase.supplier.name if user_can(request.user, "suppliers", "view") else "",
                "order_no": purchase.order.order_no if purchase.order_id in visible_purchase_order_ids else "", "order_date": purchase.order_date,
                "status": purchase.status, "status_display": purchase.get_status_display(),
                "quantity": sum((item.quantity for item in purchase.items.filter(sku=sku)), Decimal("0")),
                "received_quantity": sum((item.received_quantity for item in purchase.items.filter(sku=sku)), Decimal("0")),
            } for purchase in purchases] if can_view_purchases else [],
            "shipments": [{
                "id": shipment.id, "shipment_no": shipment.shipment_no, "shipment_date": shipment.shipment_date,
                "order": shipment.order_id if can_view_orders else None,
                "order_no": shipment.order.order_no if can_view_orders else "",
                "customer_name": shipment.order.customer.name if can_view_customers else "",
                "status": shipment.status, "status_display": shipment.get_status_display(),
                "quantity": sum((item.quantity for item in shipment.items.filter(sku=sku)), Decimal("0")),
            } for shipment in shipments] if can_view_orders else [],
            "orders": [{
                "id": order.id, "order_no": order.order_no, "customer_name": order.customer.name if can_view_customers else "",
                "order_date": order.order_date, "status": order.status, "status_display": order.get_status_display(),
                "quantity": sum((item.quantity for item in order.items.filter(sku=sku)), Decimal("0")),
                "shipped_quantity": sum((
                    shipment_item.quantity for item in order.items.filter(sku=sku)
                    for shipment_item in item.shipment_items.filter(shipment__status="confirmed")
                ), Decimal("0")),
            } for order in orders] if can_view_orders else [],
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
                return Response({"profile": SKUPackagingProfileSerializer(profile, context={"request": request}).data, "effective": packaging_summary(sku)})
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
        return Response({"profile": SKUPackagingProfileSerializer(profile, context={"request": request}).data, "effective": packaging_summary(sku)})


class PackagingTemplateViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    serializer_class = PackagingTemplateSerializer
    queryset = PackagingTemplate.objects.select_related("supplier").prefetch_related("sku_profiles")
    search_fields = ["code", "name", "supplier__name", "description"]

    def get_search_fields(self, request):
        return list(self.search_fields) if user_can(request.user, "suppliers", "view") else ["code", "name", "description"]

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

    def get_search_fields(self, request):
        fields = ["packaging_template__code"]
        if user_can(request.user, "skus", "view"):
            fields.append("sku__sku")
        if user_can(request.user, "products", "view"):
            fields.append("sku__product__name")
        return fields

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

    def get_queryset(self):
        if not user_can(self.request.user, "orders", "view"):
            return self.queryset.none()
        return scope_customer_related_queryset(super().get_queryset(), self.request.user, relation="order__customer")

    @staticmethod
    def _require_order_update(user):
        require_finance_permission(user, "orders", "update")

    @action(detail=True, methods=["get"], url_path="export-packing-list")
    def export_packing_list(self, request, pk=None):
        require_finance_permission(request.user, "inventory", "export")
        require_finance_permission(request.user, "orders", "view")
        require_finance_permission(request.user, "skus", "view")
        shipment = self.get_object()
        try:
            content = render_packing_list_xlsx(
                shipment,
                include_hs_code=user_can(request.user, "hs_codes", "view"),
            )
        except PackingListExportError as error:
            return Response(
                {"detail": str(error), "differences": error.differences},
                status=status.HTTP_400_BAD_REQUEST,
            )
        response = HttpResponse(content, content_type=XLSX_CONTENT_TYPE)
        response["Content-Disposition"] = f'attachment; filename="{safe_packing_list_filename(shipment.shipment_no)}"'
        return response

    @action(detail=True, methods=["post"], url_path="reverse")
    @transaction.atomic
    def reverse(self, request, pk=None):
        self._require_order_update(request.user)
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
    @transaction.atomic
    def packages(self, request, pk=None):
        require_finance_permission(request.user, "skus", "view")
        shipment = self.get_object()
        if request.method == "GET":
            return Response(ShipmentPackageSerializer(shipment.packages.prefetch_related("items__sku"), many=True, context={"request": request}).data)
        self._require_order_update(request.user)
        shipment = Shipment.objects.select_for_update().get(pk=shipment.pk)
        serializer = ShipmentPackageSerializer(data=request.data, context={"shipment": shipment, "request": request})
        serializer.is_valid(raise_exception=True)
        package = serializer.save(shipment=shipment)
        record_operation(request=request, instance=shipment, action="custom", action_label="新增装箱明细", metadata={"package_id": package.id})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post", "put", "patch", "delete"], url_path=r"packages/(?P<package_id>[^/.]+)")
    @transaction.atomic
    def update_package(self, request, pk=None, package_id=None):
        require_finance_permission(request.user, "skus", "view")
        self._require_order_update(request.user)
        shipment = self.get_object()
        shipment = Shipment.objects.select_for_update().get(pk=shipment.pk)
        if shipment.status != "confirmed":
            return Response({"detail": "只有已确认的发货单可以修改实际箱单。"}, status=status.HTTP_400_BAD_REQUEST)
        package = get_object_or_404(ShipmentPackage, pk=package_id, shipment=shipment)
        before = snapshot(package)
        if request.method == "DELETE":
            package.delete()
            record_operation(request=request, instance=shipment, action="custom", action_label="删除装箱明细", before={"package": before}, metadata={"package_id": package_id})
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = ShipmentPackageSerializer(package, data=request.data, partial=request.method == "PATCH", context={"shipment": shipment, "request": request})
        serializer.is_valid(raise_exception=True); serializer.save()
        record_operation(request=request, instance=shipment, action="custom", action_label="修改装箱明细", before={"package": before}, metadata={"package_id": package.id})
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="copy-estimated-packing")
    @transaction.atomic
    def copy_estimated_packing(self, request, pk=None):
        require_finance_permission(request.user, "skus", "view")
        self._require_order_update(request.user)
        shipment = self.get_object()
        shipment = Shipment.objects.select_for_update().get(pk=shipment.pk)
        if shipment.status != "confirmed":
            return Response({"detail": "只有已确认的发货单可以修改实际箱单。"}, status=status.HTTP_400_BAD_REQUEST)
        plan = getattr(shipment.order, "packing_plan", None)
        if not plan: return Response({"detail": "该订单尚未生成预计装箱。"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            copy_estimated_to_actual(shipment, plan, replace=request.data.get("replace") is True)
        except DjangoValidationError as error:
            return Response({"detail": error.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        record_operation(request=request, instance=shipment, action="custom", action_label="复制预计装箱方案", metadata={"packing_plan_id": plan.id})
        return Response(ShipmentPackageSerializer(shipment.packages.prefetch_related("items__sku"), many=True, context={"request": request}).data)


class ProductParameterViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    serializer_class = ProductParameterSerializer
    queryset = ProductParameter.objects.select_related("product")
    search_fields = ["product__name", "product__code", "group", "name", "value"]

    def get_search_fields(self, request):
        return list(self.search_fields) if user_can(request.user, "products", "view") else ["group", "name", "value"]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("product"):
            require_finance_permission(self.request.user, "products", "view")
            return qs.filter(product_id=self.request.query_params["product"])
        return qs


class ProductCertificateViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    serializer_class = ProductCertificateSerializer
    queryset = ProductCertificate.objects.select_related("product")
    search_fields = ["product__name", "name", "certificate_no", "issuer"]

    def get_search_fields(self, request):
        return list(self.search_fields) if user_can(request.user, "products", "view") else ["name", "certificate_no", "issuer"]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("product"):
            require_finance_permission(self.request.user, "products", "view")
            qs = qs.filter(product_id=self.request.query_params["product"])
        today = timezone.localdate()
        expiry = self.request.query_params.get("expiry")
        filters = {
            "attention": {"expires_on__lte": today + timedelta(days=90)},
            "expired": {"expires_on__lt": today},
            "expiring": {"expires_on__range": (today, today + timedelta(days=90))},
            "valid": {"expires_on__gt": today + timedelta(days=90)},
            "no_expiry": {"expires_on__isnull": True},
        }
        if expiry in filters:
            qs = qs.filter(**filters[expiry]).order_by("expires_on", "id")
        return qs


class QuoteViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    serializer_class = QuoteSerializer
    queryset = Quote.objects.select_related("customer", "root_quote", "parent_quote").prefetch_related("items__sku__product")
    search_fields = ["quote_no", "customer__name"]

    @action(detail=False, methods=["get"], url_path="preview-template")
    def preview_template(self, request):
        """Draft-only display data; a revision must use its parent's saved source."""
        from .quote_template_snapshot import QuoteTemplateSnapshotError, capture_template, resolve_quote_template
        template_id = "standard_en_with_discount" if request.query_params.get("discount") == "1" else "standard_en_no_discount"
        try:
            quote_id = request.query_params.get("quote_id")
            if quote_id:
                quote = self.get_queryset().filter(pk=quote_id).first()
                if quote is None:
                    return Response({"detail": "报价不存在或无权查看。"}, status=status.HTTP_404_NOT_FOUND)
                snapshot = resolve_quote_template(quote, template_id)
            else:
                snapshot = capture_template(template_id)
        except (QuoteTemplateSnapshotError, ValueError):
            return Response({"detail": "卖方或模板来源缺失，请核实后再预览。"}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        return Response({"seller": snapshot["seller"], "bank": snapshot["bank"], "bank_notice": snapshot["notice"]})

    def get_search_fields(self, request):
        return list(self.search_fields) if user_can(request.user, "customers", "view") else ["quote_no"]
    ordering_fields = ["quote_date", "valid_until", "created_at", "updated_at"]

    def get_queryset(self):
        qs = scope_customer_related_queryset(super().get_queryset(), self.request.user)
        if self.request.query_params.get("customer"):
            qs = qs.filter(customer_id=self.request.query_params["customer"])
        if self.request.query_params.get("status"):
            qs = qs.filter(status=self.request.query_params["status"])
        return qs.order_by("-updated_at", "-id")

    @action(detail=False, methods=["post"], url_path="availability-preview")
    def availability_preview(self, request):
        require_finance_permission(request.user, "inventory", "view")
        require_finance_permission(request.user, "skus", "view")
        serializer = QuoteAvailabilityPreviewInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sku_ids = list(dict.fromkeys(serializer.validated_data["sku_ids"]))
        found_ids = set(SKU.objects.filter(pk__in=sku_ids).values_list("pk", flat=True))
        unknown_ids = [sku_id for sku_id in sku_ids if sku_id not in found_ids]
        if unknown_ids:
            return Response(
                {"sku_ids": [f"未知 SKU ID：{', '.join(str(sku_id) for sku_id in unknown_ids)}"]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        metrics = bulk_sku_metrics(sku_ids)
        return Response({"items": [
            {
                "sku": sku_id,
                "actual_quantity": f"{metrics[sku_id]['actual_quantity']:.2f}",
                "reserved_quantity": f"{metrics[sku_id]['reserved_quantity']:.2f}",
                "available_quantity": f"{metrics[sku_id]['available_quantity']:.2f}",
                "in_transit_quantity": f"{metrics[sku_id]['in_transit_quantity']:.2f}",
            }
            for sku_id in sku_ids
        ]})

    @action(detail=True, methods=["get"])
    def availability(self, request, pk=None):
        require_finance_permission(request.user, "inventory", "view")
        require_finance_permission(request.user, "skus", "view")
        quote = self.get_object()
        items = list(quote.items.select_related("sku").order_by("id"))
        metrics = bulk_sku_metrics(item.sku_id for item in items)
        return Response({"quote": quote.id, "items": [
            {
                "quote_item": item.id,
                "sku": item.sku_id,
                "actual_quantity": f"{metrics[item.sku_id]['actual_quantity']:.2f}",
                "reserved_quantity": f"{metrics[item.sku_id]['reserved_quantity']:.2f}",
                "available_quantity": metrics[item.sku_id]["available_quantity"],
                "in_transit_quantity": f"{metrics[item.sku_id]['in_transit_quantity']:.2f}",
                "reference_lead_time_days": quote.lead_time_days,
            }
            for item in items
        ]})

    @action(detail=True, methods=["get", "post"], url_path="packing-plan")
    def packing_plan(self, request, pk=None):
        quote = self.get_object()
        require_finance_permission(request.user, "skus", "view")
        if request.method == "POST":
            plan = generate_packing_plan(quote)
            record_operation(request=request, instance=quote, action="custom", action_label="生成报价装箱方案", metadata={"packing_plan_id": plan.id})
            return Response(PackingPlanSerializer(plan, context={"request": request}).data)
        plan = getattr(quote, "packing_plan", None)
        return Response(PackingPlanSerializer(plan, context={"request": request}).data if plan else {"detail": "尚未生成预计装箱。"}, status=status.HTTP_200_OK if plan else status.HTTP_404_NOT_FOUND)

    def update(self, request, *args, **kwargs):
        return Response({"detail": "已保存报价请创建迭代版本"}, status=status.HTTP_400_BAD_REQUEST)

    def _change_status(self, request, quote, target, allowed, label):
        # The action target may have changed after the request was routed.
        # Re-read it under a row lock so exactly one competing transition wins.
        quote = Quote.objects.select_for_update().get(pk=quote.pk)
        if quote.status not in allowed:
            return Response({"detail": "当前报价状态不能执行此操作，请创建修订版重新报价。"}, status=status.HTTP_400_BAD_REQUEST)
        if target in {"sent", "accepted"}:
            from .quote_template_snapshot import QuoteTemplateSnapshotError, resolve_quote_template
            template_id = "standard_en_with_discount" if quote.discount else "standard_en_no_discount"
            try:
                resolve_quote_template(quote, template_id)
            except QuoteTemplateSnapshotError as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        before_status = quote.status
        quote.status = target
        update_fields = ["status", "updated_at"]
        if before_status == "draft" and target in {"sent", "accepted"}:
            quote.amount_calculation_version = CURRENT_AMOUNT_CALCULATION_VERSION
            update_fields.append("amount_calculation_version")
        quote.save(update_fields=update_fields)
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

    def _scoped_revision_chain(self, root_quote):
        queryset = Quote.objects.filter(Q(pk=root_quote.pk) | Q(root_quote=root_quote))
        return scope_customer_related_queryset(queryset, self.request.user)

    @action(detail=True, methods=["get", "post"], url_path="important-notes")
    def important_notes(self, request, pk=None):
        quote = self.get_object()
        root_quote = self._root_quote(quote)
        notes = QuoteImportantNote.objects.filter(root_quote=root_quote, source_quote__in=self._scoped_revision_chain(root_quote)).select_related("source_quote", "created_by", "deactivated_by")
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
            source_quote__in=self._scoped_revision_chain(root_quote),
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
            source_quote__in=self._scoped_revision_chain(root_quote),
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
        revisions = self._scoped_revision_chain(root_quote).order_by("revision_no", "id")
        orders = scope_customer_related_queryset(Order.objects.filter(quote__in=revisions), request.user).select_related("quote", "customer").prefetch_related("items__sku__product", "transactions") if user_can(request.user, "orders", "view") else Order.objects.none()
        notes = QuoteImportantNote.objects.filter(root_quote=root_quote, source_quote__in=self._scoped_revision_chain(root_quote)).select_related("source_quote", "created_by", "deactivated_by")
        return Response({
            "quote": QuoteSerializer(quote, context={"request": request}).data,
            "root_quote_no": root_quote.quote_no,
            "revisions": QuoteSerializer(revisions, many=True, context={"request": request}).data,
            "orders": OrderSerializer(orders, many=True, context={"request": request}).data,
            "important_notes": QuoteImportantNoteSerializer(notes, many=True).data,
            "order_summary": {"count": orders.count()},
        })

    @action(detail=True, methods=["get"], url_path="order-draft")
    def order_draft(self, request, pk=None):
        require_finance_permission(request.user, "orders", "create")
        require_finance_permission(request.user, "customers", "view")
        require_finance_permission(request.user, "skus", "view")
        quote = self.get_object()
        if quote.status in {"rejected", "expired"}:
            return Response(
                {"detail": "该报价已拒绝或过期，请先创建新的修订版后再转为订单。"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order_date = timezone.localdate()
        return Response({
            "customer": quote.customer_id,
            "quote": quote.id,
            "order_date": order_date,
            "expected_ship_date": order_date + timedelta(days=quote.lead_time_days) if quote.lead_time_days is not None else None,
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
                    "cost_price": item.sku.cost_price if user_can(request.user, "purchases", "view") else None,
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
            pi_template_snapshots=source.pi_template_snapshots,
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
        require_finance_permission(request.user, "customers", "view")
        require_finance_permission(request.user, "skus", "view")
        quote = self.get_object()
        try:
            export_dto = build_quotation_export_dto(quote)
        except QuotationExportValidationError as exc:
            return Response(
                {"detail": str(exc), "fields": exc.fields},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        products = []
        for item, export_item in zip(quote.items.all(), export_dto.products):
            amount = Decimal(export_item.amount)
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
                "unit_price": export_item.unit_price,
                "amount": amount,
                "unit": item.trade_snapshot.get("unit", item.unit_snapshot),
                "image_url": request.build_absolute_uri(protected_media_url(item.image_snapshot)) if item.image_snapshot else "",
            })
        totals = export_dto.totals
        payment_splits = export_dto.payment_splits
        result = {
            "invoice_no": export_dto.invoice_no,
            "seller": export_dto.template_snapshot["seller"],
            "bank": export_dto.template_snapshot["bank"],
            "bank_notice": export_dto.template_snapshot["notice"],
            "template_sha256": export_dto.template_snapshot["sha256"],
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
                "validity_days": export_dto.terms["validity_days"],
                "lead_time_days": quote.lead_time_days,
                "trading_terms": quote.trading_terms,
                "shipping_details": quote.shipping_details,
                "notes": quote.notes,
            },
            "totals": {
                "currency": totals["currency"],
                "subtotal": totals["subtotal"],
                "shipping_fee": totals["shipping_fee"],
                "discount": totals["discount"],
                "total_amount": totals["total_amount"],
            },
            "payment_splits": {
                "deposit_ratio": payment_splits["deposit_ratio"],
                "deposit_amount": payment_splits["deposit_amount"],
                "balance_ratio": payment_splits["balance_ratio"],
                "balance_amount": payment_splits["balance_amount"],
            },
            "products": products,
        }
        from django.template import Context, Engine, TemplateSyntaxError
        from .quote_export import _amount_words
        result["amount_words"] = _amount_words(Decimal(totals["total_amount"]), quote.currency)
        result["print_sha256"] = export_dto.template_snapshot["print_sha256"]
        try:
            template = Engine(autoescape=True).from_string(export_dto.template_snapshot["print_template"])
            result["print_html"] = template.render(Context(result, autoescape=True))
        except TemplateSyntaxError:
            return Response({"detail": "保存的打印模板损坏，需核实原件。"}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        return Response(result)

    @action(detail=True, methods=["get"], permission_classes=[QuoteExportPermission])
    def export(self, request, pk=None):
        require_finance_permission(request.user, "customers", "view")
        require_finance_permission(request.user, "skus", "view")
        quote = self.get_object()
        try:
            content = build_pi_export_payload(quote)
        except QuoteExportError as exc:
            return Response(
                {"detail": str(exc), "fields": exc.fields} if exc.fields else {"detail": "PI workbook generation failed."},
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

    def get_search_fields(self, request):
        return list(self.search_fields) if user_can(request.user, "customers", "view") else ["order_no"]
    ordering_fields = ["order_date", "expected_ship_date", "created_at"]

    def create(self, request, *args, **kwargs):
        if request.data.get("is_historical") or request.data.get("status") == "historical":
            return Response({"detail": "历史销售订单请使用历史订单录入入口。"}, status=status.HTTP_400_BAD_REQUEST)
        if request.data.get("status") not in (None, "", "draft"):
            return Response({"detail": "新建订单只能保存为草稿，请使用确认订单动作。"}, status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)

    @action(detail=False, methods=["post"], url_path="historical")
    def create_historical(self, request, *args, **kwargs):
        if request.data.get("status") not in (None, "", "historical") or request.data.get("is_historical") not in (None, "", True, "true", "1"):
            return Response({"detail": "历史销售订单必须通过历史录入模式创建。"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data=request.data, context={"request": request, "historical_mode": True})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(self.get_serializer(serializer.instance).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        order = self.get_object()
        if order.historical_only or order.status == "historical":
            return Response({"detail": "历史订单不能直接覆盖；请通过受控追溯更正保留原始轨迹。"}, status=status.HTTP_400_BAD_REQUEST)
        if hasattr(order, "history_continuation"):
            return Response({"detail": "历史接续订单不能直接覆盖，请通过正式数量变更或审计更正处理。"}, status=status.HTTP_400_BAD_REQUEST)
        if "status" in request.data:
            return Response({"detail": "订单状态只能通过确认、开始生产、发货、完成或取消等业务动作变更。"}, status=status.HTTP_400_BAD_REQUEST)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        order = self.get_object()
        if hasattr(order, "history_continuation"):
            return Response({"detail": "历史接续订单必须保留，请使用取消或审计更正。"}, status=status.HTTP_400_BAD_REQUEST)
        if order.status != "draft":
            return Response({"detail": "正式订单不能删除，请使用取消订单。"}, status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        require_finance_permission(request.user, "inventory", "update")
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
        require_finance_permission(request.user, "inventory", "update")
        try:
            with transaction.atomic():
                order = complete_order(self.get_object())
                record_operation(request=request, instance=order, action="custom", action_label="完成销售订单")
        except DjangoValidationError as error:
            return Response({"detail": error.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        require_finance_permission(request.user, "inventory", "update")
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
        qs = scope_customer_related_queryset(super().get_queryset(), self.request.user)
        historical_requested = self.request.query_params.get("status") == "historical"
        if self.action == "list":
            qs = qs.filter(historical_only=True, status="historical") if historical_requested else qs.filter(historical_only=False)
        if self.request.query_params.get("customer"):
            qs = qs.filter(customer_id=self.request.query_params["customer"])
        if self.request.query_params.get("quote"):
            qs = qs.filter(quote_id=self.request.query_params["quote"])
        if self.request.query_params.get("product"):
            qs = qs.filter(items__sku__product_id=self.request.query_params["product"]).distinct()
        if self.request.query_params.get("sku"):
            qs = qs.filter(items__sku_id=self.request.query_params["sku"]).distinct()
        if self.request.query_params.get("status") and not historical_requested:
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
        can_view_skus = user_can(request.user, "skus", "view")
        can_view_purchases = user_can(request.user, "purchases", "view")
        can_view_suppliers = user_can(request.user, "suppliers", "view")
        can_view_inventory = user_can(request.user, "inventory", "view")
        draft_quantities = draft_procurement_quantities(order) if can_view_purchases else {}
        rows = []
        for item in order.items.select_related("sku"):
            metrics = order_item_metrics(item)
            rows.append({
                "id": item.id, "sku": item.sku_id if can_view_skus else None,
                "sku_code": (item.sku_code_snapshot or item.sku.sku) if can_view_skus else "",
                "base_unit": item.trade_snapshot.get("base_unit", item.unit_snapshot or item.sku.unit) if can_view_skus else "",
                "sales_model": item.sales_model_snapshot if can_view_skus else "",
                "display_name": item.display_name_snapshot if can_view_skus else "",
                "quantity": item.quantity, "allocated_quantity": metrics["allocated_quantity"] if can_view_inventory else None,
                "to_procure_quantity": metrics["to_procure_quantity"] if can_view_purchases else None,
                "draft_procurement_quantity": draft_quantities.get(item.id) if can_view_purchases else None,
                "draftable_quantity": max(Decimal("0"), metrics["to_procure_quantity"] - draft_quantities[item.id]) if can_view_purchases else None,
                "purchased_quantity": metrics["purchased_quantity"] if can_view_purchases else None,
                "in_transit_quantity": metrics["in_transit_quantity"] if can_view_purchases else None,
                "arrived_quantity": metrics["received_quantity"] if can_view_purchases else None,
                "shipped_quantity": metrics["shipped_quantity"] if can_view_inventory else None,
                "unshipped_quantity": metrics["unshipped_quantity"] if can_view_inventory else None,
                "supplier_sku": item.supplier_sku_id if can_view_suppliers else None,
                "supplier_name": item.supplier_name_snapshot if can_view_suppliers else "",
                "supplier_model": item.supplier_model_snapshot if can_view_suppliers else "",
                "supplier_sku_code": item.supplier_sku_code_snapshot if can_view_suppliers else "",
            })
        purchase_orders = prefetch_purchase_related_orders(
            PurchaseOrder.objects.filter(
                items__cost_allocations__target_type="order",
                items__cost_allocations__order=order,
            ).distinct().select_related("supplier", "order").prefetch_related(
                "items__receipts", "transactions"
            )
        )
        shipments = Shipment.objects.filter(order=order).prefetch_related("items__sku", "items__inventory_movement", "items__order_item")
        return Response({
            "order": OrderSerializer(order, context={"request": request}).data,
            "items": rows,
            "purchase_orders": PurchaseOrderSerializer(purchase_orders, many=True, context={"request": request}).data if can_view_purchases else [],
            "shipments": [{
                "id": shipment.id, "shipment_no": shipment.shipment_no,
                "shipment_date": shipment.shipment_date, "status": shipment.status,
                "reversed_at": shipment.reversed_at, "reversal_reason": shipment.reversal_reason,
                "has_overage": any(line.is_overage for line in shipment.items.all()),
                "items": [{
                    "id": line.id, "sku": line.sku_id if can_view_skus else None,
                    "sku_code": ((line.inventory_movement.sku_code_snapshot if line.inventory_movement else "") or line.order_item.sku_code_snapshot or line.sku.sku) if can_view_skus else "",
                    "display_name": ((line.inventory_movement.display_name_snapshot if line.inventory_movement else "") or line.order_item.display_name_snapshot or line.sku.display_name_cn) if can_view_skus else "",
                    "base_unit": ((line.trade_snapshot or {}).get("base_unit") or line.sku.unit) if can_view_skus else "",
                    "quantity": line.quantity,
                    "is_overage": line.is_overage,
                    "inventory_movement": line.inventory_movement_id,
                    "reversal_inventory_movement": line.reversal_inventory_movement_id,
                } for line in shipment.items.all()],
            } for shipment in shipments] if can_view_inventory else [],
        })

    @action(detail=True, methods=["post"], url_path="quantity-adjustments/preview")
    def quantity_adjustment_preview(self, request, pk=None):
        require_finance_permission(request.user, "orders", "update")
        order = self.get_object()
        try:
            preview = preview_quantity_adjustment(order, request.data)
        except QuantityAdjustmentConflict as error:
            return Response({"detail": error.messages[0]}, status=status.HTTP_409_CONFLICT)
        except DjangoValidationError as error:
            return Response({"detail": _quantity_adjustment_error_message(error, request.user)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(redact_quantity_adjustment_response(
            preview,
            **_quantity_adjustment_visibility(request.user),
        ))

    @action(detail=True, methods=["get", "post"], url_path="quantity-adjustments")
    def quantity_adjustments(self, request, pk=None):
        order = self.get_object()
        visibility = _quantity_adjustment_visibility(request.user)
        if request.method == "GET":
            return Response([
                serialize_adjustment(row, **visibility)
                for row in order.quantity_adjustments.select_related("operator").all()
            ])
        require_finance_permission(request.user, "orders", "update")
        try:
            with transaction.atomic():
                adjustment, replayed, preview = apply_quantity_adjustment(
                    order,
                    request.data,
                    operator=request.user,
                )
                if not replayed:
                    lines = adjustment.lines
                    before = {
                        "quantity_change_version": max(0, adjustment.order.quantity_change_version - 1),
                        "total_amount": str(adjustment.before_total_amount),
                        "items": {str(row["order_item"]): row["old_quantity"] for row in lines},
                    }
                    after = {
                        "quantity_change_version": adjustment.order.quantity_change_version,
                        "total_amount": str(adjustment.after_total_amount),
                        "items": {str(row["order_item"]): row["new_quantity"] for row in lines},
                    }
                    record_operation(
                        request=request,
                        instance=adjustment.order,
                        action="custom",
                        action_label="调整销售订单数量",
                        before=before,
                        after=after,
                        metadata={
                            "quantity_adjustment_id": adjustment.pk,
                            "reason": adjustment.reason,
                            "summary": f"调整 {len(lines)} 条订单明细，金额差额 {adjustment.amount_delta}",
                            "warnings": adjustment.impact.get("warnings", []),
                        },
                    )
        except QuantityAdjustmentConflict as error:
            return Response({"detail": error.messages[0]}, status=status.HTTP_409_CONFLICT)
        except DjangoValidationError as error:
            return Response({"detail": _quantity_adjustment_error_message(error, request.user)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "adjustment": serialize_adjustment(adjustment, **visibility),
                "replayed": replayed,
                "preview": redact_quantity_adjustment_response(preview, **visibility),
            },
            status=status.HTTP_200_OK if replayed else status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"], url_path="procurement-plan")
    def procurement_plan(self, request, pk=None):
        order = self.get_object()
        if order.historical_only or order.status == "historical":
            return Response({"detail": "历史销售订单仅用于经营分析，不能生成采购计划。"}, status=status.HTTP_400_BAD_REQUEST)
        require_finance_permission(request.user, "purchases", "view")
        require_finance_permission(request.user, "suppliers", "view")
        require_finance_permission(request.user, "inventory", "view")
        return Response(build_procurement_plan(order))

    @action(detail=True, methods=["post"], url_path="generate-purchase-drafts")
    def generate_purchase_drafts(self, request, pk=None):
        require_finance_permission(request.user, "purchases", "create")
        require_finance_permission(request.user, "suppliers", "view")
        require_order_writes(request.user, [self.get_object().pk])
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
            "purchase_orders": PurchaseOrderSerializer(serialized_purchases, many=True, context={"request": request}).data,
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"], url_path="packing-plan")
    def packing_plan(self, request, pk=None):
        order = self.get_object()
        if (order.historical_only or order.status == "historical") and request.method == "POST":
            return Response({"detail": "历史销售订单仅用于经营分析，不能生成装箱或履约记录。"}, status=status.HTTP_400_BAD_REQUEST)
        require_finance_permission(request.user, "skus", "view")
        if request.method == "POST":
            plan = generate_packing_plan(order)
            record_operation(request=request, instance=order, action="custom", action_label="生成订单装箱方案", metadata={"packing_plan_id": plan.id})
            return Response(PackingPlanSerializer(plan, context={"request": request}).data)
        plan = getattr(order, "packing_plan", None)
        return Response(PackingPlanSerializer(plan, context={"request": request}).data if plan else {"detail": "尚未生成预计装箱。"}, status=status.HTTP_200_OK if plan else status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=["post"])
    def ship(self, request, pk=None):
        require_finance_permission(request.user, "inventory", "create")
        order = self.get_object()
        try:
            idempotency_key = require_fulfillment_idempotency_key(request)
        except DjangoValidationError as error:
            return Response({"detail": error.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        input_serializer = ShipmentInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                idempotency, replay = begin_fulfillment_idempotency(
                    key=idempotency_key,
                    operation="ship",
                    target_id=order.pk,
                    payload=input_serializer.validated_data,
                    operator_id=request.user.pk if getattr(request.user, "is_authenticated", False) else None,
                )
                if replay:
                    replay_response = Response(idempotency.response_payload, status=idempotency.response_status)
                    replay_response["Idempotent-Replay"] = "true"
                    return replay_response
                order = Order.objects.select_for_update().get(pk=order.pk)
                before = snapshot(order)
                shipment = confirm_shipment(order, input_serializer.validated_data)
                response_payload = json_safe_fulfillment_response({"id": shipment.id, "shipment_no": shipment.shipment_no, "status": shipment.status})
                order.refresh_from_db()
                after = snapshot(order)
                record_operation(request=request, instance=order, action="custom", action_label="确认订单发货", before=before, after=after, metadata={"shipment_id": shipment.id, "shipment_no": shipment.shipment_no})
                complete_fulfillment_idempotency(idempotency, response_payload)
        except FulfillmentIdempotencyConflict as error:
            return Response({"detail": error.messages[0]}, status=status.HTTP_409_CONFLICT)
        except DjangoValidationError as error:
            return Response({"detail": error.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(response_payload, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def workbench(self, request, pk=None):
        order = self.get_object()
        historical = bool(order.historical_only or order.status == "historical")
        can_view_transactions = user_can(request.user, "transactions", "view")
        can_view_finance = user_can(request.user, "finance", "view")
        quantity_adjustment_visibility = _quantity_adjustment_visibility(request.user)
        can_view_profit = can_view_transactions and can_view_finance and user_can(request.user, "purchases", "view") and not historical
        from .models import AdvanceAllocation
        advance_allocations = [] if historical else [{"id": row.pk, "transaction_no": row.advance.transaction_no,
            "transaction_date": row.advance.transaction_date, "amount": row.amount,
            "currency": row.plan.currency, "is_active": row.is_active}
            for row in AdvanceAllocation.objects.filter(plan__order=order).select_related("advance", "plan")]
        items = list(order.items.all())
        payments = list(scope_transaction_queryset(order.transactions.all(), request.user)) if can_view_transactions and not historical else []
        plans = list(order.payment_plans.all()) if can_view_finance and not historical else []
        expenses = [row for row in payments if row.direction == "expense" and row.kind not in {"supplier_payment", "refund", "unallocated_advance", "unallocated_payment"} and row.status == "confirmed"]
        inventory = [] if historical else list(InventoryMovement.objects.filter(Q(order=order) | Q(related_orders=order)).distinct().select_related("sku__product"))
        ordered_quantity = sum((item.quantity for item in items), Decimal("0"))
        shipped_quantity = Decimal("0") if historical else sum((order_item_metrics(item)["shipped_quantity"] for item in items), Decimal("0"))
        from .services.finance import order_receivable_state
        paid_amount = order.paid_amount if can_view_transactions and can_view_finance else None
        planned_receivable = sum((plan.planned_amount for plan in plans if plan.status != "cancelled"), Decimal("0"))
        from .services.profit import order_profit_summary
        profit_summary = order_profit_summary(order) if can_view_profit else None
        quantity_adjustments = [
            serialize_adjustment(row, **quantity_adjustment_visibility)
            for row in order.quantity_adjustments.select_related("operator").all()
        ]
        serializer_context = {
            "request": request,
            "mask_quantity_adjustment_financial": not quantity_adjustment_visibility["include_financial"],
        }
        return Response({
            "order": OrderSerializer(order, context=serializer_context).data,
            "source_quote": QuoteSerializer(order.quote, context={"request": request}).data if order.quote and user_can(request.user, "quotes", "view") else None,
            "items": OrderItemSerializer(items, many=True, context=serializer_context).data,
            "payments": TransactionSerializer(payments, many=True, context={"request": request}).data,
            "advance_allocations": advance_allocations if can_view_transactions and can_view_finance else [],
            "plans": PaymentPlanSerializer(plans, many=True, context={"request": request}).data,
            "inventory": InventoryMovementSerializer(inventory, many=True, context={"request": request}).data,
            "payment_summary": {
                "paid_amount": paid_amount,
                "balance_amount": order.outstanding_amount if can_view_transactions and can_view_finance else None,
                "planned_amount": planned_receivable if can_view_finance else None,
                "settlement": order_receivable_state(order, plans) if can_view_transactions and can_view_finance else None,
            },
            "expense_summary": {"expense_rmb": profit_summary["expense_rmb"] if profit_summary else None},
            "profit_summary": profit_summary,
            "quantity_adjustments": quantity_adjustments,
            "fulfillment_summary": {
                "ordered_quantity": ordered_quantity,
                "shipped_quantity": shipped_quantity if user_can(request.user, "inventory", "view") else None,
                "remaining_quantity": ordered_quantity - shipped_quantity if user_can(request.user, "inventory", "view") else None,
            },
        })

def _finance_period(request):
    today = timezone.localdate()
    try:
        start = date.fromisoformat(request.query_params.get("date_from") or today.replace(day=1).isoformat())
        end = date.fromisoformat(request.query_params.get("date_to") or today.isoformat())
        if start > end:
            raise ValueError
    except ValueError:
        raise DRFValidationError("请填写有效日期，开始日期不能晚于结束日期。")
    return start, end


def _finance_plans(user):
    return (
        scope_plan_queryset(
            PaymentPlan.objects.select_related("order__customer", "purchase_order__supplier"), user
        )
        .filter(status="open")
        .exclude(order__status__in=["draft", "cancelled"])
        .exclude(purchase_order__status__in=["draft", "cancelled"])
    )


def _finance_period_orders(user, start, end, can_view_orders=None):
    if can_view_orders is None:
        can_view_orders = user_can(user, "orders", "view")
    if not can_view_orders:
        return Order.objects.none()
    return (
        scope_customer_related_queryset(Order.objects.filter(historical_only=False), user)
        .exclude(status__in=["draft", "cancelled"])
        .filter(order_date__range=(start, end))
        .prefetch_related("items", "contract_changes", "purchase_cost_allocations", "transactions")
    )


def _finance_cash(user, start, end):
    return scope_transaction_queryset(Transaction.objects.all(), user).filter(
        status="confirmed", transaction_date__range=(start, end)
    )


def _finance_advances(user):
    return scope_transaction_queryset(Transaction.objects.all(), user).filter(
        status="confirmed", kind__in=["unallocated_advance", "unallocated_payment"]
    )


def _finance_row_rmb(row):
    return row.rmb_amount or row.amount * row.exchange_rate


def _finance_plan_rmb(row):
    exchange_rate = row.order.exchange_rate if row.order_id else row.purchase_order.exchange_rate
    return row.remaining_amount * exchange_rate


@api_view(["GET"])
def finance_dashboard(request):
    require_finance_permission(request.user, "transactions", "view")
    can_view_orders = user_can(request.user, "orders", "view")
    can_view_purchases = user_can(request.user, "purchases", "view")
    exporting = request.query_params.get("export") == "csv"
    if exporting:
        require_finance_permission(request.user, "finance", "export")
    try:
        start, end = _finance_period(request)
    except DRFValidationError as error:
        return Response({"detail": str(error.detail)}, status=400)
    today = timezone.localdate()
    plans = _finance_plans(request.user)
    receivables = plans.filter(direction="receivable") if can_view_orders else plans.none()
    payables = plans.filter(direction="payable") if can_view_purchases else plans.none()
    remaining = lambda rows: sum((row.remaining_amount * (row.order.exchange_rate if row.order_id else row.purchase_order.exchange_rate) for row in rows), Decimal("0"))
    from .services.profit import order_profit_summary
    period_orders = _finance_period_orders(request.user, start, end, can_view_orders)
    sales_rmb = sum((order.total_amount * order.exchange_rate for order in period_orders), Decimal("0"))
    profits = [order_profit_summary(order) for order in period_orders] if can_view_orders and can_view_purchases else []
    purchase_cost_rmb = sum((row["purchase_cost_rmb"] for row in profits), Decimal("0"))
    order_expense_rmb = sum((row["expense_rmb"] for row in profits), Decimal("0"))
    estimated_profit_rmb = sum((row["estimated_profit_rmb"] for row in profits), Decimal("0"))
    cash = _finance_cash(request.user, start, end)
    income, expense = Decimal("0"), Decimal("0")
    categories, monthly = {}, {}
    for row in cash:
        value = _finance_row_rmb(row)
        if row.direction == "income":
            income += value
        else:
            expense += value
        key = (row.direction, row.category)
        categories[key] = categories.get(key, Decimal("0")) + value
        month = row.transaction_date.strftime("%Y-%m")
        bucket = monthly.setdefault(month, {"month": month, "income": Decimal("0"), "expense": Decimal("0")})
        bucket[row.direction] += value
    advances = _finance_advances(request.user)
    unallocated = lambda direction: sum(((row.amount - row.allocated_amount) * row.exchange_rate for row in advances if row.direction == direction), Decimal("0"))
    due_items = [
        {
            "id": row.id, "direction": row.direction, "contract_no": row.order.order_no if row.order_id else row.purchase_order.purchase_no,
            "order": row.order_id, "purchase_order": row.purchase_order_id,
            "counterparty_name": (row.order.customer.name if user_can(request.user, "customers", "view") else "客户") if row.order_id else (row.purchase_order.supplier.name if user_can(request.user, "suppliers", "view") else "供应商"),
            "due_date": row.due_date, "remaining_amount": row.remaining_amount, "currency": row.currency,
        }
        for row in plans.filter(due_date__isnull=False, due_date__lte=today).order_by("due_date")[:12]
    ]
    payload = {"metrics": {
        "receivable_count": receivables.count(), "receivable_rmb": remaining(receivables),
        "payable_count": payables.count(), "payable_rmb": remaining(payables), "sales_rmb": sales_rmb, "monthly_sales_rmb": sales_rmb,
        "purchase_cost_rmb": purchase_cost_rmb, "order_expense_rmb": order_expense_rmb, "estimated_profit_rmb": estimated_profit_rmb,
        "income_rmb": income, "expense_rmb": expense, "net_cash_rmb": income - expense,
        "advance_receipt_rmb": unallocated("income"), "advance_payment_rmb": unallocated("expense"),
    }, "period": {"date_from": start, "date_to": end}, "due_items": due_items,
        "categories": [{"direction": key[0], "category": key[1], "amount": value} for key, value in sorted(categories.items())],
        "monthly_cash": [{**monthly[key], "net": monthly[key]["income"] - monthly[key]["expense"]} for key in sorted(monthly)]}


    from .finance_basis import book_rmb_metadata
    payload["cash_basis"] = book_rmb_metadata()

    if exporting:
        from .reporting import safe_csv
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="finance-{start}-{end}.csv"'
        response.write("\ufeff")
        writer = csv.writer(response)
        writer.writerow(["账面收支报表（人民币折算参考）", start, end, payload["cash_basis"]["note"]])
        writer.writerow(["月份", "账面收入（人民币折算参考）", "账面支出（人民币折算参考）", "账面净收支（人民币折算参考）"])
        for row in payload["monthly_cash"]:
            writer.writerow([row["month"], row["income"], row["expense"], row["net"]])
        writer.writerow([])
        writer.writerow(["方向", "分类", "人民币折算参考金额"])
        for row in payload["categories"]:
            writer.writerow(["收入" if row["direction"] == "income" else "支出", safe_csv(row["category"]), row["amount"]])
        return response
    return Response(payload)


@api_view(["GET"])
def finance_dashboard_details(request):
    """Return a paged, permission-scoped composition for one finance card.

    The endpoint intentionally exposes only records that feed the selected card.
    Actual bank cash keeps using the existing confirmed-event endpoint/table so
    its bank_date and bank voucher rules remain a single source of truth.
    """
    require_finance_permission(request.user, "transactions", "view")
    metric = request.query_params.get("metric")
    metric_config = {
        "sales_rmb": ("合同销售额", "order_date", "人民币", "订单日期范围内的正式销售订单；包含已批准合同变更，变更不分配至商品行。"),
        "purchase_cost_rmb": ("订单采购归属成本", "order_date", "人民币", "沿用现有订单采购归属成本服务，按订单日期统计。"),
        "order_expense_rmb": ("订单费用", "order_date", "人民币", "沿用现有订单利润服务中的已确认订单费用，按订单日期统计。"),
        "estimated_profit_rmb": ("预计订单利润", "order_date", "人民币", "经营估算：合同销售额 − 采购归属成本 − 订单费用，不代表会计利润。"),
        "income_rmb": ("账面收入（折算参考）", "transaction_date", "人民币折算参考", "仅统计已确认财务流水，按流水发生日期和既有人民币折算参考口径。"),
        "expense_rmb": ("账面支出（折算参考）", "transaction_date", "人民币折算参考", "仅统计已确认财务流水，按流水发生日期和既有人民币折算参考口径。"),
        "net_cash_rmb": ("账面净收支（折算参考）", "transaction_date", "人民币折算参考", "已确认账面收入减已确认账面支出；不代表银行实际到账或银行账户余额。"),
        "receivable_count": ("待收笔数", "current_balance", "笔", "当前开放应收计划去重计数，不受所选期间限制。"),
        "receivable_rmb": ("待收款", "current_balance", "人民币折算参考", "当前开放应收计划按合同汇率折算，不受所选期间限制。"),
        "payable_count": ("待付款笔数", "current_balance", "笔", "当前开放应付计划去重计数，不受所选期间限制。"),
        "payable_rmb": ("待付款", "current_balance", "人民币折算参考", "当前开放应付计划按合同汇率折算，不受所选期间限制。"),
        "advance_receipt_rmb": ("未核销预收款", "current_balance", "人民币折算参考", "当前已确认未核销预收流水按原流水汇率折算，不受所选期间限制。"),
        "advance_payment_rmb": ("未核销预付款", "current_balance", "人民币折算参考", "当前已确认未核销预付流水按原流水汇率折算，不受所选期间限制。"),
    }
    if metric not in metric_config:
        return Response({"detail": "不支持的财务指标。"}, status=400)

    title, date_basis, amount_unit, basis_note = metric_config[metric]
    try:
        start, end = _finance_period(request)
        page = int(request.query_params.get("page") or 1)
        page_size = int(request.query_params.get("page_size") or 50)
        sort_by = request.query_params.get("sort_by") or "date"
        sort_order = request.query_params.get("sort_order") or "asc"
        if page < 1 or page_size < 1 or page_size > 100 or sort_by not in {"date", "amount", "record"} or sort_order not in {"asc", "desc"}:
            raise ValueError
    except (DRFValidationError, TypeError, ValueError):
        return Response({"detail": "请填写有效的日期、页码和页大小。"}, status=400)

    can_view_orders = user_can(request.user, "orders", "view")
    can_view_purchases = user_can(request.user, "purchases", "view")
    if metric in {"sales_rmb", "receivable_count", "receivable_rmb"} and not can_view_orders:
        require_finance_permission(request.user, "orders", "view")
    if metric in {"purchase_cost_rmb", "order_expense_rmb", "estimated_profit_rmb"} and not (can_view_orders and can_view_purchases):
        require_finance_permission(request.user, "purchases", "view")
        require_finance_permission(request.user, "orders", "view")
    if metric in {"payable_count", "payable_rmb"} and not can_view_purchases:
        require_finance_permission(request.user, "purchases", "view")

    rows = []
    total_amount = Decimal("0")
    from .services.profit import order_profit_summary

    def order_relation(order):
        return order.customer.name if order.customer_id and user_can(request.user, "customers", "view") else "客户"

    def order_row(order, amount, note=""):
        return {
            "id": order.id,
            "record_label": order.order_no,
            "date": order.order_date,
            "relation_label": order_relation(order),
            "status_label": order.get_status_display(),
            "amount": amount,
            "amount_note": note,
            "detail_url": f"/orders?detail={order.id}",
            "detail_label": "查看订单",
        }

    if metric in {"sales_rmb", "purchase_cost_rmb", "order_expense_rmb", "estimated_profit_rmb"}:
        orders = _finance_period_orders(request.user, start, end, can_view_orders)
        for order in orders:
            sales = order.total_amount * order.exchange_rate
            if metric == "sales_rmb":
                amount = sales
                note = "含已批准合同变更后的合同金额；合同变更不分配至商品行。"
            else:
                profit = order_profit_summary(order)
                amount = {
                    "purchase_cost_rmb": profit["purchase_cost_rmb"],
                    "order_expense_rmb": profit["expense_rmb"],
                    "estimated_profit_rmb": profit["estimated_profit_rmb"],
                }[metric]
                note = (
                    f"销售额 ¥{sales}；采购归属成本 ¥{profit['purchase_cost_rmb']}；"
                    f"订单费用 ¥{profit['expense_rmb']}。"
                )
            total_amount += amount
            rows.append(order_row(order, amount, note))
    elif metric in {"income_rmb", "expense_rmb", "net_cash_rmb"}:
        cash = _finance_cash(request.user, start, end).select_related("customer", "supplier", "order", "purchase_order")
        for row in cash:
            value = _finance_row_rmb(row)
            if metric == "income_rmb" and row.direction != "income":
                continue
            if metric == "expense_rmb" and row.direction != "expense":
                continue
            amount = value if row.direction == "income" or metric != "net_cash_rmb" else -value
            if metric == "net_cash_rmb":
                total_amount += amount
            else:
                total_amount += value
            if row.customer_id:
                relation = row.customer.name if user_can(request.user, "customers", "view") else "客户"
            elif row.supplier_id:
                relation = row.supplier.name if user_can(request.user, "suppliers", "view") else "供应商"
            elif row.order_id:
                relation = row.order.order_no if can_view_orders else "订单"
            elif row.purchase_order_id:
                relation = row.purchase_order.purchase_no if can_view_purchases else "采购单"
            else:
                relation = "未关联业务单据"
            rows.append({
                "id": row.id,
                "record_label": row.transaction_no,
                "date": row.transaction_date,
                "relation_label": relation,
                "status_label": row.get_status_display(),
                "amount": amount,
                "amount_note": f"{row.category or '未分类'}；已确认流水。",
                "detail_url": f"/transactions?detail={row.id}",
                "detail_label": "查看财务流水",
            })
    elif metric in {"receivable_count", "receivable_rmb", "payable_count", "payable_rmb"}:
        direction = "receivable" if metric.startswith("receivable") else "payable"
        plans = _finance_plans(request.user).filter(direction=direction)
        for row in plans:
            amount = Decimal("1") if metric.endswith("_count") else _finance_plan_rmb(row)
            total_amount += amount
            if direction == "receivable":
                relation = order_relation(row.order)
                detail_url = f"/orders?detail={row.order_id}"
            else:
                relation = row.purchase_order.supplier.name if user_can(request.user, "suppliers", "view") else "供应商"
                detail_url = f"/purchase-orders?detail={row.purchase_order_id}"
            rows.append({
                "id": row.id,
                "record_label": row.order.order_no if direction == "receivable" else row.purchase_order.purchase_no,
                "date": row.due_date,
                "relation_label": relation,
                "status_label": "待结清",
                "amount": amount,
                "amount_note": "当前开放计划的未结金额。" if not metric.endswith("_count") else "一笔开放计划。",
                "detail_url": detail_url,
                "detail_label": "查看订单" if direction == "receivable" else "查看采购单",
            })
    else:
        direction = "income" if metric == "advance_receipt_rmb" else "expense"
        advances = _finance_advances(request.user).filter(direction=direction)
        advances = advances.select_related("customer", "supplier", "order", "purchase_order")
        for row in advances:
            amount = (row.amount - row.allocated_amount) * row.exchange_rate
            total_amount += amount
            relation = "客户" if row.customer_id and not user_can(request.user, "customers", "view") else (row.customer.name if row.customer_id else "供应商")
            if row.supplier_id and user_can(request.user, "suppliers", "view"):
                relation = row.supplier.name
            rows.append({
                "id": row.id,
                "record_label": row.transaction_no,
                "date": row.transaction_date,
                "relation_label": relation,
                "status_label": row.get_status_display(),
                "amount": amount,
                "amount_note": "已确认流水的未核销余额。",
                "detail_url": f"/transactions?detail={row.id}",
                "detail_label": "查看财务流水",
            })

    def sort_value(row):
        if sort_by == "amount":
            return Decimal(str(row["amount"]))
        if sort_by == "record":
            return str(row["record_label"] or "")
        return row["date"] or date.max

    rows.sort(key=sort_value, reverse=sort_order == "desc")
    total_count = len(rows)
    offset = (page - 1) * page_size
    page_rows = rows[offset:offset + page_size]
    return Response({
        "metric": metric,
        "title": title,
        "basis_note": basis_note,
        "date_basis": date_basis,
        "amount_unit": amount_unit,
        "current_balance": date_basis == "current_balance",
        "period": {"date_from": start, "date_to": end},
        "total_count": total_count,
        "total_amount": total_amount,
        "page": page,
        "page_size": page_size,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "has_more": offset + page_size < total_count,
        "rows": page_rows,
    })


class TransactionViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    queryset = Transaction.objects.select_related("customer", "order", "supplier", "purchase_order").prefetch_related("allocations__plan__order", "allocations__plan__purchase_order")
    search_fields = ["transaction_no", "category", "customer__name", "supplier__name", "order__order_no", "purchase_order__purchase_no", "reference"]

    def get_search_fields(self, request):
        fields = ["transaction_no", "category", "reference"]
        if user_can(request.user, "customers", "view"):
            fields.append("customer__name")
        if user_can(request.user, "suppliers", "view"):
            fields.append("supplier__name")
        if user_can(request.user, "orders", "view"):
            fields.append("order__order_no")
        if user_can(request.user, "purchases", "view"):
            fields.append("purchase_order__purchase_no")
        return fields
    ordering_fields = ["transaction_date", "amount", "created_at"]

    def get_queryset(self):
        qs = scope_transaction_queryset(super().get_queryset(), self.request.user)
        if self.request.query_params.get("customer"):
            require_finance_permission(self.request.user, "customers", "view")
            qs = qs.filter(customer_id=self.request.query_params["customer"])
        if self.request.query_params.get("order"):
            require_finance_permission(self.request.user, "orders", "view")
            qs = qs.filter(order_id=self.request.query_params["order"])
        for key, module in (("supplier", "suppliers"), ("purchase_order", "purchases")):
            if self.request.query_params.get(key):
                require_finance_permission(self.request.user, module, "view")
                qs = qs.filter(**{key: self.request.query_params[key]})
        for key in ("status", "direction", "kind"):
            if self.request.query_params.get(key):
                qs = qs.filter(**{key: self.request.query_params[key]})
        for key, lookup in (("date_from", "transaction_date__gte"), ("date_to", "transaction_date__lte")):
            if self.request.query_params.get(key):
                qs = qs.filter(**{lookup: self.request.query_params[key]})
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data.get("plan") or serializer.validated_data.get("kind") in {"customer_receipt", "supplier_payment", "refund", "supplier_refund", "unallocated_advance", "unallocated_payment"}:
            require_finance_permission(request.user, "finance", "update")
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
        require_finance_permission(request.user, "finance", "update")
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
        require_finance_permission(request.user, "finance", "update")
        plan = get_object_or_404(scope_plan_queryset(PaymentPlan.objects.all(), request.user), pk=plan_id)
        try:
            source = self.get_object()
            plan = allocate_advance(source, plan, amount)
        except DjangoValidationError as error:
            return Response({"detail": error.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        record_operation(request=request, instance=plan, action="custom", action_label="核销预收预付", metadata={"transaction_id": source.id, "amount": str(request.data.get("amount") or "")})
        return Response(PaymentPlanSerializer(plan, context={"request": request}).data)


class InventoryMovementViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    manual_types = {"adjust_in", "adjust_out", "sample_out", "return_in", "transfer_in", "transfer_out", "production_in", "production_out", "other_in", "other_out"}
    serializer_class = InventoryMovementSerializer
    queryset = InventoryMovement.objects.select_related("sku__product", "order")
    search_fields = ["movement_no", "sku__sku", "sku__product__name", "order__order_no", "warehouse", "reference"]

    def get_search_fields(self, request):
        fields = ["movement_no", "warehouse", "reference"]
        if user_can(request.user, "skus", "view"):
            fields.append("sku__sku")
        if user_can(request.user, "products", "view"):
            fields.append("sku__product__name")
        if user_can(request.user, "orders", "view"):
            fields.append("order__order_no")
        return fields
    ordering_fields = ["movement_date", "quantity", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("sku"):
            require_finance_permission(self.request.user, "skus", "view")
            qs = qs.filter(sku_id=self.request.query_params["sku"])
        if self.request.query_params.get("product"):
            require_finance_permission(self.request.user, "products", "view")
            qs = qs.filter(sku__product_id=self.request.query_params["product"])
        if self.request.query_params.get("order"):
            require_finance_permission(self.request.user, "orders", "view")
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
    @transaction.atomic
    def reverse(self, request, pk=None):
        input_serializer = InventoryMovementReversalInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        original = self.get_object()
        from .procurement_scope import require_order_writes
        require_order_writes(request.user, [original.order_id, *original.related_orders.values_list("pk", flat=True)])
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

    def get_search_fields(self, request):
        fields = []
        if user_can(request.user, "orders", "view"):
            fields.append("order__order_no")
        if user_can(request.user, "customers", "view"):
            fields.append("order__customer__name")
        if user_can(request.user, "purchases", "view"):
            fields.append("purchase_order__purchase_no")
        if user_can(request.user, "suppliers", "view"):
            fields.append("purchase_order__supplier__name")
        return fields or ["id"]
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
        qs = scope_plan_queryset(super().get_queryset(), self.request.user)
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
        require_finance_permission(request.user, "transactions", "create")
        plan = self.get_object()
        payload = {**request.data, "plan": plan.pk,
            "currency": request.data.get("currency", plan.currency),
            "exchange_rate": request.data.get("exchange_rate", (plan.order or plan.purchase_order).exchange_rate),
            "direction": "income" if plan.order_id else "expense",
            "kind": "customer_receipt" if plan.order_id else "supplier_payment",
            "category": request.data.get("category") or ("客户收款" if plan.order_id else "供应商付款")}
        input_serializer = TransactionSerializer(data=payload, context={"request": request})
        input_serializer.is_valid(raise_exception=True)
        try:
            row = record_transaction(input_serializer.validated_data)
        except DjangoValidationError as error:
            return Response({"detail": error.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        record_operation(request=request, instance=row, action="create", action_label="结算付款计划", metadata={"payment_plan_id": plan.id})
        return Response(TransactionSerializer(row, context={"request": request}).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        return Response({"detail": "收付款计划保留合同依据，可修改未核销计划的金额、日期和备注，不支持直接删除。"}, status=status.HTTP_400_BAD_REQUEST)


class ContractChangeRequestViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    permission_classes = [ContractFinancePermission]
    serializer_class = ContractChangeRequestSerializer
    queryset = ContractChangeRequest.objects.select_related("order", "purchase_order")

    def get_queryset(self):
        queryset = super().get_queryset()
        sales_changes = scope_customer_related_queryset(queryset.filter(order__isnull=False), self.request.user, relation="order__customer")
        purchase_changes = queryset.filter(purchase_order__isnull=False)
        if not user_can(self.request.user, "orders", "view"):
            sales_changes = sales_changes.none()
        if not user_can(self.request.user, "purchases", "view"):
            purchase_changes = purchase_changes.none()
        queryset = sales_changes | purchase_changes
        if self.request.query_params.get("order"):
            queryset = queryset.filter(order_id=self.request.query_params["order"])
        if self.request.query_params.get("purchase_order"):
            queryset = queryset.filter(purchase_order_id=self.request.query_params["purchase_order"])
        return queryset

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        require_finance_permission(request.user, "finance", "create")
        try:
            request_item = self.get_object()
            plan = approve_contract_change(request_item)
        except DjangoValidationError as error:
            return Response({"detail": error.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        record_operation(request=request, instance=request_item, action="custom", action_label="审批合同变更", metadata={"payment_plan_id": plan.id})
        return Response(PaymentPlanSerializer(plan, context={"request": request}).data, status=status.HTTP_201_CREATED)

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
    trend_start = date(today.year, today.month, 1)
    for _ in range(11):
        trend_start = (
            date(trend_start.year - 1, 12, 1)
            if trend_start.month == 1
            else date(trend_start.year, trend_start.month - 1, 1)
        )
    last_year_start = date(today.year - 1, 1, 1)
    last_year_same_day = date(today.year - 1, today.month, min(today.day, 28 if today.month == 2 else today.day))
    formal_statuses = ["confirmed", "production", "shipped", "completed"]
    can_view_customers = user_can(request.user, "customers", "view")
    can_view_orders = user_can(request.user, "orders", "view")
    can_view_products = user_can(request.user, "products", "view")
    can_view_followups = user_can(request.user, "followups", "view")
    can_view_certificates = user_can(request.user, "certificates", "view") and can_view_products
    scoped_customers = scope_customer_queryset(Customer.objects.all(), request.user) if can_view_customers else Customer.objects.none()
    valid_orders = scope_customer_related_queryset(
        Order.objects.filter(status__in=formal_statuses, historical_only=False), request.user,
    ) if can_view_orders else Order.objects.none()
    def sales_between(start, end):
        return sum(
            (order.total_amount * order.exchange_rate for order in valid_orders.filter(order_date__range=(start, end)).prefetch_related("items", "contract_changes")),
            Decimal("0"),
        )

    monthly_rows = defaultdict(lambda: {"sales": Decimal("0"), "orders": 0})
    customer_rows = defaultdict(lambda: {"sales": Decimal("0"), "orders": 0, "name": "", "country": ""})
    for order in valid_orders.filter(order_date__range=(trend_start, today)).select_related("customer").prefetch_related("items", "contract_changes"):
        amount = order.total_amount * order.exchange_rate
        month = order.order_date.strftime("%Y-%m")
        monthly_rows[month]["sales"] += amount
        monthly_rows[month]["orders"] += 1
        if order.order_date >= year_start:
            customer = customer_rows[order.customer_id]
            customer["sales"] += amount
            customer["orders"] += 1
            customer["name"], customer["country"] = order.customer.name, order.customer.country
    trend_months = []
    month_cursor = trend_start
    while month_cursor <= date(today.year, today.month, 1):
        trend_months.append(month_cursor.strftime("%Y-%m"))
        month_cursor = (
            date(month_cursor.year + 1, 1, 1)
            if month_cursor.month == 12
            else date(month_cursor.year, month_cursor.month + 1, 1)
        )
    monthly = (
        [{"month": month, **monthly_rows.get(month, {"sales": Decimal("0"), "orders": 0})} for month in trend_months]
        if monthly_rows else []
    )
    # Product-category sales deliberately remain item-only: contract adjustments have no SKU/category allocation.
    categories = OrderItem.objects.filter(order__in=valid_orders, order__order_date__range=(year_start, today)).values(
        "sku__product__category__name"
    ).annotate(sales=Sum(ExpressionWrapper(amount_expression("") * F("order__exchange_rate"), output_field=MONEY)), quantity=Sum("quantity")).order_by("-sales")[:8]
    top_customers = [
        {"id": customer_id, **values}
        for customer_id, values in sorted(customer_rows.items(), key=lambda row: row[1]["sales"], reverse=True)[:6]
    ]
    cash = scope_transaction_queryset(
        Transaction.objects.filter(status="confirmed", transaction_date__range=(year_start, today)), request.user,
    )
    if not user_can(request.user, "transactions", "view"):
        cash = cash.none()
    income = sum((row.rmb_amount or row.amount * row.exchange_rate for row in cash if row.direction == "income"), Decimal("0"))
    expense = sum((row.rmb_amount or row.amount * row.exchange_rate for row in cash if row.direction == "expense"), Decimal("0"))
    due_follow_ups = scope_customer_related_queryset(current_due_follow_ups(today=today), request.user).select_related("customer", "contact").prefetch_related("attachments") if can_view_followups else FollowUp.objects.none()
    certificates = ProductCertificate.objects.filter(expires_on__lte=today + timedelta(days=90)).select_related("product") if can_view_certificates else ProductCertificate.objects.none()
    certificate_alerts = [
        {"id": c.id, "product_id": c.product_id, "product_name": c.product.name,
         "certificate_name": c.name, "certificate_no": c.certificate_no, "expires_on": c.expires_on,
         **certificate_expiry(c.expires_on, today)}
        for c in certificates.order_by("expires_on", "id")[:5]
    ]
    return Response({
        "date_ranges": {
            "as_of": today,
            "year_start": year_start,
            "year_end": today,
            "trend_start": trend_start,
            "trend_end": today,
        },
        "certificate_alerts": certificate_alerts,
        "summary": {
            "certificate_attention": certificates.count(),
            "certificate_expired": certificates.filter(expires_on__lt=today).count(),
            "certificate_expiring": certificates.filter(expires_on__gte=today).count(),
            "sales_ytd": sales_between(year_start, today),
            "sales_last_ytd": sales_between(last_year_start, last_year_same_day),
            "orders_ytd": valid_orders.filter(order_date__range=(year_start, today)).count(),
            "active_customers": scoped_customers.filter(status__in=["customer", "company"]).count(),
            "receipts_rmb": income,
            "payments_rmb": expense,
            "follow_ups_due": due_follow_ups.count(),
        },
        "monthly_sales": monthly,
        "category_sales": list(categories) if can_view_products and user_can(request.user, "categories", "view") else [],
        "top_customers": list(top_customers) if can_view_customers else [],
        "recent_orders": OrderSerializer(valid_orders.prefetch_related("items__sku__product")[:5], many=True, context={"request": request}).data,
        "due_follow_ups": FollowUpSerializer(due_follow_ups[:5], many=True, context={"request": request}).data,
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


class _ImportStateChanged(Exception):
    """The signed preview no longer describes the current database state."""


class _ImportCSVReadFailure(ValueError):
    """A file-level CSV failure with only a complete digest and reliable rows."""

    def __init__(self, detail, *, file_sha256="", digest=None, rows=None, too_large=False):
        self.file_sha256 = file_sha256 or digest or ""
        self.digest = digest if digest is not None else (file_sha256 or None)
        self.rows = rows or []
        self.too_large = too_large
        super().__init__(detail)


class _ImportAuditWriteFailure(Exception):
    """A row failed while the all-or-nothing import transaction was writing."""

    def __init__(self, row_number, message):
        self.row_number = row_number
        self.message = message
        super().__init__(message)


_ImportCsvReadError = _ImportCSVReadFailure


def _import_model_and_key(entity):
    return {
        "customers": (Customer, "code"),
        "products": (Product, "code"),
        "skus": (SKU, "sku"),
        "transactions": (Transaction, "transaction_no"),
    }[entity]


def _import_audit_snapshot(entity, instance):
    """Keep only fields needed to explain the imported business change."""
    values = snapshot(instance)
    fields = ["id", *IMPORT_FIELDS[entity]]
    return {field: values.get(field) for field in fields if field == "id" or field in values}


def _import_audit_before_rows(entity, rows):
    model, key = _import_model_and_key(entity)
    keys = [row.get(key, "").strip() for row in rows]
    records = {
        getattr(record, key): record
        for record in model.objects.filter(**{f"{key}__in": keys})
    }
    before_rows = []
    for row_number, row in enumerate(rows, start=2):
        business_key = row.get(key, "").strip()
        instance = records.get(business_key)
        before_rows.append({
            "row_number": row_number,
            "business_key": business_key,
            "before_data": _import_audit_snapshot(entity, instance) if instance else {},
        })
    return before_rows


def _import_audit_gate(request):
    user = _import_audit_operator(request)
    if user is None:
        return Response(
            {"detail": "正式导入需要已认证的操作人；当前开发身份不能作为审计操作人。"},
            status=status.HTTP_403_FORBIDDEN,
        )
    if not settings.AUDIT_LOG_ENABLED:
        return Response(
            {"detail": "审计记录未启用，无法执行正式导入；未写入业务数据。"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return None


def _import_audit_operator(request):
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return None
    if not getattr(user, "pk", None) or getattr(getattr(user, "_state", None), "adding", True):
        return None
    user_model = get_user_model()
    if not isinstance(user, user_model):
        return None
    try:
        if not user_model._default_manager.filter(pk=user.pk).exists():
            return None
    except Exception:
        return None
    return user


def _import_retry_batch(request, entity):
    retry_id = request.data.get("retry_of_batch_id")
    if not retry_id or not settings.AUDIT_LOG_ENABLED or not isinstance(entity, str):
        return None, None
    operator = _import_audit_operator(request)
    if operator is None:
        return None, None
    try:
        retry_id = int(retry_id)
    except (TypeError, ValueError):
        return None, "无法关联失败批次，请重新预览。"
    batch = CSVImportBatch.objects.filter(
        pk=retry_id,
        entity=entity,
        status="failed",
        operator=operator,
    ).first()
    if batch is None:
        return None, "无法关联失败批次，请重新预览。"
    return batch, None


def _persist_import_preview(*, request, entity, digest, rows, outcome, errors=None, reason="", retry_of_batch=None):
    if not settings.AUDIT_LOG_ENABLED:
        return None
    operator = _import_audit_operator(request)
    with transaction.atomic():
        preview = CSVImportPreviewAudit.objects.create(
            entity=entity if isinstance(entity, str) else "",
            file_sha256=digest,
            operator=operator,
            retry_of_batch=retry_of_batch,
            endpoint=getattr(request, "path", "")[:120],
            status=outcome,
            total_rows=len(rows),
            validation_errors=errors or [],
            failure_reason=reason,
        )
        if operator is not None:
            retry_metadata = {"retry_of_batch_id": retry_of_batch.pk} if retry_of_batch else {}
            record_operation(
                request=request,
                instance=preview,
                action="custom",
                action_label="CSV 导入预览" if outcome == "ready" else "CSV 导入预览未通过",
                after=snapshot(preview),
                metadata={
                    "csv_import_preview_id": str(preview.preview_id),
                    "entity": preview.entity,
                    "status": preview.status,
                    **retry_metadata,
                },
            )
    return preview


def _import_preview_failure_response(
    *, request, entity, failure, retry_of_batch=None,
    response_status=status.HTTP_400_BAD_REQUEST,
):
    preview = None
    try:
        preview = _persist_import_preview(
            request=request,
            entity=entity,
            digest=failure.file_sha256,
            rows=failure.rows,
            outcome="failed",
            reason=str(failure),
            retry_of_batch=retry_of_batch,
        )
    except Exception:
        return Response(
            {"detail": "CSV 预览失败，审计记录未能保存。"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    payload = {"detail": str(failure)}
    if preview is not None:
        payload["preview_audit_id"] = str(preview.preview_id)
    return Response(payload, status=response_status)


def _import_preview_from_token(token, entity):
    if not token or not isinstance(entity, str):
        return None
    try:
        signed = signing.loads(token, salt=IMPORT_PREVIEW_SALT)
        preview_id = signed.get("preview_id")
    except (signing.BadSignature, AttributeError, TypeError):
        return None
    if not preview_id:
        return None
    try:
        preview = CSVImportPreviewAudit.objects.get(preview_id=preview_id, entity=entity)
    except (CSVImportPreviewAudit.DoesNotExist, ValueError, TypeError):
        return None
    if signed.get("sha256") != preview.file_sha256:
        return None
    return preview


def _previous_import_batch(preview):
    if preview is None:
        return None
    return preview.batches.order_by("-created_at", "-pk").first()


def _persist_import_failure(*, request, entity, digest, rows, reason, errors=None, before_rows=None, preview=None):
    if before_rows is None:
        before_rows = _import_audit_before_rows(entity, rows) if rows and entity in IMPORT_KEY_FIELDS else []
    by_row = {item["row_number"]: item for item in before_rows}
    error_by_row = {item["row"]: item["message"] for item in (errors or [])}
    previous_attempt = _previous_import_batch(preview)
    batch_uuid = uuid.uuid4()
    with transaction.atomic():
        batch = CSVImportBatch.objects.create(
            batch_id=batch_uuid,
            entity=entity,
            file_sha256=digest,
            operator=request.user,
            preview=preview,
            status="failed",
            total_rows=len(rows),
            failed_rows=len(rows),
            failure_reason=reason,
        )
        record_operation(
            request=request,
            instance=batch,
            action="custom",
            action_label="CSV 导入失败",
            after=snapshot(batch),
            metadata={
                "csv_import_batch_id": str(batch_uuid),
                "entity": entity,
                **({"csv_import_preview_id": str(preview.preview_id)} if preview else {}),
                **({"previous_attempt_batch_id": previous_attempt.pk} if previous_attempt else {}),
                **({"retry_of_batch_id": preview.retry_of_batch_id} if preview and preview.retry_of_batch_id else {}),
            },
        )
        for row_number, row in enumerate(rows, start=2):
            before = by_row.get(row_number, {}).get("before_data", {})
            message = error_by_row.get(row_number) or f"批次未执行：{reason}"
            CSVImportRowAudit.objects.create(
                batch=batch,
                row_number=row_number,
                business_key=row.get(IMPORT_KEY_FIELDS[entity], ""),
                object_id=str(before.get("id", "")) if before.get("id") is not None else "",
                result="failed",
                before_data=before,
                after_data={},
                error_message=message,
            )
    return batch


def _import_failure_response(
    *, request, entity, digest, rows, detail, errors=None, before_rows=None,
    response_status=status.HTTP_400_BAD_REQUEST, preview=None,
):
    try:
        batch = _persist_import_failure(
            request=request,
            entity=entity,
            digest=digest,
            rows=rows,
            reason=detail,
            errors=errors,
            before_rows=before_rows,
            preview=preview,
        )
    except Exception:
        # A business write is never reported as complete when its audit cannot
        # be persisted. The caller has already kept the business transaction
        # rolled back.
        return Response(
            {"detail": "正式导入失败，审计记录未能保存，未写入业务数据。"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    payload = {"detail": detail, "import_batch_id": str(batch.batch_id)}
    if preview is not None:
        payload["preview_audit_id"] = str(preview.preview_id)
    if errors:
        payload["errors"] = errors
    return Response(payload, status=response_status)


def _apply_import_rows_with_audit(entity, rows, user, before_rows):
    model, key = _import_model_and_key(entity)
    created = updated = 0
    row_records = []
    for before_row, row in zip(before_rows, rows):
        row_number = before_row["row_number"]
        try:
            was_created = _import_row(entity, row, user=user)
            instance = model.objects.get(**{key: row.get(key, "")})
        except Exception as exc:
            raise _ImportAuditWriteFailure(row_number, _import_error_message(exc)) from exc
        result = "created" if was_created else "updated"
        created += int(was_created)
        updated += int(not was_created)
        row_records.append({
            "row_number": row_number,
            "business_key": before_row["business_key"],
            "object_id": str(instance.pk),
            "result": result,
            "before_data": before_row["before_data"],
            "after_data": _import_audit_snapshot(entity, instance),
            "instance": instance,
        })
    return created, updated, row_records


def _persist_import_success(*, request, entity, digest, rows, created, updated, row_records, preview):
    previous_attempt = _previous_import_batch(preview)
    batch_uuid = uuid.uuid4()
    batch = CSVImportBatch.objects.create(
        batch_id=batch_uuid,
        entity=entity,
        file_sha256=digest,
        operator=request.user,
        preview=preview,
        status="succeeded",
        total_rows=len(rows),
        created_rows=created,
        updated_rows=updated,
    )
    record_operation(
        request=request,
        instance=batch,
        action="custom",
        action_label="CSV 导入完成",
        after=snapshot(batch),
        metadata={
            "csv_import_batch_id": str(batch_uuid),
            "entity": entity,
            "csv_import_preview_id": str(preview.preview_id),
            **({"previous_attempt_batch_id": previous_attempt.pk} if previous_attempt else {}),
            **({"retry_of_batch_id": preview.retry_of_batch_id} if preview.retry_of_batch_id else {}),
        },
    )
    for item in row_records:
        row_audit = CSVImportRowAudit.objects.create(
            batch=batch,
            row_number=item["row_number"],
            business_key=item["business_key"],
            object_id=item["object_id"],
            result=item["result"],
            before_data=item["before_data"],
            after_data=item["after_data"],
        )
        record_operation(
            request=request,
            instance=item["instance"],
            action="create" if item["result"] == "created" else "update",
            action_label="CSV 导入创建" if item["result"] == "created" else "CSV 导入更新",
            before=item["before_data"],
            after=item["after_data"],
            metadata={
                "csv_import_batch_id": str(batch_uuid),
                "csv_import_row_audit_id": row_audit.pk,
                "row_number": item["row_number"],
            },
        )
    return batch


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
    data = request.data
    entity = data.get("entity")
    retry_of_batch, retry_error = _import_retry_batch(request, entity)
    if retry_error:
        return Response({"detail": retry_error}, status=status.HTTP_400_BAD_REQUEST)
    if _csv_import_upload_limit_exceeded(request):
        failure = _ImportCSVReadFailure(
            _csv_import_size_limit_message(settings.CSV_IMPORT_MAX_BYTES),
            too_large=True,
        )
        return _import_preview_failure_response(
            request=request,
            entity=entity,
            failure=failure,
            retry_of_batch=retry_of_batch,
            response_status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )
    upload = request.FILES.get("file")
    try:
        rows, digest = _read_import_csv(entity, upload)
    except _ImportCSVReadFailure as exc:
        return _import_preview_failure_response(
            request=request,
            entity=entity,
            failure=exc,
            retry_of_batch=retry_of_batch,
            response_status=(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
                if exc.too_large else status.HTTP_400_BAD_REQUEST
            ),
        )
    preview_state = _import_state(entity, rows)
    result = _preview_import(entity, rows, user=request.user)
    outcome = "invalid" if result["errors"] else "ready"
    try:
        preview_audit = _persist_import_preview(
            request=request,
            entity=entity,
            digest=digest,
            rows=rows,
            outcome=outcome,
            errors=result["errors"],
            reason="预览校验未通过。" if result["errors"] else "",
            retry_of_batch=retry_of_batch,
        )
    except Exception:
        return Response(
            {"detail": "CSV 预览失败，审计记录未能保存。"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    if not result["errors"]:
        result["preview_token"] = signing.dumps(
            {
                "entity": entity,
                "sha256": digest,
                "state": preview_state,
                "preview_id": str(preview_audit.preview_id) if preview_audit else None,
            },
            salt=IMPORT_PREVIEW_SALT,
        )
    if preview_audit is not None:
        result["preview_audit_id"] = str(preview_audit.preview_id)
    return Response(result)


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def import_csv_execute(request):
    audit_gate = _import_audit_gate(request)
    if audit_gate is not None:
        return audit_gate
    data = request.data
    entity = data.get("entity")
    token = data.get("preview_token")
    preview_audit = _import_preview_from_token(token, entity)
    if _csv_import_upload_limit_exceeded(request):
        detail = _csv_import_size_limit_message(settings.CSV_IMPORT_MAX_BYTES)
        if entity in IMPORT_FIELDS:
            return _import_failure_response(
                request=request,
                entity=entity,
                digest="",
                rows=[],
                detail=detail,
                before_rows=[],
                preview=preview_audit,
                response_status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )
        return Response({"detail": detail}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
    upload = request.FILES.get("file")
    rows = []
    digest = ""
    try:
        rows, digest = _read_import_csv(entity, upload)
    except _ImportCSVReadFailure as exc:
        if entity in IMPORT_FIELDS:
            # Parsing failed before reliable row objects existed. Record only
            # the attempted batch, never synthetic or partially parsed rows.
            return _import_failure_response(
                request=request,
                entity=entity,
                digest=exc.file_sha256,
                rows=exc.rows,
                detail=str(exc),
                before_rows=[],
                preview=preview_audit,
                response_status=(
                    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
                    if exc.too_large else status.HTTP_400_BAD_REQUEST
                ),
            )
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    try:
        signed = signing.loads(token or "", salt=IMPORT_PREVIEW_SALT, max_age=IMPORT_PREVIEW_MAX_AGE_SECONDS)
    except signing.SignatureExpired:
        return _import_failure_response(
            request=request, entity=entity, digest=digest, rows=rows,
            detail="预览已过期，请重新预览后再导入。",
            preview=preview_audit,
        )
    except signing.BadSignature:
        return _import_failure_response(
            request=request, entity=entity, digest=digest, rows=rows,
            detail="预览凭证无效，请重新预览后再导入。",
            preview=preview_audit,
        )
    if (
        preview_audit is None
        or signed.get("preview_id") != str(preview_audit.preview_id)
        or preview_audit.status != "ready"
    ):
        return _import_failure_response(
            request=request, entity=entity, digest=digest, rows=rows,
            detail="预览记录不存在或已失效，请重新预览后再导入。",
            preview=preview_audit,
        )
    if signed.get("entity") != entity or signed.get("sha256") != digest:
        return _import_failure_response(
            request=request, entity=entity, digest=digest, rows=rows,
            detail="文件或数据类型已变化，请重新预览后再导入。",
            preview=preview_audit,
        )
    if signed.get("state") != _import_state(entity, rows):
        return _import_failure_response(
            request=request, entity=entity, digest=digest, rows=rows,
            detail="数据状态已发生变化，请重新预览后再导入。",
            preview=preview_audit,
        )

    # Run the exact write path once in a transaction that is rolled back. This
    # detects concurrent changes after preview without leaving any side effects.
    validation = _preview_import(entity, rows, user=request.user)
    if validation["errors"]:
        return _import_failure_response(
            request=request, entity=entity, digest=digest, rows=rows,
            detail="数据状态已变化，请重新预览后再导入。", errors=validation["errors"],
            preview=preview_audit,
        )
    before_rows = []
    try:
        with transaction.atomic():
            if signed.get("state") != _import_state(entity, rows, lock=True):
                raise _ImportStateChanged("数据状态已发生变化，请重新预览后再导入。")
            before_rows = _import_audit_before_rows(entity, rows)
            created, updated, row_records = _apply_import_rows_with_audit(entity, rows, request.user, before_rows)
            batch = _persist_import_success(
                request=request,
                entity=entity,
                digest=digest,
                rows=rows,
                created=created,
                updated=updated,
                row_records=row_records,
                preview=preview_audit,
            )
    except _ImportStateChanged as exc:
        return _import_failure_response(
            request=request, entity=entity, digest=digest, rows=rows,
            detail=str(exc), before_rows=before_rows,
            preview=preview_audit,
        )
    except _ImportAuditWriteFailure as exc:
        return _import_failure_response(
            request=request, entity=entity, digest=digest, rows=rows,
            detail="数据状态已变化，请重新预览后再导入。",
            errors=[{"row": exc.row_number, "message": exc.message, "key": rows[exc.row_number - 2].get(IMPORT_KEY_FIELDS[entity], "")}],
            before_rows=before_rows,
            preview=preview_audit,
        )
    except Exception as exc:
        return _import_failure_response(
            request=request, entity=entity, digest=digest, rows=rows,
            detail="数据状态已变化，请重新预览后再导入。",
            errors=[{"row": before_rows[0]["row_number"] if before_rows else 2, "message": _import_error_message(exc), "key": rows[0].get(IMPORT_KEY_FIELDS[entity], "") if rows else ""}],
            before_rows=before_rows,
            preview=preview_audit,
        )
    return Response({
        "total": len(rows),
        "created": created,
        "updated": updated,
        "import_batch_id": str(batch.batch_id),
        "preview_audit_id": str(preview_audit.preview_id),
    })


def _csv_import_upload_limit_exceeded(request):
    django_request = getattr(request, "_request", request)
    return bool(getattr(django_request, "_csv_import_upload_limit_exceeded", False))


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
    if not isinstance(entity, str):
        raise _ImportCSVReadFailure("请选择有效的数据类型和 CSV 文件。")
    if entity == "orders":
        raise _ImportCSVReadFailure(ORDER_IMPORT_DISABLED_MESSAGE)
    if entity not in IMPORT_FIELDS:
        raise _ImportCSVReadFailure("请选择有效的数据类型和 CSV 文件。")
    if upload is None:
        raise _ImportCSVReadFailure("请选择有效的数据类型和 CSV 文件。")

    max_bytes = settings.CSV_IMPORT_MAX_BYTES
    size = getattr(upload, "size", None)
    if isinstance(size, int) and not isinstance(size, bool) and size > max_bytes:
        raise _ImportCSVReadFailure(
            _csv_import_size_limit_message(max_bytes),
            too_large=True,
        )

    chunks = []
    bytes_read = 0
    chunk_size = min(64 * 1024, max_bytes + 1)
    while bytes_read <= max_bytes:
        requested = min(chunk_size, max_bytes + 1 - bytes_read)
        try:
            chunk = upload.read(requested)
        except OSError as exc:
            raise _ImportCSVReadFailure("CSV 文件读取失败，请重新选择文件。") from exc
        if not chunk:
            break
        if not isinstance(chunk, (bytes, bytearray, memoryview)):
            raise _ImportCSVReadFailure("CSV 文件无法读取，请上传二进制 CSV 文件。")
        chunk = bytes(chunk)
        if len(chunk) > requested:
            raise _ImportCSVReadFailure(
                _csv_import_size_limit_message(max_bytes),
                too_large=True,
            )
        bytes_read += len(chunk)
        if bytes_read > max_bytes:
            raise _ImportCSVReadFailure(
                _csv_import_size_limit_message(max_bytes),
                too_large=True,
            )
        chunks.append(chunk)

    raw = b"".join(chunks)
    digest = hashlib.sha256(raw).hexdigest()
    if not raw:
        raise _ImportCSVReadFailure("CSV 文件为空。", file_sha256=digest)

    rows = []
    try:
        text = raw.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            raise _ImportCSVReadFailure("CSV 缺少表头。", file_sha256=digest)
        headers = {str(field or "").strip() for field in reader.fieldnames}
        missing = IMPORT_REQUIRED_FIELDS[entity] - headers
        if missing:
            raise _ImportCSVReadFailure(
                f"CSV 缺少必要字段：{'、'.join(sorted(missing))}。",
                file_sha256=digest,
            )
        for parsed_row in reader:
            if None in parsed_row or any(value is None for value in parsed_row.values()):
                raise _ImportCSVReadFailure(
                    "CSV 数据行的字段数与表头不一致。",
                    file_sha256=digest,
                )
            rows.append({str(key or "").strip(): (value or "").strip() for key, value in parsed_row.items()})
    except _ImportCSVReadFailure:
        raise
    except UnicodeDecodeError as exc:
        raise _ImportCSVReadFailure(
            "CSV 文件无法读取，请使用 UTF-8 或 UTF-8 BOM 编码。",
            file_sha256=digest,
        ) from exc
    except csv.Error as exc:
        raise _ImportCSVReadFailure("CSV 文件格式无效。", file_sha256=digest) from exc
    if not rows:
        raise _ImportCSVReadFailure("CSV 没有数据行。", file_sha256=digest)
    if len(rows) > 5000:
        raise _ImportCSVReadFailure(
            "CSV 最多允许 5000 行数据。",
            file_sha256=digest,
            rows=rows,
        )
    key = IMPORT_KEY_FIELDS[entity]
    duplicates = _duplicate_key_errors(rows, key)
    if duplicates:
        for row_number, message in duplicates:
            rows[row_number - 2]["__import_error__"] = message
    return rows, digest


def _csv_import_size_limit_message(max_bytes):
    mebibyte = 1024 * 1024
    if max_bytes % mebibyte == 0:
        limit = f"{max_bytes // mebibyte} MiB（{max_bytes:,} 字节）"
    else:
        limit = f"{max_bytes:,} 字节"
    return f"CSV 文件超过大小限制（最大 {limit}）。"


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
    if isinstance(exc, Product.DoesNotExist):
        return "找不到所引用的产品，请核对 product_code。"
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
        require_finance_permission(user, "customers", "update" if instance else "create")
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
        require_finance_permission(user, "products", "update" if Product.objects.filter(code=row["code"]).exists() else "create")
        category = None
        if row.get("category"):
            require_finance_permission(user, "categories", "view")
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
        require_finance_permission(user, "skus", "update" if SKU.objects.filter(sku=row["sku"]).exists() else "create")
        require_finance_permission(user, "products", "view")
        product = Product.objects.get(code=row["product_code"])
        instance = SKU.objects.filter(sku=row["sku"]).first()
        payload = {
            "product": product.pk, "specification": row.get("specification", ""),
            "unit": row.get("unit") or "pcs",
            "default_price": _decimal(row.get("default_price")), "currency": row.get("currency") or "USD",
        }
        if str(row.get("cost_price") or "").strip():
            require_finance_permission(user, "purchases", "update")
            payload["cost_price"] = _decimal(row.get("cost_price"))
        serializer = SKUSerializer(instance, data=payload, partial=bool(instance), context={"user": user})
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
    require_finance_permission(user, "transactions", "create")
    payload = {**defaults, "transaction_no": row["transaction_no"], "customer": defaults["customer"].pk if defaults["customer"] else None, "order": order.pk if order else None}
    validate_finance_relations(defaults, user)
    require_finance_permission(user, "transactions", "create")
    if defaults.get("kind") == "customer_receipt":
        require_finance_permission(user, "finance", "update")
    serializer = TransactionSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    record_transaction(serializer.validated_data)
    return True
