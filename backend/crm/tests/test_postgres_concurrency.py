from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
import unittest

from django.db import close_old_connections, connection, connections
from django.test import TransactionTestCase
from rest_framework.exceptions import ValidationError

from crm.models import (
    Customer,
    Product,
    PurchaseOrder,
    Quote,
    QuoteChildRevisionCounter,
    QuoteNumberSequence,
    QuoteRevisionCounter,
    SKU,
    Supplier,
)
from crm.quote_numbers import allocate_revision_quote_no, allocate_root_quote_no
from crm.services.purchase_costs import save_costs


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

    def test_root_quote_number_is_unique_and_contiguous_under_concurrency(self):
        quote_date = date(2030, 1, 1)
        numbers = self.run_workers(lambda _index: allocate_root_quote_no(quote_date, "SE"), 5)

        self.assertEqual(sorted(numbers), [f"SJ20300101SE{index:03d}" for index in range(1, 6)])
        self.assertEqual(QuoteNumberSequence.objects.get(quote_date=quote_date, country_code="SE").last_value, 5)

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
            "allocations": [{"purchase_item": item.pk, "target_type": "inventory", "quantity": "100"}],
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
