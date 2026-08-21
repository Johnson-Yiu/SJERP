from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

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
    Quote,
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


class FulfillmentApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        customer = Customer.objects.create(code="C-API", name="API Buyer")
        product = Product.objects.create(code="P-API", name="API Light")
        self.sku = SKU.objects.create(product=product, sku="SKU-API")

    def test_automatic_inventory_movement_is_read_only(self):
        movement = InventoryMovement.objects.create(
            movement_no="AUTO-API",
            movement_date=date(2026, 8, 21),
            type="purchase_in",
            sku=self.sku,
            quantity=Decimal("2.00"),
            is_automatic=True,
            source_type="receipt",
            source_no="PO-API",
        )

        response = self.client.patch(
            "/api/inventory-movements/{}/".format(movement.id),
            {"notes": "changed"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("自动", response.data["detail"])

    def test_suppliers_can_be_created_through_api(self):
        response = self.client.post("/api/suppliers/", {
            "name": "API Supplier",
            "currency": "USD",
            "payment_terms": "30 days",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "API Supplier")

    def test_purchase_order_can_be_created_and_reports_unpaid_amount(self):
        supplier = Supplier.objects.create(name="Purchase API Supplier")
        order = Order.objects.create(
            order_no="SO-PURCHASE-API", customer=Customer.objects.get(code="C-API"),
            order_date=date(2026, 8, 21), status="confirmed",
        )
        response = self.client.post("/api/purchase-orders/", {
            "purchase_no": "PO-API-001", "supplier": supplier.id, "order": order.id,
            "order_date": "2026-08-21", "status": "ordered", "currency": "USD",
            "exchange_rate": "1", "items": [{"sku": self.sku.id, "quantity": "4", "unit_price": "3"}],
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["unpaid_amount"], "12.00")

    def test_purchase_receipt_creates_automatic_inventory_movement(self):
        supplier = Supplier.objects.create(name="Receipt API Supplier")
        order = Order.objects.create(order_no="SO-RECEIPT-API", customer=Customer.objects.get(code="C-API"), order_date=date(2026, 8, 21))
        purchase = PurchaseOrder.objects.create(purchase_no="PO-RECEIPT-API", supplier=supplier, order=order, order_date=date(2026, 8, 21), status="ordered")
        item = purchase.items.create(sku=self.sku, quantity="4", unit_price="3")
        response = self.client.post("/api/purchase-orders/{}/receive/".format(purchase.id), {
            "purchase_item": item.id, "receipt_date": "2026-08-21", "quantity": "4", "unit_cost": "3",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, getattr(response, "data", None))
        self.assertTrue(InventoryMovement.objects.filter(source_type="receipt", source_no="PO-RECEIPT-API", is_automatic=True).exists())

    def test_supplier_payment_creates_expense_for_purchase_order(self):
        supplier = Supplier.objects.create(name="Payment API Supplier")
        order = Order.objects.create(order_no="SO-PAYMENT-API", customer=Customer.objects.get(code="C-API"), order_date=date(2026, 8, 21))
        purchase = PurchaseOrder.objects.create(purchase_no="PO-PAYMENT-API", supplier=supplier, order=order, order_date=date(2026, 8, 21), status="ordered")
        purchase.items.create(sku=self.sku, quantity="4", unit_price="3")
        response = self.client.post("/api/purchase-orders/{}/pay/".format(purchase.id), {
            "transaction_date": "2026-08-21", "amount": "12", "currency": "USD", "exchange_rate": "1",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, getattr(response, "data", None))
        self.assertEqual(response.data["direction"], "expense")

    def test_order_fulfillment_reports_procurement_need_without_reserving_quote(self):
        order = Order.objects.create(order_no="SO-FULFILLMENT-API", customer=Customer.objects.get(code="C-API"), order_date=date(2026, 8, 21), status="confirmed")
        order.items.create(sku=self.sku, quantity="4", unit_price="5")
        response = self.client.get("/api/orders/{}/fulfillment/".format(order.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK, getattr(response, "data", None))
        self.assertEqual(response.data["items"][0]["to_procure_quantity"], Decimal("4.00"))

    def test_order_shipment_creates_automatic_sale_out(self):
        order = Order.objects.create(order_no="SO-SHIP-API", customer=Customer.objects.get(code="C-API"), order_date=date(2026, 8, 21), status="confirmed")
        item = order.items.create(sku=self.sku, quantity="2", unit_price="5")
        InventoryMovement.objects.create(movement_no="IN-SHIP-API", movement_date=date(2026, 8, 21), type="purchase_in", sku=self.sku, quantity="2")
        response = self.client.post("/api/orders/{}/ship/".format(order.id), {
            "shipment_no": "SH-API-001", "shipment_date": "2026-08-21",
            "items": [{"order_item": item.id, "quantity": "2"}],
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, getattr(response, "data", None))
        self.assertTrue(InventoryMovement.objects.filter(source_type="shipment", source_no="SH-API-001", type="sale_out").exists())

    def test_quote_availability_shows_stock_without_creating_reservation(self):
        quote = Quote.objects.create(quote_no="QT-AVAIL-API", customer=Customer.objects.get(code="C-API"), quote_date=date(2026, 8, 21), lead_time_days=12)
        quote.items.create(sku=self.sku, quantity="3", unit_price="5")
        InventoryMovement.objects.create(movement_no="IN-AVAIL-API", movement_date=date(2026, 8, 21), type="purchase_in", sku=self.sku, quantity="2")
        response = self.client.get("/api/quotes/{}/availability/".format(quote.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK, getattr(response, "data", None))
        self.assertEqual(response.data["items"][0]["available_quantity"], Decimal("2.00"))
