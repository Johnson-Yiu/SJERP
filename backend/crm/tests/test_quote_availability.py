from datetime import date
from decimal import Decimal

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.test import APIClient

from crm.models import (
    Customer,
    GoodsReceipt,
    InventoryMovement,
    InventoryReservation,
    Order,
    OrderItem,
    Product,
    PurchaseOrder,
    PurchaseOrderItem,
    Quote,
    SKU,
    Supplier,
)
from crm.services.fulfillment import bulk_sku_metrics, sku_metrics


class QuoteAvailabilityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(code="C-QUOTE-AVAIL", name="Quote Availability Buyer", country="Canada")
        self.supplier = Supplier.objects.create(code="S-QUOTE-AVAIL", name="Quote Availability Supplier")
        self.product = Product.objects.create(code="P-QUOTE-AVAIL", name="Quote Availability Light")
        self.sku = SKU.objects.create(product=self.product, sku="SKU-QUOTE-AVAIL-1", unit="pcs")
        self.sku2 = SKU.objects.create(product=self.product, sku="SKU-QUOTE-AVAIL-2", unit="pcs")

    def add_movement(self, sku, movement_no, movement_type, quantity):
        return InventoryMovement.objects.create(
            movement_no=movement_no,
            movement_date=date(2026, 10, 6),
            type=movement_type,
            sku=sku,
            quantity=Decimal(str(quantity)),
        )

    def add_reservation(self, suffix, order_status, quantity):
        order = Order.objects.create(
            order_no=f"SO-QA-{suffix}",
            customer=self.customer,
            order_date=date(2026, 10, 6),
            status=order_status,
        )
        item = OrderItem.objects.create(order=order, sku=self.sku, quantity="100", unit_price="1")
        return InventoryReservation.objects.create(order_item=item, sku=self.sku, quantity=Decimal(str(quantity)))

    def add_purchase_line(self, suffix, purchase_status, quantity, received=0, reversed_receipt=False):
        purchase = PurchaseOrder.objects.create(
            purchase_no=f"PO-QA-{suffix}",
            supplier=self.supplier,
            order_date=date(2026, 10, 6),
            status=purchase_status,
            currency="USD",
        )
        item = PurchaseOrderItem.objects.create(
            purchase_order=purchase,
            sku=self.sku,
            quantity=Decimal(str(quantity)),
            unit_price="1",
        )
        if received:
            receipt = GoodsReceipt.objects.create(
                purchase_item=item,
                receipt_date=date(2026, 10, 6),
                quantity=Decimal(str(received)),
                unit_cost="1",
            )
            incoming = self.add_movement(self.sku, f"IN-QA-{suffix}", "purchase_in", received)
            receipt.inventory_movement = incoming
            if reversed_receipt:
                reversal = self.add_movement(self.sku, f"REV-QA-{suffix}", "adjust_out", received)
                receipt.reversal_inventory_movement = reversal
            receipt.save(update_fields=["inventory_movement", "reversal_inventory_movement"])
        return item

    def test_bulk_metrics_preserve_signed_stock_active_reservations_and_negative_available(self):
        self.add_movement(self.sku, "IN-QA-BASE", "purchase_in", 100)
        for status_name in ("confirmed", "production", "shipped"):
            self.add_reservation(status_name, status_name, 10)
        for status_name in ("draft", "cancelled", "completed"):
            self.add_reservation(status_name, status_name, 100)

        metrics = bulk_sku_metrics([self.sku.pk])
        self.assertEqual(metrics[self.sku.pk]["actual_quantity"], Decimal("100.00"))
        self.assertEqual(metrics[self.sku.pk]["reserved_quantity"], Decimal("30.00"))
        self.assertEqual(metrics[self.sku.pk]["available_quantity"], Decimal("70.00"))
        self.assertEqual(metrics[self.sku.pk], sku_metrics(self.sku))

        self.add_movement(self.sku, "OUT-QA-NEGATIVE", "sample_out", 101)
        metrics = bulk_sku_metrics([self.sku.pk])[self.sku.pk]
        self.assertEqual(metrics["actual_quantity"], Decimal("-1.00"))
        self.assertEqual(metrics["available_quantity"], Decimal("-31.00"))
        self.assertEqual(metrics, sku_metrics(self.sku))

    def test_in_transit_uses_open_po_lines_and_reversed_receipts_do_not_reduce_it(self):
        self.add_movement(self.sku, "IN-QA-TRANSIT", "purchase_in", 10)
        self.add_reservation("transit", "confirmed", 5)
        self.add_purchase_line("ORDERED", "ordered", 20, received=5)
        self.add_purchase_line("PARTIAL", "partial", 30, received=35)
        self.add_purchase_line("COMPLETED", "completed", 40)
        self.add_purchase_line("CANCELLED", "cancelled", 50)
        self.add_movement(self.sku, "OUT-QA-TRANSIT", "sale_out", 40)

        metrics = bulk_sku_metrics([self.sku.pk])[self.sku.pk]
        self.assertEqual(metrics["in_transit_quantity"], Decimal("15.00"))
        self.assertEqual(metrics["available_quantity"], Decimal("5.00"))
        self.assertNotEqual(metrics["available_quantity"], Decimal("20.00"))
        self.assertEqual(metrics, sku_metrics(self.sku))

        reversed_sku = SKU.objects.create(product=self.product, sku="SKU-QUOTE-AVAIL-REVERSED", unit="pcs")
        purchase = PurchaseOrder.objects.create(
            purchase_no="PO-QA-REVERSED",
            supplier=self.supplier,
            order_date=date(2026, 10, 6),
            status="partial",
            currency="USD",
        )
        item = PurchaseOrderItem.objects.create(purchase_order=purchase, sku=reversed_sku, quantity="100", unit_price="1")
        receipt = GoodsReceipt.objects.create(purchase_item=item, receipt_date=date(2026, 10, 6), quantity="40", unit_cost="1")
        incoming = self.add_movement(reversed_sku, "IN-QA-REVERSED", "purchase_in", 40)
        reversal = self.add_movement(reversed_sku, "REV-QA-REVERSED", "adjust_out", 40)
        receipt.inventory_movement = incoming
        receipt.reversal_inventory_movement = reversal
        receipt.save(update_fields=["inventory_movement", "reversal_inventory_movement"])

        reversed_metrics = bulk_sku_metrics([reversed_sku.pk])[reversed_sku.pk]
        self.assertEqual(reversed_metrics["actual_quantity"], Decimal("0.00"))
        self.assertEqual(reversed_metrics["in_transit_quantity"], Decimal("100.00"))
        self.assertEqual(reversed_metrics, sku_metrics(reversed_sku))

    def test_preview_accepts_multiple_skus_deduplicates_and_performs_no_business_writes(self):
        self.add_movement(self.sku, "IN-QA-PREVIEW", "purchase_in", 100)
        self.add_reservation("preview", "production", 30)
        self.add_purchase_line("PREVIEW", "ordered", 50)
        before = (
            InventoryReservation.objects.count(),
            InventoryMovement.objects.count(),
            Quote.objects.count(),
            Order.objects.count(),
        )

        response = self.client.post(
            "/api/quotes/availability-preview/",
            {"sku_ids": [self.sku.pk, self.sku2.pk, self.sku.pk]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual([item["sku"] for item in response.data["items"]], [self.sku.pk, self.sku2.pk])
        self.assertEqual(response.data["items"][0], {
            "sku": self.sku.pk,
            "actual_quantity": "100.00",
            "reserved_quantity": "30.00",
            "available_quantity": "70.00",
            "in_transit_quantity": "50.00",
        })
        self.assertEqual(response.data["items"][1]["available_quantity"], "0.00")
        self.assertEqual(before, (
            InventoryReservation.objects.count(),
            InventoryMovement.objects.count(),
            Quote.objects.count(),
            Order.objects.count(),
        ))

    def test_preview_validates_required_positive_bounded_and_known_ids(self):
        for payload in ({}, {"sku_ids": []}, {"sku_ids": [0]}, {"sku_ids": ["not-an-id"]}, {"sku_ids": list(range(1, 202))}):
            with self.subTest(payload=payload):
                response = self.client.post("/api/quotes/availability-preview/", payload, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        unknown_id = max(self.sku.pk, self.sku2.pk) + 10000
        response = self.client.post("/api/quotes/availability-preview/", {"sku_ids": [unknown_id]}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(str(unknown_id), str(response.data["sku_ids"]))

    def test_creating_a_quote_does_not_reserve_inventory(self):
        before_reservations = InventoryReservation.objects.count()

        response = self.client.post(
            "/api/quotes/",
            {
                "customer": self.customer.pk,
                "quote_date": "2026-10-06",
                "currency": "USD",
                "items": [{"sku": self.sku.pk, "quantity": "2", "unit_price": "5"}],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Quote.objects.count(), 1)
        self.assertEqual(InventoryReservation.objects.count(), before_reservations)

    def test_saved_quote_availability_keeps_legacy_fields_and_matches_preview_metrics(self):
        self.add_movement(self.sku, "IN-QA-SAVED", "purchase_in", 100)
        self.add_reservation("saved", "shipped", 30)
        self.add_purchase_line("SAVED", "partial", 50)
        quote = Quote.objects.create(
            quote_no="QT-QA-AVAIL",
            customer=self.customer,
            quote_date=date(2026, 10, 6),
            lead_time_days=12,
        )
        quote_item = quote.items.create(sku=self.sku, quantity="3", unit_price="5")
        other_item = quote.items.create(sku=self.sku2, quantity="4", unit_price="2")

        saved = self.client.get(f"/api/quotes/{quote.pk}/availability/")
        preview = self.client.post("/api/quotes/availability-preview/", {"sku_ids": [self.sku.pk]}, format="json")

        self.assertEqual(saved.status_code, status.HTTP_200_OK, saved.data)
        self.assertEqual(saved.data["quote"], quote.pk)
        self.assertEqual(saved.data["items"][0]["quote_item"], quote_item.pk)
        self.assertEqual(saved.data["items"][1]["quote_item"], other_item.pk)
        self.assertEqual(saved.data["items"][0]["sku"], self.sku.pk)
        self.assertEqual(saved.data["items"][0]["available_quantity"], Decimal(preview.data["items"][0]["available_quantity"]))
        self.assertEqual(saved.data["items"][0]["actual_quantity"], "100.00")
        self.assertEqual(saved.data["items"][0]["reserved_quantity"], "30.00")
        self.assertEqual(saved.data["items"][0]["in_transit_quantity"], "50.00")
        self.assertEqual(saved.data["items"][0]["reference_lead_time_days"], 12)

    def test_preview_query_count_does_not_grow_with_sku_count(self):
        extra_skus = [SKU.objects.create(product=self.product, sku=f"SKU-QUOTE-BULK-{index}", unit="pcs") for index in range(3)]

        with CaptureQueriesContext(connection) as single_queries:
            single = self.client.post("/api/quotes/availability-preview/", {"sku_ids": [self.sku.pk]}, format="json")
        with CaptureQueriesContext(connection) as many_queries:
            many = self.client.post(
                "/api/quotes/availability-preview/",
                {"sku_ids": [self.sku.pk, *(sku.pk for sku in extra_skus)]},
                format="json",
            )

        self.assertEqual(single.status_code, status.HTTP_200_OK)
        self.assertEqual(many.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(many_queries), len(single_queries) + 1)
