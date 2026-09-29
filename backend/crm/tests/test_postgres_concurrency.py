from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
import unittest
from threading import Barrier, Event
from unittest.mock import patch

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import close_old_connections, connection, connections
from django.test import TransactionTestCase
from rest_framework.exceptions import ValidationError

from crm.models import (
    Customer,
    DocumentNumberSequence,
    InventoryMovement,
    Order,
    Product,
    PurchaseOrder,
    Quote,
    QuoteChildRevisionCounter,
    QuoteNumberSequence,
    QuoteRevisionCounter,
    SKU,
    Supplier,
    SupplierSKU,
)
from crm.quote_numbers import allocate_revision_quote_no, allocate_root_quote_no
from crm.document_numbers import allocate_document_no, sync_document_sequence_from_number
from crm.services.purchase_costs import save_costs
from crm.services.procurement import create_purchase_drafts
from crm.services.fulfillment import confirm_shipment, record_receipt, sku_metrics
from crm.views import _import_row
from rest_framework.test import APIClient


@unittest.skipUnless(connection.vendor == "postgresql", "PostgreSQL row-lock tests require PostgreSQL")
class PostgreSQLConcurrencyTests(TransactionTestCase):
    def run_workers(self, function, count):
        def worker(index):
            close_old_connections()
            try:
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

        self.assertEqual(sorted(results), [400, 200])
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

    def test_import_and_normal_order_creation_serialize_on_sequence_lock(self):
        customer = Customer.objects.create(code="PG-IMPORT-C", name="PostgreSQL Import Customer")
        DocumentNumberSequence.objects.create(document_type="SO", year=2031, last_value=49)
        import_row = {
            "order_no": "SO-2031-00050",
            "customer_code": customer.code,
            "order_date": "2031-01-01",
            "status": "draft",
            "currency": "USD",
            "exchange_rate": "1",
            "notes": "",
        }
        sync_completed = Event()
        release_import = Event()
        normal_started = Event()
        original_sync = sync_document_sequence_from_number

        def sync_and_pause(*args, **kwargs):
            result = original_sync(*args, **kwargs)
            sync_completed.set()
            if not release_import.wait(timeout=10):
                raise TimeoutError("timed out waiting to release historical import")
            return result

        def run_import():
            close_old_connections()
            try:
                return _import_row("orders", import_row)
            finally:
                connections.close_all()

        def run_normal_create():
            close_old_connections()
            try:
                normal_started.set()
                order_no = allocate_document_no("SO", year=2031)
                Order.objects.create(order_no=order_no, customer=customer, order_date=date(2031, 1, 1))
                return order_no
            finally:
                connections.close_all()

        with patch("crm.document_numbers.sync_document_sequence_from_number", side_effect=sync_and_pause):
            with ThreadPoolExecutor(max_workers=2) as executor:
                import_future = executor.submit(run_import)
                self.assertTrue(sync_completed.wait(timeout=10))
                normal_future = executor.submit(run_normal_create)
                self.assertTrue(normal_started.wait(timeout=10))
                release_import.set()
                self.assertTrue(import_future.result(timeout=10))
                self.assertEqual(normal_future.result(timeout=10), "SO-2031-00051")

        self.assertTrue(Order.objects.filter(order_no="SO-2031-00050").exists())
        self.assertTrue(Order.objects.filter(order_no="SO-2031-00051").exists())
        self.assertEqual(DocumentNumberSequence.objects.get(document_type="SO", year=2031).last_value, 51)

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
