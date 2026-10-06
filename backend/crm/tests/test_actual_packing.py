from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from crm.models import Customer, InventoryMovement, Order, PackagingTemplate, Product, ShipmentPackageItem, SKU, SKUPackagingProfile
from crm.services.fulfillment import confirm_shipment, reverse_shipment
from crm.services.packaging import generate_packing_plan


class ActualPackingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        customer = Customer.objects.create(code="C-ACT-PACK", name="Packing UAT")
        product = Product.objects.create(code="P-ACT-PACK", name="Packing Light")
        self.a = SKU.objects.create(product=product, sku="ACT-PACK-A")
        self.b = SKU.objects.create(product=product, sku="ACT-PACK-B")
        self.other = SKU.objects.create(product=product, sku="ACT-PACK-X")
        self.order = Order.objects.create(order_no="SO-ACT-PACK", customer=customer, order_date=date(2026, 10, 7), status="confirmed")
        lines = [self.order.items.create(sku=sku, quantity=quantity, unit_price="1") for sku, quantity in [(self.a, "6"), (self.a, "4"), (self.b, "8")]]
        for sku in (self.a, self.b):
            InventoryMovement.objects.create(movement_no=f"IN-ACT-{sku.pk}", movement_date=date(2026, 10, 7), type="adjust_in", sku=sku, quantity="100")
        self.shipment = confirm_shipment(self.order, {"shipment_no": "SH-ACT-PACK", "shipment_date": date(2026, 10, 7), "items": [{"order_item": line.pk, "quantity": line.quantity} for line in lines]})
        self.url = f"/api/shipments/{self.shipment.pk}/packages/"
        self.copy_url = f"/api/shipments/{self.shipment.pk}/copy-estimated-packing/"

    def payload(self, **overrides):
        return {"carton_no": 1, "actual_net_weight": "1", "actual_gross_weight": "2", "items": [{"sku": self.a.pk, "quantity": "6"}], **overrides}

    def create(self, **overrides):
        return self.client.post(self.url, self.payload(**overrides), format="json")

    def package(self):
        response = self.create()
        self.assertEqual(response.status_code, 201, response.data)
        return self.shipment.packages.get(pk=response.data["id"])

    def plan(self):
        template = PackagingTemplate.objects.create(code="ACT-PACK", name="Actual carton", carton_length="40", carton_width="30", carton_height="20", qty_per_carton="5", carton_tare_weight="1")
        for sku in (self.a, self.b):
            SKUPackagingProfile.objects.create(sku=sku, packaging_template=template, unit_net_weight="0.2")
        return generate_packing_plan(self.order)

    def test_confirmed_create_and_cbm_without_changing_business_quantities(self):
        before = list(InventoryMovement.objects.values_list("pk", "quantity"))
        response = self.create(length="40", width="30", height="20")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["actual_cbm"], "0.024000")
        self.assertEqual(list(InventoryMovement.objects.values_list("pk", "quantity")), before)
        self.assertEqual(sum(self.shipment.items.values_list("quantity", flat=True)), Decimal("18"))

    def test_mixed_sku_carton(self):
        self.assertEqual(self.create(items=[{"sku": self.a.pk, "quantity": "5"}, {"sku": self.b.pk, "quantity": "2"}]).status_code, 201)

    def test_non_shipped_sku_rejected(self):
        self.assertEqual(self.create(items=[{"sku": self.other.pk, "quantity": "1"}]).status_code, 400)

    def test_nonpositive_quantities_rejected(self):
        for quantity in ("0", "-1"):
            with self.subTest(quantity=quantity):
                self.assertEqual(self.create(items=[{"sku": self.a.pk, "quantity": quantity}]).status_code, 400)

    def test_duplicate_sku_rejected(self):
        self.assertEqual(self.create(items=[{"sku": self.a.pk, "quantity": "1"}] * 2).status_code, 400)

    def test_cumulative_overpack_rejected_and_repeated_shipment_lines_aggregated(self):
        self.package()
        rejected = self.create(carton_no=2, items=[{"sku": self.a.pk, "quantity": "5"}])
        self.assertEqual(rejected.status_code, 400)
        self.assertIn("不能超过", str(rejected.data))
        self.assertEqual(self.create(carton_no=2, items=[{"sku": self.a.pk, "quantity": "4"}]).status_code, 201)

    def test_edit_excludes_old_package_and_replaces_items(self):
        package = self.package()
        response = self.client.post(f"{self.url}{package.pk}/", self.payload(carton_no=3, items=[{"sku": self.a.pk, "quantity": "10"}], notes="edited"), format="json")
        self.assertEqual(response.status_code, 200, response.data)
        package.refresh_from_db()
        self.assertEqual(package.carton_no, 3)
        self.assertEqual(package.items.get().quantity, Decimal("10"))

    def test_duplicate_carton_number_is_friendly(self):
        package = self.package()
        response = self.create(items=[{"sku": self.b.pk, "quantity": "1"}])
        self.assertEqual(response.status_code, 400)
        self.assertIn("已存在此箱号", str(response.data))
        second = self.create(carton_no=2, items=[{"sku": self.b.pk, "quantity": "1"}])
        self.assertEqual(self.client.patch(f"{self.url}{second.data['id']}/", {"carton_no": package.carton_no}, format="json").status_code, 400)

    def test_partial_packing_allowed(self):
        self.assertEqual(self.create(items=[{"sku": self.a.pk, "quantity": "0.01"}]).status_code, 201)

    def test_all_dimensions_blank_allowed(self):
        response = self.create(length=None, width=None, height=None)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["actual_cbm"], "0.000000")

    def test_partial_and_nonpositive_dimensions_rejected(self):
        for dimensions in ({"length": "1"}, {"length": "0", "width": "1", "height": "1"}, {"length": "-1", "width": "1", "height": "1"}):
            with self.subTest(dimensions=dimensions):
                self.assertEqual(self.create(**dimensions).status_code, 400)

    def test_weight_validation(self):
        for net, gross in [("2", "1"), ("-1", "2"), ("0", "-1")]:
            with self.subTest(net=net, gross=gross):
                self.assertEqual(self.create(actual_net_weight=net, actual_gross_weight=gross).status_code, 400)

    def test_failed_update_validation_preserves_package(self):
        package = self.package()
        response = self.client.post(f"{self.url}{package.pk}/", self.payload(notes="bad", items=[{"sku": self.a.pk, "quantity": "11"}]), format="json")
        self.assertEqual(response.status_code, 400)
        package.refresh_from_db()
        self.assertEqual(package.notes, "")
        self.assertEqual(package.items.get().quantity, Decimal("6"))

    def test_failed_update_save_rolls_back_fields_and_deleted_items(self):
        package = self.package()
        old_items = list(package.items.values_list("pk", "sku_id", "quantity"))
        with patch("crm.serializers.ShipmentPackageItem.objects.bulk_create", side_effect=RuntimeError("save failed")):
            with self.assertRaises(RuntimeError):
                self.client.post(f"{self.url}{package.pk}/", self.payload(notes="changed"), format="json")
        package.refresh_from_db()
        self.assertEqual(package.notes, "")
        self.assertEqual(list(package.items.values_list("pk", "sku_id", "quantity")), old_items)

    def test_failed_create_rolls_back_new_package(self):
        with patch("crm.serializers.ShipmentPackageItem.objects.bulk_create", side_effect=RuntimeError("save failed")):
            with self.assertRaises(RuntimeError):
                self.create()
        self.assertFalse(self.shipment.packages.exists())

    def test_delete_confirmed_package_does_not_change_shipment_or_inventory(self):
        package = self.package()
        before = list(InventoryMovement.objects.values_list("pk", "quantity"))
        self.assertEqual(self.client.delete(f"{self.url}{package.pk}/").status_code, 204)
        self.shipment.refresh_from_db()
        self.assertEqual(self.shipment.status, "confirmed")
        self.assertEqual(list(InventoryMovement.objects.values_list("pk", "quantity")), before)
        self.assertFalse(self.shipment.packages.exists())

    def test_cancelled_and_draft_mutations_blocked_history_readable(self):
        package = self.package()
        self.plan()
        for state in ("cancelled", "draft"):
            self.shipment.status = state
            self.shipment.save(update_fields=["status"])
            for method, url, data in [("post", self.url, self.payload()), ("post", f"{self.url}{package.pk}/", self.payload()), ("patch", f"{self.url}{package.pk}/", {"notes": "bad"}), ("delete", f"{self.url}{package.pk}/", {}), ("post", self.copy_url, {"replace": True})]:
                with self.subTest(state=state, method=method, url=url):
                    self.assertEqual(getattr(self.client, method)(url, data, format="json").status_code, 400)
            self.assertEqual(len(self.client.get(self.url).data), 1)

    def test_shipment_reversal_keeps_package_history(self):
        package = self.package()
        reverse_shipment(self.shipment, "packing history test")
        package.refresh_from_db()
        self.assertEqual(package.items.get().quantity, Decimal("6"))
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_exact_plan_copy_succeeds_with_editable_weights_dimensions(self):
        plan = self.plan()
        response = self.client.post(self.copy_url, {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        first = self.shipment.packages.first()
        carton = plan.cartons.first()
        self.assertEqual(first.actual_net_weight, carton.estimated_net_weight)
        self.assertEqual(first.actual_gross_weight, carton.estimated_gross_weight)
        self.assertEqual(first.length, carton.length)
        self.assertEqual(self.client.patch(f"{self.url}{first.pk}/", {"notes": "actual"}, format="json").status_code, 200)

    def test_partial_shipment_copy_blocked_preserves_packages(self):
        self.plan()
        package = self.package()
        self.shipment.items.filter(sku=self.b).update(quantity="3")
        response = self.client.post(self.copy_url, {"replace": True}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("请手工录入", str(response.data))
        self.assertTrue(self.shipment.packages.filter(pk=package.pk).exists())

    def test_existing_packing_requires_explicit_boolean_replacement(self):
        self.plan()
        package = self.package()
        for payload in ({}, {"replace": False}, {"replace": "true"}):
            self.assertEqual(self.client.post(self.copy_url, payload, format="json").status_code, 400)
            self.assertTrue(self.shipment.packages.filter(pk=package.pk).exists())
        self.assertEqual(self.client.post(self.copy_url, {"replace": True}, format="json").status_code, 200)
        self.assertFalse(self.shipment.packages.filter(pk=package.pk).exists())

    def test_copy_save_failure_restores_existing_packages(self):
        self.plan()
        package = self.package()
        old_items = list(package.items.values_list("pk", "sku_id", "quantity"))
        original_bulk_create = ShipmentPackageItem.objects.bulk_create
        calls = 0
        def fail_after_first_carton(items):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("copy failed after first carton")
            return original_bulk_create(items)
        with patch("crm.serializers.ShipmentPackageItem.objects.bulk_create", side_effect=fail_after_first_carton):
            with self.assertRaises(RuntimeError):
                self.client.post(self.copy_url, {"replace": True}, format="json")
        self.assertTrue(self.shipment.packages.filter(pk=package.pk).exists())
        self.assertEqual(list(self.shipment.packages.values_list("pk", flat=True)), [package.pk])
        self.assertEqual(list(package.items.values_list("pk", "sku_id", "quantity")), old_items)

    def test_delete_failure_rolls_back_package_and_items(self):
        package = self.package()
        old_items = list(package.items.values_list("pk", "sku_id", "quantity"))
        with patch("crm.views.record_operation", side_effect=RuntimeError("audit save failed")):
            with self.assertRaises(RuntimeError):
                self.client.delete(f"{self.url}{package.pk}/")
        self.assertTrue(self.shipment.packages.filter(pk=package.pk).exists())
        self.assertEqual(list(package.items.values_list("pk", "sku_id", "quantity")), old_items)

    def test_invalid_copy_physical_values_preserve_existing_packing(self):
        plan = self.plan()
        package = self.package()
        plan.cartons.filter(pk=plan.cartons.first().pk).update(estimated_gross_weight="0")
        response = self.client.post(self.copy_url, {"replace": True}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertTrue(self.shipment.packages.filter(pk=package.pk).exists())
        self.assertEqual(package.items.get().quantity, Decimal("6"))

    def test_regenerating_plan_does_not_change_actual_packing(self):
        self.plan()
        self.assertEqual(self.client.post(self.copy_url, {}, format="json").status_code, 200)
        before = list(self.shipment.packages.values_list("pk", "length", "actual_net_weight"))
        SKUPackagingProfile.objects.filter(sku=self.a).update(unit_net_weight="0.9")
        generate_packing_plan(self.order)
        self.assertEqual(list(self.shipment.packages.values_list("pk", "length", "actual_net_weight")), before)

    def test_fulfillment_uses_shipment_snapshot_and_sku_ids(self):
        movement = self.shipment.items.first().inventory_movement
        movement.sku_code_snapshot = "SAVED-SKU"
        movement.display_name_snapshot = "Saved shipment name"
        movement.save(update_fields=["sku_code_snapshot", "display_name_snapshot"])
        response = self.client.get(f"/api/orders/{self.order.pk}/fulfillment/")
        row = next(line for line in response.data["shipments"][0]["items"] if line["inventory_movement"] == movement.pk)
        self.assertEqual(row["sku"], movement.sku_id)
        self.assertEqual(row["sku_code"], "SAVED-SKU")
        self.assertEqual(row["display_name"], "Saved shipment name")
