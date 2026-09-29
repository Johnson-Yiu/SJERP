from crm.trade_units import normalize_trade, portion_trade, TRADE_FIELDS
from decimal import Decimal
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Case, DecimalField, F, Q, Sum, When
from django.db.models.functions import Coalesce
from django.utils import timezone

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
    SupplierSKU,
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
        total=Coalesce(Sum("receipts__quantity", filter=Q(receipts__reversal_inventory_movement__isnull=True)), Decimal("0"), output_field=QUANTITY_FIELD)
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
    """Retain the order-facing entry point while using the SKU-wide allocator."""
    order = Order.objects.select_for_update().get(pk=order.pk)
    created = []
    for sku in SKU.objects.filter(pk__in=order.items.values("sku_id")).order_by("pk"):
        created.extend(rebalance_sku_reservations(sku))
    return [row for row in created if row.order_item.order_id == order.pk]


def order_item_metrics(item: OrderItem) -> dict[str, Decimal]:
    allocated = item.reservations.aggregate(
        total=Coalesce(Sum("quantity"), Decimal("0"), output_field=QUANTITY_FIELD)
    )["total"]
    purchase_items = PurchaseOrderItem.objects.filter(
        cost_allocations__target_type="order", cost_allocations__order=item.order,
        sku=item.sku,
        purchase_order__status__in=["ordered", "partial", "completed"],
    ).distinct().select_related("purchase_order").prefetch_related("receipts", "cost_allocations")
    purchased = received = in_transit = Decimal(0)
    for row in purchase_items:
        quantity = sum((a.quantity for a in row.cost_allocations.all() if a.target_type == "order" and a.order_id == item.order_id), Decimal(0))
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
    purchase_item = PurchaseOrderItem.objects.select_for_update(of=("self",)).select_related(
        "purchase_order", "sku"
    ).get(pk=purchase_item.pk)
    if purchase_item.purchase_order.status not in {"ordered", "partial", "completed"}:
        raise ValidationError("只有已下单的采购单可以登记验货入库。")
    related_order_ids = list(
        purchase_item.cost_allocations.filter(target_type="order", order__isnull=False)
        .order_by("order_id").values_list("order_id", flat=True).distinct()
    )
    # Keep the shared sales-order -> SKU locking order used by shipment confirmation.
    # This prevents receipt's related-order write from waiting on a shipment that is
    # itself waiting for the same SKU lock.
    if related_order_ids:
        list(Order.objects.select_for_update().filter(pk__in=related_order_ids).order_by("pk"))
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
        order=None,
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
    if related_order_ids:
        movement.related_orders.set(related_order_ids)
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
    rebalance_sku_reservations(purchase_item.sku)
    return receipt


@transaction.atomic
def rebalance_sku_reservations(sku: SKU):
    """Rebuild one SKU's reservations from stock and received purchase allocations."""
    sku = SKU.objects.select_for_update().get(pk=sku.pk)
    InventoryReservation.objects.filter(sku_id=sku.pk).delete()
    available = max(Decimal("0"), signed_inventory_quantity(sku))
    items = list(OrderItem.objects.filter(
        sku_id=sku.pk,
        order__status__in=ACTIVE_ORDER_STATUSES,
    ).select_related("order").order_by("order__order_date", "order_id", "pk"))

    received_by_order = {}
    purchase_items = PurchaseOrderItem.objects.filter(
        sku_id=sku.pk,
        purchase_order__status__in=["ordered", "partial", "completed"],
    ).prefetch_related("receipts", "cost_allocations")
    for purchase_item in purchase_items:
        received = min(purchase_item.received_quantity, purchase_item.quantity)
        if received <= 0 or purchase_item.quantity <= 0:
            continue
        for allocation in purchase_item.cost_allocations.all():
            if allocation.target_type != "order" or not allocation.order_id:
                continue
            received_by_order[allocation.order_id] = received_by_order.get(allocation.order_id, Decimal("0")) + (
                received * allocation.quantity / purchase_item.quantity
            )

    shipped_by_item = {item.pk: _shipped_quantity(item) for item in items}
    shipped_by_order = {}
    for item in items:
        shipped_by_order[item.order_id] = shipped_by_order.get(item.order_id, Decimal("0")) + shipped_by_item[item.pk]
    priority_by_order = {
        order_id: max(Decimal("0"), quantity - shipped_by_order.get(order_id, Decimal("0")))
        for order_id, quantity in received_by_order.items()
    }

    created = []
    reserved_by_item = {}

    def reserve(item, limit):
        nonlocal available
        remaining_need = max(
            Decimal("0"), item.quantity - shipped_by_item[item.pk] - reserved_by_item.get(item.pk, Decimal("0"))
        )
        quantity = min(remaining_need, max(Decimal("0"), limit), available)
        if quantity > 0:
            created.append(InventoryReservation.objects.create(order_item=item, sku=sku, quantity=quantity))
            available -= quantity
            reserved_by_item[item.pk] = reserved_by_item.get(item.pk, Decimal("0")) + quantity
        return quantity

    # Received quantities explicitly assigned to an order take precedence.
    for item in items:
        priority = priority_by_order.get(item.order_id, Decimal("0"))
        if priority > 0:
            used = reserve(item, priority)
            priority_by_order[item.order_id] -= used
    # All remaining stock follows the stable general order.
    for item in items:
        reserve(item, available)
        if available <= 0:
            break
    return created


@transaction.atomic
def reverse_receipt(receipt: GoodsReceipt, reason: str) -> GoodsReceipt:
    reason = str(reason or "").strip()
    if not reason:
        raise ValidationError("冲销原因不能为空。")
    receipt = GoodsReceipt.objects.select_for_update().get(pk=receipt.pk)
    if receipt.reversal_inventory_movement_id:
        raise ValidationError("该入库记录已经冲销，不能重复操作。")
    purchase_item = PurchaseOrderItem.objects.select_for_update().select_related("purchase_order", "sku").get(pk=receipt.purchase_item_id)
    sku = SKU.objects.select_for_update().get(pk=purchase_item.sku_id)
    supplier_sku = SupplierSKU.objects.get(pk=purchase_item.supplier_sku_id) if purchase_item.supplier_sku_id else None
    original_movement = (
        InventoryMovement.objects.select_for_update().get(pk=receipt.inventory_movement_id)
        if receipt.inventory_movement_id else None
    )
    actual_quantity = signed_inventory_quantity(sku)
    if actual_quantity < receipt.quantity:
        raise ValidationError("当前 SKU 实际库存不足以冲销，请先处理后续出库。")
    movement = InventoryMovement.objects.create(
        **{k: getattr(receipt, k) for k in TRADE_FIELDS},
        movement_no=_movement_no("REV"),
        movement_date=timezone.localdate(),
        type="adjust_out",
        sku=sku,
        supplier_sku=supplier_sku,
        order=None,
        quantity=receipt.quantity,
        warehouse=original_movement.warehouse if original_movement else "默认仓",
        unit_cost=receipt.unit_cost,
        reference=original_movement.movement_no if original_movement else "",
        source_type="reversal",
        source_no=purchase_item.purchase_order.purchase_no,
        is_automatic=True,
        notes=f"冲销采购入库 #{receipt.pk}：{reason}",
    )
    if original_movement:
        movement.related_orders.set(original_movement.related_orders.order_by("pk"))
    receipt.reversal_inventory_movement = movement
    receipt.reversed_at = timezone.now()
    receipt.reversal_reason = reason
    receipt.save(update_fields=["reversal_inventory_movement", "reversed_at", "reversal_reason", "updated_at"])
    purchase_order = purchase_item.purchase_order
    purchase_order.status = _receipt_status(purchase_order)
    purchase_order.save(update_fields=["status", "updated_at"])
    rebalance_sku_reservations(sku)
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
        order_status_before_confirm=order.status,
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

        def create_line(order_item, line_quantity, overage=False, line_reason="", source_order_item=None):
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
            return ShipmentItem.objects.create(
                **portion_trade(converted, line_quantity),
                shipment=shipment,
                order_item=order_item,
                sku=order_item.sku,
                quantity=line_quantity,
                is_overage=overage,
                overage_reason=line_reason,
                creates_supplement=overage,
                source_order_item=source_order_item,
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
            shipment_item = create_line(supplement, extra_quantity, True, reason, source_order_item=item)
            if reason == "customer_addon":
                from crm.models import PaymentPlan
                if item.unit_price > 0:
                    plan = PaymentPlan.objects.create(order=order, direction="receivable", currency=order.currency,
                        due_date=payload["shipment_date"], planned_amount=extra_quantity * item.unit_price,
                        notes=f"发货单 {shipment.shipment_no} 客户追加")
                    shipment_item.generated_payment_plan = plan
                    shipment_item.save(update_fields=["generated_payment_plan"])
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
def reverse_shipment(shipment: Shipment, reason: str) -> Shipment:
    reason = str(reason or "").strip()
    if not reason:
        raise ValidationError("冲销原因不能为空。")

    shipment = Shipment.objects.select_for_update().get(pk=shipment.pk)
    if shipment.status != "confirmed":
        if shipment.status == "cancelled" or shipment.reversed_at:
            raise ValidationError("该发货单已经冲销，不能重复操作。")
        raise ValidationError("只有已确认的发货单可以冲销。")

    order = Order.objects.select_for_update().get(pk=shipment.order_id)
    if order.status in {"completed", "cancelled"}:
        raise ValidationError("已完成或已取消的订单不能冲销发货。")

    items = list(ShipmentItem.objects.select_for_update().filter(shipment=shipment).order_by("pk"))
    overage_items = [item for item in items if item.is_overage]
    supplements = []
    addon_plans = []
    for item in overage_items:
        source = item.source_order_item
        supplement = item.order_item
        if not source or source.order_id != order.pk or source.sku_id != item.sku_id:
            raise ValidationError("该历史超发记录缺少原订单明细关联，需要人工核对后才能冲销。")
        if supplement.order_id != order.pk or supplement.sku_id != item.sku_id or not item.creates_supplement:
            raise ValidationError("超发增补订单明细异常，无法安全冲销。")
        if ShipmentItem.objects.filter(order_item=supplement, shipment__status="confirmed").exclude(pk=item.pk).exists():
            raise ValidationError("增补订单明细已被其他有效发货引用，无法安全冲销。")
        supplements.append(supplement)
        if item.overage_reason == "customer_addon":
            if not item.generated_payment_plan_id:
                raise ValidationError("该历史客户追加记录缺少应收计划关联，需要人工核对后才能冲销。")
            plan = item.generated_payment_plan
            if plan.settled_amount > 0 or plan.transactions.filter(status="confirmed").exists() or plan.advance_allocations.filter(is_active=True).exists():
                raise ValidationError("该客户追加已经发生收款或预收款核销，请先处理相关财务流水后再冲销发货。")
            addon_plans.append(plan)
    future_total = order.total_amount - sum((item.amount for item in supplements), Decimal("0"))
    if overage_items and order.paid_amount > future_total:
        raise ValidationError("冲销后订单已收金额将超过订单金额，请先处理相关收款或退款。")

    movement_ids = [item.inventory_movement_id for item in items if item.inventory_movement_id]
    locked_movements = {
        movement.pk: movement
        for movement in InventoryMovement.objects.select_for_update().filter(pk__in=movement_ids).order_by("pk")
    }
    original_movements = {}
    for item in items:
        original_movement = locked_movements.get(item.inventory_movement_id)
        if (
            original_movement is None
            or original_movement.type != "sale_out"
            or original_movement.source_type != "shipment"
            or original_movement.sku_id != item.sku_id
            or original_movement.order_id != shipment.order_id
            or original_movement.quantity != item.quantity
        ):
            raise ValidationError("原销售出库流水缺失或异常，无法安全冲销，请先检查库存流水。")
        if item.reversal_inventory_movement_id:
            raise ValidationError("该发货明细已经冲销，不能重复操作。")
        original_movements[item.pk] = original_movement

    sku_ids = sorted({item.sku_id for item in items})
    locked_skus = {
        sku.pk: sku
        for sku in SKU.objects.select_for_update().filter(pk__in=sku_ids).order_by("pk")
    }
    now = timezone.now()
    for item in items:
        original_movement = original_movements[item.pk]
        movement = InventoryMovement.objects.create(
            **{k: getattr(item, k) for k in TRADE_FIELDS},
            movement_no=_movement_no("REV"),
            movement_date=timezone.localdate(),
            type="adjust_in",
            sku=locked_skus[item.sku_id],
            supplier_sku=original_movement.supplier_sku,
            order=order,
            quantity=item.quantity,
            warehouse=original_movement.warehouse,
            unit_cost=original_movement.unit_cost,
            reference=original_movement.movement_no,
            source_type="reversal",
            source_no=shipment.shipment_no,
            is_automatic=True,
            notes=f"冲销销售发货 {shipment.shipment_no}：{reason}",
        )
        item.reversal_inventory_movement = movement
        item.save(update_fields=["reversal_inventory_movement"])

    for item in overage_items:
        item.order_item = item.source_order_item
        item.save(update_fields=["order_item"])
    for plan in addon_plans:
        plan.status = "cancelled"
        plan.save(update_fields=["status", "updated_at"])
    for supplement in {item.pk: item for item in supplements}.values():
        supplement.delete()

    shipment.status = "cancelled"
    shipment.reversed_at = now
    shipment.reversal_reason = reason
    shipment.save(update_fields=["status", "reversed_at", "reversal_reason", "updated_at"])

    order_items = list(order.items.all())
    if order_items and all(_shipped_quantity(item) >= item.quantity for item in order_items):
        order.status = "shipped"
    else:
        order.status = shipment.order_status_before_confirm if shipment.order_status_before_confirm in {"confirmed", "production"} else "confirmed"
    order.save(update_fields=["status", "updated_at"])

    for sku in locked_skus.values():
        rebalance_sku_reservations(sku)
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
