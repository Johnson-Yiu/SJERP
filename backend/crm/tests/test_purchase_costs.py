from datetime import date
from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from crm.models import Customer, Order, Product, PurchaseOrder, PurchaseCostAllocation, SKU, Supplier
from crm.services.purchase_costs import cost_summary, order_purchase_cost, split_amount
from crm.services.fulfillment import order_item_metrics


class PurchaseCostTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        customer = Customer.objects.create(code="COST", name="Buyer")
        supplier = Supplier.objects.create(code="CP", name="Supplier")
        sku = SKU.objects.create(sku="COST", product=Product.objects.create(code="COST", name="Wire"))
        self.a = Order.objects.create(order_no="COST-A", customer=customer, order_date=date.today())
        self.b = Order.objects.create(order_no="COST-B", customer=customer, order_date=date.today())
        self.a.items.create(sku=sku, quantity=200, unit_price=20)
        self.b.items.create(sku=sku, quantity=300, unit_price=20)
        self.purchase = PurchaseOrder.objects.create(purchase_no="COST-P", supplier=supplier, order=self.a, order_date=date.today(), status="ordered", exchange_rate=7)
        self.item = self.purchase.items.create(sku=sku, quantity=1000, unit_price=10)
        self.url = f"/api/purchase-orders/{self.purchase.pk}/cost-allocation/"

    def payload(self):
        return {"version": 0, "allocations": [
            {"purchase_item": self.item.pk, "target_type": "order", "order": self.a.pk, "quantity": "200"},
            {"purchase_item": self.item.pk, "target_type": "order", "order": self.b.pk, "quantity": "300"}],
            "expenses": [{"name": "运费", "amount": "100", "method": "amount"}]}

    def test_split_inventory_freight_profit_and_legacy(self):
        self.assertEqual(order_purchase_cost(self.a), (Decimal(70000), Decimal(0)))
        response = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(response.status_code, 200, response.data)
        rows = response.data["allocations"]
        self.assertEqual([r["quantity"] for r in rows], [200, 300, 500])
        self.assertEqual([r["additional_amount"] for r in rows], [20, 30, 50])
        self.assertEqual(response.data["total_amount"], 10100)
        self.assertEqual(order_purchase_cost(self.a), (14000, 140))
        self.assertEqual(order_purchase_cost(self.b), (21000, 210))
        self.assertEqual(order_item_metrics(self.b.items.get())["purchased_quantity"], 300)
        workbench = self.client.get(f"/api/orders/{self.b.pk}/workbench/")
        self.assertEqual(workbench.status_code, 200)
        self.assertEqual(workbench.data["profit_summary"]["purchase_cost_rmb"], 21210)

    def test_invalid_and_stale_requests_are_atomic(self):
        for patch in ({"quantity": "1001"}, {"purchase_item": 999999}, {"quantity": "-1"}, {"quantity": "NaN"}, {"quantity": "0.001"}, {"target_type": "inventory"}):
            data = self.payload()
            data["allocations"][0].update(patch)
            response = self.client.post(self.url, data, format="json")
            self.assertEqual(response.status_code, 400, response.data)
            self.assertEqual(self.item.cost_allocations.count(), 1)
        self.assertEqual(self.client.post(self.url, self.payload(), format="json").status_code, 200)
        self.assertEqual(self.client.post(self.url, self.payload(), format="json").status_code, 400)
        self.assertEqual(self.client.patch(f"/api/purchase-orders/{self.purchase.pk}/", {"exchange_rate": "8"}, format="json").status_code, 400)

    def test_rounding_and_zero_cost(self):
        self.assertEqual(split_amount(Decimal("0.01"), [Decimal(1)] * 3), [Decimal("0.01"), 0, 0])
        self.item.unit_price = 0
        self.item.save()
        data = self.payload()
        self.assertEqual(self.client.post(self.url, data, format="json").status_code, 400)
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.cost_allocation_version, 0)
        data["expenses"][0]["method"] = "quantity"
        self.assertEqual(self.client.post(self.url, data, format="json").status_code, 200)

    def test_cancelled_and_reallocation(self):
        self.assertEqual(self.client.post(self.url, self.payload(), format="json").status_code, 200)
        data = {"version": 1, "allocations": [], "expenses": []}
        self.assertEqual(self.client.post(self.url, data, format="json").status_code, 200)
        self.assertEqual(order_purchase_cost(self.a), (0, 0))
        self.purchase.refresh_from_db()
        self.assertEqual(cost_summary(self.purchase)["allocations"][0]["quantity"], 1000)
        self.purchase.status = "cancelled"
        self.purchase.save()
        data["version"] = 2
        self.assertEqual(self.client.post(self.url, data, format="json").status_code, 400)

    def test_custom_targets_roundtrip_and_validation(self):
        data = self.payload()
        data["allocations"] = [{"purchase_item": self.item.pk, "target_type": "other", "quantity": "1000", "target_name": "   "}]
        self.assertEqual(self.client.post(self.url, data, format="json").status_code, 400)
        data["allocations"][0]["target_name"] = "项目备用物料"
        self.assertEqual(self.client.post(self.url, data, format="json").status_code, 200)
        result = self.client.get(self.url).data
        self.assertEqual(result["allocations"][0]["target_name"], "项目备用物料")
        self.assertTrue(result["allocations"][0]["display_name"])
        self.assertEqual(result["total_amount"], 10100)
        self.assertEqual(order_purchase_cost(self.a), (0, 0))
        for index, target in enumerate(["gift", "after_sales", "research", "internal", "marketing"], 1):
            data["version"] = index
            data["allocations"][0]["target_type"] = target
            response = self.client.post(self.url, data, format="json")
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data["allocations"][0]["target_name"], "")

    def test_preview_matches_save_without_writes(self):
        from crm.models import OperationLog
        before_logs = OperationLog.objects.count()
        preview_url = self.url.replace("cost-allocation/", "cost-allocation-preview/")
        response = self.client.post(preview_url, self.payload(), format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["additional_amount"], 100)
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.cost_allocation_version, 0)
        self.assertEqual(self.purchase.additional_costs, [])
        self.assertEqual(self.item.cost_allocations.count(), 1)
        self.assertEqual(OperationLog.objects.count(), before_logs)
        saved = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(response.data["allocations"], saved.data["allocations"])
        self.assertEqual(response.data["total_amount"], saved.data["total_amount"])

    def test_preview_rejects_overallocation_without_changes(self):
        data = self.payload()
        data["allocations"][0]["quantity"] = "1001"
        response = self.client.post(self.url.replace("cost-allocation/", "cost-allocation-preview/"), data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.item.cost_allocations.count(), 1)

    def test_purchase_order_reference_is_not_cost_or_fulfillment_ownership(self):
        self.assertEqual(self.item.cost_allocations.get().order_id, self.a.id)
        self.assertEqual(self.client.post(self.url, {
            "version": 0,
            "allocations": [{"purchase_item": self.item.id, "target_type": "inventory", "quantity": "1000"}],
            "expenses": [],
        }, format="json").status_code, 200)
        self.assertEqual(order_purchase_cost(self.a), (Decimal(0), Decimal(0)))
        self.assertEqual(order_item_metrics(self.a.items.get())["purchased_quantity"], Decimal(0))

    def test_version_zero_item_save_does_not_rewrite_existing_allocations(self):
        PurchaseCostAllocation.objects.filter(purchase_item=self.item).delete()
        PurchaseCostAllocation.objects.create(purchase_item=self.item, target_type="order", order=self.b, quantity="60")
        PurchaseCostAllocation.objects.create(purchase_item=self.item, target_type="inventory", quantity="40")
        self.item.unit_price = 12
        self.item.save()
        rows = list(self.item.cost_allocations.order_by("id"))
        self.assertEqual([(row.target_type, row.order_id, row.quantity) for row in rows], [
            ("order", self.b.id, Decimal("60")), ("inventory", None, Decimal("40")),
        ])
