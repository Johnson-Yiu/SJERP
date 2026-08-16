import csv
import io
from datetime import date
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Case, Count, DecimalField, ExpressionWrapper, F, IntegerField, OuterRef, Q, Subquery, Sum, Value, When
from django.db.models.functions import Coalesce, TruncMonth
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action, api_view, parser_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from .models import AccessRole, CategoryAttribute, Contact, Customer, EmployeeProfile, FollowUp, InventoryMovement, Order, OrderItem, OrganizationUnit, Position, Product, ProductCategory, ProductCertificate, ProductParameter, Quote, RolePermission, SKU, Transaction
from .permissions import PermissionAdminOnly, QuoteExportPermission
from .quote_numbers import allocate_revision_quote_no
from .quote_export import QuoteExportError, build_pi_export_payload
from .quote_snapshots import create_quote_items
from .serializers import AccessRoleSerializer, CategoryAttributeSerializer, ContactSerializer, CustomerSerializer, EmployeeProfileSerializer, FollowUpSerializer, InventoryMovementSerializer, OrderSerializer, OrganizationUnitSerializer, PositionSerializer, ProductCategorySerializer, ProductCertificateSerializer, ProductParameterSerializer, ProductSerializer, QuoteSerializer, RolePermissionSerializer, SKUSerializer, TransactionSerializer, next_product_code

MONEY = DecimalField(max_digits=20, decimal_places=2)


class OrganizationUnitViewSet(viewsets.ModelViewSet):
    serializer_class = OrganizationUnitSerializer
    queryset = OrganizationUnit.objects.select_related("parent").prefetch_related("positions").annotate(employee_count=Count("employees"))
    search_fields = ["name", "code"]


class PositionViewSet(viewsets.ModelViewSet):
    serializer_class = PositionSerializer
    queryset = Position.objects.select_related("unit")
    search_fields = ["name", "code", "unit__name"]


class AccessRoleViewSet(viewsets.ModelViewSet):
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


class RolePermissionViewSet(viewsets.ModelViewSet):
    serializer_class = RolePermissionSerializer
    queryset = RolePermission.objects.select_related("role")
    permission_classes = [PermissionAdminOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(role_id=self.request.query_params["role"]) if self.request.query_params.get("role") else qs


class EmployeeProfileViewSet(viewsets.ModelViewSet):
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

    if request.user.is_authenticated:
        profile = getattr(request.user, "employee_profile", None)
        name = profile.display_name if profile else request.user.get_full_name() or request.user.username
        roles = list(profile.roles.values_list("name", flat=True)) if profile else []
        role = "、".join(roles) or ("超级管理员" if request.user.is_superuser else "管理员")
        return Response({"name": name, "role": role, "authenticated": True})
    return Response({"name": settings.DEFAULT_OPERATOR_NAME, "role": "超级管理员", "authenticated": False})


class CustomerViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    search_fields = ["name", "code", "country", "owner", "source"]
    ordering_fields = ["name", "created_at", "updated_at", "next_follow_up"]

    def get_queryset(self):
        sales_value = ExpressionWrapper(F("quantity") * F("unit_price") * F("order__exchange_rate"), output_field=MONEY)
        sales = OrderItem.objects.filter(order__customer=OuterRef("pk")).exclude(order__status="cancelled").values("order__customer").annotate(total=Sum(sales_value)).values("total")
        order_count = Order.objects.filter(customer=OuterRef("pk")).exclude(status="cancelled").values("customer").annotate(total=Count("id")).values("total")
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
        line_total = ExpressionWrapper(F("items__quantity") * F("items__unit_price") * F("exchange_rate"), output_field=MONEY)
        yearly = []
        for target in [year - 1, year]:
            orders = customer.orders.exclude(status="cancelled").filter(order_date__year=target)
            yearly.append({
                "year": target,
                "orders": orders.count(),
                "sales": orders.aggregate(v=Coalesce(Sum(line_total), Decimal("0"), output_field=MONEY))["v"],
            })
        products = OrderItem.objects.filter(order__customer=customer).exclude(order__status="cancelled").values(
            "sku__product__id", "sku__product__name"
        ).annotate(
            sales=Sum(ExpressionWrapper(F("quantity") * F("unit_price") * F("order__exchange_rate"), output_field=MONEY)),
            quantity=Sum("quantity"),
        ).order_by("-sales")[:10]
        return Response({
            "customer": CustomerSerializer(customer).data,
            "yearly": yearly,
            "top_products": list(products),
            "recent_orders": OrderSerializer(customer.orders.prefetch_related("items__sku__product")[:5], many=True).data,
            "recent_follow_ups": FollowUpSerializer(customer.follow_ups.select_related("contact")[:5], many=True).data,
        })


class ContactViewSet(viewsets.ModelViewSet):
    queryset = Contact.objects.select_related("customer")
    serializer_class = ContactSerializer
    search_fields = ["name", "email", "phone", "customer__name"]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(customer_id=self.request.query_params["customer"]) if self.request.query_params.get("customer") else qs


class FollowUpViewSet(viewsets.ModelViewSet):
    queryset = FollowUp.objects.select_related("customer", "contact")
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


class ProductCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = ProductCategorySerializer
    queryset = ProductCategory.objects.select_related("parent").prefetch_related("attributes", "parent__attributes", "parent__parent__attributes").annotate(product_count=Count("products", distinct=True), child_count=Count("children", distinct=True))
    search_fields = ["name"]

    @action(detail=False, methods=["get"])
    def tree(self, request):
        return Response(self.get_serializer(self.get_queryset().order_by("parent_id", "sort_order", "id"), many=True).data)

    @action(detail=False, methods=["post"])
    @transaction.atomic
    def reorder(self, request):
        category = get_object_or_404(ProductCategory, pk=request.data.get("id"))
        parent_id = request.data.get("parent") or None
        new_parent = get_object_or_404(ProductCategory, pk=parent_id) if parent_id else None
        cursor = new_parent
        while cursor:
            if cursor.pk == category.pk:
                return Response({"detail": "不能把分类移动到自身或其子分类下。"}, status=status.HTTP_400_BAD_REQUEST)
            cursor = cursor.parent
        old_parent_id = category.parent_id
        category.parent = new_parent
        category.save(update_fields=["parent", "updated_at"])
        siblings = list(ProductCategory.objects.filter(parent=new_parent).exclude(pk=category.pk).order_by("sort_order", "id"))
        index = max(0, min(int(request.data.get("index", len(siblings))), len(siblings)))
        siblings.insert(index, category)
        for order, sibling in enumerate(siblings):
            ProductCategory.objects.filter(pk=sibling.pk).update(sort_order=order)
        if old_parent_id != parent_id:
            for order, sibling in enumerate(ProductCategory.objects.filter(parent_id=old_parent_id).order_by("sort_order", "id")):
                ProductCategory.objects.filter(pk=sibling.pk).update(sort_order=order)
        return Response({"detail": "分类位置已更新。"})


class CategoryAttributeViewSet(viewsets.ModelViewSet):
    serializer_class = CategoryAttributeSerializer
    queryset = CategoryAttribute.objects.select_related("category")

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(category_id=self.request.query_params["category"]) if self.request.query_params.get("category") else qs

    @action(detail=False, methods=["post"])
    @transaction.atomic
    def reorder(self, request):
        category = get_object_or_404(ProductCategory, pk=request.data.get("category"))
        ids = request.data.get("ids")
        if not isinstance(ids, list):
            return Response({"detail": "ids 必须为属性 ID 数组。"}, status=status.HTTP_400_BAD_REQUEST)
        attributes = list(CategoryAttribute.objects.filter(category=category).order_by("sort_order", "id"))
        existing_ids = {attribute.id for attribute in attributes}
        if set(ids) != existing_ids or len(ids) != len(existing_ids):
            return Response({"detail": "排序内容与当前分类属性不一致。"}, status=status.HTTP_400_BAD_REQUEST)
        for order, attribute_id in enumerate(ids):
            CategoryAttribute.objects.filter(pk=attribute_id).update(sort_order=order)
        return Response({"detail": "属性排序已更新。"})


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    queryset = Product.objects.select_related("category").annotate(
        sku_count=Count("skus", distinct=True),
        parameter_count=Count("parameters", distinct=True),
        certificate_count=Count("certificates", distinct=True),
    )
    search_fields = ["name", "name_en", "code", "hs_code", "category__name"]

    def get_queryset(self):
        queryset = super().get_queryset()
        category_id = self.request.query_params.get("category")
        if category_id:
            queryset = queryset.filter(Q(category_id=category_id) | Q(additional_categories__id=category_id)).distinct()
        return queryset

    @action(detail=False, methods=["get"], url_path="next-code")
    def next_code(self, request):
        return Response({"code": next_product_code()})

    @action(detail=True, methods=["get"])
    def customers(self, request, pk=None):
        rows = OrderItem.objects.filter(sku__product=self.get_object()).exclude(order__status="cancelled").values(
            "order__customer__id", "order__customer__name", "order__customer__country"
        ).annotate(
            sales=Sum(ExpressionWrapper(F("quantity") * F("unit_price") * F("order__exchange_rate"), output_field=MONEY)),
            order_count=Count("order", distinct=True), quantity=Sum("quantity"),
        ).order_by("-sales")
        return Response(list(rows))


class SKUViewSet(viewsets.ModelViewSet):
    serializer_class = SKUSerializer
    queryset = SKU.objects.select_related("product").annotate(
        stock_quantity=Coalesce(Sum(Case(
            When(inventory_movements__type__in=["sale_out", "adjust_out", "sample_out"], then=-F("inventory_movements__quantity")),
            default=F("inventory_movements__quantity"), output_field=MONEY,
        )), Decimal("0"), output_field=MONEY)
    ).order_by("sku")
    search_fields = ["sku", "specification", "product__name", "product__code"]

    def get_queryset(self):
        qs = super().get_queryset()
        # 列表默认隐藏停用 SKU；但 retrieve / update 必须能读取它们，
        # 才能支持管理员重新启用软停用的 SKU。
        if self.action == "list" and self.request.query_params.get("include_inactive") != "1":
            qs = qs.filter(active=True)
        return qs.filter(product_id=self.request.query_params["product"]) if self.request.query_params.get("product") else qs

    @action(detail=True, methods=["post", "delete"], parser_classes=[MultiPartParser, FormParser])
    def image(self, request, pk=None):
        sku = self.get_object()
        if request.method == "DELETE":
            if sku.image:
                sku.image.delete(save=False)
            sku.image = ""
            sku.save(update_fields=["image"])
            return Response(self.get_serializer(sku).data)

        upload = request.FILES.get("image")
        allowed_mime_types = {"image/gif", "image/jpeg", "image/png", "image/webp"}
        if upload is None:
            return Response({"image": "请上传图片文件。"}, status=status.HTTP_400_BAD_REQUEST)
        if upload.content_type not in allowed_mime_types:
            return Response({"image": "仅支持 GIF、JPEG、PNG 或 WebP 图片。"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(sku, data={"image": upload}, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ProductParameterViewSet(viewsets.ModelViewSet):
    serializer_class = ProductParameterSerializer
    queryset = ProductParameter.objects.select_related("product")
    search_fields = ["product__name", "product__code", "group", "name", "value"]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(product_id=self.request.query_params["product"]) if self.request.query_params.get("product") else qs


class ProductCertificateViewSet(viewsets.ModelViewSet):
    serializer_class = ProductCertificateSerializer
    queryset = ProductCertificate.objects.select_related("product")
    search_fields = ["product__name", "name", "certificate_no", "issuer"]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(product_id=self.request.query_params["product"]) if self.request.query_params.get("product") else qs


class QuoteViewSet(viewsets.ModelViewSet):
    serializer_class = QuoteSerializer
    queryset = Quote.objects.select_related("customer", "root_quote").prefetch_related("items__sku__product")
    search_fields = ["quote_no", "customer__name"]
    ordering_fields = ["quote_date", "valid_until", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(customer_id=self.request.query_params["customer"]) if self.request.query_params.get("customer") else qs

    def update(self, request, *args, **kwargs):
        return Response({"detail": "已保存报价请创建迭代版本"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "Saved quotations are permanent records and cannot be deleted."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def revise(self, request, pk=None):
        source = self.get_object()
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        changes = serializer.validated_data.copy()
        item_data = changes.pop("items", None)
        if "customer" in changes and changes["customer"].pk != source.customer_id:
            raise serializers.ValidationError({"customer": "修订版本不能更换客户。"})
        root_quote = source.root_quote or source
        try:
            quote_no, revision_no = allocate_revision_quote_no(root_quote)
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
        revision = Quote.objects.create(
            quote_no=quote_no,
            root_quote=root_quote,
            revision_no=revision_no,
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
                }
                for item in source_items
            ]
            create_quote_items(revision, item_data, source_items=source_items)
        else:
            create_quote_items(revision, item_data)
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
                "sku": item.sku_code_snapshot,
                "product_name": item.product_name_snapshot,
                "description": item.description,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "amount": amount,
                "unit": item.unit_snapshot,
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


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    queryset = Order.objects.select_related("customer", "quote").prefetch_related("items__sku__product", "transactions")
    search_fields = ["order_no", "customer__name"]
    ordering_fields = ["order_date", "expected_ship_date", "created_at"]

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
        return qs


class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    queryset = Transaction.objects.select_related("customer", "order")
    search_fields = ["transaction_no", "category", "customer__name", "order__order_no", "reference"]
    ordering_fields = ["transaction_date", "amount", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("customer"):
            qs = qs.filter(customer_id=self.request.query_params["customer"])
        if self.request.query_params.get("order"):
            qs = qs.filter(order_id=self.request.query_params["order"])
        return qs


class InventoryMovementViewSet(viewsets.ModelViewSet):
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
            qs = qs.filter(order_id=self.request.query_params["order"])
        return qs


@api_view(["GET"])
def dashboard(request):
    today = timezone.localdate()
    year_start = date(today.year, 1, 1)
    last_year_start = date(today.year - 1, 1, 1)
    last_year_same_day = date(today.year - 1, today.month, min(today.day, 28 if today.month == 2 else today.day))
    valid_orders = Order.objects.exclude(status="cancelled")
    item_value = ExpressionWrapper(F("items__quantity") * F("items__unit_price") * F("exchange_rate"), output_field=MONEY)

    def sales_between(start, end):
        return valid_orders.filter(order_date__range=(start, end)).aggregate(
            v=Coalesce(Sum(item_value), Decimal("0"), output_field=MONEY)
        )["v"]

    monthly = valid_orders.filter(order_date__gte=last_year_start).annotate(month=TruncMonth("order_date")).values("month").annotate(
        sales=Coalesce(Sum(item_value), Decimal("0"), output_field=MONEY), orders=Count("id", distinct=True)
    ).order_by("month")
    categories = OrderItem.objects.filter(order__order_date__gte=year_start).exclude(order__status="cancelled").values(
        "sku__product__category__name"
    ).annotate(sales=Sum(ExpressionWrapper(F("quantity") * F("unit_price") * F("order__exchange_rate"), output_field=MONEY)), quantity=Sum("quantity")).order_by("-sales")[:8]
    top_customers = Customer.objects.filter(orders__order_date__gte=year_start).exclude(orders__status="cancelled").values("id", "name", "country").annotate(
        sales=Sum(ExpressionWrapper(F("orders__items__quantity") * F("orders__items__unit_price") * F("orders__exchange_rate"), output_field=MONEY)),
        orders=Count("orders", distinct=True),
    ).order_by("-sales")[:6]
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
            "follow_ups_due": FollowUp.objects.filter(next_follow_up__lte=today).count(),
        },
        "monthly_sales": [{"month": row["month"].strftime("%Y-%m"), "sales": row["sales"], "orders": row["orders"]} for row in monthly],
        "category_sales": list(categories),
        "top_customers": list(top_customers),
        "recent_orders": OrderSerializer(valid_orders.prefetch_related("items__sku__product")[:5], many=True).data,
        "due_follow_ups": FollowUpSerializer(FollowUp.objects.filter(next_follow_up__lte=today).select_related("customer", "contact")[:5], many=True).data,
    })


IMPORT_FIELDS = {
    "customers": ["code", "name", "country", "source", "status", "owner", "website", "address", "notes"],
    "products": ["code", "name", "category", "description", "status"],
    "skus": ["sku", "product_code", "specification", "unit", "cost_price", "default_price", "currency"],
    "orders": ["order_no", "customer_code", "order_date", "status", "currency", "exchange_rate", "notes"],
    "transactions": ["transaction_no", "transaction_date", "direction", "category", "amount", "currency", "exchange_rate", "customer_code", "order_no", "payment_method", "reference", "notes"],
}


@api_view(["GET"])
def import_templates(request):
    return Response(IMPORT_FIELDS)


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def import_csv(request):
    entity = request.data.get("entity")
    upload = request.FILES.get("file")
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
    if entity == "customers":
        _, created = Customer.objects.update_or_create(code=row["code"], defaults={k: row.get(k, "") for k in IMPORT_FIELDS[entity] if k != "code"})
        return created
    if entity == "products":
        category = None
        if row.get("category"):
            category, _ = ProductCategory.objects.get_or_create(name=row["category"])
        defaults = {"name": row["name"], "category": category, "description": row.get("description", ""), "status": row.get("status") or "active"}
        _, created = Product.objects.update_or_create(code=row["code"], defaults=defaults)
        return created
    if entity == "skus":
        product = Product.objects.get(code=row["product_code"])
        defaults = {"product": product, "specification": row.get("specification", ""), "unit": row.get("unit") or "pcs", "cost_price": _decimal(row.get("cost_price")), "default_price": _decimal(row.get("default_price")), "currency": row.get("currency") or "USD"}
        _, created = SKU.objects.update_or_create(sku=row["sku"], defaults=defaults)
        return created
    if entity == "orders":
        customer = Customer.objects.get(code=row["customer_code"])
        defaults = {"customer": customer, "order_date": row["order_date"], "status": row.get("status") or "confirmed", "currency": row.get("currency") or "USD", "exchange_rate": _decimal(row.get("exchange_rate"), "1"), "notes": row.get("notes", "")}
        _, created = Order.objects.update_or_create(order_no=row["order_no"], defaults=defaults)
        return created
    customer = Customer.objects.filter(code=row.get("customer_code")).first() if row.get("customer_code") else None
    order = Order.objects.filter(order_no=row.get("order_no")).first() if row.get("order_no") else None
    defaults = {"transaction_date": row["transaction_date"], "direction": row["direction"], "category": row["category"], "amount": _decimal(row["amount"]), "currency": row.get("currency") or "USD", "exchange_rate": _decimal(row.get("exchange_rate"), "1"), "customer": customer or (order.customer if order else None), "order": order, "payment_method": row.get("payment_method", ""), "reference": row.get("reference", ""), "notes": row.get("notes", "")}
    _, created = Transaction.objects.update_or_create(transaction_no=row["transaction_no"], defaults=defaults)
    return created
