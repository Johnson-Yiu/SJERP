"""Explicit, atomic lifecycle transitions for purchase orders."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from crm.models import AdvanceAllocation, GoodsReceipt, PaymentPlan, PurchaseMOQException, PurchaseOrder, Supplier
from crm.services.finance import ensure_default_payment_plans
from crm.services.historical import reject_historical


class PurchaseMOQExceptionRequired(ValidationError):
    """Raised once when a PO needs an operator's explicit MOQ exception reason."""

    code = "purchase_moq_exception_required"

    def __init__(self, exceptions):
        self.exceptions = exceptions
        super().__init__("本采购单存在低于供应商 MOQ 的明细，请填写例外原因后继续下单。", code=self.code)


def _validate_purchase_for_placement(purchase, items=None):
    if purchase.order_id and purchase.order.status not in {"confirmed", "production"}:
        raise ValidationError("关联销售订单当前状态不允许继续采购，请检查订单状态或改为独立采购。")
    items = list(items if items is not None else purchase.items.select_related("sku", "supplier_sku", "trade_unit").order_by("id"))
    if not purchase.supplier_id:
        raise ValidationError("采购单必须选择供应商。")
    if not purchase.supplier.is_active:
        raise ValidationError("停用供应商不能确认新采购，请先启用供应商或更换供应商。")
    if not items:
        raise ValidationError("采购单至少需要一条商品明细。")
    if purchase.exchange_rate <= 0:
        raise ValidationError("汇率必须大于零。")
    for item in items:
        if not item.sku.active:
            raise ValidationError(f"SKU {item.sku.sku} 已停用，不能确认下单。")
        if item.quantity <= 0 or item.unit_price < 0:
            raise ValidationError("采购数量必须大于零，单价不能为负。")
        source = item.supplier_sku
        # A manual purchase may intentionally have no maintained SupplierSKU.
        # When a source is present it remains a strict purchasing identity.
        if source and (source.supplier_id != purchase.supplier_id or source.sku_id != item.sku_id):
            raise ValidationError("采购明细的供应商来源必须匹配当前供应商和 SKU。")
        if source and not source.is_active:
            raise ValidationError("采购明细不能使用已停用的供应商来源。")
        if item.trade_unit_id and item.trade_unit.supplier_id and item.trade_unit.supplier_id != purchase.supplier_id:
            raise ValidationError("包装规格的供应商必须与采购单供应商一致。")


def _purchase_moq_exceptions(items):
    """Aggregate one PO by the maintained supplier SKU in base units.

    SupplierSKU.moq=0 is the existing sentinel for an unmaintained MOQ, so it
    must never become an invented threshold. PurchaseOrderItem.quantity is the
    trusted base-unit value produced by the existing trade-unit normalizer.
    """
    grouped = {}
    for item in items:
        source = item.supplier_sku
        if source is None or source.moq is None or source.moq <= 0:
            continue
        key = source.pk
        detail = grouped.setdefault(key, {
            "purchase_item_ids": [],
            "sku_code": item.sku_code_snapshot or item.sku.sku,
            "display_name": item.display_name_snapshot or item.sku.display_name_cn or item.sku.product.name,
            "supplier_sku_code": item.supplier_sku_code_snapshot or source.supplier_sku_code,
            "actual_quantity": Decimal("0"),
            "moq": source.moq,
            "base_unit": (item.trade_snapshot or {}).get("base_unit") or item.sku.unit,
        })
        detail["purchase_item_ids"].append(item.pk)
        detail["actual_quantity"] += item.quantity

    exceptions = []
    for detail in grouped.values():
        if detail["actual_quantity"] >= detail["moq"]:
            continue
        actual = detail["actual_quantity"]
        moq = detail["moq"]
        exceptions.append({
            **detail,
            "actual_quantity": str(actual),
            "moq": str(moq),
            "shortage": str(moq - actual),
        })
    return exceptions


@transaction.atomic
def place_purchase_order(purchase, *, moq_exception_reason="", operator=None):
    purchase = PurchaseOrder.objects.select_for_update(of=("self",)).select_related("supplier", "order").get(pk=purchase.pk)
    reject_historical(purchase, "确认下单或生成应付计划")
    if purchase.status != "draft":
        raise ValidationError("只有采购草稿可以确认下单。")
    items = list(purchase.items.select_related("sku", "supplier_sku", "trade_unit").order_by("id"))
    _validate_purchase_for_placement(purchase, items)
    moq_exceptions = _purchase_moq_exceptions(items)
    reason = str(moq_exception_reason or "").strip()
    if len(reason) > 500:
        raise ValidationError("MOQ 例外原因不能超过500字。")
    if moq_exceptions and not reason:
        raise PurchaseMOQExceptionRequired(moq_exceptions)
    supplier = Supplier.objects.select_for_update().get(pk=purchase.supplier_id)
    purchase.supplier_name_snapshot = supplier.name
    purchase.supplier_address_snapshot = supplier.address or ""
    purchase.supplier_contact_name_snapshot = supplier.contact_name or ""
    purchase.supplier_phone_snapshot = supplier.phone or ""
    purchase.supplier_email_snapshot = supplier.email or ""
    purchase.status = "ordered"
    purchase.save(update_fields=[
        "status",
        "supplier_name_snapshot",
        "supplier_address_snapshot",
        "supplier_contact_name_snapshot",
        "supplier_phone_snapshot",
        "supplier_email_snapshot",
        "updated_at",
    ])
    if moq_exceptions:
        PurchaseMOQException.objects.create(
            purchase_order=purchase,
            reason=reason,
            details=moq_exceptions,
            operator=operator if getattr(operator, "is_authenticated", False) else None,
        )
    ensure_default_payment_plans(purchase)
    return PurchaseOrder.objects.get(pk=purchase.pk)


@transaction.atomic
def cancel_purchase_order(purchase, reason):
    reason = str(reason or "").strip()
    if not reason:
        raise ValidationError("取消原因不能为空。")
    purchase = PurchaseOrder.objects.select_for_update().get(pk=purchase.pk)
    reject_historical(purchase, "取消正式采购")
    if purchase.status not in {"draft", "ordered"}:
        raise ValidationError("当前采购单状态不能取消。")
    if GoodsReceipt.objects.filter(purchase_item__purchase_order=purchase, reversal_inventory_movement__isnull=True).exists():
        raise ValidationError("采购单已有有效到货记录，不能直接取消。")
    if purchase.transactions.filter(status="confirmed").exists():
        raise ValidationError("采购单已有正式付款记录，不能直接取消。")
    if AdvanceAllocation.objects.filter(plan__purchase_order=purchase, is_active=True).exists():
        raise ValidationError("采购单已有有效预付款核销，不能直接取消。")
    if purchase.payment_plans.filter(settled_amount__gt=Decimal("0")).exists():
        raise ValidationError("采购单已有已结算付款计划，不能直接取消。")
    purchase.status = "cancelled"
    purchase.cancelled_at = timezone.now()
    purchase.cancellation_reason = reason
    purchase.save(update_fields=["status", "cancelled_at", "cancellation_reason", "updated_at"])
    PaymentPlan.objects.filter(purchase_order=purchase, status="open", settled_amount=0).update(status="cancelled")
    return purchase
