"""Explicit, atomic lifecycle transitions for sales orders."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from crm.models import AdvanceAllocation, Customer, InventoryReservation, Order, PaymentPlan, PurchaseOrder, Quote, Shipment
from crm.services.finance import ensure_default_payment_plans
from crm.services.fulfillment import allocate_order, order_item_metrics
from crm.trade_units import trade_values


def _validate_order_for_confirmation(order):
    items = list(order.items.select_related("sku", "trade_unit").order_by("id"))
    if not items:
        raise ValidationError("订单至少需要一条商品明细。")
    if order.exchange_rate <= 0:
        raise ValidationError("汇率必须大于零。")
    if order.quote_id and order.quote.customer_id != order.customer_id:
        raise ValidationError("来源报价必须属于当前客户。")
    for item in items:
        if not item.sku.active:
            raise ValidationError(f"SKU {item.sku.sku} 已停用，不能确认订单。")
        if item.quantity <= 0 or item.unit_price < 0:
            raise ValidationError("订单数量必须大于零，单价不能为负。")
    return items


def _order_item_payload(items):
    return [
        {
            "sku": item.sku,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "notes": item.notes,
            **trade_values(item),
        }
        for item in items
    ]


def _capture_order_party_snapshot(order, quote=None):
    """Freeze the party data used by this order at formal confirmation.

    A quote is the authoritative source for buyer/contact fields when one is
    attached to the order.  Empty legacy quote fields stay empty rather than
    being silently replaced with the current customer master.  Country is not
    part of the existing quote snapshot schema, so it is captured from the
    customer selected on this order at confirmation time.
    """
    customer = Customer.objects.select_for_update().get(pk=order.customer_id)
    if quote is not None:
        values = {
            "customer_name_snapshot": quote.buyer_company_name,
            "customer_country_snapshot": customer.country,
            "customer_address_snapshot": quote.buyer_address,
            "customer_contact_name_snapshot": quote.recipient_name,
            "customer_phone_snapshot": quote.buyer_phone,
            "customer_email_snapshot": quote.buyer_email,
        }
    else:
        contact = customer.contacts.order_by("-is_primary", "name", "id").first()
        values = {
            "customer_name_snapshot": customer.name,
            "customer_country_snapshot": customer.country,
            "customer_address_snapshot": customer.address,
            "customer_contact_name_snapshot": contact.name if contact else "",
            "customer_phone_snapshot": contact.phone if contact else "",
            "customer_email_snapshot": contact.email if contact else "",
        }
    for field, value in values.items():
        setattr(order, field, value or "")
    return values


@transaction.atomic
def confirm_order(order):
    """Confirm one draft, creating all formal side effects together."""
    # Lock only the Order row first.  ``quote`` is nullable, so joining it here
    # would create a nullable outer join that PostgreSQL cannot lock.
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status != "draft":
        raise ValidationError("只有草稿订单可以确认。")

    items = _validate_order_for_confirmation(order)
    final_quote = None
    if order.quote_id:
        # The revision allocator and copied quote rows are deliberately invoked only
        # here: editing a draft must not create a legal/commercial quote revision.
        source_quote = Quote.objects.select_for_update().get(pk=order.quote_id)
        if source_quote.status in {"rejected", "expired"}:
            raise ValidationError("来源报价已拒绝或过期，请先基于新的报价修订版更新订单来源。")
        from crm.serializers import OrderSerializer

        final_quote = OrderSerializer()._create_quote_revision_if_needed(
            source_quote,
            {
                "currency": order.currency,
                "exchange_rate": order.exchange_rate,
                "shipping_fee": order.shipping_fee,
                "discount": order.discount,
                "notes": order.notes,
            },
            _order_item_payload(items),
        )

    _capture_order_party_snapshot(order, final_quote)
    order.quote = final_quote
    order.status = "confirmed"
    order.save(update_fields=[
        "quote",
        "status",
        "customer_name_snapshot",
        "customer_country_snapshot",
        "customer_address_snapshot",
        "customer_contact_name_snapshot",
        "customer_phone_snapshot",
        "customer_email_snapshot",
        "updated_at",
    ])
    allocate_order(order)
    ensure_default_payment_plans(order)
    if final_quote:
        Quote.objects.filter(pk=final_quote.pk).update(status="accepted")
    return Order.objects.get(pk=order.pk)


@transaction.atomic
def start_order_production(order):
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status != "confirmed":
        raise ValidationError("只有已确认订单可以开始生产。")
    order.status = "production"
    order.save(update_fields=["status", "updated_at"])
    return order


@transaction.atomic
def complete_order(order):
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status != "shipped":
        raise ValidationError("只有已发货订单可以完成。")
    items = list(order.items.all())
    if not items or any(order_item_metrics(item)["shipped_quantity"] < item.quantity for item in items):
        raise ValidationError("订单尚未全部发货，不能标记为已完成。")
    order.status = "completed"
    order.save(update_fields=["status", "updated_at"])
    return order


@transaction.atomic
def cancel_order(order, reason):
    reason = str(reason or "").strip()
    if not reason:
        raise ValidationError("取消原因不能为空。")
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status not in {"draft", "confirmed", "production"}:
        raise ValidationError("当前订单状态不能取消。")
    if Shipment.objects.filter(order=order, status="confirmed").exists():
        raise ValidationError("订单已有有效发货记录，不能直接取消。")
    formal_purchase_statuses = ["ordered", "partial", "completed"]
    if PurchaseOrder.objects.filter(
        items__cost_allocations__target_type="order",
        items__cost_allocations__order=order,
        status__in=formal_purchase_statuses,
    ).exists():
        raise ValidationError("订单已有正式采购记录，不能直接取消。")
    if order.transactions.filter(status="confirmed").exists():
        raise ValidationError("订单已有正式收付款记录，不能直接取消。")
    if AdvanceAllocation.objects.filter(plan__order=order, is_active=True).exists():
        raise ValidationError("订单已有有效预收款核销，不能直接取消。")
    if order.payment_plans.filter(settled_amount__gt=Decimal("0")).exists():
        raise ValidationError("订单已有已结算收款计划，不能直接取消。")

    order.status = "cancelled"
    order.cancelled_at = timezone.now()
    order.cancellation_reason = reason
    order.save(update_fields=["status", "cancelled_at", "cancellation_reason", "updated_at"])
    InventoryReservation.objects.filter(order_item__order=order).delete()
    PaymentPlan.objects.filter(order=order, status="open", settled_amount=0).update(status="cancelled")
    return order
