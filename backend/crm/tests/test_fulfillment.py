from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from crm.models import (
    Customer,
    InventoryMovement,
    Order,
    Product,
    PurchaseOrder,
    PurchaseOrderItem,
    Shipment,
    ShipmentItem,
    SKU,
    Supplier,
)
from crm.services.fulfillment import (
    allocate_order,
    confirm_shipment,
    order_item_metrics,
    record_receipt,
    record_supplier_payment,
)


class FulfillmentModelTests(TestCase):
    def setUp(self):
        customer = Customer.objects.create(code="C-FULFILLMENT", name="Fulfillment Buyer")
        product = Product.objects.create(code="P-FULFILLMENT", name="Fulfillment Light")
        self.sku = SKU.objects.create(product=product, sku="SKU-FULFILLMENT")
        self.order = Order.objects.create(
            order_no="SO-FULFILLMENT",
            customer=customer,
            order_date=date(2026, 8, 21),
        )
        self.order_item = self.order.items.create(
            sku=self.sku,
            quantity=Decimal("10.00"),
            unit_price=Decimal("5.00"),
        )
        self.supplier = Supplier.objects.create(name="Fulfillment Supplier")

    def test_purchase_and_shipment_lines_reject_zero_quantity(self):
        purchase = PurchaseOrder.objects.create(
            purchase_no="PO-FULFILLMENT",
            supplier=self.supplier,
            order=self.order,
            order_date=date(2026, 8, 21),
            status="draft",
            currency="USD",
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PurchaseOrderItem.objects.create(
                    purchase_order=purchase,
                    sku=self.sku,
                    quantity=Decimal("0"),
                    unit_price=Decimal("2.00"),
                )


class FulfillmentServiceTests(TestCase):
    def setUp(self):
        customer = Customer.objects.create(code="C-SERVICE", name="Service Buyer")
        product = Product.objects.create(code="P-SERVICE", name="Service Light")
        self.sku = SKU.objects.create(product=product, sku="SKU-SERVICE")
        self.order = Order.objects.create(
            order_no="SO-SERVICE",
            customer=customer,
            order_date=date(2026, 8, 21),
            status="confirmed",
        )
        self.order_item = self.order.items.create(
            sku=self.sku,
            quantity=Decimal("10.00"),
            unit_price=Decimal("5.00"),
        )

    def test_order_allocation_uses_stock_then_marks_remaining_for_procurement(self):
        InventoryMovement.objects.create(
            movement_no="HIST-IN-SERVICE",
            movement_date=date(2026, 8, 21),
            type="purchase_in",
            sku=self.sku,
            quantity=Decimal("6.00"),
            warehouse="默认仓",
        )

        reservations = allocate_order(self.order)

        self.assertEqual(reservations[0].quantity, Decimal("6.00"))
        self.assertEqual(
            order_item_metrics(self.order_item)["to_procure_quantity"],
            Decimal("4.00"),
        )

    def test_receipt_and_shipment_create_automatic_inventory_movements(self):
        supplier = Supplier.objects.create(name="Service Supplier")
        purchase = PurchaseOrder.objects.create(
            purchase_no="PO-SERVICE",
            supplier=supplier,
            order=self.order,
            order_date=date(2026, 8, 21),
            status="ordered",
        )
        purchase_item = purchase.items.create(
            sku=self.sku,
            quantity=Decimal("10.00"),
            unit_price=Decimal("3.00"),
        )

        receipt = record_receipt(purchase_item, {
            "receipt_date": date(2026, 8, 21),
            "quantity": Decimal("10.00"),
            "unit_cost": Decimal("3.00"),
        })
        shipment = confirm_shipment(self.order, {
            "shipment_no": "SH-SERVICE",
            "shipment_date": date(2026, 8, 21),
            "items": [{"order_item": self.order_item.id, "quantity": Decimal("10.00")}],
        })

        self.assertTrue(receipt.inventory_movement.is_automatic)
        self.assertEqual(receipt.inventory_movement.type, "purchase_in")
        self.assertEqual(shipment.items.count(), 1)
        self.assertEqual(
            InventoryMovement.objects.filter(source_type="shipment", is_automatic=True).count(),
            1,
        )

    def test_over_receipt_requires_reason_and_supplier_payment_cannot_exceed_unpaid(self):
        supplier = Supplier.objects.create(name="Payment Supplier")
        purchase = PurchaseOrder.objects.create(
            purchase_no="PO-PAYMENT",
            supplier=supplier,
            order=self.order,
            order_date=date(2026, 8, 21),
            status="ordered",
        )
        item = purchase.items.create(
            sku=self.sku,
            quantity=Decimal("4.00"),
            unit_price=Decimal("3.00"),
        )

        with self.assertRaises(ValidationError):
            record_receipt(item, {
                "receipt_date": date(2026, 8, 21),
                "quantity": Decimal("5.00"),
                "unit_cost": Decimal("3.00"),
            })
        receipt = record_receipt(item, {
            "receipt_date": date(2026, 8, 21),
            "quantity": Decimal("5.00"),
            "unit_cost": Decimal("3.00"),
            "is_overage": True,
            "overage_reason": "gift",
        })
        self.assertTrue(receipt.is_overage)
        payment = record_supplier_payment(purchase, {
            "transaction_date": date(2026, 8, 21),
            "amount": Decimal("12.00"),
            "currency": "USD",
            "exchange_rate": Decimal("1"),
        })
        self.assertEqual(payment.purchase_order, purchase)
        with self.assertRaises(ValidationError):
            record_supplier_payment(purchase, {
                "transaction_date": date(2026, 8, 21),
                "amount": Decimal("0.01"),
                "currency": "USD",
                "exchange_rate": Decimal("1"),
            })

        shipment = Shipment.objects.create(
            shipment_no="SH-FULFILLMENT",
            order=self.order,
            shipment_date=date(2026, 8, 21),
            status="draft",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ShipmentItem.objects.create(
                    shipment=shipment,
                    order_item=self.order_item,
                    sku=self.sku,
                    quantity=Decimal("0"),
                )
