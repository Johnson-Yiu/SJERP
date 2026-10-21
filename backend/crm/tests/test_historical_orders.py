from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from crm.models import Customer, GoodsReceipt, InventoryMovement, InventoryReservation, PaymentPlan, Product, PurchaseCostAllocation, PurchaseOrder, Shipment, SKU, Supplier, Transaction


class HistoricalOrderIsolationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(code="HIST-C", name="历史客户", country="中国")
        self.supplier = Supplier.objects.create(code="HS", name="历史供应商", country="中国")
        self.sku = SKU.objects.create(
            sku="HIST-SKU",
            product=Product.objects.create(code="HIST-P", name="历史灯具"),
            unit="pcs",
            cost_price=0,
        )

    def sales_payload(self):
        return {
            "customer": self.customer.pk,
            "order_date": "2019-06-15",
            "currency": "CNY",
            "exchange_rate": "1",
            "items": [{"sku": self.sku.pk, "quantity": "12", "unit_price": "80"}],
        }

    def purchase_payload(self):
        return {
            "supplier": self.supplier.pk,
            "order_date": "2019-05-20",
            "currency": "CNY",
            "exchange_rate": "1",
            "items": [{"sku": self.sku.pk, "quantity": "20", "unit_price": "30"}],
        }

    def test_historical_sales_entry_preserves_date_and_creates_no_formal_side_effects(self):
        response = self.client.post("/api/orders/historical/", self.sales_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        order = self._get_order(response.data["id"])
        self.assertTrue(order.historical_only)
        self.assertEqual(order.status, "historical")
        self.assertEqual(order.order_date, date(2019, 6, 15))
        self.assertEqual(order.total_amount, Decimal("960"))
        self.assertFalse(PaymentPlan.objects.filter(order=order).exists())
        self.assertFalse(InventoryReservation.objects.filter(order_item__order=order).exists())
        self.assertFalse(Transaction.objects.filter(order=order).exists())
        self.assertFalse(Shipment.objects.filter(order=order).exists())
        self.assertFalse(InventoryMovement.objects.filter(order=order).exists())
        self.assertEqual(self.client.get("/api/orders/").data["count"], 0)
        self.assertEqual(self.client.get("/api/orders/", {"status": "historical"}).data["count"], 1)
        self.assertEqual(self.client.post(f"/api/orders/{order.pk}/confirm/", {}, format="json").status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.client.post(f"/api/orders/{order.pk}/generate-purchase-drafts/", {"groups": []}, format="json").status_code, status.HTTP_400_BAD_REQUEST)

    def test_historical_purchase_entry_preserves_date_and_blocks_place_and_payment(self):
        response = self.client.post("/api/purchase-orders/historical/", self.purchase_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        purchase = PurchaseOrder.objects.get(pk=response.data["id"])
        self.assertTrue(purchase.historical_only)
        self.assertEqual(purchase.status, "historical")
        self.assertEqual(purchase.order_date, date(2019, 5, 20))
        self.assertFalse(PaymentPlan.objects.filter(purchase_order=purchase).exists())
        self.assertFalse(Transaction.objects.filter(purchase_order=purchase).exists())
        self.assertFalse(GoodsReceipt.objects.filter(purchase_item__purchase_order=purchase).exists())
        self.assertFalse(InventoryMovement.objects.filter(reference=purchase.purchase_no).exists())
        self.assertFalse(PurchaseCostAllocation.objects.filter(purchase_item__purchase_order=purchase).exists())
        self.assertEqual(self.client.get("/api/purchase-orders/").data["count"], 0)
        self.assertEqual(self.client.get("/api/purchase-orders/", {"status": "historical"}).data["count"], 1)
        self.assertEqual(self.client.post(f"/api/purchase-orders/{purchase.pk}/place/", {}, format="json").status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.client.post(f"/api/purchase-orders/{purchase.pk}/pay/", {"amount": "1", "transaction_date": "2019-05-20"}, format="json").status_code, status.HTTP_400_BAD_REQUEST)

    def test_historical_mode_cannot_be_smuggled_through_formal_create_endpoints(self):
        self.assertEqual(self.client.post("/api/orders/", {**self.sales_payload(), "is_historical": True}, format="json").status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.client.post("/api/purchase-orders/", {**self.purchase_payload(), "status": "historical"}, format="json").status_code, status.HTTP_400_BAD_REQUEST)

    def test_formal_reports_exclude_history_and_separate_analysis_includes_it(self):
        history_response = self.client.post("/api/orders/historical/", self.sales_payload(), format="json")
        self.assertEqual(history_response.status_code, status.HTTP_201_CREATED, history_response.data)
        formal = self._get_order(self.client.post("/api/orders/", {
            **self.sales_payload(), "order_date": "2026-06-15", "items": [{"sku": self.sku.pk, "quantity": "2", "unit_price": "80"}],
        }, format="json").data["id"])
        formal.status = "confirmed"
        formal.save(update_fields=["status"])
        report = self.client.get("/api/reports/data/", {"source": "sales", "group_by": "customer", "date_from": "2019-01-01", "date_to": "2026-12-31"})
        self.assertEqual(report.status_code, status.HTTP_200_OK, report.data)
        self.assertEqual(report.data["totals"]["count"], 1)
        historical = self.client.get("/api/reports/historical/", {"date_from": "2019-01-01", "date_to": "2019-12-31"})
        self.assertEqual(historical.status_code, status.HTTP_200_OK, historical.data)
        self.assertEqual(historical.data["sales"]["order_count"], 1)
        self.assertEqual(historical.data["sales"]["amount_rmb"], Decimal("960"))
        self.assertFalse(historical.data["profit"]["available"])

    def _get_order(self, pk):
        from crm.models import Order
        return Order.objects.get(pk=pk)
