from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from crm.models import Customer, Order, PackagingTemplate, Product, Quote, SKU, Shipment, ShipmentPackage, SKUPackagingProfile
from crm.services.packaging import copy_estimated_to_actual, generate_packing_plan, resolve_packaging


class PackagingDomainTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.product = Product.objects.create(code="P-PACK", name="Packaging Light")
        self.sku = SKU.objects.create(product=self.product, sku="SKU-PACK")
        self.template = PackagingTemplate.objects.create(code="CTN-50", name="50 pcs carton", carton_length="50", carton_width="40", carton_height="30", qty_per_carton="50", carton_tare_weight="1.5")

    def test_template_cbm_and_profile_override_resolution(self):
        self.assertEqual(self.template.cbm, Decimal("0.060000"))
        profile = SKUPackagingProfile.objects.create(sku=self.sku, packaging_template=self.template, unit_net_weight="0.2", qty_per_carton_override="40")
        resolved = resolve_packaging(self.sku)
        self.assertEqual(resolved.qty_per_carton, Decimal("40"))
        self.assertEqual(resolved.status, "COMPLETE")
        self.assertEqual(profile.packaging_template, self.template)

    def test_not_configured_and_partial_status(self):
        self.assertEqual(resolve_packaging(self.sku).status, "NOT_CONFIGURED")
        SKUPackagingProfile.objects.create(sku=self.sku, unit_net_weight="0.2")
        self.assertEqual(resolve_packaging(self.sku).status, "PARTIAL")

    def test_same_carton_repack_and_manual_tail_rules_and_snapshot(self):
        customer = Customer.objects.create(code="C-PACK", name="Packing Buyer")
        quote = Quote.objects.create(quote_no="QT-PACK", customer=customer, quote_date=date.today())
        quote.items.create(sku=self.sku, quantity="120", unit_price="1")
        SKUPackagingProfile.objects.create(sku=self.sku, packaging_template=self.template, unit_net_weight="0.2")
        plan = generate_packing_plan(quote)
        self.assertEqual(plan.total_cartons, 3)
        self.assertTrue(plan.cartons.last().is_partial)
        self.template.qty_per_carton = "40"; self.template.save()
        self.assertEqual(plan.cartons.first().qty_per_carton_snapshot, Decimal("50"))
        self.template.qty_per_carton = "50"
        self.template.partial_carton_policy = "REPACK"; self.template.save()
        plan = generate_packing_plan(quote)
        self.assertTrue(plan.cartons.last().requires_confirmation)
        self.template.partial_carton_policy = "MANUAL"; self.template.save()
        quote.items.update(quantity="120")
        plan = generate_packing_plan(quote)
        self.assertEqual(plan.total_cartons, 2)
        self.assertTrue(plan.warnings)

    def test_order_tail_goods_policy_overrides_sku_template_policy(self):
        customer = Customer.objects.create(code="C-ORDER-PACK", name="Order Packing Buyer")
        order = Order.objects.create(order_no="SO-POLICY", customer=customer, order_date=date.today(), tail_goods_policy="MANUAL")
        order.items.create(sku=self.sku, quantity="120", unit_price="1")
        SKUPackagingProfile.objects.create(sku=self.sku, packaging_template=self.template, unit_net_weight="0.2")

        plan = generate_packing_plan(order)
        self.assertEqual(plan.total_cartons, 2)
        self.assertTrue(plan.warnings)

        order.tail_goods_policy = "REPACK"
        order.save(update_fields=["tail_goods_policy"])
        plan = generate_packing_plan(order)
        self.assertEqual(plan.total_cartons, 3)
        self.assertTrue(plan.cartons.last().requires_confirmation)

    def test_actual_packing_is_independent_and_can_mix_skus(self):
        customer = Customer.objects.create(code="C-ACTUAL", name="Actual Buyer")
        order = Order.objects.create(order_no="SO-PACK", customer=customer, order_date=date.today())
        order.items.create(sku=self.sku, quantity="100", unit_price="1")
        SKUPackagingProfile.objects.create(sku=self.sku, packaging_template=self.template, unit_net_weight="0.2")
        plan = generate_packing_plan(order)
        shipment = Shipment.objects.create(shipment_no="SH-PACK", order=order, shipment_date=date.today())
        copy_estimated_to_actual(shipment, plan)
        package = shipment.packages.first()
        other = SKU.objects.create(product=self.product, sku="SKU-MIX")
        package.items.create(sku=other, quantity="2")
        package.length = "60"; package.save()
        self.assertEqual(SKUPackagingProfile.objects.get(sku=self.sku).packaging_template_id, self.template.id)
        self.assertEqual(package.items.count(), 2)

    def test_shipment_package_api_creates_package_for_current_shipment(self):
        customer = Customer.objects.create(code="C-PACK-API", name="Packing API Buyer")
        order = Order.objects.create(order_no="SO-PACK-API", customer=customer, order_date=date.today())
        shipment = Shipment.objects.create(shipment_no="SH-PACK-API", order=order, shipment_date=date.today())

        response = self.client.post(f"/api/shipments/{shipment.pk}/packages/", {
            "carton_no": 1,
            "length": "50",
            "width": "40",
            "height": "30",
            "actual_net_weight": "10",
            "actual_gross_weight": "11",
            "items": [{"sku": self.sku.pk, "quantity": "10"}],
        }, format="json")

        self.assertEqual(response.status_code, 201, response.data)
        package = ShipmentPackage.objects.get(pk=response.data["id"])
        self.assertEqual(package.shipment, shipment)
