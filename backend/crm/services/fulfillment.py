from crm.trade_units import normalize_trade, portion_trade, TRADE_FIELDS
from decimal import Decimal
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Case, DecimalField, F, Q, Sum, When
from django.db.models.functions import Coalesce

from crm.models import (
    GoodsReceipt,
    InventoryMovement,
    InventoryReservation,
    Order,
    OrderItem,
    PurchaseOrderItem,
    Shipment,
    ShipmentItem,
    SKU,
    Transaction,
)


QUANTITY_FIELD = DecimalField(max_digits=18, decimal_places=2)
OUTGOING_MOVEMENT_TYPES = [
    "sale_out",
    "adjust_out",
    "sample_out",
    "transfer_out",
    "production_out",
    "other_out",
]
ACTIVE_ORDER_STATUSES = ["confirmed", "production", "shipped"]
OPEN_PURCHASE_STATUSES = ["ordered", "partial"]


def signed_inventory_quantity(sku: SKU) -> Decimal:
    return sku.inventory_movements.aggregate(
        total=Coalesce(
            Sum(
                Case(
                    When(type__in=OUTGOING_MOVEMENT_TYPES, then=-F("quantity")),
                    default=F("quantity"),
                    output_field=QUANTITY_FIELD,
                )
            ),
            Decimal("0"),
            output_field=QUANTITY_FIELD,
        )
    )["total"]


def active_reservation_quantity(sku: SKU) -> Decimal:
    return InventoryReservation.objects.filter(
        sku=sku,
        order_item__order__status__in=ACTIVE_ORDER_STATUSES,
    ).aggregate(total=Coalesce(Sum("quantity"), Decimal("0"), output_field=QUANTITY_FIELD))["total"]


def received_quantity_for_sku(sku: SKU) -> Decimal:
    return PurchaseOrderItem.objects.filter(sku=sku).aggregate(
        total=Coalesce(Sum("receipts__quantity"), Decimal("0"), output_field=QUANTITY_FIELD)
    )["total"]


def open_purchase_quantity(sku: SKU) -> Decimal:
    return PurchaseOrderItem.objects.filter(
        sku=sku,
        purchase_order__status__in=OPEN_PURCHASE_STATUSES,
    ).aggregate(total=Coalesce(Sum("quantity"), Decimal("0"), output_field=QUANTITY_FIELD))["total"]


def sku_metrics(sku: SKU) -> dict[str, Decimal]:
    actual = signed_inventory_quantity(sku)
    reserved = active_reservation_quantity(sku)
    return {
        "actual_quantity": actual,
        "reserved_quantity": reserved,
        "available_quantity": actual - reserved,
        "in_transit_quantity": sum((max(Decimal("0"), item.quantity - item.received_quantity)
            for item in PurchaseOrderItem.objects.filter(sku=sku, purchase_order__status__in=OPEN_PURCHASE_STATUSES).prefetch_related("receipts")), Decimal("0")),
    }


@transaction.atomic
def allocate_order(order):
    order = Order.objects.select_for_update().get(pk=order.pk)
    list(SKU.objects.select_for_update().filter(pk__in=order.items.values("sku_id")).order_by("pk"))
    InventoryReservation.objects.filter(order_item__order=order).delete()
    if order.status not in ACTIVE_ORDER_STATUSES:
        return []
    created = []
    for item in order.items.select_related("sku").order_by("id"):
        available = sku_metrics(item.sku)["available_quantity"]
        quantity = min(max(Decimal("0"), item.quantity - _shipped_quantity(item)), max(Decimal("0"), available))
        if quantity > 0:
            created.append(InventoryReservation.objects.create(
                order_item=item,
                sku=item.sku,
                quantity=quantity,
            ))
    return created


def order_item_metrics(item: OrderItem) -> dict[str, Decimal]:
    allocated = item.reservations.aggregate(
        total=Coalesce(Sum("quantity"), Decimal("0"), output_field=QUANTITY_FIELD)
    )["total"]
    purchase_items = PurchaseOrderItem.objects.filter(
        Q(purchase_order__order=item.order, purchase_order__cost_allocation_version=0) | Q(cost_allocations__order=item.order),
        sku=item.sku,
        purchase_order__status__in=["ordered", "partial", "completed"],
    ).distinct().select_related("purchase_order").prefetch_related("receipts", "cost_allocations")
    purchased = received = in_transit = Decimal(0)
    for row in purchase_items:
        quantity = (sum((a.quantity for a in row.cost_allocations.all() if a.order_id == item.order_id), Decimal(0))
            if row.purchase_order.cost_allocation_version else row.quantity)
        # Receipts are recorded for the whole purchase line; attribute progress proportionally.
        arrived = min(row.received_quantity, row.quantity) * quantity / row.quantity
        purchased += quantity
        received += arrived
        if row.purchase_order.status in OPEN_PURCHASE_STATUSES:
            in_transit += max(Decimal(0), quantity - arrived)
    shipped = _shipped_quantity(item)
    # Distribute shared-SKU procurement across order lines exactly once.
    prior_demand = Decimal("0")
    for previous in item.order.items.filter(sku=item.sku, id__lt=item.id):
        reserved = previous.reservations.aggregate(total=Sum("quantity"))["total"] or Decimal("0")
        prior_demand += max(Decimal("0"), previous.quantity - _shipped_quantity(previous) - reserved)
    outstanding_purchase = max(Decimal("0"), in_transit - prior_demand)
    return {
        "allocated_quantity": allocated,
        "to_procure_quantity": max(Decimal("0"), item.quantity - shipped - allocated - outstanding_purchase),
        "purchased_quantity": purchased,
        "received_quantity": received,
        "in_transit_quantity": in_transit,
        "shipped_quantity": shipped,
        "unshipped_quantity": max(Decimal("0"), item.quantity - shipped),
    }


def _movement_no(prefix: str) -> str:
    return "{}-{}".format(prefix, uuid4().hex[:16].upper())


def _receipt_status(purchase_order):
    quantities = [(item.quantity, item.received_quantity) for item in purchase_order.items.all()]
    if quantities and all(received >= ordered for ordered, received in quantities):
        return "completed"
    if any(received > 0 for _, received in quantities):
        return "partial"
    return "ordered"


@transaction.atomic
def record_receipt(purchase_item: PurchaseOrderItem, payload: dict) -> GoodsReceipt:
    purchase_item = PurchaseOrderItem.objects.select_for_update().select_related(
        "purchase_order", "sku"
    ).get(pk=purchase_item.pk)
    if purchase_item.purchase_order.status not in {"ordered", "partial", "completed"}:
        raise ValidationError("只有已下单的采购单可以登记验货入库。")
    SKU.objects.select_for_update().get(pk=purchase_item.sku_id)
    if not payload.get('trade_unit') and 'quantity' not in payload:
        raise ValidationError('请填写基础数量，或选择交易规格并填写交易数量。')
    converted = normalize_trade(payload, purchase_item.sku, price_field="unit_cost", existing=purchase_item, supplier_id=purchase_item.purchase_order.supplier_id)
    payload = {**payload, **converted}
    quantity = payload["quantity"]
    remaining = purchase_item.remaining_quantity
    is_overage = bool(payload.get("is_overage", False))
    reason = payload.get("overage_reason", "")
    if quantity <= 0:
        raise ValidationError("到货数量必须大于零。")
    if quantity > remaining and not (is_overage and reason in {"overprocurement", "gift", "carton_variance"}):
        raise ValidationError("超到必须选择原因。")
    if quantity <= remaining:
        is_overage = False
        reason = ""
    movement = InventoryMovement.objects.create(
        **{k: converted[k] for k in TRADE_FIELDS if k in converted},
        movement_no=_movement_no("GR"),
        movement_date=payload["receipt_date"],
        type="purchase_in",
        sku=purchase_item.sku,
        supplier_sku=purchase_item.supplier_sku,
        order=purchase_item.purchase_order.order,
        quantity=quantity,
        warehouse="默认仓",
        unit_cost=payload.get("unit_cost", Decimal("0")),
        reference=purchase_item.purchase_order.purchase_no,
        source_type="receipt",
        source_no=purchase_item.purchase_order.purchase_no,
        is_automatic=True,
        is_overage=is_overage,
        overage_reason=reason,
        notes=payload.get("notes", ""),
    )
    receipt = GoodsReceipt.objects.create(
        **{k: converted[k] for k in TRADE_FIELDS if k in converted},
        purchase_item=purchase_item,
        receipt_date=payload["receipt_date"],
        quantity=quantity,
        unit_cost=payload.get("unit_cost", Decimal("0")),
        is_overage=is_overage,
        overage_reason=reason,
        notes=payload.get("notes", ""),
        inventory_movement=movement,
    )
    purchase_order = purchase_item.purchase_order
    purchase_order.status = _receipt_status(purchase_order)
    purchase_order.save(update_fields=["status", "updated_at"])
    if purchase_order.order_id:
        allocate_order(purchase_order.order)
    return receipt


def _shipped_quantity(order_item: OrderItem) -> Decimal:
    confirmed = order_item.shipment_items.filter(shipment__status="confirmed").aggregate(
        total=Coalesce(Sum("quantity"), Decimal("0"), output_field=QUANTITY_FIELD)
    )["total"]
    # Pre-shipment-module records have an order/SKU but no ShipmentItem.
    # Count them once, distributing across repeated SKU lines in their saved order.
    legacy = InventoryMovement.objects.filter(order=order_item.order, sku=order_item.sku,
        type="sale_out", shipment_item__isnull=True).aggregate(total=Sum("quantity"))["total"] or Decimal("0")
    prior_quantity = order_item.order.items.filter(sku=order_item.sku, pk__lt=order_item.pk).aggregate(total=Sum("quantity"))["total"] or Decimal("0")
    legacy_share = min(order_item.quantity, max(Decimal("0"), legacy - prior_quantity))
    return confirmed + legacy_share


@transaction.atomic
def complete_order(order: Order) -> Order:
    """Close an order only after fulfillment and receivable work is complete."""
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status != "shipped":
        raise ValidationError("只有全部发货后的订单才能完成。")
    if any(_shipped_quantity(item) < item.quantity for item in order.items.select_for_update()):
        raise ValidationError("订单仍有待发数量，不能完成。")
    plans = list(order.payment_plans.select_for_update().exclude(status="cancelled"))
    if order.total_amount > 0 and (not plans or any(plan.remaining_amount > 0 for plan in plans)):
        raise ValidationError("订单仍有待收款计划，全部结清后才能完成。")
    order.status = "completed"
    order.save(update_fields=["status", "updated_at"])
    allocate_order(order)
    return order


@transaction.atomic
def cancel_order(order: Order) -> Order:
    """Cancel an unexecuted order and release its inventory reservation."""
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status in {"cancelled", "completed"}:
        raise ValidationError("已取消或已完成订单不能再次取消。")
    history = order.shipments.exists() or order.purchase_orders.exclude(status="cancelled").exists()
    financial = order.transactions.exists() or order.payment_plans.filter(settled_amount__gt=0).exists() or order.payment_plans.filter(advance_allocations__isnull=False).exists()
    if history or financial:
        raise ValidationError("订单已有采购、发货或收付款记录，不能直接取消；请按实际业务办理退货或退款。")
    order.status = "cancelled"
    order.save(update_fields=["status", "updated_at"])
    order.payment_plans.filter(settled_amount=0).update(status="cancelled")
    allocate_order(order)
    return order


@transaction.atomic
def confirm_shipment(order: Order, payload: dict) -> Shipment:
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status not in ACTIVE_ORDER_STATUSES:
        raise ValidationError("只有已确认且未取消或完成的订单可以发货。")
    if not payload.get("items"):
        raise ValidationError("请至少选择一条发货明细。")
    ids = [line.get("order_item") for line in payload["items"]]
    if len(ids) != len(set(ids)) or order.items.filter(pk__in=ids).count() != len(ids):
        raise ValidationError("发货明细必须属于当前订单，且不能重复。")
    list(SKU.objects.select_for_update().filter(pk__in=order.items.values("sku_id")).order_by("pk"))
    shipment = Shipment.objects.create(
        shipment_no=payload.get("shipment_no") or _movement_no("SH"),
        order=order,
        shipment_date=payload["shipment_date"],
        logistics_provider=payload.get("logistics_provider", ""),
        waybill_no=payload.get("waybill_no", ""),
        status="confirmed",
        notes=payload.get("notes", ""),
    )
    for line in payload["items"]:
        item = OrderItem.objects.select_for_update().select_related("sku").get(
            pk=line["order_item"], order=order
        )
        if not line.get('trade_unit') and 'quantity' not in line:
            raise ValidationError('请填写基础数量，或选择交易规格并填写交易数量。')
        converted = normalize_trade(line, item.sku, price_field=None, existing=item)
        quantity = converted["quantity"]
        remaining = item.quantity - _shipped_quantity(item)
        reason = line.get("overage_reason", "")
        is_overage = quantity > remaining
        if quantity <= 0:
            raise ValidationError("发货数量必须大于零。")
        if is_overage and reason not in {"customer_addon", "gift_or_sample", "packing_variance"}:
            raise ValidationError("超发必须选择客户追加、赠品/样品或包装尾差原因。")
        if not is_overage:
            reason = ""
        own_reserved = InventoryReservation.objects.filter(sku=item.sku, order_item__order=order).aggregate(total=Sum("quantity"))["total"] or Decimal("0")
        if quantity > sku_metrics(item.sku)["available_quantity"] + own_reserved:
            raise ValidationError("库存不足，不能确认发货。")

        def create_line(order_item, line_quantity, overage=False, line_reason=""):
            movement = InventoryMovement.objects.create(
                **portion_trade(converted, line_quantity),
                movement_no=_movement_no("SH"),
                movement_date=payload["shipment_date"],
                type="sale_out",
                sku=order_item.sku,
                order=order,
                quantity=line_quantity,
                warehouse="默认仓",
                reference=shipment.shipment_no,
                source_type="shipment",
                source_no=shipment.shipment_no,
                is_automatic=True,
                is_overage=overage,
                overage_reason=line_reason,
            )
            ShipmentItem.objects.create(
                **portion_trade(converted, line_quantity),
                shipment=shipment,
                order_item=order_item,
                sku=order_item.sku,
                quantity=line_quantity,
                is_overage=overage,
                overage_reason=line_reason,
                creates_supplement=overage and line_reason == "customer_addon",
                inventory_movement=movement,
            )

        normal_quantity = min(quantity, max(Decimal("0"), remaining))
        if normal_quantity:
            create_line(item, normal_quantity)
        extra_quantity = quantity - normal_quantity
        if extra_quantity:
            supplement = OrderItem.objects.create(
                order=order,
                sku=item.sku,
                quantity=extra_quantity,
                unit_price=item.unit_price if reason == "customer_addon" else Decimal("0"),
                cost_price=item.cost_price,
                notes="超发登记：{}".format({
                    "customer_addon": "客户追加",
                    "gift_or_sample": "赠品或样品",
                    "packing_variance": "包装尾差",
                }[reason]),
            )
            create_line(supplement, extra_quantity, True, reason)
            if reason == "customer_addon":
                from crm.models import PaymentPlan
                if item.unit_price > 0:
                    PaymentPlan.objects.create(order=order, direction="receivable", currency=order.currency,
                        due_date=payload["shipment_date"], planned_amount=extra_quantity * item.unit_price,
                        notes=f"发货单 {shipment.shipment_no} 客户追加")
        # Consume this order's reservations as stock leaves, including other lines of the same SKU.
        to_release = quantity
        for reservation in InventoryReservation.objects.filter(sku=item.sku, order_item__order=order).order_by("pk"):
            used = min(to_release, reservation.quantity)
            reservation.quantity -= used
            to_release -= used
            if reservation.quantity:
                reservation.save(update_fields=["quantity"])
            else:
                reservation.delete()
    if all(_shipped_quantity(item) >= item.quantity for item in order.items.all()):
        order.status = "shipped"
        order.save(update_fields=["status", "updated_at"])
    allocate_order(order)
    return shipment


@transaction.atomic
def record_supplier_payment(purchase_order, payload: dict) -> Transaction:
    purchase_order = purchase_order.__class__.objects.select_for_update().get(pk=purchase_order.pk)
    amount = Decimal(payload["amount"])
    if amount <= 0:
        raise ValidationError("付款金额必须大于零。")
    if amount > purchase_order.unpaid_amount:
        raise ValidationError("付款金额不能超过采购单未付金额。")
    from .finance import record_contract_payment
    return record_contract_payment(purchase_order, {**payload, "category": "供应商付款"})
