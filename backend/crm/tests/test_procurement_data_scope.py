from django.test import TestCase, override_settings
from crm.models import PurchaseOrder, PurchaseCostAllocation, RolePermission
from crm.tests import test_finance_data_scope as fixture

@override_settings(**fixture.RBAC_SETTINGS, PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ProcurementDataScopeTests(TestCase):
    make_employee = fixture.FinanceDataScopeTests.make_employee
    setUp = fixture.FinanceDataScopeTests.setUp

    def payload(self, order=None):
        return {"version": PurchaseOrder.objects.get(pk=self.purchase.pk).cost_allocation_version, "expenses": [], "allocations": [{"purchase_item": self.purchase.items.get().pk, "target_type": "order" if order else "inventory", "order": order.pk if order else None, "quantity": "1"}]}

    def test_four_scopes_and_normal_collaboration(self):
        url = f"/api/purchase-orders/{self.purchase.pk}/cost-allocation/"
        for employee, index in ((self.employee_a, 0), (self.manager, 1), (self.tree_manager, 2), (self.all_user, 3)):
            self.purchase.order = self.orders[index]
            self.purchase.save()
            PurchaseCostAllocation.objects.filter(purchase_item__purchase_order=self.purchase).update(order=self.orders[index])
            self.client.force_authenticate(employee.user)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["allocations"][0]["order"], self.orders[index].pk)
            response = self.client.post(url, self.payload(self.orders[0]), format="json")
            self.assertEqual(response.status_code, 200, response.data)

    def test_old_and_new_cost_targets_are_checked(self):
        url = f"/api/purchase-orders/{self.purchase.pk}/cost-allocation/"
        data = self.client.get(url).data
        self.assertEqual(data["allocations"][0]["order"], self.orders[3].pk)
        self.assertTrue(data["can_edit"])
        for endpoint in (url, url.replace("cost-allocation/", "cost-allocation-preview/")):
            self.assertEqual(self.client.post(endpoint, self.payload(self.orders[0]), format="json").status_code, 200)
        self.purchase.order = None
        self.purchase.save()
        PurchaseCostAllocation.objects.filter(purchase_item__purchase_order=self.purchase).update(order=None, target_type="inventory")
        self.assertEqual(self.client.post(url, self.payload(self.orders[3]), format="json").status_code, 200)

    def test_independent_procurement_without_sales_permission(self):
        self.purchase.order = None
        self.purchase.save()
        PurchaseCostAllocation.objects.filter(purchase_item__purchase_order=self.purchase).update(order=None, target_type="inventory")
        RolePermission.objects.filter(role=self.roles["self"], module="orders").update(can_view=False, can_update=False)
        url = f"/api/purchase-orders/{self.purchase.pk}/cost-allocation/"
        response = self.client.post(url, self.payload(), format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.client.post(url, self.payload(self.orders[0]), format="json").status_code, 200)

    def test_hidden_order_rebinding_and_search(self):
        self.purchase.status = "draft"
        self.purchase.save()
        for order in (None, self.orders[0].pk):
            self.assertEqual(self.client.patch(f"/api/purchase-orders/{self.purchase.pk}/", {"order": order}, format="json").status_code, 403)
        response = self.client.get("/api/purchase-orders/", {"search": self.orders[3].order_no})
        rows = response.data.get("results", []) if isinstance(response.data, dict) else response.data
        self.assertEqual(rows, [])

    def test_shared_receipt_reverse_preserves_sales_snapshot(self):
        before = list(self.orders[3].items.values())
        RolePermission.objects.filter(role=self.roles["self"], module="orders").update(can_view=False, can_update=False)
        url = f"/api/purchase-orders/{self.purchase.pk}/receive/"
        data = {"purchase_item": self.purchase.items.get().pk, "quantity": "1", "receipt_date": "2026-10-12"}
        response = self.client.post(url, data, format="json", HTTP_IDEMPOTENCY_KEY="iss006-procurement-scope-receipt")
        self.assertEqual(response.status_code, 201, response.data)
        reverse = self.client.post(f"/api/purchase-orders/{self.purchase.pk}/receipts/{response.data['id']}/reverse/", {"reason": "回归冲销"}, format="json")
        self.assertEqual(reverse.status_code, 200, reverse.data)
        self.assertEqual(list(self.orders[3].items.values()), before)

    def test_missing_inventory_and_purchases_denied(self):
        RolePermission.objects.filter(role=self.roles["self"], module="inventory").update(can_create=False)
        response = self.client.post(f"/api/purchase-orders/{self.purchase.pk}/receive/", {"purchase_item": self.purchase.items.get().pk, "quantity": "1", "receipt_date": "2026-10-12"}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.purchase.items.get().receipts.exists())
        RolePermission.objects.filter(role=self.roles["self"], module="purchases").update(can_view=False)
        self.assertEqual(self.client.get(f"/api/purchase-orders/{self.purchase.pk}/").status_code, 403)

    def test_supplier_allocation_and_drafts_require_each_module(self):
        from crm.models import SupplierSKU
        source = SupplierSKU.objects.create(supplier=self.supplier, sku=self.sku, supplier_sku_code="ZZ-SCOPE", purchase_price=20, currency="CNY")
        item = self.orders[0].items.get()
        url = f"/api/orders/{self.orders[0].pk}/items/{item.pk}/supplier-allocation/"
        response = self.client.post(url, {"supplier_sku": source.pk}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        RolePermission.objects.filter(role=self.roles["self"], module="suppliers").update(can_update=False)
        self.assertEqual(self.client.post(url, {"supplier_sku": source.pk, "scope": "recommended"}, format="json").status_code, 403)
        self.assertEqual(self.client.post(url, {"supplier_sku": source.pk, "scope": "order_only"}, format="json").status_code, 200)
        foreign = self.orders[3].items.get()
        self.assertEqual(self.client.post(f"/api/orders/{self.orders[3].pk}/items/{foreign.pk}/supplier-allocation/", {"supplier_sku": source.pk}, format="json").status_code, 404)
        self.assertEqual(self.client.post(f"/api/orders/{self.orders[0].pk}/items/{foreign.pk}/supplier-allocation/", {"supplier_sku": source.pk}, format="json").status_code, 404)
        draft_url = f"/api/orders/{self.orders[0].pk}/generate-purchase-drafts/"
        payload = {"groups": [{"supplier": self.supplier.pk, "currency": "CNY", "exchange_rate": "1", "items": [{"order_item": item.pk, "quantity": "1", "unit_price": "20"}]}]}
        response = self.client.post(draft_url, payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        RolePermission.objects.filter(role=self.roles["self"], module="purchases").update(can_create=False)
        self.assertEqual(self.client.post(draft_url, payload, format="json").status_code, 403)

    def test_multi_order_read_and_audit_snapshots_do_not_leak(self):
        from crm.models import OperationLog
        from crm.serializers import OperationLogSerializer
        item = self.purchase.items.get()
        PurchaseCostAllocation.objects.filter(purchase_item=item).update(quantity="0.5")
        PurchaseCostAllocation.objects.create(purchase_item=item, order=self.orders[0], target_type="order", quantity="0.5")
        response = self.client.get(f"/api/purchase-orders/{self.purchase.pk}/cost-allocation/")
        rows = response.data["allocations"]
        self.assertEqual({r["order"] for r in rows}, {self.orders[3].pk, self.orders[0].pk})
        self.assertEqual(sum(r["quantity"] for r in rows), 1)
        self.assertTrue(response.data["can_edit"])
        from django.contrib.contenttypes.models import ContentType
        log = OperationLog.objects.create(content_type=ContentType.objects.get_for_model(self.purchase), entity="crm.purchaseorder", object_id=str(self.purchase.pk), object_label="F-PO", entity_label="采购", action="custom", action_label="成本分配", metadata={"order": self.orders[3].pk})
        self.assertEqual(OperationLogSerializer(log, context={"user": self.employee_a.user}).data["metadata"], {})
        log.refresh_from_db()
        self.assertEqual(log.metadata, {"order": self.orders[3].pk})

    def test_missing_sales_view_and_update_deny_cost_even_with_all_scope(self):
        self.client.force_authenticate(self.all_user.user)
        url = f"/api/purchase-orders/{self.purchase.pk}/cost-allocation/"
        for field in ("can_view", "can_update"):
            RolePermission.objects.filter(role=self.roles["all"], module="orders").update(**{field: False})
            self.assertEqual(self.client.post(url, self.payload(), format="json").status_code, 200)
            RolePermission.objects.filter(role=self.roles["all"], module="orders").update(**{field: True})

    def test_candidates_and_reports_cannot_bypass_purchases_view(self):
        RolePermission.objects.filter(role=self.roles["self"], module="purchases").update(can_view=False)
        response = self.client.get(f"/api/skus/{self.sku.pk}/supplier-candidates/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["candidates"], [])
        response = self.client.get("/api/reports/data/", {"source": "purchase"})
        self.assertEqual(response.status_code, 403)
