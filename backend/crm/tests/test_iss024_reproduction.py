from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from crm.models import (
    Customer,
    CustomerSupplierPreference,
    Order,
    OrderItem,
    Product,
    PurchaseOrder,
    PurchaseOrderItem,
    SKU,
    Supplier,
    SupplierSKU,
)
from crm.services.supplier_allocation import supplier_options


class ISS024RecommendationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.product = Product.objects.create(code="ISS024-P", name="ISS-024 product")
        self.sku = SKU.objects.create(product=self.product, sku="ISS024-SKU", display_name_cn="ISS-024 SKU", cost_price=Decimal("9.00"))
        self.supplier_a = Supplier.objects.create(name="ISS-024 Supplier A", code="IA")
        self.supplier_b = Supplier.objects.create(name="ISS-024 Supplier B", code="IB")
        self.source_a = SupplierSKU.objects.create(
            supplier=self.supplier_a, sku=self.sku, supplier_sku_code="IA-SKU", purchase_price=Decimal("3.00"), is_preferred=True,
        )
        self.source_b = SupplierSKU.objects.create(
            supplier=self.supplier_b, sku=self.sku, supplier_sku_code="IB-SKU", purchase_price=Decimal("2.80"),
        )
        self.customer_a = Customer.objects.create(code="ISS024-A", name="ISS-024 Customer A")
        self.customer_b = Customer.objects.create(code="ISS024-B", name="ISS-024 Customer B")
        self.order_a = Order.objects.create(order_no="ISS024-SO-A", customer=self.customer_a, order_date=date(2026, 10, 1), status="confirmed")
        self.order_b = Order.objects.create(order_no="ISS024-SO-B", customer=self.customer_b, order_date=date(2026, 10, 2), status="confirmed")
        self.item_a = OrderItem.objects.create(order=self.order_a, sku=self.sku, quantity=Decimal("1"), unit_price=Decimal("10"))
        self.item_b = OrderItem.objects.create(order=self.order_b, sku=self.sku, quantity=Decimal("1"), unit_price=Decimal("10"))

    def create_history(self, supplier, source, order, no, price):
        purchase = PurchaseOrder.objects.create(
            purchase_no=no, supplier=supplier, order=order, order_date=date(2026, 10, 3),
            status="completed", currency="USD",
        )
        return PurchaseOrderItem.objects.create(
            purchase_order=purchase, sku=self.sku, supplier_sku=source, quantity=1, unit_price=price,
        )

    def allocation_url(self, order, item):
        return f"/api/orders/{order.pk}/items/{item.pk}/supplier-allocation/"

    def test_customer_history_overrides_global_weak_preference_without_cross_customer_leak(self):
        self.create_history(self.supplier_a, self.source_a, self.order_a, "ISS024-PO-A", Decimal("3.00"))
        self.create_history(self.supplier_b, self.source_b, self.order_b, "ISS024-PO-B", Decimal("2.80"))

        options_a = supplier_options(self.item_a)
        options_b = supplier_options(self.item_b)

        self.assertEqual(options_a[0]["recommended_supplier_sku_id"], self.source_a.pk)
        self.assertEqual(options_a[0]["recommended_source"], "historical_purchase")
        self.assertEqual(options_b[0]["recommended_supplier_sku_id"], self.source_b.pk)
        self.assertEqual(options_b[0]["recommended_source"], "historical_purchase")
        self.assertNotIn("ISS024-SO-A", repr(options_b))
        self.assertNotIn("ISS-024 Customer A", repr(options_b))

    def test_order_only_is_default_and_does_not_create_customer_preference(self):
        response = self.client.post(
            self.allocation_url(self.order_b, self.item_b),
            {"supplier_sku": self.source_b.pk, "scope": "order_only"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(CustomerSupplierPreference.objects.filter(customer=self.customer_b, sku=self.sku).exists())
        self.source_a.refresh_from_db()
        self.assertTrue(self.source_a.is_preferred)

    def test_customer_preferred_updates_only_current_customer_and_keeps_global_source(self):
        response = self.client.post(
            self.allocation_url(self.order_b, self.item_b),
            {"supplier_sku": self.source_b.pk, "scope": "customer_preferred", "note": "客户 B 指定"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        preference = CustomerSupplierPreference.objects.get(customer=self.customer_b, sku=self.sku)
        self.assertEqual(preference.supplier_sku_id, self.source_b.pk)
        self.item_b.refresh_from_db()
        self.assertEqual(self.item_b.supplier_allocation_scope, "customer_preferred")
        self.source_a.refresh_from_db()
        self.assertTrue(self.source_a.is_preferred)
        self.assertEqual(self.client.get(self.allocation_url(self.order_b, self.item_b)).data["recommendation"]["supplier_sku"], self.source_b.pk)
        self.assertEqual(self.client.get(self.allocation_url(self.order_a, self.item_a)).data["recommendation"]["supplier_sku"], self.source_a.pk)

    def test_inactive_customer_preference_warns_and_is_not_recommended(self):
        CustomerSupplierPreference.objects.create(customer=self.customer_b, sku=self.sku, supplier_sku=self.source_b)
        self.source_b.is_active = False
        self.source_b.save(update_fields=["is_active", "updated_at"])

        response = self.client.get(self.allocation_url(self.order_b, self.item_b))

        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("已停用", response.data["recommendation_warning"])
        self.assertNotIn(self.source_b.pk, [row["recommended_supplier_sku_id"] for row in response.data["candidates"]])
        self.assertNotEqual(response.data["recommendation"]["supplier_sku"], self.source_b.pk)

    def test_manual_purchase_without_supplier_sku_does_not_create_permanent_source(self):
        manual_supplier = Supplier.objects.create(name="ISS-024 Manual Supplier", code="IM")
        response = self.client.post(
            "/api/purchase-orders/",
            {
                "exchange_rate": "1", "supplier": manual_supplier.pk, "order": self.order_b.pk,
                "order_date": "2026-10-03", "currency": "USD",
                "items": [{"sku": self.sku.pk, "quantity": "2", "unit_price": "4.50"}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        item = PurchaseOrderItem.objects.get(purchase_order_id=response.data["id"])
        self.assertIsNone(item.supplier_sku_id)
        self.assertEqual(SupplierSKU.objects.count(), 2)
        self.assertEqual(item.unit_price, Decimal("4.500000000000"))
        self.assertEqual(self.sku.cost_price, Decimal("9.00"))
