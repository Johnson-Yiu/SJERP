from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from crm.models import Contact, Customer, InventoryMovement, Order, PaymentPlan, Product, ProductCategory, SKU
from crm.quote_numbers import allocate_root_quote_no
from crm.services.finance import record_transaction
from crm.services.fulfillment import confirm_shipment


class UATRegressionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(code="UAT-CUSTOMER", name="UAT Buyer", country="Sweden", status="customer")
        self.category = ProductCategory.objects.create(name="UAT Root Category")
        self.product = Product.objects.create(code="UAT-PRODUCT", name="UAT Product", category=self.category)
        self.sku = SKU.objects.create(sku="UAT-SKU", product=self.product, unit="pcs", default_price=Decimal("10"))

    def test_quote_number_supports_uat_countries_and_iso_code(self):
        for country, expected in (("Sweden", "SE"), ("Finland", "FI"), ("菲律宾", "PH"), ("SE", "SE")):
            with self.subTest(country=country):
                self.assertEqual(allocate_root_quote_no(date(2026, 9, 23), country)[10:12], expected)

    def test_customer_primary_contact_email_is_persisted_and_listed(self):
        Contact.objects.create(customer=self.customer, name="UAT Contact", email="uat.contact@example.com", is_primary=True)

        response = self.client.get("/api/customers/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        row = next(item for item in response.data["results"] if item["id"] == self.customer.id)
        self.assertEqual(row["primary_contact_email"], "uat.contact@example.com")

    def test_root_product_category_is_retained(self):
        response = self.client.get(f"/api/products/{self.product.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["category"], self.category.id)
        self.assertEqual(response.data["category_name"], "UAT Root Category")

    def test_optional_customer_follow_up_date_can_be_cleared(self):
        self.customer.next_follow_up = date(2026, 9, 24)
        self.customer.save(update_fields=["next_follow_up"])

        response = self.client.patch(f"/api/customers/{self.customer.id}/", {"next_follow_up": None}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertIsNone(response.data["next_follow_up"])

    def test_quote_recipient_email_is_saved_as_a_quote_snapshot(self):
        response = self.client.post("/api/quotes/", {
            "customer": self.customer.id, "quote_date": "2026-09-23", "currency": "USD", "exchange_rate": "7.2",
            "recipient_name": "Quote Recipient", "buyer_email": "quote.recipient@example.com",
            "items": [{"sku": self.sku.id, "quantity": "1", "unit_price": "10"}],
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["buyer_email"], "quote.recipient@example.com")

    def test_direct_usd_customer_receipt_is_accepted(self):
        order = Order.objects.create(order_no="UAT-RECEIPT", customer=self.customer, order_date=date(2026, 9, 23), status="confirmed", currency="USD", exchange_rate=Decimal("7.2"))
        order.items.create(sku=self.sku, quantity=Decimal("10"), unit_price=Decimal("10"))

        response = self.client.post("/api/transactions/", {
            "transaction_date": "2026-09-23", "direction": "income", "kind": "customer_receipt",
            "category": "客户收款", "amount": "25.00", "currency": "USD", "exchange_rate": "7.2", "order": order.id,
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["amount"], "25.0000")
        self.assertEqual(response.data["customer"], self.customer.id)

    def test_order_completion_requires_fulfillment_and_payment_then_closes(self):
        order = Order.objects.create(order_no="UAT-COMPLETE", customer=self.customer, order_date=date(2026, 9, 23), status="confirmed", currency="USD", exchange_rate=Decimal("7.2"))
        item = order.items.create(sku=self.sku, quantity=Decimal("2"), unit_price=Decimal("10"))
        InventoryMovement.objects.create(movement_no="UAT-STOCK", movement_date=date(2026, 9, 23), type="adjust_in", sku=self.sku, quantity=Decimal("2"))
        plan = PaymentPlan.objects.create(order=order, direction="receivable", currency="USD", due_date=date(2026, 9, 23), planned_amount=Decimal("20"))
        confirm_shipment(order, {"shipment_date": date(2026, 9, 23), "items": [{"order_item": item.id, "quantity": Decimal("2")} ]})

        blocked = self.client.post(f"/api/orders/{order.id}/complete/")
        self.assertEqual(blocked.status_code, status.HTTP_400_BAD_REQUEST, blocked.data)
        record_transaction({"transaction_date": date(2026, 9, 23), "direction": "income", "kind": "customer_receipt",
            "category": "客户收款", "amount": Decimal("20"), "currency": "USD", "exchange_rate": Decimal("7.2"), "order": order})
        plan.refresh_from_db()
        self.assertEqual(plan.status, "settled")

        response = self.client.post(f"/api/orders/{order.id}/complete/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["status"], "completed")

    def test_order_cancel_releases_unsettled_plan(self):
        order = Order.objects.create(order_no="UAT-CANCEL", customer=self.customer, order_date=date(2026, 9, 23), status="confirmed", currency="USD", exchange_rate=Decimal("7.2"))
        order.items.create(sku=self.sku, quantity=Decimal("1"), unit_price=Decimal("10"))
        plan = PaymentPlan.objects.create(order=order, direction="receivable", currency="USD", due_date=date(2026, 9, 23), planned_amount=Decimal("10"))

        response = self.client.post(f"/api/orders/{order.id}/cancel/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        plan.refresh_from_db()
        self.assertEqual(response.data["status"], "cancelled")
        self.assertEqual(plan.status, "cancelled")
