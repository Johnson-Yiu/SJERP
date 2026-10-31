from .procurement_scope import scoped_supplier_candidates
from .finance_scope import require_finance_permission
from .permissions import user_can
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    CustomerSupplierPreference, Order, OrderItem, Product, SKU, SKUParameterPlan, Supplier, SupplierCapability, SupplierCandidateOverride, SupplierSKU,
)
from .audit import AuditTrailMixin, record_operation, snapshot
from .services.sku_plans import draft_plan, analyze, publish, validate_definitions, definitions_for
from .services.supplier_candidates import validate_filters, matches, candidates
from .sku_identity import raw_parameter_value
from .sales_scope import scope_customer_related_queryset


class CapabilitySerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)

    class Meta:
        model = SupplierCapability
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        user = self.context.get("request").user if self.context.get("request") else self.context.get("user")
        if not user_can(user, "products", "view"):
            data["product"] = None
        return data

    def validate(self, attrs):
        user = self.context.get("request").user if self.context.get("request") else self.context.get("user")
        product = attrs.get("product", getattr(self.instance, "product", None))
        if product and user is not None:
            require_finance_permission(user, "products", "view")
        validate_filters(product, attrs.get("filters", getattr(self.instance, "filters", {})))
        if not isinstance(attrs.get("characteristics", {}), dict) or any(not isinstance(v, str) for v in attrs.get("characteristics", {}).values()):
            raise ValidationError({"characteristics": "供货特点须为名称和文本值。"})
        return attrs


class SupplierCapabilityViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    queryset = SupplierCapability.objects.select_related("supplier", "product").order_by("id")
    serializer_class = CapabilitySerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("product"):
            require_finance_permission(self.request.user, "products", "view")
            return qs.filter(product_id=self.request.query_params["product"])
        return qs

    @action(detail=False, methods=["post"])
    def preview(self, request):
        require_finance_permission(request.user, "products", "view")
        require_finance_permission(request.user, "skus", "view")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rule = SupplierCapability(**serializer.validated_data)
        return Response([{"id": sku.pk, "sku": sku.sku, "name": sku.display_name_cn} for sku in rule.product.skus.filter(active=True) if matches(sku, rule)])


class SupplierCandidatesView(APIView):
    def get(self, request, pk):
        require_finance_permission(request.user, "skus", "view")
        sku = get_object_or_404(SKU, pk=pk)
        customer = None
        order_id = request.query_params.get("order")
        if order_id:
            require_finance_permission(request.user, "orders", "view")
            order = get_object_or_404(
                scope_customer_related_queryset(Order.objects.select_related("customer"), request.user),
                pk=order_id,
            )
            customer = order.customer
        from .services.supplier_candidates import candidate_payload
        payload = candidate_payload(sku, customer=customer)
        return Response({
            "candidates": scoped_supplier_candidates(payload["candidates"], request.user),
            "recommendation": {
                "supplier": payload["recommended_supplier"],
                "supplier_sku": payload["recommended_supplier_sku_id"],
                "source": payload["recommended_source"],
            },
            "recommendation_warning": payload["recommendation_warning"],
            "can_set_customer_preference": user_can(request.user, "suppliers", "update"),
            "overrides": list(sku.candidate_overrides.values("supplier", "is_allowed", "characteristics")),
        })

    @transaction.atomic
    def post(self, request, pk):
        require_finance_permission(request.user, "skus", "view")
        sku = get_object_or_404(SKU.objects.select_for_update(), pk=pk)
        supplier = get_object_or_404(Supplier, pk=request.data.get("supplier"))
        if not supplier.is_active:
            raise ValidationError("停用供应商不能加入新采购候选池，请先启用供应商。")
        allowed = request.data.get("is_allowed")
        if allowed is None:
            sku.candidate_overrides.filter(supplier=supplier).delete()
        else:
            if not isinstance(allowed, bool):
                raise ValidationError("请选择加入或排除。")
            traits = request.data.get("characteristics", {})
            if not isinstance(traits, dict) or any(not isinstance(v, str) for v in traits.values()):
                raise ValidationError("供货特点须为名称和文本值。")
            SupplierCandidateOverride.objects.update_or_create(sku=sku, supplier=supplier, defaults={"is_allowed": allowed, "characteristics": traits})
        record_operation(request=request, instance=sku, action="custom", action_label="调整候选供应商", metadata={"supplier_id": supplier.pk, "is_allowed": allowed})
        return self.get(request, pk)


class ProductSupplierCandidatePoolView(APIView):
    """Return the product-level candidate pool used by the product workspace."""

    @transaction.atomic
    def post(self, request, pk):
        from .services.supplier_candidates import eligible_suppliers
        class BindingInput(serializers.Serializer):
            sku_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), allow_empty=False, max_length=1000)
            suppliers = serializers.ListField(child=serializers.DictField(), allow_empty=False, max_length=100)
        class SupplierInput(serializers.Serializer):
            supplier = serializers.IntegerField(min_value=1)
            priority = serializers.ChoiceField(choices=["高", "中", "低"], default="中")
            quality = serializers.ChoiceField(choices=["A+", "A", "B", "C"], default="B")
            stability = serializers.ChoiceField(choices=["高", "中", "低"], default="中")
            delivery = serializers.ChoiceField(choices=["快", "标准", "慢"], default="标准")
            notes = serializers.CharField(allow_blank=True, max_length=2000, default="")
        require_finance_permission(request.user, "products", "view")
        require_finance_permission(request.user, "skus", "view")
        product = get_object_or_404(Product.objects.select_for_update(), pk=pk)
        payload = BindingInput(data=request.data)
        payload.is_valid(raise_exception=True)
        ids = set(payload.validated_data["sku_ids"])
        skus = list(product.skus.select_for_update().filter(pk__in=ids, active=True))
        if len(skus) != len(ids):
            raise ValidationError("包含其他产品或已停用的 SKU，请重新选择。")
        inputs = SupplierInput(data=payload.validated_data["suppliers"], many=True)
        inputs.is_valid(raise_exception=True)
        existing = set(Supplier.objects.filter(is_active=True).values_list("pk", flat=True))
        supplier_ids = [item["supplier"] for item in inputs.validated_data]
        if len(set(supplier_ids)) != len(supplier_ids) or not set(supplier_ids) <= existing:
            raise ValidationError("供应商重复或已不存在，请刷新后重新选择。")
        for item in inputs.validated_data:
            traits = {"推荐优先级": item["priority"], "质量等级": item["quality"], "供货稳定度": item["stability"], "交货期": item["delivery"], "其他备注": item["notes"]}
            for sku in skus:
                override, _ = SupplierCandidateOverride.objects.get_or_create(sku=sku, supplier_id=item["supplier"])
                override.is_allowed = True
                override.characteristics = {**override.characteristics, **traits}
                override.save()
        record_operation(request=request, instance=product, action="custom", action_label="批量绑定 SKU 候选供应商", metadata={"sku_ids": sorted(ids), "supplier_ids": supplier_ids})
        return Response({"sku_count": len(skus), "supplier_count": len(supplier_ids)})

    def get(self, request, pk):
        require_finance_permission(request.user, "products", "view")
        require_finance_permission(request.user, "skus", "view")
        product = get_object_or_404(Product, pk=pk)
        if request.query_params.get("eligible") == "1":
            from .services.supplier_candidates import eligible_suppliers
            from .serializers import SupplierSerializer
            matched = set(eligible_suppliers(product).values_list("pk", flat=True))
            queryset = Supplier.objects.filter(is_active=True) if request.query_params.get("all") == "1" else Supplier.objects.filter(pk__in=matched, is_active=True)
            data = SupplierSerializer(queryset.prefetch_related("supply_categories", "purchase_orders").order_by("name"), many=True, context={"request": request}).data
            for row in data:
                row["category_match"] = row["id"] in matched
            return Response(sorted(data, key=lambda row: not row["category_match"]))
        search = str(request.query_params.get("search", "")).strip().casefold()
        source_filter = str(request.query_params.get("source", "")).strip()
        supplier_filter = str(request.query_params.get("supplier", "")).strip()
        parameter_key = str(request.query_params.get("parameter_key", "")).strip()
        parameter_value_filter = str(request.query_params.get("parameter_value", "")).strip()
        rows = []
        for sku in product.skus.filter(active=True).select_related("product").order_by("sku"):
            values = sku.parameter_values or {}
            if parameter_key and str(values.get(parameter_key, "")) != parameter_value_filter:
                continue
            pool = scoped_supplier_candidates(candidates(sku), request.user)
            if supplier_filter:
                pool = [row for row in pool if str(row["supplier"]) == supplier_filter]
            if source_filter:
                pool = [row for row in pool if source_filter in row.get("source_types", [])]
            if search and search not in " ".join(str(value or "") for value in [sku.sku, sku.display_name_cn, sku.sales_model, sku.specification]).casefold():
                continue
            preferred = next((row for row in pool if any(source["is_preferred"] for source in row["supplier_skus"])), None)
            last_purchase = max((row["last_purchase"] for row in pool if row.get("last_purchase")), key=lambda row: str(row["date"]), default=None)
            source_types = []
            for row in pool:
                for source_type in row.get("source_types", []):
                    if source_type not in source_types:
                        source_types.append(source_type)
            rows.append({
                "sku_id": sku.pk,
                "sku_code": sku.sku,
                "sku_name": sku.display_name_cn or sku.product.name,
                "sales_model": sku.sales_model or "",
                "parameters": values,
                "candidate_supplier_count": len(pool),
                "preferred_supplier": {"id": preferred["supplier"], "name": preferred["supplier_name"]} if preferred else None,
                "candidate_source_types": source_types,
                "last_purchase": last_purchase,
                "status": "ready" if pool else "needs_source",
                "candidates": pool,
            })
        definitions = definitions_for(product)
        parameter_options = []
        for definition in definitions:
            category_id = definition.get("category_id", 0)
            definition_key = definition.get("key", "")
            key = f"{category_id}:{definition_key}"
            values = sorted({str(value) for sku in product.skus.filter(active=True) if (value := raw_parameter_value(sku.parameter_values, key, definition.get("name", ""))) not in ("", None)})
            if values:
                parameter_options.append({"key": key, "name": definition.get("name", "") or definition_key, "values": values})
        with_candidates = sum(1 for row in rows if row["candidate_supplier_count"])
        return Response({
            "product": product.pk,
            "sku_total": len(rows),
            "with_candidates": with_candidates,
            "coverage_rate": round(with_candidates / len(rows) * 100, 1) if rows else 0,
            "parameter_options": parameter_options,
            "rows": rows,
        })


class OrderItemSupplierAllocationView(APIView):
    """Read and update the supplier selected for one sales-order line."""

    def _item(self, request, order_id, item_id):
        require_finance_permission(request.user, "orders", "view")
        require_finance_permission(request.user, "suppliers", "view")
        require_finance_permission(request.user, "skus", "view")
        scoped_orders = scope_customer_related_queryset(Order.objects.all(), request.user)
        queryset = OrderItem.objects.select_related("order", "sku", "sku__product", "supplier_sku__supplier").filter(
            order__in=scoped_orders,
        )
        return get_object_or_404(queryset, pk=item_id, order_id=order_id)

    @staticmethod
    def _allocation_payload(item, user):
        from .services.supplier_allocation import supplier_allocation_payload
        payload = supplier_allocation_payload(item)
        if not user_can(user, "purchases", "view"):
            for field in ("purchase_price", "currency", "moq", "lead_time_days"):
                payload[field] = None
        return payload

    def get(self, request, order_id, item_id):
        item = self._item(request, order_id, item_id)
        from .services.supplier_allocation import supplier_option_payload
        option_payload = supplier_option_payload(item)

        return Response({
            "order": {"id": item.order_id, "order_no": item.order.order_no, "status": item.order.status},
            "order_item": {
                "id": item.pk,
                "sku": item.sku_id,
                "sku_code": item.sku_code_snapshot or item.sku.sku,
                "display_name": item.display_name_snapshot or item.sku.display_name_cn or item.sku.product.name,
                "description": item.description_snapshot,
                "quantity": item.quantity,
                "unit": item.unit_snapshot or item.sku.unit,
            },
            "allocation": self._allocation_payload(item, request.user),
            "candidates": scoped_supplier_candidates(option_payload["candidates"], request.user),
            "recommendation": {
                "supplier": option_payload["recommended_supplier"],
                "supplier_sku": option_payload["recommended_supplier_sku_id"],
                "source": option_payload["recommended_source"],
            },
            "recommendation_warning": option_payload["recommendation_warning"],
            "can_set_customer_preference": user_can(request.user, "suppliers", "update"),
        })

    @transaction.atomic
    def post(self, request, order_id, item_id):
        from .services.supplier_allocation import allocate_order_item_supplier, set_customer_supplier_preference

        item = self._item(request, order_id, item_id)
        requested_scope = request.data.get("scope", "order_only")
        if requested_scope in {"recommended", "customer_preferred"}:
            require_finance_permission(request.user, "suppliers", "update")
        supplier_sku_id = request.data.get("supplier_sku") or request.data.get("supplier_sku_id")
        if not supplier_sku_id:
            raise ValidationError({"supplier_sku": "请选择一个 Supplier SKU 作为本次采购来源。"})
        try:
            updated = allocate_order_item_supplier(
                item.pk,
                supplier_sku_id,
                scope=requested_scope,
                note=request.data.get("note", ""),
            )
        except DjangoValidationError as error:
            detail = getattr(error, "message_dict", None) or getattr(error, "messages", None) or [str(error)]
            raise ValidationError(detail)
        if updated.supplier_allocation_scope == "customer_preferred":
            source = SupplierSKU.objects.select_related("supplier", "sku").get(pk=updated.supplier_sku_id)
            existing_preference = CustomerSupplierPreference.objects.filter(
                customer=updated.order.customer,
                sku=updated.sku,
            ).first()
            before_preference = snapshot(existing_preference)
            preference = set_customer_supplier_preference(
                updated.order.customer,
                updated.sku,
                source,
                user=request.user,
            )
            record_operation(
                request=request,
                instance=preference,
                action="custom",
                action_label="设置客户 SKU 优先采购来源",
                before=before_preference,
                metadata={"sku_id": updated.sku_id, "supplier_sku_id": source.pk},
            )
        record_operation(
            request=request,
            instance=updated,
            action="custom",
            action_label="为销售订单行分配供应商",
            metadata={
                "order_id": updated.order_id,
                "order_item_id": updated.pk,
                "sku_id": updated.sku_id,
                "supplier_sku_id": updated.supplier_sku_id,
                "scope": updated.supplier_allocation_scope,
            },
        )
        return Response({"allocation": self._allocation_payload(updated, request.user)})


def plan_data(plan):
    return {"id": plan.pk, "version": plan.version, "status": plan.status, "definitions": plan.definitions, "assignments": plan.assignments, "updated_at": plan.updated_at.isoformat()}


class ProductSKUPlanView(APIView):
    def get(self, request, pk):
        require_finance_permission(request.user, "products", "view")
        product = get_object_or_404(Product, pk=pk)
        return Response({"definitions": definitions_for(product), "plans": [plan_data(p) for p in product.sku_parameter_plans.order_by("-version")],
                         "skus": list(product.skus.filter(active=True).values("id", "sku", "display_name_cn", "parameter_values")),
                         "relationships": list(product.skus.filter(successors__isnull=False).values("id", "sku", "successors__target_id", "successors__target__sku"))})

    def post(self, request, pk):
        require_finance_permission(request.user, "products", "view")
        return Response(plan_data(draft_plan(get_object_or_404(Product, pk=pk))))

    @transaction.atomic
    def patch(self, request, pk):
        require_finance_permission(request.user, "products", "view")
        Product.objects.select_for_update().get(pk=pk)
        plan = get_object_or_404(SKUParameterPlan.objects.select_for_update(), product_id=pk, status="draft")
        if request.data.get("updated_at") != plan.updated_at.isoformat():
            raise ValidationError("草稿已被其他操作修改，请重新加载。")
        plan.definitions = validate_definitions(request.data.get("definitions", plan.definitions))
        plan.assignments = request.data.get("assignments", plan.assignments)
        analyze(plan)
        plan.save()
        return Response(plan_data(plan))

    @transaction.atomic
    def delete(self, request, pk):
        require_finance_permission(request.user, "products", "view")
        Product.objects.select_for_update().get(pk=pk)
        SKUParameterPlan.objects.filter(product_id=pk, status="draft").delete()
        return Response(status=204)


class ProductSKUPlanActionView(APIView):
    @transaction.atomic
    def post(self, request, pk, operation):
        require_finance_permission(request.user, "products", "view")
        Product.objects.select_for_update().get(pk=pk)
        plan = get_object_or_404(SKUParameterPlan.objects.select_for_update(), product_id=pk, status="draft")
        if request.data.get("updated_at") != plan.updated_at.isoformat():
            raise ValidationError("草稿已改变，请重新分析。")
        if operation == "analyze":
            return Response(analyze(plan))
        if operation != "publish":
            raise ValidationError("未知操作。")
        result = publish(plan)
        record_operation(request=request, instance=plan.product, action="custom", action_label="发布 SKU 参数方案", metadata={"version": plan.version, "impact": result})
        return Response(result)


class ProductCombinationRulesView(APIView):
    def get(self, request, pk):
        require_finance_permission(request.user, "products", "view")
        return Response({"rules": get_object_or_404(Product, pk=pk).combination_rules})

    @transaction.atomic
    def post(self, request, pk):
        require_finance_permission(request.user, "products", "view")
        from .services.sku_combination_rules import validate_rules
        product = get_object_or_404(Product.objects.select_for_update(), pk=pk)
        if "rules" not in request.data:
            raise ValidationError({"rules": "请提交组合规则。"})
        rules = request.data["rules"]
        validate_rules(product, rules)
        if request.data.get("save") is True:
            product.combination_rules = rules
            product.save(update_fields=["combination_rules", "updated_at"])
            record_operation(request=request, instance=product, action="custom", action_label="保存 SKU 组合规则", metadata={"rules": rules})
        return Response({"rules": rules, "valid": True})
