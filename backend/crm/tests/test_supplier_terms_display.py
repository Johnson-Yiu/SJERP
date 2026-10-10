from copy import deepcopy

from django.test import TestCase

from crm.context import _product_context, _supplier_context
from crm.models import Product, Supplier
from crm.serializers import SupplierSerializer
from crm.supplier_display import payment_terms_summary


class SupplierTermsDisplayTests(TestCase):
    def setUp(self):
        self.config = [
            {"label": "预付款", "ratio": "0.50", "due_basis": "order_date", "offset_days": 0},
            {"label": "尾款", "ratio": "0.50", "due_basis": "expected_arrival_date", "offset_days": 0},
        ]
        self.supplier = Supplier.objects.create(
            name="Display supplier", code="DS", payment_terms="旧说明：30/70",
            payment_terms_config=self.config,
        )

    def test_custom_summary_uses_config_and_preserves_data(self):
        original = deepcopy(self.config)
        self.assertEqual(payment_terms_summary(self.config), "预付款 50% / 尾款 50%")
        self.assertEqual(self.config, original)
        data = SupplierSerializer(self.supplier).data
        self.assertEqual(data["payment_terms_summary"], "预付款 50% / 尾款 50%")
        self.assertEqual(data["payment_terms"], "旧说明：30/70")
        self.assertTrue(SupplierSerializer().fields["payment_terms_summary"].read_only)

    def test_empty_config_displays_system_default(self):
        self.supplier.payment_terms_config = []
        self.assertEqual(SupplierSerializer(self.supplier).data["payment_terms_summary"],
                         "预付款 30% / 尾款 70%（系统默认）")
        self.assertEqual(payment_terms_summary(None), "预付款 30% / 尾款 70%（系统默认）")

    def test_supplier_and_product_context_distinguish_notes_from_rules(self):
        info = dict(_supplier_context(self.supplier.pk)["info"])
        self.assertNotIn("付款条款", info)
        self.assertEqual(info["付款条款说明（备注）"], "旧说明：30/70")
        self.assertEqual(info["系统执行付款规则"], "预付款 50% / 尾款 50%")
        product = Product.objects.create(name="Display product", code="DISPLAY")
        product.suppliers.add(self.supplier)
        section = next(s for s in _product_context(product.pk)["sections"] if s["key"] == "suppliers")
        self.assertIn(["payment_terms", "付款条款说明（备注）"], section["columns"])
        self.assertIn(["payment_terms_summary", "系统执行付款规则"], section["columns"])
        self.assertEqual(section["rows"][0]["payment_terms_summary"], "预付款 50% / 尾款 50%")

    def test_fractional_percent_is_not_rounded(self):
        self.config[0]["ratio"] = "0.12345678901234567890123456789"
        self.config[1]["ratio"] = "0.87654321098765432109876543211"
        self.assertEqual(payment_terms_summary(self.config),
                         "预付款 12.345678901234567890123456789% / 尾款 87.654321098765432109876543211%")
