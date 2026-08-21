from decimal import Decimal
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Case, DecimalField, F, Sum, When
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
OUTGOING_MOVEMENT_TYPES = ["sale_out", "adjust_out", "sample_out"]
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
        "in_transit_quantity": open_purchase_quantity(sku) - received_quantity_for_sku(sku),
    }


@transaction.atomic
def allocate_order(order):
    InventoryReservation.objects.filter(order_item__order=order).delete()
    created = []
    for item in order.items.select_related("sku").order_by("id"):
        available = sku_metrics(item.sku)["available_quantity"]
        quantity = min(item.quantity, max(Decimal("0"), available))
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
    purchased = PurchaseOrderItem.objects.filter(
        purchase_order__order=item.order,
        sku=item.sku,
        purchase_order__status__in=OPEN_PURCHASE_STATUSES,
    ).aggregate(total=Coalesce(Sum("quantity"), Decimal("0"), output_field=QUANTITY_FIELD))["total"]
    return {
        "allocated_quantity": allocated,
        "to_procure_quantity": max(Decimal("0"), item.quantity - allocated - purchased),
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
    quantity = Decimal(payload["quantity"])
    remaining = purchase_item.remaining_quantity
    is_overage = bool(payload.get("is_overage", False))
    reason = payload.get("overage_reason", "")
    if quantity <= 0:
        raise ValidationError("到货数量必须大于零。")
    if quantity > remaining and not (is_overage and reason):
        raise ValidationError("超到必须选择原因。")
    if quantity <= remaining:
        is_overage = False
        reason = ""
    movement = InventoryMovement.objects.create(
        movement_no=_movement_no("GR"),
        movement_date=payload["receipt_date"],
        type="purchase_in",
        sku=purchase_item.sku,
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
    return receipt


def _shipped_quantity(order_item: OrderItem) -> Decimal:
    return order_item.shipment_items.filter(shipment__status="confirmed").aggregate(
        total=Coalesce(Sum("quantity"), Decimal("0"), output_field=QUANTITY_FIELD)
    )["total"]


@transaction.atomic
def confirm_shipment(order: Order, payload: dict) -> Shipment:
    order = Order.objects.select_for_update().get(pk=order.pk)
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
        quantity = Decimal(line["quantity"])
        remaining = item.quantity - _shipped_quantity(item)
        reason = line.get("overage_reason", "")
        is_overage = quantity > remaining
        if quantity <= 0:
            raise ValidationError("发货数量必须大于零。")
        if is_overage and not reason:
            raise ValidationError("超发必须选择原因。")
        if quantity > sku_metrics(item.sku)["actual_quantity"]:
            raise ValidationError("库存不足，不能确认发货。")
        movement = InventoryMovement.objects.create(
            movement_no=_movement_no("SH"),
            movement_date=payload["shipment_date"],
            type="sale_out",
            sku=item.sku,
            order=order,
            quantity=quantity,
            warehouse="默认仓",
            reference=shipment.shipment_no,
            source_type="shipment",
            source_no=shipment.shipment_no,
            is_automatic=True,
            is_overage=is_overage,
            overage_reason=reason if is_overage else "",
        )
        ShipmentItem.objects.create(
            shipment=shipment,
            order_item=item,
            sku=item.sku,
            quantity=quantity,
            is_overage=is_overage,
            overage_reason=reason if is_overage else "",
            creates_supplement=reason == "customer_addon",
            inventory_movement=movement,
        )
    return shipment


@transaction.atomic
def record_supplier_payment(purchase_order, payload: dict) -> Transaction:
    purchase_order = purchase_order.__class__.objects.select_for_update().get(pk=purchase_order.pk)
    amount = Decimal(payload["amount"])
    if amount <= 0:
        raise ValidationError("付款金额必须大于零。")
    if amount > purchase_order.unpaid_amount:
        raise ValidationError("付款金额不能超过采购单未付金额。")
    return Transaction.objects.create(
        transaction_no=_movement_no("PAY"),
        transaction_date=payload["transaction_date"],
        direction="expense",
        category="供应商付款",
        amount=amount,
        currency=payload.get("currency", purchase_order.currency),
        exchange_rate=payload.get("exchange_rate", purchase_order.exchange_rate),
        purchase_order=purchase_order,
        status="confirmed",
        payment_method=payload.get("payment_method", ""),
        reference=payload.get("reference", purchase_order.purchase_no),
        notes=payload.get("notes", ""),
    )
