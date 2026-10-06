from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from crm.models import (
    Customer,
    InventoryMovement,
    InventoryReservation,
    Order,
    PaymentPlan,
    Product,
    ProductCategory,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseCostAllocation,
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
    rebalance_sku_reservations,
    record_receipt,
    record_supplier_payment,
    reverse_receipt,
    sku_metrics,
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
        self.supplier = Supplier.objects.create(name="Fulfillment Supplier", code="FS")

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
        supplier = Supplier.objects.create(name="Service Supplier", code="SV")
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
        supplier = Supplier.objects.create(name="Payment Supplier", code="PS")
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


class ReservationRebalanceTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(code="RF", name="Reservation Buyer")
        self.supplier = Supplier.objects.create(code="RS", name="Reservation Supplier")
        self.sku = SKU.objects.create(sku="SKU-RESERVE", product=Product.objects.create(code="PR", name="Reservation Product"))
        self.a = self.make_order("SO-RES-A", date(2026, 1, 2))
        self.b = self.make_order("SO-RES-B", date(2026, 1, 1))
        self.client = APIClient()

    def make_order(self, order_no, order_date, quantity=10):
        order = Order.objects.create(order_no=order_no, customer=self.customer, order_date=order_date, status="confirmed")
        order.items.create(sku=self.sku, quantity=quantity, unit_price=5)
        return order

    def make_purchase(self, *, order, quantity=10):
        purchase = PurchaseOrder.objects.create(
            purchase_no=f"PO-RES-{PurchaseOrder.objects.count() + 1}", supplier=self.supplier,
            order=order, order_date=date(2026, 1, 3), status="ordered",
        )
        return purchase.items.create(sku=self.sku, quantity=quantity, unit_price=2)

    def set_allocations(self, item, rows):
        PurchaseCostAllocation.objects.filter(purchase_item=item).delete()
        PurchaseCostAllocation.objects.bulk_create([
            PurchaseCostAllocation(purchase_item=item, target_type=target, order=order, quantity=quantity)
            for target, order, quantity in rows
        ])

    def reserved(self, order):
        return InventoryReservation.objects.filter(order_item__order=order).aggregate(total=Sum("quantity"))["total"] or Decimal("0")

    def test_independent_receipt_rebalances_available_stock_to_active_order(self):
        item = self.make_purchase(order=None)
        record_receipt(item, {"receipt_date": date(2026, 1, 3), "quantity": 10, "unit_cost": 2})
        self.assertEqual(self.reserved(self.b), Decimal("10"))
        self.assertEqual(self.reserved(self.a), Decimal("0"))

    def test_receipt_uses_cost_allocation_not_purchase_reference(self):
        item = self.make_purchase(order=self.a)
        self.set_allocations(item, [("order", self.b, Decimal("10"))])
        receipt = record_receipt(item, {"receipt_date": date(2026, 1, 3), "quantity": 10, "unit_cost": 2})
        receipt.inventory_movement.refresh_from_db()
        self.assertIsNone(receipt.inventory_movement.order_id)
        self.assertEqual(list(receipt.inventory_movement.related_orders.values_list("id", flat=True)), [self.b.id])
        self.assertEqual(self.reserved(self.b), Decimal("10"))
        self.assertEqual(self.reserved(self.a), Decimal("0"))

    def test_shared_partial_receipt_is_proportionally_reserved_without_duplication(self):
        self.a.items.update(quantity=100)
        self.b.items.update(quantity=100)
        item = self.make_purchase(order=self.a, quantity=100)
        self.set_allocations(item, [("order", self.a, Decimal("60")), ("order", self.b, Decimal("40"))])
        record_receipt(item, {"receipt_date": date(2026, 1, 3), "quantity": 50, "unit_cost": 2})
        self.assertEqual(self.reserved(self.a), Decimal("30"))
        self.assertEqual(self.reserved(self.b), Decimal("20"))
        self.assertEqual(sum((row.quantity for row in InventoryReservation.objects.filter(sku=self.sku)), Decimal("0")), Decimal("50"))

    def test_inventory_remainder_follows_stable_order_after_allocated_priority(self):
        self.a.items.update(quantity=40)
        self.b.items.update(quantity=60)
        item = self.make_purchase(order=self.a, quantity=100)
        self.set_allocations(item, [("order", self.a, Decimal("40")), ("inventory", None, Decimal("60"))])
        record_receipt(item, {"receipt_date": date(2026, 1, 3), "quantity": 100, "unit_cost": 2})
        self.assertEqual(self.reserved(self.a), Decimal("40"))
        self.assertEqual(self.reserved(self.b), Decimal("60"))

    def test_priority_and_general_passes_cap_one_order_item_at_remaining_demand(self):
        self.b.items.update(quantity=1)
        item = self.make_purchase(order=self.a, quantity=4)
        self.set_allocations(item, [("order", self.a, Decimal("4"))])
        InventoryMovement.objects.create(
            movement_no="RES-CAP-STOCK", movement_date=date(2026, 1, 3), type="adjust_in", sku=self.sku, quantity=100,
        )
        record_receipt(item, {"receipt_date": date(2026, 1, 3), "quantity": 4, "unit_cost": 2})
        self.assertEqual(self.reserved(self.a), Decimal("10"))
        self.assertLessEqual(self.reserved(self.a), self.a.items.get().quantity)
        self.assertLessEqual(
            sum((row.quantity for row in InventoryReservation.objects.filter(sku=self.sku)), Decimal("0")),
            sku_metrics(self.sku)["actual_quantity"],
        )

    def test_shipped_quantity_reduces_received_allocation_priority(self):
        self.a.items.update(quantity=100)
        self.b.items.update(quantity=80)
        item = self.make_purchase(order=self.a, quantity=60)
        self.set_allocations(item, [("order", self.a, Decimal("60"))])
        record_receipt(item, {"receipt_date": date(2026, 1, 3), "quantity": 60, "unit_cost": 2})
        confirm_shipment(self.a, {
            "shipment_no": "SH-RES-PRIORITY", "shipment_date": date(2026, 1, 3),
            "items": [{"order_item": self.a.items.get().id, "quantity": 40}],
        })
        InventoryMovement.objects.create(
            movement_no="RES-PRIORITY-STOCK", movement_date=date(2026, 1, 3), type="adjust_in", sku=self.sku, quantity=100,
        )
        rebalance_sku_reservations(self.sku)
        # A's 60 allocated arrivals have already supplied 40 shipped units: only 20 remain priority.
        self.assertEqual(self.reserved(self.b), Decimal("80"))
        self.assertEqual(self.reserved(self.a), Decimal("40"))

    def test_repeated_sku_order_lines_never_exceed_each_line_remaining_demand(self):
        second = self.a.items.create(sku=self.sku, quantity=10, unit_price=5)
        self.b.items.update(quantity=1)
        item = self.make_purchase(order=self.a, quantity=10)
        self.set_allocations(item, [("order", self.a, Decimal("10"))])
        InventoryMovement.objects.create(
            movement_no="RES-DUPLICATE-STOCK", movement_date=date(2026, 1, 3), type="adjust_in", sku=self.sku, quantity=100,
        )
        record_receipt(item, {"receipt_date": date(2026, 1, 3), "quantity": 10, "unit_cost": 2})
        for line in self.a.items.filter(sku=self.sku):
            reserved = InventoryReservation.objects.filter(order_item=line).aggregate(total=Sum("quantity"))["total"] or Decimal("0")
            self.assertLessEqual(reserved, line.quantity)
        self.assertLessEqual(
            sum((row.quantity for row in InventoryReservation.objects.filter(sku=self.sku)), Decimal("0")),
            sku_metrics(self.sku)["actual_quantity"],
        )

    def test_cost_allocation_change_and_receipt_reversal_rebalance_reservations(self):
        from crm.services.purchase_costs import save_costs

        item = self.make_purchase(order=self.a)
        receipt = record_receipt(item, {"receipt_date": date(2026, 1, 3), "quantity": 10, "unit_cost": 2})
        save_costs(item.purchase_order, {"version": 0, "allocations": [
            {"purchase_item": item.id, "target_type": "order", "order": self.b, "quantity": Decimal("10")},
        ], "expenses": []})
        self.assertEqual(self.reserved(self.b), Decimal("10"))
        self.assertEqual(self.reserved(self.a), Decimal("0"))
        reverse_receipt(receipt, "test reversal")
        self.assertEqual(self.reserved(self.a), Decimal("0"))
        self.assertEqual(self.reserved(self.b), Decimal("0"))

    def test_manual_inventory_create_and_reversal_rebalance_reservations(self):
        response = self.client.post("/api/inventory-movements/", {
            "movement_date": "2026-01-03", "type": "adjust_in", "sku": self.sku.id, "quantity": "10",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(self.reserved(self.b), Decimal("10"))

        outgoing = InventoryMovement.objects.create(
            movement_no="MANUAL-RES-OUT", movement_date=date(2026, 1, 3), type="adjust_out", sku=self.sku,
            quantity=5, source_type="manual", is_automatic=False,
        )
        rebalance_sku_reservations(self.sku)
        self.assertEqual(self.reserved(self.b), Decimal("5"))
        response = self.client.delete(f"/api/inventory-movements/{outgoing.id}/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertTrue(InventoryMovement.objects.filter(pk=outgoing.pk).exists())
        response = self.client.post(f"/api/inventory-movements/{outgoing.id}/reverse/", {"reason": "盘点更正"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(self.reserved(self.b), Decimal("10"))


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
        category = ProductCategory.objects.create(name="Supplier API category")
        response = self.client.post("/api/suppliers/", {
            "name": "API Supplier",
            "code": "AP",
            "payment_terms": "30 days",
            "store_url": "https://1688.com/store/api-supplier",
            "supply_categories": [category.pk],
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "API Supplier")
        self.assertEqual(response.data["code"], "AP")
        self.assertEqual(response.data["store_url"], "https://1688.com/store/api-supplier")

    def test_supplier_defaults_are_applied_by_api(self):
        category = ProductCategory.objects.create(name="Supplier defaults category")
        response = self.client.post("/api/suppliers/", {
            "name": "Default Supplier",
            "code": "DF",
            "supply_categories": [category.pk],
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["country"], "中国")
        self.assertEqual(response.data["payment_terms"], "30%预付款，70%尾款发货前结清")
        self.assertEqual(response.data["main_products"], "")

    def test_supplier_code_is_unique_and_reports_the_existing_supplier(self):
        Supplier.objects.create(name="Existing Supplier", code="ES")
        response = self.client.post("/api/suppliers/", {
            "name": "Duplicate Supplier",
            "code": "es",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("ES 与 Existing Supplier-ES 重复", response.data["code"][0])

    def test_product_can_be_created_with_suppliers(self):
        supplier = Supplier.objects.create(name="Product Supplier", code="PD")
        response = self.client.post("/api/products/", {
            "name": "Supplier-linked product", "sales_model_prefix": "SUPP01", "suppliers": [supplier.id],
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, getattr(response, "data", None))
        self.assertEqual(response.data["suppliers"], [supplier.id])

    def test_purchase_order_can_be_created_and_reports_unpaid_amount(self):
        supplier = Supplier.objects.create(name="Purchase API Supplier", code="PA")
        order = Order.objects.create(
            order_no="SO-PURCHASE-API", customer=Customer.objects.get(code="C-API"),
            order_date=date(2026, 8, 21), status="confirmed",
        )
        response = self.client.post("/api/purchase-orders/", {
            "supplier": supplier.id, "order": order.id,
            "order_date": "2026-08-21", "status": "draft", "currency": "USD",
            "exchange_rate": "1", "items": [{"sku": self.sku.id, "quantity": "4", "unit_price": "3"}],
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        placed = self.client.post(f"/api/purchase-orders/{response.data['id']}/place/", {}, format="json")
        self.assertEqual(placed.status_code, status.HTTP_200_OK, placed.data)
        response = self.client.get(f"/api/purchase-orders/{response.data['id']}/")
        self.assertEqual(response.data["unpaid_amount"], "12.00")

    def test_purchase_receipt_creates_automatic_inventory_movement(self):
        supplier = Supplier.objects.create(name="Receipt API Supplier", code="RA")
        order = Order.objects.create(order_no="SO-RECEIPT-API", customer=Customer.objects.get(code="C-API"), order_date=date(2026, 8, 21))
        purchase = PurchaseOrder.objects.create(purchase_no="PO-RECEIPT-API", supplier=supplier, order=order, order_date=date(2026, 8, 21), status="ordered")
        item = purchase.items.create(sku=self.sku, quantity="4", unit_price="3")
        response = self.client.post("/api/purchase-orders/{}/receive/".format(purchase.id), {
            "purchase_item": item.id, "receipt_date": "2026-08-21", "quantity": "4", "unit_cost": "3",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, getattr(response, "data", None))
        self.assertTrue(InventoryMovement.objects.filter(source_type="receipt", source_no="PO-RECEIPT-API", is_automatic=True).exists())

    def test_over_receipt_returns_a_user_facing_validation_error(self):
        supplier = Supplier.objects.create(name="Over Receipt Supplier", code="OR")
        order = Order.objects.create(order_no="SO-OVER-RECEIPT", customer=Customer.objects.get(code="C-API"), order_date=date(2026, 8, 21))
        purchase = PurchaseOrder.objects.create(purchase_no="PO-OVER-RECEIPT", supplier=supplier, order=order, order_date=date(2026, 8, 21), status="ordered")
        item = purchase.items.create(sku=self.sku, quantity="1", unit_price="3")
        response = self.client.post(f"/api/purchase-orders/{purchase.id}/receive/", {"purchase_item": item.id, "receipt_date": "2026-08-21", "quantity": "2", "unit_cost": "3"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("超到必须选择原因", response.data["detail"])

    def test_supplier_payment_creates_expense_for_purchase_order(self):
        supplier = Supplier.objects.create(name="Payment API Supplier", code="PY")
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

    def test_reserved_production_order_can_ship_partially_through_api(self):
        order = Order.objects.create(order_no="SO-SHIP-RESERVED-API", customer=Customer.objects.get(code="C-API"), order_date=date(2026, 8, 21), status="production")
        item = order.items.create(sku=self.sku, quantity="20", unit_price="5")
        InventoryMovement.objects.create(movement_no="IN-SHIP-RESERVED-API", movement_date=date(2026, 8, 21), type="purchase_in", sku=self.sku, quantity="20")
        reservations = allocate_order(order)
        self.assertEqual(sum((row.quantity for row in reservations), Decimal("0")), Decimal("20.00"))

        payload = {
            "shipment_date": "2026-08-21",
            "items": [{"order_item": item.id, "quantity": "10", "trade_unit": None, "overage_reason": ""}],
        }
        response = self.client.post(f"/api/orders/{order.id}/ship/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, getattr(response, "data", None))
        self.assertEqual(Shipment.objects.filter(order=order, status="confirmed").count(), 1)
        self.assertEqual(ShipmentItem.objects.filter(shipment__order=order).aggregate(total=Sum("quantity"))["total"], Decimal("10.00"))
        self.assertEqual(InventoryMovement.objects.filter(order=order, type="sale_out", source_type="shipment").aggregate(total=Sum("quantity"))["total"], Decimal("10.00"))
        self.assertEqual(InventoryReservation.objects.filter(order_item=item).aggregate(total=Sum("quantity"))["total"], Decimal("10.00"))

        response = self.client.post(f"/api/orders/{order.id}/ship/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, getattr(response, "data", None))
        order.refresh_from_db()
        self.assertEqual(order.status, "shipped")
        self.assertEqual(Shipment.objects.filter(order=order, status="confirmed").count(), 2)
        self.assertEqual(ShipmentItem.objects.filter(shipment__order=order).aggregate(total=Sum("quantity"))["total"], Decimal("20.00"))
        self.assertEqual(InventoryMovement.objects.filter(order=order, type="sale_out", source_type="shipment").aggregate(total=Sum("quantity"))["total"], Decimal("20.00"))

        repeated = self.client.post(f"/api/orders/{order.id}/ship/", payload, format="json")
        self.assertEqual(repeated.status_code, status.HTTP_400_BAD_REQUEST, repeated.data)
        self.assertEqual(Shipment.objects.filter(order=order, status="confirmed").count(), 2)
        self.assertEqual(InventoryMovement.objects.filter(order=order, type="sale_out", source_type="shipment").aggregate(total=Sum("quantity"))["total"], Decimal("20.00"))

    def test_one_api_batch_ships_multiple_skus_with_full_and_partial_lines(self):
        sku_b = SKU.objects.create(product=self.sku.product, sku="SKU-BATCH-B")
        order = Order.objects.create(order_no="SO-BATCH-PARTIAL", customer=Customer.objects.get(code="C-API"), order_date=date(2026, 8, 21), status="confirmed")
        line_a = order.items.create(sku=self.sku, quantity="2", unit_price="5")
        line_b = order.items.create(sku=sku_b, quantity="3", unit_price="7")
        InventoryMovement.objects.create(movement_no="IN-BATCH-A", movement_date=date(2026, 8, 21), type="purchase_in", sku=self.sku, quantity="2")
        InventoryMovement.objects.create(movement_no="IN-BATCH-B", movement_date=date(2026, 8, 21), type="purchase_in", sku=sku_b, quantity="3")
        allocate_order(order)

        response = self.client.post(f"/api/orders/{order.id}/ship/", {
            "shipment_date": "2026-08-21",
            "items": [
                {"order_item": line_a.id, "quantity": "2"},
                {"order_item": line_b.id, "quantity": "1.25"},
            ],
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        shipments = Shipment.objects.filter(order=order, status="confirmed")
        self.assertEqual(shipments.count(), 1)
        shipment = shipments.get()
        shipment_items = list(ShipmentItem.objects.filter(shipment=shipment).order_by("pk"))
        self.assertEqual({row.order_item_id for row in shipment_items}, {line_a.id, line_b.id})
        self.assertEqual(len(shipment_items), 2)
        movements = list(InventoryMovement.objects.filter(order=order, source_type="shipment", type="sale_out"))
        self.assertEqual(len(movements), 2)
        self.assertEqual({movement.source_no for movement in movements}, {shipment.shipment_no})
        line_a.refresh_from_db()
        line_b.refresh_from_db()
        self.assertEqual(order_item_metrics(line_a)["unshipped_quantity"], Decimal("0.00"))
        self.assertEqual(order_item_metrics(line_b)["unshipped_quantity"], Decimal("1.75"))

    def test_multi_line_batch_stock_failure_rolls_back_earlier_line_and_reservation(self):
        sku_b = SKU.objects.create(product=self.sku.product, sku="SKU-BATCH-EMPTY")
        order = Order.objects.create(order_no="SO-BATCH-ATOMIC", customer=Customer.objects.get(code="C-API"), order_date=date(2026, 8, 21), status="production")
        line_a = order.items.create(sku=self.sku, quantity="2", unit_price="5")
        line_b = order.items.create(sku=sku_b, quantity="1", unit_price="7")
        InventoryMovement.objects.create(movement_no="IN-BATCH-ATOMIC", movement_date=date(2026, 8, 21), type="purchase_in", sku=self.sku, quantity="2")
        reservation = InventoryReservation.objects.create(order_item=line_a, sku=self.sku, quantity="2")
        before_sale_out = InventoryMovement.objects.filter(type="sale_out").count()

        response = self.client.post(f"/api/orders/{order.id}/ship/", {
            "shipment_date": "2026-08-21",
            "items": [
                {"order_item": line_a.id, "quantity": "1"},
                {"order_item": line_b.id, "quantity": "1"},
            ],
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertEqual(response.data["detail"], "库存不足，不能确认发货。")
        self.assertFalse(Shipment.objects.filter(order=order).exists())
        self.assertFalse(ShipmentItem.objects.filter(order_item__order=order).exists())
        self.assertEqual(InventoryMovement.objects.filter(type="sale_out").count(), before_sale_out)
        self.assertEqual(InventoryReservation.objects.get(pk=reservation.pk).quantity, Decimal("2.00"))
        line_a.refresh_from_db()
        self.assertEqual(order_item_metrics(line_a)["unshipped_quantity"], Decimal("2.00"))

    def test_batch_rejects_duplicate_and_foreign_order_item_ids(self):
        order = Order.objects.create(order_no="SO-BATCH-IDS", customer=Customer.objects.get(code="C-API"), order_date=date(2026, 8, 21), status="confirmed")
        line = order.items.create(sku=self.sku, quantity="2", unit_price="5")
        other_order = Order.objects.create(order_no="SO-BATCH-OTHER", customer=Customer.objects.get(code="C-API"), order_date=date(2026, 8, 21), status="confirmed")
        foreign_line = other_order.items.create(sku=self.sku, quantity="2", unit_price="5")

        duplicate = self.client.post(f"/api/orders/{order.id}/ship/", {
            "shipment_date": "2026-08-21", "items": [
                {"order_item": line.id, "quantity": "1"}, {"order_item": line.id, "quantity": "1"},
            ],
        }, format="json")
        foreign = self.client.post(f"/api/orders/{order.id}/ship/", {
            "shipment_date": "2026-08-21", "items": [{"order_item": foreign_line.id, "quantity": "1"}],
        }, format="json")

        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST, duplicate.data)
        self.assertEqual(foreign.status_code, status.HTTP_400_BAD_REQUEST, foreign.data)
        self.assertFalse(Shipment.objects.filter(order=order).exists())

    def test_mixed_normal_and_customer_addon_lines_create_receivable_only_for_overage(self):
        sku_b = SKU.objects.create(product=self.sku.product, sku="SKU-BATCH-ADDON")
        order = Order.objects.create(order_no="SO-BATCH-ADDON", customer=Customer.objects.get(code="C-API"), order_date=date(2026, 8, 21), status="confirmed", currency="USD")
        normal = order.items.create(sku=self.sku, quantity="2", unit_price="5")
        addon = order.items.create(sku=sku_b, quantity="1", unit_price="8")
        InventoryMovement.objects.create(movement_no="IN-BATCH-ADDON-A", movement_date=date(2026, 8, 21), type="purchase_in", sku=self.sku, quantity="2")
        InventoryMovement.objects.create(movement_no="IN-BATCH-ADDON-B", movement_date=date(2026, 8, 21), type="purchase_in", sku=sku_b, quantity="2")

        response = self.client.post(f"/api/orders/{order.id}/ship/", {
            "shipment_date": "2026-08-21",
            "items": [
                {"order_item": normal.id, "quantity": "2"},
                {"order_item": addon.id, "quantity": "2", "overage_reason": "customer_addon"},
            ],
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        shipment = Shipment.objects.get(order=order)
        normal_item = ShipmentItem.objects.get(shipment=shipment, order_item=normal)
        overage_item = ShipmentItem.objects.get(shipment=shipment, is_overage=True)
        self.assertFalse(normal_item.is_overage)
        self.assertEqual(overage_item.source_order_item_id, addon.id)
        self.assertEqual(overage_item.overage_reason, "customer_addon")
        self.assertEqual(ShipmentItem.objects.filter(shipment=shipment).count(), 3)
        plans = PaymentPlan.objects.filter(order=order, direction="receivable")
        self.assertEqual(plans.count(), 1)
        self.assertEqual(plans.get().planned_amount, Decimal("8.00"))
        self.assertEqual(overage_item.generated_payment_plan_id, plans.get().id)

    def test_multi_sku_batch_reversal_restores_all_movements_and_reservations(self):
        sku_b = SKU.objects.create(product=self.sku.product, sku="SKU-BATCH-REVERSE")
        order = Order.objects.create(order_no="SO-BATCH-REVERSE", customer=Customer.objects.get(code="C-API"), order_date=date(2026, 8, 21), status="confirmed")
        line_a = order.items.create(sku=self.sku, quantity="2", unit_price="5")
        line_b = order.items.create(sku=sku_b, quantity="3", unit_price="7")
        InventoryMovement.objects.create(movement_no="IN-BATCH-REV-A", movement_date=date(2026, 8, 21), type="purchase_in", sku=self.sku, quantity="2")
        InventoryMovement.objects.create(movement_no="IN-BATCH-REV-B", movement_date=date(2026, 8, 21), type="purchase_in", sku=sku_b, quantity="3")
        allocate_order(order)
        shipment_response = self.client.post(f"/api/orders/{order.id}/ship/", {
            "shipment_date": "2026-08-21", "items": [
                {"order_item": line_a.id, "quantity": "2"}, {"order_item": line_b.id, "quantity": "3"},
            ],
        }, format="json")
        self.assertEqual(shipment_response.status_code, status.HTTP_201_CREATED, shipment_response.data)
        shipment = Shipment.objects.get(order=order)

        reversal = self.client.post(f"/api/shipments/{shipment.id}/reverse/", {"reason": "PCR-006 API batch reversal"}, format="json")

        self.assertEqual(reversal.status_code, status.HTTP_200_OK, reversal.data)
        shipment.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(shipment.status, "cancelled")
        self.assertEqual(order.status, "confirmed")
        self.assertEqual(ShipmentItem.objects.filter(shipment=shipment).count(), 2)
        for line, sku in ((line_a, self.sku), (line_b, sku_b)):
            line.refresh_from_db()
            self.assertEqual(order_item_metrics(line)["unshipped_quantity"], line.quantity)
            self.assertEqual(InventoryReservation.objects.filter(order_item=line).aggregate(total=Sum("quantity"))["total"], line.quantity)
            self.assertEqual(InventoryMovement.objects.filter(source_type="reversal", source_no=shipment.shipment_no, sku=sku, type="adjust_in").aggregate(total=Sum("quantity"))["total"], line.quantity)

    def test_reserved_order_with_inventory_exactly_equal_to_reservation_can_ship_all(self):
        sku = SKU.objects.create(product=self.sku.product, sku="SKU-SHIP-EXACT-API")
        order = Order.objects.create(order_no="SO-SHIP-EXACT-API", customer=Customer.objects.get(code="C-API"), order_date=date(2026, 8, 21), status="confirmed")
        item = order.items.create(sku=sku, quantity="2", unit_price="5")
        supplier = Supplier.objects.create(name="Shipment receipt supplier", code="SR")
        purchase = PurchaseOrder.objects.create(
            purchase_no="PO-SHIP-EXACT-API", supplier=supplier, order=order,
            order_date=date(2026, 8, 21), status="ordered",
        )
        purchase_item = purchase.items.create(sku=sku, quantity="2", unit_price="3")
        record_receipt(purchase_item, {
            "receipt_date": date(2026, 8, 21), "quantity": Decimal("2"), "unit_cost": Decimal("3"),
        })
        self.assertEqual(sku_metrics(sku)["actual_quantity"], Decimal("2.00"))
        self.assertEqual(sku_metrics(sku)["reserved_quantity"], Decimal("2.00"))

        response = self.client.post(f"/api/orders/{order.id}/ship/", {
            "shipment_date": "2026-08-21",
            "items": [{"order_item": item.id, "quantity": "2", "trade_unit": None, "overage_reason": ""}],
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        order.refresh_from_db()
        self.assertEqual(order.status, "shipped")
        self.assertEqual(InventoryMovement.objects.filter(sku=sku, type="sale_out", source_type="shipment").aggregate(total=Sum("quantity"))["total"], Decimal("2.00"))
        self.assertFalse(InventoryReservation.objects.filter(order_item=item).exists())

    def test_insufficient_inventory_shipment_rolls_back_all_records(self):
        order = Order.objects.create(order_no="SO-SHIP-SHORT-API", customer=Customer.objects.get(code="C-API"), order_date=date(2026, 8, 21), status="production")
        item = order.items.create(sku=self.sku, quantity="2", unit_price="5")
        InventoryMovement.objects.create(movement_no="IN-SHIP-SHORT-API", movement_date=date(2026, 8, 21), type="purchase_in", sku=self.sku, quantity="1")
        reservation = InventoryReservation.objects.create(order_item=item, sku=self.sku, quantity="2")

        response = self.client.post(f"/api/orders/{order.id}/ship/", {
            "shipment_date": "2026-08-21",
            "items": [{"order_item": item.id, "quantity": "2", "trade_unit": None, "overage_reason": ""}],
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertEqual(response.data["detail"], "库存不足，不能确认发货。")
        self.assertFalse(Shipment.objects.filter(order=order).exists())
        self.assertFalse(ShipmentItem.objects.filter(order_item=item).exists())
        self.assertFalse(InventoryMovement.objects.filter(order=order, source_type="shipment").exists())
        self.assertEqual(InventoryMovement.objects.filter(sku=self.sku, type="purchase_in").aggregate(total=Sum("quantity"))["total"], Decimal("1.00"))
        self.assertEqual(InventoryReservation.objects.get(pk=reservation.pk).quantity, Decimal("2.00"))

    def test_over_shipment_returns_a_user_facing_validation_error(self):
        order = Order.objects.create(order_no="SO-OVER-SHIP", customer=Customer.objects.get(code="C-API"), order_date=date(2026, 8, 21), status="confirmed")
        item = order.items.create(sku=self.sku, quantity="1", unit_price="5")
        InventoryMovement.objects.create(movement_no="IN-OVER-SHIP", movement_date=date(2026, 8, 21), type="purchase_in", sku=self.sku, quantity="2")
        response = self.client.post(f"/api/orders/{order.id}/ship/", {"shipment_no": "SH-OVER-SHIP", "shipment_date": "2026-08-21", "items": [{"order_item": item.id, "quantity": "2"}]}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("超发必须选择", response.data["detail"])

    def test_quote_availability_shows_stock_without_creating_reservation(self):
        quote = Quote.objects.create(quote_no="QT-AVAIL-API", customer=Customer.objects.get(code="C-API"), quote_date=date(2026, 8, 21), lead_time_days=12)
        quote.items.create(sku=self.sku, quantity="3", unit_price="5")
        InventoryMovement.objects.create(movement_no="IN-AVAIL-API", movement_date=date(2026, 8, 21), type="purchase_in", sku=self.sku, quantity="2")
        response = self.client.get("/api/quotes/{}/availability/".format(quote.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK, getattr(response, "data", None))
        self.assertEqual(response.data["items"][0]["available_quantity"], Decimal("2.00"))

    def test_confirmed_order_created_by_api_reserves_available_stock(self):
        InventoryMovement.objects.create(
            movement_no="IN-ORDER-RESERVATION-API", movement_date=date(2026, 8, 21),
            type="purchase_in", sku=self.sku, quantity="3",
        )
        response = self.client.post("/api/orders/", {
            "customer": Customer.objects.get(code="C-API").id,
            "order_date": "2026-08-21", "status": "draft", "currency": "USD",
            "exchange_rate": "1", "items": [{"sku": self.sku.id, "quantity": "5", "unit_price": "8"}],
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, getattr(response, "data", None))
        self.assertEqual(response.data["items"][0]["quantity"], "5.00")
        self.assertEqual(
            response.data["items"][0]["sku"], self.sku.id,
        )
        self.assertEqual(
            Order.objects.get(pk=response.data["id"]).items.first().reservations.count(),
            0,
        )
        confirmed = self.client.post(f"/api/orders/{response.data['id']}/confirm/", {}, format="json")
        self.assertEqual(confirmed.status_code, status.HTTP_200_OK, confirmed.data)
        self.assertEqual(
            Order.objects.get(pk=response.data["id"]).items.first().reservations.first().quantity,
            Decimal("3.00"),
        )

    def test_customer_addon_shipment_creates_a_priced_order_supplement(self):
        order = Order.objects.create(order_no="SO-ADDON-API", customer=Customer.objects.get(code="C-API"), order_date=date(2026, 8, 21), status="confirmed")
        item = order.items.create(sku=self.sku, quantity="2", unit_price="7.50")
        InventoryMovement.objects.create(movement_no="IN-ADDON-API", movement_date=date(2026, 8, 21), type="purchase_in", sku=self.sku, quantity="3")
        response = self.client.post("/api/orders/{}/ship/".format(order.id), {
            "shipment_no": "SH-ADDON-API", "shipment_date": "2026-08-21",
            "items": [{"order_item": item.id, "quantity": "3", "overage_reason": "customer_addon"}],
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, getattr(response, "data", None))
        self.assertEqual(order.items.count(), 2)
        supplement = order.items.exclude(pk=item.pk).get()
        self.assertEqual(supplement.quantity, Decimal("1.00"))
        self.assertEqual(supplement.unit_price, Decimal("7.50"))
        self.assertIn("客户追加", supplement.notes)

    def test_sku_inventory_detail_lists_related_purchase_shipments_and_orders(self):
        customer = Customer.objects.get(code="C-API")
        supplier = Supplier.objects.create(name="SKU Detail Supplier", code="SD")
        order = Order.objects.create(order_no="SO-SKU-DETAIL", customer=customer, order_date=date(2026, 8, 21), status="confirmed")
        order_item = order.items.create(sku=self.sku, quantity="4", unit_price="8")
        purchase = PurchaseOrder.objects.create(purchase_no="PO-SKU-DETAIL", supplier=supplier, order=order, order_date=date(2026, 8, 21), status="ordered")
        purchase_item = purchase.items.create(sku=self.sku, quantity="4", unit_price="3")
        record_receipt(purchase_item, {"receipt_date": date(2026, 8, 21), "quantity": "4", "unit_cost": "3"})
        confirm_shipment(order, {"shipment_no": "SH-SKU-DETAIL", "shipment_date": date(2026, 8, 21), "items": [{"order_item": order_item.id, "quantity": "2"}]})

        response = self.client.get("/api/skus/{}/inventory-detail/".format(self.sku.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK, getattr(response, "data", None))
        self.assertEqual(response.data["purchases"][0]["purchase_no"], "PO-SKU-DETAIL")
        self.assertEqual(response.data["purchases"][0]["supplier_name"], "SKU Detail Supplier")
        self.assertEqual(response.data["shipments"][0]["shipment_no"], "SH-SKU-DETAIL")
        self.assertEqual(response.data["orders"][0]["order_no"], "SO-SKU-DETAIL")
        self.assertEqual(response.data["orders"][0]["customer_name"], "API Buyer")
