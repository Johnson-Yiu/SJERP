from datetime import date
from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from crm.models import Product, SKU, Supplier, PurchaseOrder, Transaction

class PurchaseSafetyTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.supplier = Supplier.objects.create(code="RB", name="R0B1 UAT Supplier")
        self.sku = SKU.objects.create(sku="R0B1", product=Product.objects.create(code="R0B1", name="Safety sample"))

    def payload(self, currency="USD", rate="7"):
        return {"supplier": self.supplier.pk, "order_date": date.today().isoformat(), "currency": currency, "exchange_rate": rate, "items": [{"sku": self.sku.pk, "quantity": "1", "unit_price": "10"}]}

    def test_purchase_invalid_exchange_rates_return_400(self):
        for currency, rate in (("CNY", "7"), ("USD", "0"), ("EUR", "-1"), ("GBP", "0")):
            with self.subTest(currency=currency, rate=rate):
                result = self.client.post("/api/purchase-orders/", self.payload(currency, rate), format="json")
                self.assertEqual(result.status_code, 400, result.data)
                self.assertIn("exchange_rate", result.data)
        valid = self.client.post("/api/purchase-orders/", self.payload("CNY", "1"), format="json")
        self.assertEqual(valid.status_code, 201, valid.data)
        patched = self.client.patch(f"/api/purchase-orders/{valid.data['id']}/", {"exchange_rate": "2"}, format="json")
        self.assertEqual(patched.status_code, 400, patched.data)

    def test_actual_payment_rate_belongs_to_transaction_not_contract(self):
        for currency, contract_rate, actual_rate in (("USD", "7", "7.45"), ("CNY", "1", "1")):
            with self.subTest(currency=currency):
                result = self.client.post("/api/purchase-orders/", self.payload(currency, contract_rate), format="json")
                self.assertEqual(result.status_code, 201, result.data)
                pk = result.data["id"]
                placed = self.client.post(f"/api/purchase-orders/{pk}/place/")
                self.assertEqual(placed.status_code, 200, placed.data)
                paid = self.client.post(f"/api/purchase-orders/{pk}/pay/", {"transaction_date": date.today().isoformat(), "amount": "1", "currency": currency, "exchange_rate": actual_rate}, format="json", HTTP_IDEMPOTENCY_KEY=f"payment-{pk}")
                self.assertEqual(paid.status_code, 201, paid.data)
                self.assertEqual(Transaction.objects.get(pk=paid.data["id"]).exchange_rate, Decimal(actual_rate))
                self.assertEqual(PurchaseOrder.objects.get(pk=pk).exchange_rate, Decimal(contract_rate))

    def test_zero_price_purchase_remains_legal_to_create_and_place(self):
        data = self.payload("CNY", "1")
        data["items"][0]["unit_price"] = "0"
        created = self.client.post("/api/purchase-orders/", data, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        placed = self.client.post(f"/api/purchase-orders/{created.data['id']}/place/")
        self.assertEqual(placed.status_code, 200, placed.data)
        self.assertEqual(PurchaseOrder.objects.get(pk=created.data["id"]).items.get().unit_price, Decimal("0"))
