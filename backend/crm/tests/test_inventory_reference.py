from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from crm.models import (
    AccessRole,
    EmployeeProfile,
    InventoryMovement,
    OrganizationUnit,
    Position,
    Product,
    PurchaseOrder,
    PurchaseOrderItem,
    RolePermission,
    SKU,
    SupplierSKU,
    Supplier,
)


RBAC_SETTINGS = {
    "APP_STAGE": "production",
    "DEBUG": False,
    "DEVELOPMENT_SUPERADMIN": False,
    "RBAC_ENFORCEMENT": True,
}


@override_settings(**RBAC_SETTINGS)
class InventoryReferenceTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        company = OrganizationUnit.objects.create(name="库存参考公司", code="INV-REF-ROOT", type="company")
        position = Position.objects.create(unit=company, name="采购员工", code="INV-REF-POS")
        role = AccessRole.objects.create(name="库存参考采购角色", code="inv-ref-role", default_data_scope="all")
        for module in ("purchases", "skus", "products", "suppliers", "orders", "inventory"):
            RolePermission.objects.create(
                role=role,
                module=module,
                can_view=True,
                can_create=True,
                can_update=True,
                can_delete=True,
                can_export=True,
                can_import=True,
            )
        user = get_user_model().objects.create_user(username="inventory-reference-user", password="test-password")
        profile = EmployeeProfile.objects.create(user=user, display_name="库存参考采购员工", unit=company, position=position)
        profile.roles.add(role)
        self.role = role
        self.client.force_authenticate(user=user)

        product = Product.objects.create(code="P-INV-REF", name="库存参考产品")
        self.sku = SKU.objects.create(
            product=product,
            sku="SKU-INV-REF-001",
            display_name_cn="库存参考 SKU",
            specification="24W / 白光",
            description_cn="采购参考描述",
            parameter_values={"色温": "4000K"},
            product_details=[{"notes": "可定制线长", "custom": "是"}],
            unit="pcs",
        )
        InventoryMovement.objects.create(
            movement_no="IM-INV-REF-IN",
            movement_date=date(2026, 10, 20),
            type="purchase_in",
            sku=self.sku,
            quantity=Decimal("12"),
        )
        InventoryMovement.objects.create(
            movement_no="IM-INV-REF-OUT",
            movement_date=date(2026, 10, 20),
            type="sample_out",
            sku=self.sku,
            quantity=Decimal("3"),
        )
        supplier = Supplier.objects.create(code="IR", name="库存参考供应商")
        source = SupplierSKU.objects.create(
            supplier=supplier,
            sku=self.sku,
            supplier_sku_code="IR-REF-001",
            supplier_model="IR-24W",
            purchase_price=Decimal("2"),
            characteristics={"包装": "防潮袋", "LOGO": "客户标记待确认"},
        )
        purchase = PurchaseOrder.objects.create(
            purchase_no="PO-INV-REF",
            supplier=supplier,
            order_date=date(2026, 10, 20),
            status="ordered",
            currency="CNY",
        )
        PurchaseOrderItem.objects.create(purchase_order=purchase, sku=self.sku, supplier_sku=source, quantity=Decimal("7"), unit_price=Decimal("2"))
        InventoryMovement.objects.filter(movement_no="IM-INV-REF-IN").update(
            supplier_sku=source,
            warehouse="北区成品仓",
            reference="PO-INV-REF",
            source_type="receipt",
            source_no="PO-INV-REF",
            notes="防潮袋；客户 LOGO 待确认",
        )

    def test_sku_detail_reuses_authoritative_metrics_and_inventory_context(self):
        response = self.client.get(f"/api/skus/{self.sku.pk}/")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["sku_code"], self.sku.sku)
        self.assertEqual(response.data["actual_quantity"], Decimal("9"))
        self.assertEqual(response.data["reserved_quantity"], Decimal("0"))
        self.assertEqual(response.data["available_quantity"], Decimal("9"))
        self.assertEqual(response.data["in_transit_quantity"], Decimal("7"))
        self.assertEqual(response.data["specification"], "24W / 白光")

        detail = self.client.get(f"/api/skus/{self.sku.pk}/inventory-detail/")
        self.assertEqual(detail.status_code, 200, detail.data)
        self.assertEqual(detail.data["sku"]["unit"], "pcs")
        self.assertEqual([row["movement_no"] for row in detail.data["movements"]], ["IM-INV-REF-OUT", "IM-INV-REF-IN"])
        movement = detail.data["movements"][1]
        self.assertEqual(movement["warehouse"], "北区成品仓")
        self.assertEqual(movement["source_no"], "PO-INV-REF")
        self.assertEqual(movement["notes"], "防潮袋；客户 LOGO 待确认")
        self.assertEqual(movement["supplier_characteristics"], {"包装": "防潮袋", "LOGO": "客户标记待确认"})
        self.assertEqual(detail.data["purchases"][0]["quantity"], Decimal("7.00"))
        self.assertEqual(detail.data["purchases"][0]["supplier_sources"][0]["characteristics"], {"包装": "防潮袋", "LOGO": "客户标记待确认"})

    def test_inventory_detail_separates_historical_snapshot_from_current_supplier_profile(self):
        source = SupplierSKU.objects.get(sku=self.sku)
        supplier = source.supplier
        supplier.name = "当前供应商B"
        supplier.save(update_fields=["name"])
        source.supplier_model = "当前型号B"
        source.supplier_sku_code = "当前编码B"
        source.characteristics = {"包装": "当前纸箱", "LOGO": "当前档案B"}
        source.save(update_fields=["supplier_model", "supplier_sku_code", "characteristics"])

        detail = self.client.get(f"/api/skus/{self.sku.pk}/inventory-detail/")

        self.assertEqual(detail.status_code, 200, detail.data)
        purchase_source = detail.data["purchases"][0]["supplier_sources"][0]
        self.assertEqual(purchase_source["source_label"], "历史采购来源快照")
        self.assertEqual(purchase_source["supplier_name"], "库存参考供应商")
        self.assertEqual(purchase_source["supplier_model"], "IR-24W")
        self.assertEqual(purchase_source["supplier_sku_code"], "IR-REF-001")
        self.assertEqual(purchase_source["characteristics"], {"包装": "防潮袋", "LOGO": "客户标记待确认"})
        movement = next(row for row in detail.data["movements"] if row["movement_no"] == "IM-INV-REF-IN")
        self.assertEqual(movement["source_label"], "当前供应来源档案")
        self.assertEqual(movement["supplier_name"], "当前供应商B")
        self.assertEqual(movement["supplier_model"], "当前型号B")
        self.assertEqual(movement["supplier_sku_code"], "当前编码B")
        self.assertEqual(movement["supplier_characteristics"], {"包装": "当前纸箱", "LOGO": "当前档案B"})

    def test_inventory_detail_does_not_invent_history_when_snapshots_are_empty(self):
        item = PurchaseOrderItem.objects.get(purchase_order__purchase_no="PO-INV-REF", sku=self.sku)
        PurchaseOrderItem.objects.filter(pk=item.pk).update(
            supplier_name_snapshot="",
            supplier_model_snapshot="",
            supplier_sku_code_snapshot="",
            supplier_characteristics_snapshot={},
        )
        source = SupplierSKU.objects.get(pk=item.supplier_sku_id)
        source.characteristics = {"包装": "当前纸箱", "LOGO": "当前档案B"}
        source.save(update_fields=["characteristics"])

        detail = self.client.get(f"/api/skus/{self.sku.pk}/inventory-detail/")

        self.assertEqual(detail.status_code, 200, detail.data)
        purchase_source = detail.data["purchases"][0]["supplier_sources"][0]
        self.assertEqual(purchase_source["source_label"], "历史采购来源未记录")
        self.assertEqual(purchase_source["supplier_name"], "")
        self.assertEqual(purchase_source["supplier_model"], "")
        self.assertEqual(purchase_source["supplier_sku_code"], "")
        self.assertEqual(purchase_source["characteristics"], {})

    def test_sku_detail_does_not_turn_hidden_inventory_into_zero(self):
        RolePermission.objects.filter(role=self.role, module="inventory").update(can_view=False)

        response = self.client.get(f"/api/skus/{self.sku.pk}/")

        self.assertEqual(response.status_code, 200, response.data)
        for field in ("stock_quantity", "actual_quantity", "reserved_quantity", "available_quantity", "in_transit_quantity"):
            self.assertIsNone(response.data[field])

        detail = self.client.get(f"/api/skus/{self.sku.pk}/inventory-detail/")
        self.assertEqual(detail.status_code, 403, detail.data)

    def test_inventory_detail_redacts_supplier_traits_without_supplier_permission(self):
        RolePermission.objects.filter(role=self.role, module="suppliers").update(can_view=False)
        source = SupplierSKU.objects.get(sku=self.sku)
        source.supplier_model = "当前型号B"
        source.supplier_sku_code = "当前编码B"
        source.characteristics = {"包装": "当前纸箱", "LOGO": "当前档案B"}
        source.save(update_fields=["supplier_model", "supplier_sku_code", "characteristics"])

        response = self.client.get(f"/api/skus/{self.sku.pk}/inventory-detail/")

        self.assertEqual(response.status_code, 200, response.data)
        movement = next(row for row in response.data["movements"] if row["movement_no"] == "IM-INV-REF-IN")
        self.assertEqual(movement["supplier_name"], "")
        self.assertEqual(movement["supplier_characteristics"], {})
        self.assertEqual(response.data["purchases"][0]["supplier_name"], "")
        self.assertEqual(response.data["purchases"][0]["supplier_sources"], [])
        self.assertEqual(movement["supplier_model"], "")
        self.assertEqual(movement["supplier_sku_code"], "")
