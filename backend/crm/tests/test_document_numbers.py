from datetime import date
from unittest.mock import patch

from django.test import TestCase
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.test import APIClient

from crm.document_numbers import allocate_document_no
from crm.models import Customer, DocumentNumberSequence, Order, Product, PurchaseOrder, SKU, Supplier
from crm.views import _import_row


class DocumentNumberApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(code="DN-C", name="Document Number Customer")
        self.supplier = Supplier.objects.create(code="DN", name="Document Number Supplier")
        self.sku = SKU.objects.create(
            sku="DN-SKU",
            product=Product.objects.create(code="DN-P", name="Document Number Product"),
            default_price=10,
        )
        self.today = date(2026, 12, 31)

    def order_payload(self, **overrides):
        payload = {
            "customer": self.customer.pk,
            "order_date": "2020-01-01",
            "currency": "USD",
            "exchange_rate": "1",
            "items": [{"sku": self.sku.pk, "quantity": "1", "unit_price": "10"}],
        }
        payload.update(overrides)
        return payload

    def purchase_payload(self, **overrides):
        payload = {
            "supplier": self.supplier.pk,
            "order_date": "2020-01-01",
            "currency": "USD",
            "exchange_rate": "1",
            "items": [{"sku": self.sku.pk, "quantity": "1", "unit_price": "4"}],
        }
        payload.update(overrides)
        return payload

    def create_order(self, **overrides):
        with patch("crm.document_numbers.timezone.localdate", return_value=self.today):
            response = self.client.post("/api/orders/", self.order_payload(**overrides), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return response.data

    def create_purchase(self, **overrides):
        with patch("crm.document_numbers.timezone.localdate", return_value=self.today):
            response = self.client.post("/api/purchase-orders/", self.purchase_payload(**overrides), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return response.data

    def test_order_and_purchase_numbers_are_independent_and_ignore_business_date(self):
        first_order = self.create_order()
        second_order = self.create_order(order_date="2027-01-02")
        purchase = self.create_purchase()

        self.assertEqual(first_order["order_no"], "SO-2026-00001")
        self.assertEqual(second_order["order_no"], "SO-2026-00002")
        self.assertEqual(purchase["purchase_no"], "PO-2026-00001")

    def test_document_numbers_are_immutable_through_lifecycle_and_draft_edits(self):
        order_data = self.create_order()
        order = Order.objects.get(pk=order_data["id"])
        self.assertEqual(self.client.patch(f"/api/orders/{order.pk}/", {"notes": "draft edit"}, format="json").status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.post(f"/api/orders/{order.pk}/confirm/", {}, format="json").status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.post(f"/api/orders/{order.pk}/cancel/", {"reason": "cancel"}, format="json").status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.order_no, order_data["order_no"])

        purchase_data = self.create_purchase()
        purchase = PurchaseOrder.objects.get(pk=purchase_data["id"])
        self.assertEqual(self.client.patch(f"/api/purchase-orders/{purchase.pk}/", {"notes": "draft edit"}, format="json").status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.post(f"/api/purchase-orders/{purchase.pk}/place/", {}, format="json").status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.post(f"/api/purchase-orders/{purchase.pk}/cancel/", {"reason": "cancel"}, format="json").status_code, status.HTTP_200_OK)
        purchase.refresh_from_db()
        self.assertEqual(purchase.purchase_no, purchase_data["purchase_no"])

    def test_api_rejects_explicit_document_numbers_on_create_and_update(self):
        with patch("crm.document_numbers.timezone.localdate", return_value=self.today):
            order_response = self.client.post("/api/orders/", self.order_payload(order_no="HACK"), format="json")
            purchase_response = self.client.post("/api/purchase-orders/", self.purchase_payload(purchase_no="HACK"), format="json")
        self.assertEqual(order_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(purchase_response.status_code, status.HTTP_400_BAD_REQUEST)

        order = self.create_order()
        purchase = self.create_purchase()
        self.assertEqual(self.client.patch(f"/api/orders/{order['id']}/", {"order_no": "HACK"}, format="json").status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.client.patch(f"/api/purchase-orders/{purchase['id']}/", {"purchase_no": "HACK"}, format="json").status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.client.put(f"/api/orders/{order['id']}/", self.order_payload(order_no="HACK"), format="json").status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.client.put(f"/api/purchase-orders/{purchase['id']}/", self.purchase_payload(purchase_no="HACK"), format="json").status_code, status.HTTP_400_BAD_REQUEST)

    def test_deleted_draft_does_not_reuse_number(self):
        order = self.create_order()
        purchase = self.create_purchase()
        self.assertEqual(self.client.delete(f"/api/orders/{order['id']}/").status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.client.delete(f"/api/purchase-orders/{purchase['id']}/").status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.create_order()["order_no"], "SO-2026-00002")
        self.assertEqual(self.create_purchase()["purchase_no"], "PO-2026-00002")

    def test_failed_create_rolls_back_allocated_number(self):
        with patch("crm.serializers.OrderItem.objects.bulk_create", side_effect=RuntimeError("fail")):
            with patch("crm.document_numbers.timezone.localdate", return_value=self.today):
                with self.assertRaises(RuntimeError):
                    self.client.post("/api/orders/", self.order_payload(), format="json")
        self.assertFalse(DocumentNumberSequence.objects.filter(document_type="SO", year=2026).exists())
        self.assertEqual(self.create_order()["order_no"], "SO-2026-00001")

        with patch("crm.serializers.PurchaseOrderItem.objects.bulk_create", side_effect=RuntimeError("fail")):
            with patch("crm.document_numbers.timezone.localdate", return_value=self.today):
                with self.assertRaises(RuntimeError):
                    self.client.post("/api/purchase-orders/", self.purchase_payload(), format="json")
        self.assertFalse(DocumentNumberSequence.objects.filter(document_type="PO", year=2026).exists())
        self.assertEqual(self.create_purchase()["purchase_no"], "PO-2026-00001")

    def test_lazy_initialization_respects_matching_history_but_ignores_legacy_format(self):
        Order.objects.create(order_no="SO-2026-00008", customer=self.customer, order_date=self.today)
        PurchaseOrder.objects.create(purchase_no="PO-20261231-121212", supplier=self.supplier, order_date=self.today)

        self.assertEqual(self.create_order()["order_no"], "SO-2026-00009")
        self.assertEqual(self.create_purchase()["purchase_no"], "PO-2026-00001")

    def test_year_changes_reset_each_document_type_sequence(self):
        with patch("crm.document_numbers.timezone.localdate", return_value=date(2026, 12, 31)):
            self.assertEqual(allocate_document_no("SO"), "SO-2026-00001")
            self.assertEqual(allocate_document_no("PO"), "PO-2026-00001")
        with patch("crm.document_numbers.timezone.localdate", return_value=date(2027, 1, 1)):
            self.assertEqual(allocate_document_no("SO"), "SO-2027-00001")
            self.assertEqual(allocate_document_no("PO"), "PO-2027-00001")

    def test_sequence_stops_at_five_digit_limit(self):
        DocumentNumberSequence.objects.create(document_type="SO", year=2026, last_value=99999)
        with self.assertRaisesMessage(ValidationError, "2026 年销售订单编号已超过 99999"):
            allocate_document_no("SO", year=2026)


class DocumentNumberImportTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(code="DI-C", name="Document Import Customer")
        self.sku = SKU.objects.create(
            sku="DI-SKU",
            product=Product.objects.create(code="DI-P", name="Document Import Product"),
            default_price=10,
        )
        self.today = date(2026, 12, 31)

    def create_order(self):
        with patch("crm.document_numbers.timezone.localdate", return_value=self.today):
            response = self.client.post(
                "/api/orders/",
                {
                    "customer": self.customer.pk,
                    "order_date": "2020-01-01",
                    "currency": "USD",
                    "exchange_rate": "1",
                    "items": [{"sku": self.sku.pk, "quantity": "1", "unit_price": "10"}],
                },
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return response.data

    def import_order(self, order_no):
        return _import_row(
            "orders",
            {
                "order_no": order_no,
                "customer_code": self.customer.code,
                "order_date": "2020-01-01",
                "status": "draft",
                "currency": "USD",
                "exchange_rate": "1",
                "notes": "",
            },
        )

    def test_imported_larger_formal_number_advances_sequence_and_next_api_order(self):
        DocumentNumberSequence.objects.create(document_type="SO", year=2026, last_value=10)

        self.assertTrue(self.import_order("SO-2026-00050"))
        self.assertTrue(Order.objects.filter(order_no="SO-2026-00050").exists())
        self.assertEqual(DocumentNumberSequence.objects.get(document_type="SO", year=2026).last_value, 50)
        self.assertEqual(self.create_order()["order_no"], "SO-2026-00051")

    def test_imported_smaller_formal_number_does_not_move_sequence_backward(self):
        DocumentNumberSequence.objects.create(document_type="SO", year=2026, last_value=50)

        self.assertTrue(self.import_order("SO-2026-00020"))
        self.assertEqual(DocumentNumberSequence.objects.get(document_type="SO", year=2026).last_value, 50)
        self.assertEqual(self.create_order()["order_no"], "SO-2026-00051")

    def test_legacy_imported_number_does_not_affect_sequence(self):
        DocumentNumberSequence.objects.create(document_type="SO", year=2026, last_value=10)

        self.assertTrue(self.import_order("LEGACY-SO-1001"))
        self.assertTrue(Order.objects.filter(order_no="LEGACY-SO-1001").exists())
        self.assertEqual(DocumentNumberSequence.objects.get(document_type="SO", year=2026).last_value, 10)

    def test_imported_formal_number_initializes_missing_sequence(self):
        self.assertTrue(self.import_order("SO-2026-00008"))
        self.assertGreaterEqual(DocumentNumberSequence.objects.get(document_type="SO", year=2026).last_value, 8)
        self.assertEqual(self.create_order()["order_no"], "SO-2026-00009")

    def test_failed_import_rolls_back_sequence_sync(self):
        DocumentNumberSequence.objects.create(document_type="SO", year=2031, last_value=49)

        with patch.object(Order.objects, "update_or_create", side_effect=RuntimeError("order save failed")):
            with self.assertRaisesMessage(RuntimeError, "order save failed"):
                self.import_order("SO-2031-00050")

        self.assertFalse(Order.objects.filter(order_no="SO-2031-00050").exists())
        self.assertEqual(DocumentNumberSequence.objects.get(document_type="SO", year=2031).last_value, 49)
