from rest_framework import status
from rest_framework.test import APIClient

from django.test import TestCase

from crm.models import Product, SKU, SKUVersion


class SkuDisplayNameUniquenessTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.product_a = Product.objects.create(code="P-DISPLAY-NAME-A", name="产品 A")
        self.product_b = Product.objects.create(code="P-DISPLAY-NAME-B", name="产品 B")

    def create_sku(self, product, code, name, model):
        response = self.client.post(
            "/api/skus/",
            {"product": product.id, "sku": code, "display_name_cn": name, "sales_model": model},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return SKU.objects.get(pk=response.data["id"])

    def test_display_name_is_unique_without_case_sensitivity(self):
        first = self.create_sku(self.product_a, "SKU-DISPLAY-A", "Manual V", "MODEL-DISPLAY-A")

        duplicate = self.client.post(
            "/api/skus/",
            {"product": self.product_b.id, "sku": "SKU-DISPLAY-B", "display_name_cn": "manual v", "sales_model": "MODEL-DISPLAY-B"},
            format="json",
        )

        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST, duplicate.data)
        self.assertIn("display_name_cn", duplicate.data)
        first.refresh_from_db()
        self.assertEqual(first.display_name_key, "manual v")

    def test_renaming_an_existing_sku_to_a_case_insensitive_duplicate_is_rejected(self):
        self.create_sku(self.product_a, "SKU-DISPLAY-C", "Manual V", "MODEL-DISPLAY-C")
        second = self.create_sku(self.product_b, "SKU-DISPLAY-D", "Other Name", "MODEL-DISPLAY-D")

        response = self.client.patch(
            f"/api/skus/{second.id}/",
            {"display_name_cn": "MANUAL v"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        second.refresh_from_db()
        self.assertEqual(second.display_name_cn, "Other Name")

    def test_renaming_an_existing_sku_requires_explicit_identity_confirmation(self):
        sku = self.create_sku(self.product_a, "SKU-DISPLAY-E", "Original Name", "MODEL-DISPLAY-E")

        response = self.client.patch(f"/api/skus/{sku.id}/", {"display_name_cn": "Renamed Name"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

        response = self.client.patch(
            f"/api/skus/{sku.id}/",
            {"display_name_cn": "Renamed Name", "identity_change_confirmed": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        sku.refresh_from_db()
        self.assertEqual(sku.display_name_cn, "Renamed Name")
        self.assertEqual(SKUVersion.objects.get(sku=sku).display_name_cn_snapshot, "Original Name")

    def test_sku_detail_context_exposes_history_names_and_version_snapshot(self):
        sku = self.create_sku(self.product_a, "SKU-DISPLAY-F", "Original Name", "MODEL-DISPLAY-F")
        response = self.client.patch(
            f"/api/skus/{sku.id}/",
            {"display_name_cn": "Renamed Name", "identity_change_confirmed": True, "change_reason": "参数口径调整"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        context_response = self.client.get(f"/api/context/skus/{sku.id}/")
        self.assertEqual(context_response.status_code, status.HTTP_200_OK, context_response.data)
        sections = {section["key"]: section for section in context_response.data["sections"]}
        self.assertEqual(sections["versions"]["title"], "历史名称 / 历史版本")
        self.assertEqual(sections["versions"]["rows"][0]["display_name_cn"], "Original Name")
        self.assertEqual(sections["versions"]["rows"][0]["sales_model"], "MODEL-DISPLAY-F")

        version_id = sections["versions"]["rows"][0]["id"]
        version_response = self.client.get(f"/api/context/sku-versions/{version_id}/")
        self.assertEqual(version_response.status_code, status.HTTP_200_OK, version_response.data)
        self.assertEqual(version_response.data["info"][3][1], "Original Name")
