from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from crm.models import Customer, Order, OrderItem, Product, SKU, Supplier, SupplierSKU
from crm.serializers import SupplierSKUSerializer
from crm.services.sku_costs import verification_state


class SkuCostVerificationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(username="sku-cost-reviewer", password="test-password")
        self.product = Product.objects.create(code="P-COST-R1", name="成本核实灯具")
        self.supplier_a = Supplier.objects.create(code="CA", name="成本供应商 A")
        self.supplier_b = Supplier.objects.create(code="CB", name="成本供应商 B")

    def make_sku(self, code="SKU-COST-R1", **overrides):
        values = {
            "product": self.product,
            "sku": code,
            "display_name_cn": f"成本核实 {code}",
            "sales_model": f"COST-{code}",
            "cost_price": Decimal("10.0000"),
            "cost_currency": "USD",
        }
        values.update(overrides)
        return SKU.objects.create(**values)

    def make_source(self, sku, supplier, code, **overrides):
        values = {
            "sku": sku,
            "supplier": supplier,
            "supplier_sku_code": code,
            "purchase_price": Decimal("8.0000"),
            "currency": "USD",
        }
        values.update(overrides)
        return SupplierSKU.objects.create(**values)

    def authenticate(self):
        self.client.force_authenticate(self.user)

    def test_new_sku_defaults_cost_currency_but_legacy_unknown_remains_unknown(self):
        created = SKU.objects.create(product=self.product, sku="SKU-COST-R1-NEW", display_name_cn="新建成本 SKU")
        self.assertEqual(created.cost_currency, "CNY")

        SKU.objects.filter(pk=created.pk).update(cost_currency=None)
        created.refresh_from_db()
        created.description_en = "unchanged cost meaning"
        created.save(update_fields=["description_en", "updated_at"])
        created.refresh_from_db()
        self.assertIsNone(created.cost_currency)

    def test_cost_verification_is_server_owned_and_price_or_currency_change_invalidates(self):
        sku = self.make_sku()
        self.authenticate()

        verified = self.client.post(f"/api/skus/{sku.pk}/verify-cost/", {}, format="json")
        self.assertEqual(verified.status_code, 200, verified.data)
        sku.refresh_from_db()
        self.assertIsNotNone(sku.cost_verified_at)
        self.assertEqual(sku.cost_verified_by_id, self.user.pk)

        verified_at = sku.cost_verified_at
        sku.description_en = "unrelated description change"
        sku.save(update_fields=["description_en", "updated_at"])
        sku.refresh_from_db()
        self.assertEqual(sku.cost_verified_at, verified_at)

        sku.cost_price = Decimal("11.0000")
        sku.save(update_fields=["cost_price", "updated_at"])
        sku.refresh_from_db()
        self.assertIsNone(sku.cost_verified_at)
        self.assertIsNone(sku.cost_verified_by_id)

        self.assertEqual(self.client.post(f"/api/skus/{sku.pk}/verify-cost/", {}, format="json").status_code, 200)
        sku.refresh_from_db()
        sku.cost_currency = "CNY"
        sku.save(update_fields=["cost_currency", "updated_at"])
        sku.refresh_from_db()
        self.assertIsNone(sku.cost_verified_at)
        self.assertIsNone(sku.cost_verified_by_id)

    def test_invalid_sku_cost_cannot_be_verified_or_overwrite_previous_verification(self):
        sku = self.make_sku()
        self.authenticate()
        self.assertEqual(self.client.post(f"/api/skus/{sku.pk}/verify-cost/", {}, format="json").status_code, 200)
        sku.refresh_from_db()
        verified_at = sku.cost_verified_at
        SKU.objects.filter(pk=sku.pk).update(cost_price=0, cost_currency=None)

        response = self.client.post(f"/api/skus/{sku.pk}/verify-cost/", {}, format="json")

        self.assertEqual(response.status_code, 400)
        sku.refresh_from_db()
        self.assertEqual(sku.cost_verified_at, verified_at)
        self.assertEqual(sku.cost_verified_by_id, self.user.pk)

    def test_supplier_price_verification_is_independent_per_source(self):
        sku = self.make_sku()
        first = self.make_source(sku, self.supplier_a, "SOURCE-A")
        second = self.make_source(sku, self.supplier_b, "SOURCE-B")
        self.authenticate()

        response = self.client.post(f"/api/supplier-skus/{first.pk}/verify-price/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.purchase_price_verified_by_id, self.user.pk)
        self.assertIsNone(second.purchase_price_verified_at)

        verified_at = first.purchase_price_verified_at
        first.remarks = "unrelated supplier note"
        first.save(update_fields=["remarks", "updated_at"])
        first.refresh_from_db()
        self.assertEqual(first.purchase_price_verified_at, verified_at)

        first.currency = "CNY"
        first.save(update_fields=["currency", "updated_at"])
        first.refresh_from_db()
        self.assertIsNone(first.purchase_price_verified_at)

        self.assertEqual(self.client.post(f"/api/supplier-skus/{second.pk}/verify-price/", {}, format="json").status_code, 200)
        second.refresh_from_db()
        self.assertIsNotNone(second.purchase_price_verified_at)
        second.purchase_price = Decimal("9.0000")
        second.save(update_fields=["purchase_price", "updated_at"])
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertIsNone(first.purchase_price_verified_at)
        self.assertIsNone(second.purchase_price_verified_at)

    def test_invalid_supplier_price_cannot_be_verified_or_overwrite_previous_verification(self):
        sku = self.make_sku()
        source = self.make_source(sku, self.supplier_a, "SOURCE-INVALID")
        self.authenticate()
        self.assertEqual(self.client.post(f"/api/supplier-skus/{source.pk}/verify-price/", {}, format="json").status_code, 200)
        source.refresh_from_db()
        verified_at = source.purchase_price_verified_at
        SupplierSKU.objects.filter(pk=source.pk).update(purchase_price=0, currency="")

        response = self.client.post(f"/api/supplier-skus/{source.pk}/verify-price/", {}, format="json")

        self.assertEqual(response.status_code, 400)
        source.refresh_from_db()
        self.assertEqual(source.purchase_price_verified_at, verified_at)
        self.assertEqual(source.purchase_price_verified_by_id, self.user.pk)

    def test_order_cost_currency_snapshot_is_stable_and_unknown_is_blank(self):
        customer = Customer.objects.create(code="C-COST-R1", name="成本快照客户")
        sku = self.make_sku(cost_currency="CNY")
        order = Order.objects.create(order_no="SO-COST-R1", customer=customer, order_date="2026-10-19")
        item = OrderItem.objects.create(order=order, sku=sku, quantity=1, unit_price=20)
        self.assertEqual(item.cost_currency_snapshot, "CNY")

        unknown = self.make_sku(code="SKU-COST-R1-UNKNOWN")
        SKU.objects.filter(pk=unknown.pk).update(cost_currency=None)
        unknown.refresh_from_db()
        unknown_item = OrderItem.objects.create(order=order, sku=unknown, quantity=1, unit_price=20)
        self.assertEqual(unknown_item.cost_currency_snapshot, "")

    def test_risk_preview_reports_state_without_cost_amounts(self):
        missing = self.make_sku(code="SKU-RISK-MISSING", sales_model=None, cost_price=0, cost_currency=None)
        unverified = self.make_sku(code="SKU-RISK-UNVERIFIED")
        self.make_source(unverified, self.supplier_a, "SOURCE-RISK")
        self.authenticate()

        response = self.client.get(
            "/api/quotes/risk-preview/",
            {"sku_ids": f"{missing.pk},{unverified.pk}"},
        )
        self.assertEqual(response.status_code, 200, response.data)
        rows = {row["sku"]: row for row in response.data["items"]}
        self.assertIn("missing_sales_model", rows[missing.pk]["risk_codes"])
        self.assertIn("missing_supplier_source", rows[missing.pk]["risk_codes"])
        self.assertIn("missing_reference_cost", rows[missing.pk]["risk_codes"])
        self.assertIn("cost_unverified", rows[unverified.pk]["risk_codes"])
        self.assertIn("supplier_price_unverified", rows[unverified.pk]["risk_codes"])
        for row in response.data["items"]:
            self.assertNotIn("cost_price", row)
            self.assertNotIn("purchase_price", row)
            self.assertNotIn("cost_currency", row)

    def test_ordinary_order_api_cannot_inject_cost_currency_or_verification(self):
        self.authenticate()
        customer = Customer.objects.create(code="C-INJECT", name="成本字段测试客户")
        for sales_currency, cost_currency in (("USD", "CNY"), ("CNY", "USD"), ("USD", "EUR"), ("USD", None)):
            with self.subTest(sales_currency=sales_currency, cost_currency=cost_currency):
                sku = self.make_sku(code="INJECT-" + str(cost_currency), currency=sales_currency)
                SKU.objects.filter(pk=sku.pk).update(cost_currency=cost_currency)
                result = self.client.post("/api/orders/", {"customer": customer.pk, "order_date": "2026-10-19",
                    "currency": sales_currency, "exchange_rate": "1" if sales_currency == "CNY" else "7.2",
                    "items": [{"sku": sku.pk, "quantity": 1, "unit_price": "20", "cost_price": "10",
                               "cost_currency_snapshot": "GBP", "cost_verification_snapshot": "current"}]}, format="json")
                self.assertEqual(result.status_code, 201, result.data)
                item = OrderItem.objects.get(order_id=result.data["id"])
                self.assertEqual(item.cost_currency_snapshot, cost_currency or "")
                self.assertEqual(item.cost_verification_snapshot, "unverified" if cost_currency else "missing")

    @override_settings(APP_STAGE="production", DEBUG=False, DEVELOPMENT_SUPERADMIN=False, RBAC_ENFORCEMENT=True)
    def test_supplier_cost_serializer_hides_price_currency_without_purchase_view(self):
        sku = self.make_sku()
        source = self.make_source(sku, self.supplier_a, "SOURCE-HIDDEN")
        request = RequestFactory().get("/api/supplier-skus/")
        request.user = AnonymousUser()
        data = SupplierSKUSerializer(source, context={"request": request}).data
        self.assertIsNone(data["purchase_price"])
        self.assertIsNone(data["currency"])
        self.assertEqual(data["purchase_price_verified_by_name"], "")

    def test_verification_state_uses_ninety_day_warning_only(self):
        now = timezone.now()
        self.assertEqual(verification_state(Decimal("1"), "USD", now), "current")
        self.assertEqual(verification_state(Decimal("1"), "USD", now - timedelta(days=91)), "expired")
        self.assertEqual(verification_state(Decimal("0"), "USD", now), "missing")
        self.assertEqual(verification_state(Decimal("1"), "", now), "missing")
