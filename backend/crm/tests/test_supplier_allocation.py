from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from crm.models import Customer, Order, OrderItem, Product, PurchaseOrder, PurchaseOrderItem, SKU, Supplier, SupplierSKU


class SupplierAllocationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        customer = Customer.objects.create(code="C-ALLOC", name="Allocation Buyer")
        self.product = Product.objects.create(code="P-ALLOC", name="Allocation Product")
        self.sku = SKU.objects.create(product=self.product, sku="SKU-ALLOC", display_name_cn="分配测试 SKU")
        self.other_sku = SKU.objects.create(product=self.product, sku="SKU-ALLOC-OTHER", display_name_cn="另一个 SKU")
        self.order = Order.objects.create(order_no="SO-ALLOC", customer=customer, order_date=date(2026, 9, 16), status="confirmed")
        self.item = OrderItem.objects.create(order=self.order, sku=self.sku, quantity=Decimal("100"), unit_price=Decimal("8"))
        self.supplier_a = Supplier.objects.create(name="分配供应商 A", code="AA")
        self.supplier_b = Supplier.objects.create(name="分配供应商 B", code="AB")
        self.source_a = SupplierSKU.objects.create(
            supplier=self.supplier_a, sku=self.sku, supplier_sku_code="AA-SKU-1",
            supplier_model="AA-MODEL-1", purchase_price=Decimal("3.20"), currency="USD",
            moq=Decimal("20"), lead_time_days=7, characteristics={"包装": "10米/卷"},
        )

    def allocation_url(self):
        return f"/api/orders/{self.order.pk}/items/{self.item.pk}/supplier-allocation/"

    def test_candidate_pool_parameter_filters_use_definition_dictionary_keys(self):
        SKU.objects.filter(pk=self.sku.pk).update(parameter_values={"7:voltage": "24V"})
        with patch("crm.sku_management.definitions_for", return_value=[{"category_id": 7, "key": "voltage", "name": "电压"}]):
            response = self.client.get(f"/api/products/{self.product.pk}/supplier-candidate-pool/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["parameter_options"], [{"key": "7:voltage", "name": "电压", "values": ["24V"]}])

    def test_product_candidate_pool_exposes_supplier_source_and_coverage(self):
        response = self.client.get(f"/api/products/{self.product.pk}/supplier-candidate-pool/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["sku_total"], 2)
        self.assertEqual(response.data["with_candidates"], 1)
        row = next(row for row in response.data["rows"] if row["sku_id"] == self.sku.pk)
        self.assertEqual(row["candidate_supplier_count"], 1)
        self.assertTrue(row["candidates"][0]["can_allocate"])
        self.assertEqual(row["candidates"][0]["supplier_skus"][0]["id"], self.source_a.pk)

    def test_order_item_supplier_allocation_snapshots_source_and_purchase_inherits_it(self):
        options = self.client.get(self.allocation_url())
        self.assertEqual(options.status_code, status.HTTP_200_OK, options.data)
        self.assertEqual(options.data["candidates"][0]["recommended_supplier_sku_id"], self.source_a.pk)

        response = self.client.post(
            self.allocation_url(),
            {"supplier_sku": self.source_a.pk, "scope": "recommended", "note": "本次订单按交期优先"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.item.refresh_from_db()
        self.source_a.refresh_from_db()
        self.assertEqual(self.item.supplier_sku_id, self.source_a.pk)
        self.assertEqual(self.item.supplier_name_snapshot, self.supplier_a.name)
        self.assertEqual(self.item.supplier_model_snapshot, "AA-MODEL-1")
        self.assertEqual(self.item.supplier_price_snapshot, Decimal("3.2000"))
        self.assertEqual(self.item.supplier_allocation_scope, "recommended")
        self.assertTrue(self.source_a.is_preferred)

        purchase = self.client.post(
            "/api/purchase-orders/",
            {
                "purchase_no": "PO-ALLOC",
                "supplier": self.supplier_a.pk,
                "order": self.order.pk,
                "order_date": "2026-09-16",
                "status": "ordered",
                "currency": "USD",
                "items": [{"sku": self.sku.pk, "quantity": "100", "unit_price": "3.20"}],
            },
            format="json",
        )
        self.assertEqual(purchase.status_code, status.HTTP_201_CREATED, purchase.data)
        purchase_item = PurchaseOrderItem.objects.get(purchase_order_id=purchase.data["id"])
        self.assertEqual(purchase_item.supplier_sku_id, self.source_a.pk)
        self.assertEqual(purchase_item.supplier_model_snapshot, "AA-MODEL-1")

    def test_legacy_historical_purchase_without_supplier_sku_remains_visible_as_pending_source(self):
        purchase = PurchaseOrder.objects.create(
            purchase_no="PO-ALLOC-HISTORY",
            supplier=self.supplier_b,
            order_date=date(2026, 9, 15),
            status="completed",
            currency="USD",
        )
        PurchaseOrderItem.objects.create(
            purchase_order=purchase,
            sku=self.sku,
            quantity=Decimal("10"),
            unit_price=Decimal("2.80"),
        )

        response = self.client.get(f"/api/products/{self.product.pk}/supplier-candidate-pool/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        row = next(row for row in response.data["rows"] if row["sku_id"] == self.sku.pk)
        legacy_candidate = next(candidate for candidate in row["candidates"] if candidate["supplier"] == self.supplier_b.pk)
        self.assertIn("historical_purchase", legacy_candidate["source_types"])
        self.assertFalse(legacy_candidate["can_allocate"])

    def test_allocation_rejects_wrong_sku_and_completed_order(self):
        wrong_source = SupplierSKU.objects.create(supplier=self.supplier_b, sku=self.other_sku, supplier_sku_code="AB-WRONG")
        response = self.client.post(self.allocation_url(), {"supplier_sku": wrong_source.pk}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.order.status = "completed"
        self.order.save(update_fields=["status", "updated_at"])
        response = self.client.post(self.allocation_url(), {"supplier_sku": self.source_a.pk}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
