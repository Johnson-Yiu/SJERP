from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from crm.models import (
    AccessRole,
    EmployeeProfile,
    InventoryMovement,
    OperationLog,
    OrganizationUnit,
    Position,
    Product,
    PurchaseOrder,
    PurchaseOrderItem,
    RolePermission,
    SKU,
    Supplier,
    SupplierSKU,
    Transaction,
)
from crm.services.supplier_candidates import candidates


RBAC_SETTINGS = {
    "APP_STAGE": "production",
    "DEBUG": False,
    "DEVELOPMENT_SUPERADMIN": False,
    "RBAC_ENFORCEMENT": True,
    "AUDIT_LOG_ENABLED": True,
}


@override_settings(**RBAC_SETTINGS, PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class SupplierLifecycleApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.unit = OrganizationUnit.objects.create(name="ISS-026 测试部", code="ISS026")
        self.position = Position.objects.create(unit=self.unit, name="测试员工", code="ISS026-STAFF")
        self.writer_role = AccessRole.objects.create(name="ISS-026 供应商维护", code="iss026-supplier-writer")
        self.viewer_role = AccessRole.objects.create(name="ISS-026 供应商只读", code="iss026-supplier-viewer")
        self.grant(self.writer_role, "suppliers", can_view=True, can_update=True, can_delete=True)
        self.grant(self.writer_role, "purchases", can_view=True, can_create=True, can_update=True)
        self.grant(self.writer_role, "skus", can_view=True)
        self.grant(self.viewer_role, "suppliers", can_view=True)
        self.writer = self.make_user("iss026-writer", [self.writer_role])
        self.viewer = self.make_user("iss026-viewer", [self.viewer_role])
        self.client.force_authenticate(user=self.writer)

        product = Product.objects.create(code="ISS026-P", name="ISS-026 测试产品")
        self.sku = SKU.objects.create(product=product, sku="ISS026-SKU", display_name_cn="ISS-026 测试 SKU")
        self.active_supplier = Supplier.objects.create(name="ISS-026 启用供应商", code="IA")
        self.history_supplier = Supplier.objects.create(name="ISS-026 历史供应商", code="IH")
        self.source = SupplierSKU.objects.create(
            supplier=self.history_supplier,
            sku=self.sku,
            supplier_sku_code="ISS026-SOURCE",
            purchase_price=Decimal("3.2"),
        )
        self.purchase = PurchaseOrder.objects.create(
            purchase_no="ISS026-PO",
            supplier=self.history_supplier,
            order_date=date(2026, 10, 24),
            status="ordered",
            currency="USD",
            exchange_rate=1,
            supplier_name_snapshot=self.history_supplier.name,
        )
        self.purchase_item = PurchaseOrderItem.objects.create(
            purchase_order=self.purchase,
            sku=self.sku,
            supplier_sku=self.source,
            quantity=Decimal("2"),
            unit_price=Decimal("3.2"),
            supplier_name_snapshot=self.history_supplier.name,
        )
        self.transaction = Transaction.objects.create(
            transaction_no="ISS026-TX",
            transaction_date=date(2026, 10, 24),
            direction="expense",
            category="供应商付款",
            amount=Decimal("6.4"),
            currency="USD",
            exchange_rate=1,
            supplier=self.history_supplier,
            purchase_order=self.purchase,
        )

    def grant(self, role, module, **values):
        defaults = {
            "can_view": False,
            "can_create": False,
            "can_update": False,
            "can_delete": False,
            "can_export": False,
            "can_import": False,
        }
        defaults.update(values)
        return RolePermission.objects.update_or_create(role=role, module=module, defaults=defaults)[0]

    def make_user(self, username, roles):
        user = get_user_model().objects.create_user(username=username, password="iss026-password")
        EmployeeProfile.objects.create(
            user=user,
            display_name=username,
            unit=self.unit,
            position=self.position,
        ).roles.set(roles)
        return user

    def test_delete_is_rejected_for_suppliers_with_and_without_history(self):
        for supplier in (self.active_supplier, self.history_supplier):
            response = self.client.delete(f"/api/suppliers/{supplier.pk}/")
            self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED, response.data)
            self.assertTrue(Supplier.objects.filter(pk=supplier.pk).exists())

    def test_deactivate_reactivate_filters_new_candidates_and_records_audit(self):
        self.source.supplier = self.active_supplier
        self.source.supplier_sku_code = "ISS026-ACTIVE-SOURCE"
        self.source.save(update_fields=["supplier", "supplier_sku_code", "updated_at"])

        active_only = self.client.get("/api/suppliers/?active_only=1")
        self.assertEqual(active_only.status_code, status.HTTP_200_OK)
        self.assertEqual({row["id"] for row in active_only.data["results"]}, {self.active_supplier.pk, self.history_supplier.pk})

        deactivated = self.client.post(f"/api/suppliers/{self.active_supplier.pk}/deactivate/", {}, format="json")
        self.assertEqual(deactivated.status_code, status.HTTP_200_OK, deactivated.data)
        self.active_supplier.refresh_from_db()
        self.assertFalse(self.active_supplier.is_active)
        self.assertNotIn(self.active_supplier.pk, {row["supplier"] for row in candidates(self.sku)})

        active_only = self.client.get("/api/suppliers/?active_only=1")
        self.assertEqual(active_only.status_code, status.HTTP_200_OK)
        self.assertNotIn(self.active_supplier.pk, {row["id"] for row in active_only.data["results"]})
        self.assertEqual(
            self.client.post(
                "/api/purchase-orders/",
                {
                    "supplier": self.active_supplier.pk,
                    "order_date": "2026-10-24",
                    "currency": "USD",
                    "exchange_rate": "1",
                    "items": [{"sku": self.sku.pk, "quantity": "1", "unit_price": "3"}],
                },
                format="json",
            ).status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        reactivated = self.client.post(f"/api/suppliers/{self.active_supplier.pk}/activate/", {}, format="json")
        self.assertEqual(reactivated.status_code, status.HTTP_200_OK, reactivated.data)
        self.active_supplier.refresh_from_db()
        self.assertTrue(self.active_supplier.is_active)
        self.assertIn(self.active_supplier.pk, {row["supplier"] for row in candidates(self.sku)})

        logs = OperationLog.objects.filter(entity="crm.supplier", object_id=str(self.active_supplier.pk)).order_by("id")
        self.assertEqual(list(logs.values_list("action_label", flat=True)), ["停用供应商", "启用供应商"])
        self.assertTrue(logs.first().before_data["is_active"])
        self.assertTrue(logs.last().after_data["is_active"])

    def test_history_and_supplier_sources_remain_readable_after_deactivation(self):
        response = self.client.post(f"/api/suppliers/{self.history_supplier.pk}/deactivate/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.purchase.refresh_from_db()
        self.purchase_item.refresh_from_db()
        self.transaction.refresh_from_db()
        self.source.refresh_from_db()
        self.assertEqual(self.purchase.supplier_id, self.history_supplier.pk)
        self.assertEqual(self.purchase.supplier_name_snapshot, "ISS-026 历史供应商")
        self.assertEqual(self.purchase_item.supplier_sku_id, self.source.pk)
        self.assertEqual(self.transaction.supplier_id, self.history_supplier.pk)
        self.assertTrue(Supplier.objects.filter(pk=self.history_supplier.pk).exists())
        self.assertEqual(self.client.get(f"/api/purchase-orders/{self.purchase.pk}/").status_code, status.HTTP_200_OK)

    def test_rbac_allows_lifecycle_update_only_with_supplier_update_permission(self):
        self.client.force_authenticate(user=self.viewer)
        self.assertEqual(self.client.get("/api/suppliers/").status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.post(f"/api/suppliers/{self.active_supplier.pk}/deactivate/", {}, format="json").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.delete(f"/api/suppliers/{self.active_supplier.pk}/").status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.writer)
        rejected_patch = self.client.patch(
            f"/api/suppliers/{self.active_supplier.pk}/",
            {"is_active": False},
            format="json",
        )
        self.assertEqual(rejected_patch.status_code, status.HTTP_400_BAD_REQUEST, rejected_patch.data)
        self.active_supplier.refresh_from_db()
        self.assertTrue(self.active_supplier.is_active)
