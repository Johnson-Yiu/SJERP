from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from crm.models import (
    Customer,
    InventoryReservation,
    Order,
    OrderItem,
    PaymentPlan,
    Product,
    PurchaseCostAllocation,
    PurchaseOrder,
    Shipment,
    ShipmentItem,
    SKU,
    Supplier,
    Transaction,
)
from crm.services.fulfillment import order_item_metrics
from crm.services.purchase_costs import order_purchase_cost


class Iss021AuditProbeTests(TestCase):
    """Read-only audit probe for the not-yet-implemented formal quantity change."""

    def setUp(self):
        self.client = APIClient()
        self.day = date(2026, 10, 21)
        self.customer = Customer.objects.create(code="ISS021-C", name="ISS-021 audit buyer")
        product = Product.objects.create(code="ISS021-P", name="ISS-021 audit product")
        self.sku = SKU.objects.create(product=product, sku="ISS021-SKU", unit="pcs", default_price="10")
        self.order = Order.objects.create(
            order_no="SO-ISS021-AUDIT",
            customer=self.customer,
            order_date=self.day,
            status="confirmed",
            currency="USD",
            exchange_rate="1",
        )
        self.item = self.order.items.create(sku=self.sku, quantity="100", unit_price="10")

    def quantity_patch(self, quantity):
        return self.client.patch(
            f"/api/orders/{self.order.pk}/",
            {"items": [{"sku": self.sku.pk, "quantity": str(quantity), "unit_price": "10"}]},
            format="json",
        )

    def test_all_candidate_formal_quantity_changes_are_rejected_without_side_effects(self):
        # 100 -> 150 and 100 -> 60 are both outside the current formal-order API.
        for quantity in (150, 60):
            with self.subTest(quantity=quantity):
                response = self.quantity_patch(quantity)
                self.assertEqual(response.status_code, 400, response.data)
                self.item.refresh_from_db()
                self.assertEqual(self.item.quantity, Decimal("100.00"))

        # 100 -> 60 after 50 shipped: the current API still rejects the whole
        # operation; the metric preserves the historical shipment and exposes
        # the remaining quantity against the unchanged order line.
        shipment = Shipment.objects.create(
            shipment_no="SH-ISS021-50",
            order=self.order,
            shipment_date=self.day,
            status="confirmed",
            order_status_before_confirm="confirmed",
        )
        ShipmentItem.objects.create(shipment=shipment, order_item=self.item, sku=self.sku, quantity="50")
        response = self.quantity_patch(60)
        self.assertEqual(response.status_code, 400, response.data)
        metrics = order_item_metrics(self.item)
        self.assertEqual(metrics["shipped_quantity"], Decimal("50"))
        self.assertEqual(metrics["unshipped_quantity"], Decimal("50"))

        # A 70-unit shipment is also retained and cannot be made inconsistent
        # by a rejected quantity change.
        shipment.items.update(quantity="70")
        response = self.quantity_patch(60)
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(order_item_metrics(self.item)["shipped_quantity"], Decimal("70"))

    def test_purchase_payment_and_shared_cost_facts_remain_unchanged(self):
        supplier = Supplier.objects.create(code="I2", name="ISS-021 audit supplier")
        purchase = PurchaseOrder.objects.create(
            purchase_no="PO-ISS021-SHARED",
            supplier=supplier,
            order_date=self.day,
            status="ordered",
            currency="USD",
            exchange_rate="1",
        )
        purchase_item = purchase.items.create(sku=self.sku, quantity="100", unit_price="4")

        other_order = Order.objects.create(
            order_no="SO-ISS021-B",
            customer=self.customer,
            order_date=self.day,
            status="confirmed",
            currency="USD",
            exchange_rate="1",
        )
        other_item = other_order.items.create(sku=self.sku, quantity="40", unit_price="10")
        PurchaseCostAllocation.objects.filter(purchase_item=purchase_item).delete()
        PurchaseCostAllocation.objects.bulk_create([
            PurchaseCostAllocation(purchase_item=purchase_item, target_type="order", order=self.order, quantity="60"),
            PurchaseCostAllocation(purchase_item=purchase_item, target_type="order", order=other_order, quantity="40"),
        ])
        before_cost = order_purchase_cost(self.order)

        PaymentPlan.objects.create(order=self.order, direction="receivable", currency="USD", planned_amount="1000")
        Transaction.objects.create(
            transaction_no="TX-ISS021-PAID",
            transaction_date=self.day,
            direction="income",
            kind="customer_receipt",
            category="ISS-021 probe",
            amount="300",
            currency="USD",
            exchange_rate="1",
            customer=self.customer,
            order=self.order,
            status="confirmed",
        )
        before_paid = self.order.paid_amount
        before_reservations = list(InventoryReservation.objects.filter(order_item=self.item).values_list("quantity", flat=True))

        response = self.quantity_patch(60)
        self.assertEqual(response.status_code, 400, response.data)

        self.item.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.item.quantity, Decimal("100.00"))
        self.assertEqual(self.order.paid_amount, before_paid)
        self.assertEqual(order_purchase_cost(self.order), before_cost)
        self.assertEqual(
            list(PurchaseCostAllocation.objects.filter(purchase_item=purchase_item).order_by("id").values_list("order_id", "quantity")),
            [(self.order.pk, Decimal("60.00")), (other_order.pk, Decimal("40.00"))],
        )
        self.assertEqual(list(InventoryReservation.objects.filter(order_item=self.item).values_list("quantity", flat=True)), before_reservations)
        other_item.refresh_from_db()
        self.assertEqual(Decimal(str(other_item.quantity)), Decimal("40.00"))

    def test_multiple_sku_patch_cannot_delete_or_recreate_formal_lines(self):
        second_sku = SKU.objects.create(product=self.sku.product, sku="ISS021-SKU-B", unit="pcs", default_price="8")
        second_item = self.order.items.create(sku=second_sku, quantity="25", unit_price="8")

        response = self.client.patch(
            f"/api/orders/{self.order.pk}/",
            {"items": [
                {"sku": self.sku.pk, "quantity": "60", "unit_price": "10"},
                {"sku": second_sku.pk, "quantity": "25", "unit_price": "8"},
            ]},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(OrderItem.objects.filter(order=self.order).count(), 2)
        self.assertEqual(OrderItem.objects.get(pk=self.item.pk).quantity, Decimal("100.00"))
        self.assertEqual(OrderItem.objects.get(pk=second_item.pk).quantity, Decimal("25.00"))
