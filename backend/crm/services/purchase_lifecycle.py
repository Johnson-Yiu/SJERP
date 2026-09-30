"""Explicit, atomic lifecycle transitions for purchase orders."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from crm.models import AdvanceAllocation, GoodsReceipt, PaymentPlan, PurchaseOrder
from crm.services.finance import ensure_default_payment_plans


def _validate_purchase_for_placement(purchase):
    if purchase.order_id and purchase.order.status not in {"confirmed", "production"}:
        raise ValidationError("关联销售订单当前状态不允许继续采购，请检查订单状态或改为独立采购。")
    items = list(purchase.items.select_related("sku", "supplier_sku", "trade_unit").order_by("id"))
    if not purchase.supplier_id:
        raise ValidationError("采购单必须选择供应商。")
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


@transaction.atomic
def place_purchase_order(purchase):
    purchase = PurchaseOrder.objects.select_for_update(of=("self",)).select_related("supplier", "order").get(pk=purchase.pk)
    if purchase.status != "draft":
        raise ValidationError("只有采购草稿可以确认下单。")
    _validate_purchase_for_placement(purchase)
    purchase.status = "ordered"
    purchase.save(update_fields=["status", "updated_at"])
    ensure_default_payment_plans(purchase)
    return PurchaseOrder.objects.get(pk=purchase.pk)


@transaction.atomic
def cancel_purchase_order(purchase, reason):
    reason = str(reason or "").strip()
    if not reason:
        raise ValidationError("取消原因不能为空。")
    purchase = PurchaseOrder.objects.select_for_update().get(pk=purchase.pk)
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
