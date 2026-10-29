"""Isolated audit probe for receipt/shipment replay and reversal idempotency.

Run only against a disposable SQLite database after migrations.  This script
does not modify product code or any shared/business database.
"""

import json
import os
from datetime import date
from decimal import Decimal

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from crm.models import Customer, GoodsReceipt, InventoryMovement, Order, Product, PurchaseOrder, SKU, Supplier  # noqa: E402
from crm.services.fulfillment import confirm_shipment, record_receipt, reverse_receipt, reverse_shipment, sku_metrics  # noqa: E402


DAY = date(2026, 10, 29)


def snapshot(sku, purchase_item, purchase, order):
    return {
        "actual": str(sku_metrics(sku)["actual_quantity"]),
        "reserved": str(sku_metrics(sku)["reserved_quantity"]),
        "purchase_status": purchase.status,
        "order_status": order.status,
        "receipts": GoodsReceipt.objects.filter(purchase_item=purchase_item).count(),
        "purchase_in_movements": InventoryMovement.objects.filter(
            sku=sku, source_type="receipt", type="purchase_in"
        ).count(),
        "shipments": order.shipments.count(),
        "shipment_items": sum(shipment.items.count() for shipment in order.shipments.all()),
        "sale_out_movements": InventoryMovement.objects.filter(
            order=order, source_type="shipment", type="sale_out"
        ).count(),
    }


customer = Customer.objects.create(code="AUDIT-CLOSURE-C", name="Closure Audit Customer")
supplier = Supplier.objects.create(code="AUDIT-CLOSURE-S", name="Closure Audit Supplier")
sku = SKU.objects.create(
    sku="AUDIT-CLOSURE-SKU",
    product=Product.objects.create(code="AUDIT-CLOSURE-P", name="Closure Audit Product"),
)
purchase = PurchaseOrder.objects.create(
    purchase_no="AUDIT-CLOSURE-PO",
    supplier=supplier,
    order_date=DAY,
    status="ordered",
    currency="CNY",
    exchange_rate=Decimal("1"),
)
purchase_item = purchase.items.create(sku=sku, quantity=Decimal("10"), unit_price=Decimal("5"))
order = Order.objects.create(
    order_no="AUDIT-CLOSURE-SO",
    customer=customer,
    order_date=DAY,
    status="confirmed",
)
order_item = order.items.create(sku=sku, quantity=Decimal("5"), unit_price=Decimal("10"))

before_receipt_replay = snapshot(sku, purchase_item, purchase, order)
first_receipt = record_receipt(
    purchase_item,
    {"receipt_date": DAY, "quantity": Decimal("4"), "unit_cost": Decimal("5")},
)
after_first_receipt = snapshot(sku, purchase_item, purchase, order)
second_receipt = record_receipt(
    purchase_item,
    {"receipt_date": DAY, "quantity": Decimal("4"), "unit_cost": Decimal("5")},
)
after_second_receipt = snapshot(sku, purchase_item, purchase, order)

before_shipment_replay = snapshot(sku, purchase_item, purchase, order)
first_shipment = confirm_shipment(
    order,
    {"shipment_date": DAY, "items": [{"order_item": order_item.pk, "quantity": Decimal("2")}]},
)
after_first_shipment = snapshot(sku, purchase_item, purchase, order)
second_shipment = confirm_shipment(
    order,
    {"shipment_date": DAY, "items": [{"order_item": order_item.pk, "quantity": Decimal("2")}]},
)
after_second_shipment = snapshot(sku, purchase_item, purchase, order)

reversal_before = snapshot(sku, purchase_item, purchase, order)
reverse_receipt(first_receipt, "审查：首次收货冲销")
reversal_after_receipt = snapshot(sku, purchase_item, purchase, order)
receipt_replay_error = None
try:
    reverse_receipt(first_receipt, "审查：重复收货冲销")
except Exception as exc:  # noqa: BLE001 - preserve exact domain rejection for evidence
    receipt_replay_error = str(exc)
reversal_after_receipt_replay = snapshot(sku, purchase_item, purchase, order)

reverse_shipment(first_shipment, "审查：首次发货冲销")
reversal_after_shipment = snapshot(sku, purchase_item, purchase, order)
shipment_replay_error = None
try:
    reverse_shipment(first_shipment, "审查：重复发货冲销")
except Exception as exc:  # noqa: BLE001 - preserve exact domain rejection for evidence
    shipment_replay_error = str(exc)
reversal_after_shipment_replay = snapshot(sku, purchase_item, purchase, order)

print(
    json.dumps(
        {
            "environment": {
                "database_url": os.environ.get("DATABASE_URL", ""),
                "media_root": os.environ.get("MEDIA_ROOT", ""),
                "development_superadmin": os.environ.get("DEVELOPMENT_SUPERADMIN"),
            },
            "receipt_replay": {
                "before": before_receipt_replay,
                "first": {"id": first_receipt.pk, "status": purchase.status},
                "after_first": after_first_receipt,
                "second": {"id": second_receipt.pk, "status": purchase.status},
                "after_second": after_second_receipt,
                "same_business_payload_created_second_record": first_receipt.pk != second_receipt.pk,
            },
            "shipment_replay": {
                "before": before_shipment_replay,
                "first": {"id": first_shipment.pk},
                "after_first": after_first_shipment,
                "second": {"id": second_shipment.pk},
                "after_second": after_second_shipment,
                "same_business_payload_created_second_record": first_shipment.pk != second_shipment.pk,
            },
            "reversal_replay": {
                "before": reversal_before,
                "after_first_receipt_reversal": reversal_after_receipt,
                "receipt_replay_error": receipt_replay_error,
                "after_receipt_replay": reversal_after_receipt_replay,
                "after_first_shipment_reversal": reversal_after_shipment,
                "shipment_replay_error": shipment_replay_error,
                "after_shipment_replay": reversal_after_shipment_replay,
                "receipt_replay_state_unchanged": reversal_after_receipt_replay == reversal_after_receipt,
                "shipment_replay_state_unchanged": reversal_after_shipment_replay == reversal_after_shipment,
            },
        },
        ensure_ascii=False,
        indent=2,
        default=str,
    )
)
