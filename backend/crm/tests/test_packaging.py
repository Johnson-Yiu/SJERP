from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
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
        shipment = Shipment.objects.create(shipment_no="SH-PACK", order=order, shipment_date=date.today(), status="confirmed")
        shipment.items.create(order_item=order.items.get(), sku=self.sku, quantity="100")
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
        shipment = Shipment.objects.create(shipment_no="SH-PACK-API", order=order, shipment_date=date.today(), status="confirmed")
        line = order.items.create(sku=self.sku, quantity="10", unit_price="1")
        shipment.items.create(order_item=line, sku=self.sku, quantity="10")

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

    def test_profile_effective_changes_clear_verification_but_same_value_does_not(self):
        profile = SKUPackagingProfile.objects.create(
            sku=self.sku, packaging_template=self.template, unit_net_weight="0.2",
            verified_at=timezone.now(),
        )
        url = f"/api/sku-packaging-profiles/{profile.pk}/"
        same = self.client.patch(url, {"unit_net_weight": "0.2"}, format="json")
        self.assertEqual(same.status_code, 200, same.data)
        profile.refresh_from_db()
        self.assertIsNotNone(profile.verified_at)

        changed = self.client.patch(url, {"unit_net_weight": "0.3"}, format="json")
        self.assertEqual(changed.status_code, 200, changed.data)
        profile.refresh_from_db()
        self.assertIsNone(profile.verified_at)
        self.assertIsNone(profile.verified_by)

    def test_sku_packaging_save_then_verify_records_final_configuration(self):
        response = self.client.put(f"/api/skus/{self.sku.pk}/packaging/", {
            "packaging_template": self.template.pk,
            "unit_net_weight": "0.4",
            "verify": True,
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        profile = SKUPackagingProfile.objects.get(sku=self.sku)
        self.assertEqual(profile.unit_net_weight, Decimal("0.4"))
        self.assertIsNotNone(profile.verified_at)

    def test_sku_packaging_template_and_overrides_persist_across_detail_reads(self):
        saved = self.client.put(f"/api/skus/{self.sku.pk}/packaging/", {
            "packaging_template": self.template.pk,
            "qty_per_carton_override": "10",
            "unit_net_weight": "0.500",
        }, format="json")

        self.assertEqual(saved.status_code, 200, saved.data)
        sku_detail = self.client.get(f"/api/skus/{self.sku.pk}/")
        packaging_detail = self.client.get(f"/api/skus/{self.sku.pk}/packaging/")
        template_detail = self.client.get(f"/api/packaging-templates/{self.template.pk}/")

        self.assertEqual(sku_detail.status_code, 200, sku_detail.data)
        self.assertEqual(sku_detail.data["packaging"]["template"], self.template.pk)
        self.assertEqual(packaging_detail.data["profile"]["packaging_template"], self.template.pk)
        self.assertEqual(packaging_detail.data["profile"]["qty_per_carton_override"], "10.00")
        self.assertEqual(packaging_detail.data["profile"]["unit_net_weight"], "0.500")
        self.assertEqual(template_detail.data["linked_sku_count"], 1)

        changed = self.client.put(f"/api/skus/{self.sku.pk}/packaging/", {
            "packaging_template": self.template.pk,
            "qty_per_carton_override": "12",
            "unit_net_weight": "0.750",
        }, format="json")
        self.assertEqual(changed.status_code, 200, changed.data)
        packaging_detail = self.client.get(f"/api/skus/{self.sku.pk}/packaging/")
        self.assertEqual(packaging_detail.data["profile"]["packaging_template"], self.template.pk)
        self.assertEqual(packaging_detail.data["profile"]["qty_per_carton_override"], "12.00")
        self.assertEqual(packaging_detail.data["profile"]["unit_net_weight"], "0.750")

    def test_physical_template_update_invalidates_all_profiles_but_name_does_not(self):
        other = SKU.objects.create(product=self.product, sku="SKU-PACK-OTHER")
        first = SKUPackagingProfile.objects.create(sku=self.sku, packaging_template=self.template, verified_at=timezone.now())
        second = SKUPackagingProfile.objects.create(sku=other, packaging_template=self.template, verified_at=timezone.now())
        url = f"/api/packaging-templates/{self.template.pk}/"
        renamed = self.client.patch(url, {"name": "renamed"}, format="json")
        self.assertEqual(renamed.status_code, 200, renamed.data)
        first.refresh_from_db(); second.refresh_from_db()
        self.assertIsNotNone(first.verified_at)
        self.assertIsNotNone(second.verified_at)

        resized = self.client.patch(url, {"carton_length": "55"}, format="json")
        self.assertEqual(resized.status_code, 200, resized.data)
        first.refresh_from_db(); second.refresh_from_db()
        self.assertIsNone(first.verified_at)
        self.assertIsNone(second.verified_at)

    def test_inactive_template_profile_identity_and_numeric_boundaries(self):
        inactive = PackagingTemplate.objects.create(
            code="CTN-INACTIVE", name="Inactive", active=False,
            carton_length="50", carton_width="40", carton_height="30", carton_tare_weight="1",
        )
        rejected = self.client.post("/api/sku-packaging-profiles/", {
            "sku": self.sku.pk, "packaging_template": inactive.pk,
        }, format="json")
        self.assertEqual(rejected.status_code, 400)
        profile = SKUPackagingProfile.objects.create(sku=self.sku, packaging_template=inactive)
        other = SKU.objects.create(product=self.product, sku="SKU-PACK-PROFILE-OTHER")
        profile_url = f"/api/sku-packaging-profiles/{profile.pk}/"
        self.assertEqual(self.client.patch(profile_url, {"sku": other.pk}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(profile_url, {"unit_net_weight": "0.1"}, format="json").status_code, 200)

        for field, value in {
            "qty_per_carton_override": "0",
            "carton_length_override": "0",
            "carton_width_override": "-1",
            "carton_height_override": "0",
            "unit_net_weight": "-0.1",
            "carton_tare_weight_override": "-0.1",
            "gross_weight_override": "-0.1",
        }.items():
            self.assertEqual(self.client.patch(profile_url, {field: value}, format="json").status_code, 400, field)

    def test_linked_template_cannot_be_deleted_and_packing_snapshot_is_stable(self):
        customer = Customer.objects.create(code="C-PACK-SNAPSHOT", name="Packing Snapshot Buyer")
        quote = Quote.objects.create(quote_no="QT-PACK-SNAPSHOT", customer=customer, quote_date=date.today())
        quote.items.create(sku=self.sku, quantity="50", unit_price="1")
        SKUPackagingProfile.objects.create(sku=self.sku, packaging_template=self.template, unit_net_weight="0.2")
        plan = generate_packing_plan(quote)
        carton = plan.cartons.first()
        original_snapshot = dict(carton.packaging_template_snapshot)
        original_dimensions = (carton.length, carton.width, carton.height)
        rejected = self.client.delete(f"/api/packaging-templates/{self.template.pk}/")
        self.assertEqual(rejected.status_code, 400)
        self.assertIn("仍被 SKU 使用", str(rejected.data))

        updated = self.client.patch(f"/api/packaging-templates/{self.template.pk}/", {"carton_length": "60"}, format="json")
        self.assertEqual(updated.status_code, 200, updated.data)
        carton.refresh_from_db()
        self.assertEqual(carton.packaging_template_snapshot, original_snapshot)
        self.assertEqual((carton.length, carton.width, carton.height), original_dimensions)
