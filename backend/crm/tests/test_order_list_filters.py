from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from crm.models import Customer, Order


class OrderListFilterApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.today = timezone.localdate()
        self.customer = Customer.objects.create(code="OLFA", name="Filter Buyer Alpha")
        self.other_customer = Customer.objects.create(code="OLFB", name="Filter Buyer Beta")

    def order(self, number, *, status, expected_ship_date=None, customer=None):
        return Order.objects.create(
            order_no=number,
            customer=customer or self.customer,
            order_date=self.today,
            status=status,
            expected_ship_date=expected_ship_date,
        )

    def response_order_numbers(self, response):
        self.assertEqual(response.status_code, 200, response.data)
        rows = response.data.get("results", response.data)
        return {row["order_no"] for row in rows}

    def test_status_filter_is_exact_and_customer_filter_still_combines(self):
        self.order("OL-STATUS-PRODUCTION", status="production")
        self.order("OL-STATUS-CONFIRMED", status="confirmed")
        self.order("OL-STATUS-OTHER-CUSTOMER", status="production", customer=self.other_customer)

        exact = self.client.get("/api/orders/?status=production")
        self.assertEqual(self.response_order_numbers(exact), {
            "OL-STATUS-PRODUCTION", "OL-STATUS-OTHER-CUSTOMER",
        })

        combined = self.client.get(f"/api/orders/?customer={self.customer.id}&status=production")
        self.assertEqual(self.response_order_numbers(combined), {"OL-STATUS-PRODUCTION"})

    def test_unshipped_includes_only_confirmed_and_production(self):
        included = {
            self.order("OL-UNSHIPPED-CONFIRMED", status="confirmed").order_no,
            self.order("OL-UNSHIPPED-PRODUCTION", status="production").order_no,
        }
        for state in ("draft", "shipped", "completed", "cancelled"):
            self.order(f"OL-UNSHIPPED-{state.upper()}", status=state)

        response = self.client.get("/api/orders/?todo=unshipped")
        self.assertEqual(self.response_order_numbers(response), included)

    def test_due_uses_local_today_and_excludes_future_null_and_terminal_orders(self):
        included = {
            self.order("OL-DUE-YESTERDAY", status="confirmed", expected_ship_date=self.today - timedelta(days=1)).order_no,
            self.order("OL-DUE-TODAY", status="production", expected_ship_date=self.today).order_no,
        }
        excluded = [
            ("OL-DUE-FUTURE", "confirmed", self.today + timedelta(days=1)),
            ("OL-DUE-NULL", "production", None),
            ("OL-DUE-DRAFT", "draft", self.today),
            ("OL-DUE-SHIPPED", "shipped", self.today - timedelta(days=1)),
            ("OL-DUE-COMPLETED", "completed", self.today - timedelta(days=1)),
            ("OL-DUE-CANCELLED", "cancelled", self.today - timedelta(days=1)),
        ]
        for number, state, ship_date in excluded:
            self.order(number, status=state, expected_ship_date=ship_date)

        response = self.client.get("/api/orders/?todo=due")
        self.assertEqual(self.response_order_numbers(response), included)

    def test_search_combines_with_unshipped_todo(self):
        self.order("SO-ALPHA-OPEN", status="production")
        self.order("SO-ALPHA-CLOSED", status="completed")
        self.order("SO-BETA-OPEN", status="confirmed")

        response = self.client.get("/api/orders/?search=SO-ALPHA&todo=unshipped")
        self.assertEqual(self.response_order_numbers(response), {"SO-ALPHA-OPEN"})
