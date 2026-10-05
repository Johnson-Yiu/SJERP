from datetime import date

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from crm.models import Customer, Order, Product, PurchaseCostAllocation, PurchaseOrder, SKU, Supplier


class PurchaseOrderRelatedOrdersApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        customer = Customer.objects.create(code="PORA-C", name="Related Order Customer")
        self.supplier = Supplier.objects.create(code="RA", name="Related Order Supplier")
        self.sku = SKU.objects.create(
            sku="PORA-SKU",
            product=Product.objects.create(code="PORA-P", name="Related Order Product"),
        )
        self.source_order = Order.objects.create(
            order_no="SO-PORA-SOURCE", customer=customer, order_date=date(2026, 10, 1), status="confirmed"
        )
        self.allocated_order = Order.objects.create(
            order_no="SO-PORA-ALLOC", customer=customer, order_date=date(2026, 10, 2), status="confirmed"
        )
        self.other_order = Order.objects.create(
            order_no="SO-PORA-OTHER", customer=customer, order_date=date(2026, 10, 3), status="cancelled"
        )
        self.source_order.items.create(sku=self.sku, quantity=10, unit_price=20)
        self.allocated_order.items.create(sku=self.sku, quantity=10, unit_price=20)
        self.other_order.items.create(sku=self.sku, quantity=10, unit_price=20)

    def make_purchase(self, suffix, *, source_order=None, item_count=1):
        purchase = PurchaseOrder.objects.create(
            purchase_no=f"PO-PORA-{suffix}",
            supplier=self.supplier,
            order=source_order,
            order_date=date(2026, 10, 4),
            status="ordered",
        )
        items = [
            purchase.items.create(sku=self.sku, quantity=10, unit_price=2)
            for _ in range(item_count)
        ]
        return purchase, items

    def set_allocations(self, item, rows):
        PurchaseCostAllocation.objects.filter(purchase_item=item).delete()
        PurchaseCostAllocation.objects.bulk_create([
            PurchaseCostAllocation(
                purchase_item=item,
                target_type=target_type,
                order=order,
                quantity=1,
                target_name=target_name,
            )
            for target_type, order, target_name in rows
        ])

    def get_purchase(self, purchase):
        response = self.client.get(f"/api/purchase-orders/{purchase.pk}/")
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def test_one_sales_order_allocation_is_exposed_in_navigation_shape(self):
        purchase, (item,) = self.make_purchase("ONE")
        self.set_allocations(item, [("order", self.allocated_order, "")])

        data = self.get_purchase(purchase)

        self.assertEqual(data["related_orders"], [{"id": self.allocated_order.id, "order_no": self.allocated_order.order_no}])

    def test_allocations_on_multiple_items_to_same_order_are_unique(self):
        purchase, items = self.make_purchase("UNIQUE", item_count=2)
        for item in items:
            self.set_allocations(item, [("order", self.allocated_order, "")])

        data = self.get_purchase(purchase)

        self.assertEqual(data["related_orders"], [{"id": self.allocated_order.id, "order_no": self.allocated_order.order_no}])

    def test_two_sales_order_allocations_are_stably_ordered_and_include_cancelled_history(self):
        purchase, (item,) = self.make_purchase("MULTI")
        self.set_allocations(item, [
            ("order", self.other_order, ""),
            ("order", self.allocated_order, ""),
        ])

        data = self.get_purchase(purchase)

        self.assertEqual(data["related_orders"], [
            {"id": order.id, "order_no": order.order_no}
            for order in sorted([self.other_order, self.allocated_order], key=lambda order: order.id)
        ])

    def test_source_order_stays_separate_from_actual_cost_allocation(self):
        purchase, (item,) = self.make_purchase("DISTINCT", source_order=self.source_order)
        self.set_allocations(item, [("order", self.allocated_order, "")])

        data = self.get_purchase(purchase)

        self.assertEqual(data["order"], self.source_order.id)
        self.assertEqual(data["order_no"], self.source_order.order_no)
        self.assertEqual(data["related_orders"], [{"id": self.allocated_order.id, "order_no": self.allocated_order.order_no}])
        self.assertNotIn(self.source_order.id, [row["id"] for row in data["related_orders"]])

    def test_non_order_allocations_do_not_create_related_order_links(self):
        purchase, (item,) = self.make_purchase("NONORDER", source_order=self.source_order)
        self.set_allocations(item, [
            ("inventory", None, ""),
            ("sample", None, "sample stock"),
            ("other", None, "internal test"),
        ])

        data = self.get_purchase(purchase)

        self.assertEqual(data["order"], self.source_order.id)
        self.assertEqual(data["related_orders"], [])

    def test_existing_purchase_order_fields_remain_available(self):
        purchase, (item,) = self.make_purchase("FIELDS", source_order=self.source_order)
        self.set_allocations(item, [("order", self.allocated_order, "")])

        data = self.get_purchase(purchase)

        for field in ("id", "purchase_no", "supplier", "supplier_name", "order", "order_no", "status", "items", "total_amount"):
            self.assertIn(field, data)

    def test_purchase_list_prefetches_order_allocations_without_per_purchase_queries(self):
        first, (first_item,) = self.make_purchase("LIST-1")
        self.set_allocations(first_item, [("order", self.allocated_order, "")])

        def allocation_query_count():
            with CaptureQueriesContext(connection) as queries:
                response = self.client.get("/api/purchase-orders/")
            self.assertEqual(response.status_code, 200, response.data)
            return sum("crm_purchasecostallocation" in query["sql"].lower() for query in queries.captured_queries)

        one_purchase_query_count = allocation_query_count()
        self.assertGreaterEqual(one_purchase_query_count, 1)
        second, (second_item,) = self.make_purchase("LIST-2")
        third, (third_item,) = self.make_purchase("LIST-3")
        self.set_allocations(second_item, [("order", self.other_order, "")])
        self.set_allocations(third_item, [("order", self.allocated_order, "")])

        self.assertEqual(allocation_query_count(), one_purchase_query_count)

    def test_order_fulfillment_serializes_actual_allocations_with_one_prefetch(self):
        allocation_table = PurchaseCostAllocation._meta.db_table.lower()

        def fulfillment_result_and_query_count():
            with CaptureQueriesContext(connection) as queries:
                response = self.client.get(f"/api/orders/{self.allocated_order.pk}/fulfillment/")
            self.assertEqual(response.status_code, 200, response.data)
            allocation_query_count = sum(
                f"from {allocation_table}" in query["sql"].lower()
                or f'from "{allocation_table}"' in query["sql"].lower()
                for query in queries.captured_queries
            )
            return response.data, allocation_query_count

        first, (first_item,) = self.make_purchase("FULFILL-1")
        self.set_allocations(first_item, [("order", self.allocated_order, "")])
        one_purchase_data, one_purchase_queries = fulfillment_result_and_query_count()
        self.assertEqual(one_purchase_data["purchase_orders"][0]["related_orders"], [
            {"id": self.allocated_order.id, "order_no": self.allocated_order.order_no}
        ])

        second, (second_item,) = self.make_purchase("FULFILL-2")
        self.set_allocations(second_item, [("order", self.allocated_order, "")])
        two_purchase_data, two_purchase_queries = fulfillment_result_and_query_count()

        self.assertEqual(len(two_purchase_data["purchase_orders"]), 2)
        self.assertTrue(all(
            purchase["related_orders"] == [{"id": self.allocated_order.id, "order_no": self.allocated_order.order_no}]
            for purchase in two_purchase_data["purchase_orders"]
        ))
        self.assertGreaterEqual(one_purchase_queries, 1)
        self.assertEqual(two_purchase_queries, one_purchase_queries)
