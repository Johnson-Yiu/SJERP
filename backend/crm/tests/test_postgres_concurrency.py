from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
import unittest
from threading import Barrier
from unittest.mock import patch

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import close_old_connections, connection, connections
from django.db.models import Sum
from django.test import TransactionTestCase
from rest_framework.exceptions import ValidationError

from crm.models import (
    Customer,
    DocumentNumberSequence,
    GoodsReceipt,
    InventoryMovement,
    InventoryReservation,
    Order,
    Product,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseCostAllocation,
    Quote,
    QuoteChildRevisionCounter,
    QuoteNumberSequence,
    QuoteRevisionCounter,
    SKU,
    Supplier,
    SupplierSKU,
)
from crm.quote_numbers import allocate_revision_quote_no, allocate_root_quote_no
from crm.document_numbers import allocate_document_no
from crm.services.purchase_costs import save_costs
from crm.services.procurement import create_purchase_drafts
from crm.services.fulfillment import confirm_shipment, record_receipt, reverse_receipt, sku_metrics
from rest_framework.test import APIClient


@unittest.skipUnless(connection.vendor == "postgresql", "PostgreSQL row-lock tests require PostgreSQL")
class PostgreSQLConcurrencyTests(TransactionTestCase):
    def run_workers(self, function, count):
        def worker(index):
            close_old_connections()
            try:
                # Bound lock waits so a regression fails instead of leaving a
                # PostgreSQL concurrency suite hung indefinitely.
                with connections["default"].cursor() as cursor:
                    cursor.execute("SET statement_timeout = '20000ms'")
                return function(index)
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=count) as executor:
            return list(executor.map(worker, range(count)))

    def test_supplier_category_through_table_exists(self):
        through = Supplier._meta.get_field("supply_categories").remote_field.through
        self.assertIn(through._meta.db_table, connection.introspection.table_names())
        product_table = Product._meta.db_table
        self.assertIn(product_table, connection.introspection.table_names())
        with connection.cursor() as cursor:
            columns = {
                column.name
                for column in connection.introspection.get_table_description(cursor, product_table)
            }
        self.assertIn(Product._meta.get_field("combination_rules").column, columns)

    def test_order_confirm_locks_nullable_quote_without_outer_join_error(self):
        client = APIClient()
        customer = Customer.objects.create(code="PG-LIFECYCLE-C", name="PostgreSQL Lifecycle Customer")
        sku = SKU.objects.create(sku="PG-LIFECYCLE-SKU", product=Product.objects.create(code="PG-LIFECYCLE-P", name="PostgreSQL Lifecycle Product"))
        quote = Quote.objects.create(quote_no="SJ20300101US001", customer=customer, quote_date=date(2030, 1, 1), currency="USD")
        quote.items.create(sku=sku, quantity=1, unit_price=10)
        quoted_order = Order.objects.create(order_no="PG-LIFECYCLE-QUOTE", customer=customer, quote=quote, order_date=date(2030, 1, 1), currency="USD")
        quoted_order.items.create(sku=sku, quantity=1, unit_price=10)
        unquoted_order = Order.objects.create(order_no="PG-LIFECYCLE-NO-QUOTE", customer=customer, order_date=date(2030, 1, 1), currency="USD")
        unquoted_order.items.create(sku=sku, quantity=1, unit_price=10)

        for order in (quoted_order, unquoted_order):
            response = client.post(f"/api/orders/{order.id}/confirm/", {}, format="json")
            self.assertEqual(response.status_code, 200, response.data)
            order.refresh_from_db()
            self.assertEqual(order.status, "confirmed")

    def test_concurrent_accept_and_reject_only_allow_one_quote_transition(self):
        customer = Customer.objects.create(code="PG-H2-C", name="PostgreSQL H2 Customer")
        quote = Quote.objects.create(quote_no="SJ20300102US001", customer=customer, quote_date=date(2030, 1, 2))
        barrier = Barrier(2)

        def transition(action):
            client = APIClient()
            barrier.wait(timeout=10)
            response = client.post(f"/api/quotes/{quote.id}/{action}/", {}, format="json")
            return response.status_code

        results = self.run_workers(lambda index: transition(("accept", "reject")[index]), 2)

        self.assertEqual(sorted(results), [200, 400])
        quote.refresh_from_db()
        self.assertIn(quote.status, {"accepted", "rejected"})

    def test_root_quote_number_is_unique_and_contiguous_under_concurrency(self):
        quote_date = date(2030, 1, 1)
        numbers = self.run_workers(lambda _index: allocate_root_quote_no(quote_date, "SE"), 5)

        self.assertEqual(sorted(numbers), [f"SJ20300101SE{index:03d}" for index in range(1, 6)])
        self.assertEqual(QuoteNumberSequence.objects.get(quote_date=quote_date, country_code="SE").last_value, 5)

    def test_order_and_purchase_numbers_are_unique_and_contiguous_under_concurrency(self):
        order_numbers = self.run_workers(lambda _index: allocate_document_no("SO", year=2030), 20)
        purchase_numbers = self.run_workers(lambda _index: allocate_document_no("PO", year=2030), 20)

        self.assertEqual(sorted(order_numbers), [f"SO-2030-{index:05d}" for index in range(1, 21)])
        self.assertEqual(sorted(purchase_numbers), [f"PO-2030-{index:05d}" for index in range(1, 21)])
        self.assertEqual(DocumentNumberSequence.objects.get(document_type="SO", year=2030).last_value, 20)
        self.assertEqual(DocumentNumberSequence.objects.get(document_type="PO", year=2030).last_value, 20)

    def test_order_csv_import_is_rejected_without_advancing_sequence(self):
        DocumentNumberSequence.objects.create(document_type="SO", year=2031, last_value=49)
        response = APIClient().post("/api/import/csv/", {"entity": "orders"}, format="multipart")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["detail"],
            "正式订单导入暂未开放，请通过订单业务流程创建；避免绕过报价、库存预留和收款计划。",
        )
        self.assertFalse(Order.objects.filter(order_no="SO-2031-00050").exists())
        self.assertEqual(DocumentNumberSequence.objects.get(document_type="SO", year=2031).last_value, 49)

    def test_purchase_draft_generation_does_not_duplicate_under_concurrency(self):
        customer = Customer.objects.create(code="PG-PROC-C", name="PostgreSQL Procurement Customer")
        supplier = Supplier.objects.create(code="PP", name="PostgreSQL Procurement Supplier")
        sku = SKU.objects.create(sku="PG-PROC-SKU", product=Product.objects.create(code="PG-PROC-P", name="PostgreSQL Procurement Product"))
        source = SupplierSKU.objects.create(supplier=supplier, sku=sku, supplier_sku_code="PG-PROC-SOURCE", currency="USD", purchase_price=2)
        order = Order.objects.create(order_no="SO-PG-PROC", customer=customer, order_date=date(2031, 1, 1), status="confirmed")
        item = order.items.create(sku=sku, supplier_sku=source, quantity=100, unit_price=10)
        payload = {"groups": [{
            "supplier": supplier.id, "currency": "USD", "exchange_rate": Decimal("7"),
            "items": [{"order_item": item.id, "quantity": Decimal("100"), "unit_price": Decimal("2")}],
        }]}
        barrier = Barrier(2)

        def generate_once(_index):
            barrier.wait(timeout=10)
            try:
                created = create_purchase_drafts(Order.objects.get(pk=order.pk), payload)
                return ("created", [purchase.purchase_no for purchase in created])
            except DjangoValidationError as error:
                return ("rejected", str(error))

        results = self.run_workers(generate_once, 2)
        self.assertEqual([result[0] for result in results].count("created"), 1)
        self.assertEqual([result[0] for result in results].count("rejected"), 1)
        drafts = PurchaseOrder.objects.filter(order=order, status="draft")
        self.assertEqual(drafts.count(), 1)
        self.assertEqual(sum(item.quantity for item in drafts.get().items.all()), Decimal("100"))

    def test_quote_revision_counters_are_unique_and_contiguous_under_concurrency(self):
        customer = Customer.objects.create(code="PG-REV-C", name="PostgreSQL Revision Customer")
        root = Quote.objects.create(
            quote_no="SJ20300101US001",
            customer=customer,
            quote_date=date(2030, 1, 1),
            currency="USD",
        )

        results = self.run_workers(lambda _index: allocate_revision_quote_no(root), 5)

        self.assertEqual(sorted(revision_no for _quote_no, revision_no in results), [1, 2, 3, 4, 5])
        self.assertEqual(sorted(int(quote_no.rsplit("-", 1)[-1]) for quote_no, _revision_no in results), [1, 2, 3, 4, 5])
        self.assertEqual(QuoteRevisionCounter.objects.get(root_quote=root).last_value, 5)
        self.assertEqual(QuoteChildRevisionCounter.objects.get(parent_quote=root).last_value, 5)

    def test_purchase_cost_save_allows_one_writer_and_rejects_stale_writer(self):
        customer = Customer.objects.create(code="PG-COST-C", name="PostgreSQL Cost Customer")
        supplier = Supplier.objects.create(code="PC", name="PostgreSQL Cost Supplier")
        sku = SKU.objects.create(sku="PG-COST-SKU", product=Product.objects.create(code="PG-COST-P", name="PostgreSQL Cost Product"))
        purchase = PurchaseOrder.objects.create(
            purchase_no="PG-COST-PO",
            supplier=supplier,
            order_date=date(2030, 1, 1),
            status="ordered",
        )
        item = purchase.items.create(sku=sku, quantity=100, unit_price=10)
        payload = {
            "version": 0,
            "allocations": [{"purchase_item": item.pk, "target_type": "inventory", "quantity": Decimal("100")}],
            "expenses": [],
        }

        def save_once(_index):
            try:
                save_costs(PurchaseOrder.objects.get(pk=purchase.pk), payload)
                return "ok"
            except ValidationError as error:
                return f"error:{error}"

        results = self.run_workers(save_once, 2)

        self.assertEqual(results.count("ok"), 1)
        errors = [result for result in results if result.startswith("error:")]
        self.assertEqual(len(errors), 1)
        self.assertIn("成本分配已被其他人修改", errors[0])
        purchase.refresh_from_db()
        self.assertEqual(purchase.cost_allocation_version, 1)
        self.assertEqual(purchase.items.get().cost_allocations.count(), 1)

    def test_receipt_and_shipment_concurrently_rebalance_one_sku_without_deadlock(self):
        customer = Customer.objects.create(code="PG-F1-C", name="PostgreSQL F1 Customer")
        supplier = Supplier.objects.create(code="F1", name="PostgreSQL F1 Supplier")
        sku = SKU.objects.create(sku="PG-F1-SKU", product=Product.objects.create(code="PG-F1-P", name="PostgreSQL F1 Product"))
        order = Order.objects.create(order_no="SO-PG-F1", customer=customer, order_date=date(2031, 1, 1), status="confirmed")
        order_item = order.items.create(sku=sku, quantity=10, unit_price=10)
        # Existing stock makes either lock winner able to complete its business action.
        InventoryMovement.objects.create(movement_no="PG-F1-OPEN", movement_date=date(2031, 1, 1), type="adjust_in", sku=sku, quantity=10)
        purchase = PurchaseOrder.objects.create(purchase_no="PO-PG-F1", supplier=supplier, order=order, order_date=date(2031, 1, 1), status="ordered")
        purchase_item = purchase.items.create(sku=sku, quantity=10, unit_price=2)
        barrier = Barrier(2)

        def receive():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return record_receipt(PurchaseOrder.objects.get(pk=purchase.pk).items.get(pk=purchase_item.pk), {
                    "receipt_date": date(2031, 1, 1), "quantity": Decimal("10"), "unit_cost": Decimal("2"),
                }).pk
            finally:
                connections.close_all()

        def ship():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return confirm_shipment(Order.objects.get(pk=order.pk), {
                    "shipment_no": "SH-PG-F1", "shipment_date": date(2031, 1, 1),
                    "items": [{"order_item": order_item.pk, "quantity": Decimal("10")}],
                }).pk
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            receipt_future = executor.submit(receive)
            shipment_future = executor.submit(ship)
            self.assertTrue(receipt_future.result(timeout=15))
            self.assertTrue(shipment_future.result(timeout=15))

        metrics = sku_metrics(SKU.objects.get(pk=sku.pk))
        self.assertEqual(metrics["actual_quantity"], Decimal("10"))
        self.assertGreaterEqual(metrics["reserved_quantity"], Decimal("0"))
        self.assertLessEqual(metrics["reserved_quantity"], metrics["actual_quantity"])
        self.assertEqual(InventoryMovement.objects.filter(sku=sku, type="purchase_in", source_type="receipt").count(), 1)
        self.assertEqual(InventoryMovement.objects.filter(sku=sku, type="sale_out", source_type="shipment").count(), 1)

    def test_same_purchase_order_different_sku_receipts_serialize_status_and_reservations(self):
        customer = Customer.objects.create(code="PG-PO-LOCK-C", name="PO Lock Customer")
        supplier = Supplier.objects.create(code="PL", name="PO Lock Supplier")
        product = Product.objects.create(code="PG-PO-LOCK-P", name="PO Lock Product")
        order = Order.objects.create(
            order_no="SO-PG-PO-LOCK", customer=customer,
            order_date=date(2031, 2, 1), status="confirmed",
        )
        purchase = PurchaseOrder.objects.create(
            purchase_no="PO-PG-PO-LOCK", supplier=supplier, order=order,
            order_date=date(2031, 2, 1), status="ordered",
        )
        sku_lines = []
        for suffix in ("A", "B"):
            sku = SKU.objects.create(
                sku=f"PG-PO-LOCK-{suffix}", product=product,
            )
            order_item = order.items.create(sku=sku, quantity=5, unit_price=10)
            purchase_item = purchase.items.create(sku=sku, quantity=5, unit_price=2)
            PurchaseCostAllocation.objects.create(
                purchase_item=purchase_item, target_type="order", order=order,
                quantity=5,
            )
            sku_lines.append((sku, order_item, purchase_item))
        barrier = Barrier(2)

        def receive(index):
            _sku, _order_item, purchase_item = sku_lines[index]
            barrier.wait(timeout=10)
            return record_receipt(PurchaseOrderItem.objects.get(pk=purchase_item.pk), {
                "receipt_date": date(2031, 2, 1),
                "quantity": Decimal("5"),
                "unit_cost": Decimal("2"),
            }).pk

        receipt_ids = self.run_workers(receive, 2)

        purchase.refresh_from_db()
        self.assertEqual(purchase.status, "completed")
        self.assertEqual(GoodsReceipt.objects.filter(pk__in=receipt_ids).count(), 2)
        self.assertEqual(
            InventoryMovement.objects.filter(
                source_type="receipt", type="purchase_in", reference=purchase.purchase_no,
            ).count(),
            2,
        )
        for sku, order_item, purchase_item in sku_lines:
            purchase_item.refresh_from_db()
            self.assertEqual(purchase_item.received_quantity, Decimal("5.00"))
            self.assertEqual(sku_metrics(sku)["actual_quantity"], Decimal("5.00"))
            self.assertEqual(
                InventoryReservation.objects.filter(order_item=order_item).aggregate(
                    total=Sum("quantity")
                )["total"],
                Decimal("5.00"),
            )

    def test_receipt_and_reversal_race_keeps_purchase_stock_and_reservations_consistent(self):
        customer = Customer.objects.create(code="PG-PO-RACE-C", name="PO Race Customer")
        supplier = Supplier.objects.create(code="PR", name="PO Race Supplier")
        sku = SKU.objects.create(
            sku="PG-PO-RACE-SKU",
            product=Product.objects.create(code="PG-PO-RACE-P", name="PO Race Product"),
        )
        order = Order.objects.create(
            order_no="SO-PG-PO-RACE", customer=customer,
            order_date=date(2031, 3, 1), status="confirmed",
        )
        order_item = order.items.create(sku=sku, quantity=5, unit_price=10)
        purchase = PurchaseOrder.objects.create(
            purchase_no="PO-PG-PO-RACE", supplier=supplier, order=order,
            order_date=date(2031, 3, 1), status="ordered",
        )
        purchase_item = purchase.items.create(sku=sku, quantity=10, unit_price=2)
        PurchaseCostAllocation.objects.create(
            purchase_item=purchase_item, target_type="order", order=order,
            quantity=10,
        )
        original_receipt = record_receipt(purchase_item, {
            "receipt_date": date(2031, 3, 1),
            "quantity": Decimal("5"),
            "unit_cost": Decimal("2"),
        })
        barrier = Barrier(2)

        def run_racing_operation(index):
            barrier.wait(timeout=10)
            if index == 0:
                new_receipt = record_receipt(PurchaseOrderItem.objects.get(pk=purchase_item.pk), {
                    "receipt_date": date(2031, 3, 2),
                    "quantity": Decimal("5"),
                    "unit_cost": Decimal("2"),
                })
                return "receipt", new_receipt.pk
            reversed_receipt = reverse_receipt(
                GoodsReceipt.objects.get(pk=original_receipt.pk),
                "PostgreSQL concurrent receipt/reversal regression",
            )
            return "reversal", reversed_receipt.pk

        operations = dict(self.run_workers(run_racing_operation, 2))
        new_receipt_id = operations["receipt"]
        reversed_receipt_id = operations["reversal"]

        purchase.refresh_from_db()
        order_item.refresh_from_db()
        self.assertEqual(purchase.status, "partial")
        self.assertEqual(GoodsReceipt.objects.filter(purchase_item=purchase_item).count(), 2)
        original_receipt.refresh_from_db()
        self.assertEqual(original_receipt.pk, reversed_receipt_id)
        self.assertIsNotNone(original_receipt.reversal_inventory_movement_id)
        self.assertEqual(
            GoodsReceipt.objects.filter(
                pk=new_receipt_id, reversal_inventory_movement__isnull=True,
            ).count(),
            1,
        )
        self.assertEqual(purchase_item.received_quantity, Decimal("5.00"))
        self.assertEqual(sku_metrics(sku)["actual_quantity"], Decimal("5.00"))
        self.assertEqual(
            InventoryMovement.objects.filter(
                sku=sku, type="purchase_in", source_type="receipt",
            ).aggregate(total=Sum("quantity"))["total"],
            Decimal("10.00"),
        )
        self.assertEqual(
            InventoryMovement.objects.filter(
                sku=sku, type="adjust_out", source_type="reversal",
            ).aggregate(total=Sum("quantity"))["total"],
            Decimal("5.00"),
        )
        self.assertEqual(
            InventoryReservation.objects.filter(order_item=order_item).aggregate(
                total=Sum("quantity")
            )["total"],
            Decimal("5.00"),
        )
