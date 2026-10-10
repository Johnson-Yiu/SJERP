from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient
from crm.models import Product, SKU, SKUVersion, PackagingTemplate, SKUPackagingProfile
from crm.serializers import SKUSerializer


class SKUAtomicPackagingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.product = Product.objects.create(code="ATOMIC", name="Atomic light")
        self.template = PackagingTemplate.objects.create(code="ATOMIC-CARTON", name="Carton", carton_length=50, carton_width=40, carton_height=30, qty_per_carton=50)

    def payload(self, index=1, qty=50):
        return {"product": self.product.pk, "sales_model": f"ATOMIC-{index}", "display_name_cn": f"Atomic {index}", "packaging_profile_input": {"packaging_template": self.template.pk, "qty_per_carton_override": qty, "unit_net_weight": "0.15"}}

    def create(self):
        response = self.client.post("/api/skus/", self.payload(), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return SKU.objects.get(pk=response.data["id"])

    def test_create_valid_and_invalid(self):
        self.assertEqual(self.client.post("/api/skus/", self.payload(qty=0), format="json").status_code, 400)
        self.assertFalse(SKU.objects.exists())
        sku = self.create()
        self.assertEqual(sku.packaging_profile.qty_per_carton_override, 50)
        self.assertEqual(sku.packaging_profile.unit_net_weight, Decimal("0.15"))

    def test_edit_invalid_rolls_back_then_valid_updates_both(self):
        sku = self.create()
        data = {"description_cn": "Updated", "packaging_profile_input": self.payload(qty=0)["packaging_profile_input"]}
        response = self.client.patch(f"/api/skus/{sku.pk}/", data, format="json")
        self.assertEqual(response.status_code, 400)
        sku.refresh_from_db()
        self.assertEqual(sku.description_cn, "Atomic light")
        self.assertEqual(sku.packaging_profile.qty_per_carton_override, 50)
        self.assertFalse(SKUVersion.objects.exists())
        data["packaging_profile_input"]["qty_per_carton_override"] = 40
        self.assertEqual(self.client.patch(f"/api/skus/{sku.pk}/", data, format="json").status_code, 200)
        sku.refresh_from_db()
        self.assertEqual(sku.description_cn, "Updated")
        self.assertEqual(sku.packaging_profile.qty_per_carton_override, 40)
        self.assertEqual(sku.versions.count(), 1)

    def test_batch_invalid_third_rolls_back_and_valid_maps_profiles(self):
        items = [self.payload(i, 0 if i == 3 else 50+i) for i in range(1, 4)]
        self.assertEqual(self.client.post("/api/skus/batch-create/", {"items": items}, format="json").status_code, 400)
        self.assertFalse(SKU.objects.exists())
        self.assertFalse(SKUPackagingProfile.objects.exists())
        items[2]["packaging_profile_input"]["qty_per_carton_override"] = 53
        response = self.client.post("/api/skus/batch-create/", {"items": items}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        for index, row in enumerate(response.data, 1):
            self.assertEqual(SKU.objects.get(pk=row["id"]).packaging_profile.qty_per_carton_override, 50+index)

    def test_omitted_or_null_keeps_profile(self):
        sku = self.create()
        for data in ({"description_cn": "Change"}, {"packaging_profile_input": None}):
            self.assertEqual(self.client.patch(f"/api/skus/{sku.pk}/", data, format="json").status_code, 200)
            self.assertEqual(SKUPackagingProfile.objects.get(sku=sku).qty_per_carton_override, 50)

    def test_disabled_template_cannot_new_bind(self):
        self.template.active = False
        self.template.save()
        self.assertEqual(self.client.post("/api/skus/", self.payload(), format="json").status_code, 400)
        self.assertFalse(SKU.objects.exists())
        sku = SKU.objects.create(product=self.product, sku="ATOMIC-OLD")
        self.assertEqual(self.client.patch(f"/api/skus/{sku.pk}/", {"description_cn": "Bad", "packaging_profile_input": self.payload()["packaging_profile_input"]}, format="json").status_code, 400)
        sku.refresh_from_db()
        self.assertEqual(sku.description_cn, "Atomic light")
        self.assertFalse(sku.versions.exists())

    def test_late_profile_failure_rolls_back_sku_and_version(self):
        sku = self.create()
        serializer = SKUSerializer(sku, data={"description_cn": "Late failure", "packaging_profile_input": self.payload()["packaging_profile_input"]}, partial=True)
        serializer.is_valid(raise_exception=True)
        with patch("crm.serializers.SKUPackagingProfileSerializer.save", side_effect=RuntimeError("write failed")):
            with self.assertRaises(RuntimeError):
                serializer.save()
        sku.refresh_from_db()
        self.assertEqual(sku.description_cn, "Atomic light")
        self.assertFalse(sku.versions.exists())

    def test_late_create_profile_failure_rolls_back_sku(self):
        serializer = SKUSerializer(data=self.payload())
        serializer.is_valid(raise_exception=True)
        with patch("crm.serializers.SKUPackagingProfileSerializer.save", side_effect=RuntimeError("write failed")):
            with self.assertRaises(RuntimeError):
                serializer.save()
        self.assertFalse(SKU.objects.exists())
        self.assertFalse(SKUPackagingProfile.objects.exists())

    def test_audit_failure_rolls_back_database_save(self):
        with patch("crm.audit.record_operation", side_effect=RuntimeError("audit failed")):
            with self.assertRaises(RuntimeError):
                self.client.post("/api/skus/", self.payload(), format="json")
        self.assertFalse(SKU.objects.exists())
        self.assertFalse(SKUPackagingProfile.objects.exists())

    def test_effective_changes_clear_verification_and_reuse_numeric_checks(self):
        from django.utils import timezone
        sku = self.create()
        profile = sku.packaging_profile
        profile.verified_at = timezone.now()
        profile.save()
        for field in ("carton_length_override", "carton_width_override", "carton_height_override", "unit_net_weight", "carton_tare_weight_override", "gross_weight_override"):
            response = self.client.patch(f"/api/skus/{sku.pk}/", {"packaging_profile_input": {field: -1}}, format="json")
            self.assertEqual(response.status_code, 400, (field, response.data))
        response = self.client.patch(f"/api/skus/{sku.pk}/", {"packaging_profile_input": {"qty_per_carton_override": 40}}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        profile.refresh_from_db()
        self.assertIsNone(profile.verified_at)
