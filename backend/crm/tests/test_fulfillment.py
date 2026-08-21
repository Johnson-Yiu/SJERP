from datetime import date
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from crm.models import (
    Customer,
    Order,
    Product,
    PurchaseOrder,
    PurchaseOrderItem,
    Shipment,
    ShipmentItem,
    SKU,
    Supplier,
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
