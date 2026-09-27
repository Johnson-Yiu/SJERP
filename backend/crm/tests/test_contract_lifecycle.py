from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from crm.models import Customer, InventoryMovement, InventoryReservation, Order, PaymentPlan, Product, Quote, SKU, Supplier, Transaction


class ContractLifecycleApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.day = date(2026, 9, 28)
        self.customer = Customer.objects.create(code="C-LIFECYCLE", name="Lifecycle Buyer", country="Germany")
        product = Product.objects.create(code="P-LIFECYCLE", name="Lifecycle Product")
        self.sku = SKU.objects.create(product=product, sku="SKU-LIFECYCLE", default_price="10")
        self.quote = Quote.objects.create(quote_no="SJ20260928DE001", customer=self.customer, quote_date=self.day, currency="USD")
        self.quote.items.create(sku=self.sku, quantity="2", unit_price="10", description="Lifecycle product")

    def order_payload(self, **overrides):
        payload = {
            "order_no": f"SO-LIFECYCLE-{Order.objects.count() + 1}",
            "customer": self.customer.id,
            "quote": self.quote.id,
            "order_date": self.day.isoformat(),
            "currency": "USD",
            "exchange_rate": "1",
            "shipping_fee": "0",
            "discount": "0",
            "items": [{"sku": self.sku.id, "quantity": "2", "unit_price": "10"}],
        }
        payload.update(overrides)
        return payload

    def create_draft(self, **overrides):
        response = self.client.post("/api/orders/", self.order_payload(**overrides), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return response

    def test_order_draft_has_no_formal_side_effects_and_confirm_creates_them(self):
        InventoryMovement.objects.create(movement_no="IN-LIFECYCLE", movement_date=self.day, type="adjust_in", sku=self.sku, quantity="2")
        created = self.create_draft()
        order = Order.objects.get(pk=created.data["id"])

        self.assertEqual(order.status, "draft")
        self.assertEqual(Quote.objects.count(), 1)
        self.assertEqual(self.quote.status, "draft")
        self.assertFalse(PaymentPlan.objects.filter(order=order).exists())
        self.assertFalse(InventoryReservation.objects.filter(order_item__order=order).exists())

        confirmed = self.client.post(f"/api/orders/{order.id}/confirm/", {}, format="json")
        self.assertEqual(confirmed.status_code, status.HTTP_200_OK, confirmed.data)
        order.refresh_from_db()
        self.quote.refresh_from_db()
        self.assertEqual(order.status, "confirmed")
        self.assertEqual(self.quote.status, "accepted")
        self.assertTrue(PaymentPlan.objects.filter(order=order).exists())
        self.assertEqual(InventoryReservation.objects.get(order_item__order=order).quantity, Decimal("2"))

    def test_order_revision_is_created_once_on_confirm_and_is_atomic(self):
        created = self.create_draft(shipping_fee="5")
        order = Order.objects.get(pk=created.data["id"])
        self.assertEqual(Quote.objects.count(), 1)

        confirmed = self.client.post(f"/api/orders/{order.id}/confirm/", {}, format="json")
        self.assertEqual(confirmed.status_code, status.HTTP_200_OK, confirmed.data)
        order.refresh_from_db()
        self.assertNotEqual(order.quote_id, self.quote.id)
        self.assertEqual(order.quote.parent_quote_id, self.quote.id)
        self.assertEqual(order.quote.status, "accepted")
        self.assertEqual(Quote.objects.count(), 2)

        repeated = self.client.post(f"/api/orders/{order.id}/confirm/", {}, format="json")
        self.assertEqual(repeated.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Quote.objects.count(), 2)
        self.assertTrue(PaymentPlan.objects.filter(order=order).exists())

        failed = self.create_draft(order_no="SO-LIFECYCLE-ROLLBACK")
        failed_order = Order.objects.get(pk=failed.data["id"])
        with patch("crm.services.order_lifecycle.allocate_order", side_effect=ValidationError("reservation failed")):
            response = self.client.post(f"/api/orders/{failed_order.id}/confirm/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        failed_order.refresh_from_db()
        self.assertEqual(failed_order.status, "draft")
        self.assertEqual(failed_order.quote_id, self.quote.id)
        self.assertFalse(PaymentPlan.objects.filter(order=failed_order).exists())

    def test_order_state_actions_patch_delete_and_cancel_guards(self):
        created = self.create_draft()
        order = Order.objects.get(pk=created.data["id"])
        self.assertEqual(self.client.patch(f"/api/orders/{order.id}/", {"status": "confirmed"}, format="json").status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.client.post(f"/api/orders/{order.id}/start-production/", {}, format="json").status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.client.delete(f"/api/orders/{order.id}/").status_code, status.HTTP_204_NO_CONTENT)

        InventoryMovement.objects.create(movement_no="IN-LIFECYCLE-CANCEL", movement_date=self.day, type="adjust_in", sku=self.sku, quantity="2")
        order = Order.objects.get(pk=self.create_draft(order_no="SO-LIFECYCLE-CANCEL").data["id"])
        self.assertEqual(self.client.post(f"/api/orders/{order.id}/confirm/", {}, format="json").status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.post(f"/api/orders/{order.id}/start-production/", {}, format="json").status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.delete(f"/api/orders/{order.id}/").status_code, status.HTTP_400_BAD_REQUEST)
        cancelled = self.client.post(f"/api/orders/{order.id}/cancel/", {"reason": "客户取消需求"}, format="json")
        self.assertEqual(cancelled.status_code, status.HTTP_200_OK, cancelled.data)
        order.refresh_from_db()
        self.assertEqual(order.status, "cancelled")
        self.assertEqual(order.cancellation_reason, "客户取消需求")
        self.assertIsNotNone(order.cancelled_at)
        self.assertFalse(InventoryReservation.objects.filter(order_item__order=order).exists())
        self.assertTrue(all(plan.status == "cancelled" for plan in order.payment_plans.all()))

    def test_purchase_draft_place_cancel_and_guards(self):
        supplier = Supplier.objects.create(code="LC", name="Lifecycle Supplier")
        payload = {
            "purchase_no": "PO-LIFECYCLE-1", "supplier": supplier.id, "order_date": self.day.isoformat(),
            "currency": "USD", "exchange_rate": "1", "items": [{"sku": self.sku.id, "quantity": "2", "unit_price": "4"}],
        }
        created = self.client.post("/api/purchase-orders/", payload, format="json")
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        purchase_id = created.data["id"]
        self.assertEqual(created.data["status"], "draft")
        self.assertFalse(PaymentPlan.objects.filter(purchase_order_id=purchase_id).exists())
        self.assertEqual(self.client.post(f"/api/purchase-orders/{purchase_id}/receive/", {}, format="json").status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.client.post(f"/api/purchase-orders/{purchase_id}/place/", {}, format="json").status_code, status.HTTP_200_OK)
        self.assertTrue(PaymentPlan.objects.filter(purchase_order_id=purchase_id).exists())
        self.assertEqual(self.client.post(f"/api/purchase-orders/{purchase_id}/place/", {}, format="json").status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.client.delete(f"/api/purchase-orders/{purchase_id}/").status_code, status.HTTP_400_BAD_REQUEST)
        cancelled = self.client.post(f"/api/purchase-orders/{purchase_id}/cancel/", {"reason": "供应商停止供货"}, format="json")
        self.assertEqual(cancelled.status_code, status.HTTP_200_OK, cancelled.data)
        self.assertEqual(cancelled.data["status"], "cancelled")
        self.assertTrue(all(plan.status == "cancelled" for plan in PaymentPlan.objects.filter(purchase_order_id=purchase_id)))

    def test_purchase_cancel_rejects_confirmed_payment_history(self):
        supplier = Supplier.objects.create(code="LH", name="Lifecycle History Supplier")
        purchase = self.client.post("/api/purchase-orders/", {
            "purchase_no": "PO-LIFECYCLE-HISTORY", "supplier": supplier.id, "order_date": self.day.isoformat(),
            "currency": "USD", "exchange_rate": "1", "items": [{"sku": self.sku.id, "quantity": "2", "unit_price": "4"}],
        }, format="json")
        self.assertEqual(purchase.status_code, status.HTTP_201_CREATED, purchase.data)
        self.assertEqual(self.client.post(f"/api/purchase-orders/{purchase.data['id']}/place/", {}, format="json").status_code, status.HTTP_200_OK)
        purchase_plan = PaymentPlan.objects.filter(purchase_order_id=purchase.data["id"]).first()
        Transaction.objects.create(
            transaction_no="TX-LIFECYCLE-HISTORY", transaction_date=self.day, direction="expense", category="供应商付款",
            amount="1", currency="USD", exchange_rate="1", supplier=supplier, purchase_order_id=purchase.data["id"], plan=purchase_plan,
        )
        response = self.client.post(f"/api/purchase-orders/{purchase.data['id']}/cancel/", {"reason": "不应取消"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
