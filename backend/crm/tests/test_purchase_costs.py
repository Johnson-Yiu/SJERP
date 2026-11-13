from datetime import date
from csv import reader
from io import StringIO
from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from crm.models import ContractChangeRequest, Customer, Order, Product, PurchaseOrder, PurchaseCostAllocation, PaymentPlan, SKU, Supplier, Transaction, InventoryMovement
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
        self.assertEqual(self.client.post(self.url, data, format="json").status_code, 400)
        data["expenses"] = []
        self.assertEqual(self.client.post(self.url, data, format="json").status_code, 200)

    def test_legacy_quantity_summary_is_unchanged_until_explicit_amount_save(self):
        second = self.purchase.items.create(sku=self.item.sku, quantity=1000, unit_price=1)
        self.purchase.additional_costs = [{"name": "历史运费", "amount": "1000", "method": "quantity"}]
        self.purchase.save(update_fields=["additional_costs"])
        before = list(self.item.cost_allocations.values())
        for _ in range(2):
            summary = self.client.get(self.url)
            self.assertEqual(summary.status_code, 200)
            self.assertEqual([r["additional_amount"] for r in summary.data["allocations"]], [500, 500])
            self.assertEqual(summary.data["expenses"][0]["method"], "quantity")
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.cost_allocation_version, 0)
        self.assertEqual(self.purchase.additional_costs[0]["method"], "quantity")
        self.assertEqual(list(self.item.cost_allocations.values()), before)
        data = {"version": 0, "allocations": [], "expenses": [{"name": "历史运费", "amount": "1000", "method": "amount"}]}
        preview = self.client.post(self.url.replace("cost-allocation/", "cost-allocation-preview/"), data, format="json")
        self.assertEqual(preview.status_code, 200, preview.data)
        self.assertEqual([r["additional_amount"] for r in preview.data["allocations"]], [Decimal("909.09"), Decimal("90.91")])
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.additional_costs[0]["method"], "quantity")
        saved = self.client.post(self.url, data, format="json")
        self.assertEqual(saved.status_code, 200, saved.data)
        self.assertEqual(saved.data["allocations"], preview.data["allocations"])
        self.assertEqual(saved.data["total_amount"], 12000)

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

    def test_approved_contract_changes_flow_through_cost_and_profit(self):
        self.item.unit_price = Decimal("0.10")
        self.item.save()
        PaymentPlan.objects.create(purchase_order=self.purchase, direction="payable", currency=self.purchase.currency, planned_amount=100)
        for delta, expected in [("-10", 90), ("30", 120)]:
            with self.subTest(delta=delta):
                created = self.client.post("/api/contract-changes/", {
                    "purchase_order": self.purchase.pk, "amount_delta": delta, "notes": "Cost regression",
                }, format="json")
                self.assertEqual(created.status_code, 201, created.data)
                self.assertEqual(self.client.get(self.url).data["total_amount"], self.purchase.total_amount)
                approved = self.client.post(f"/api/contract-changes/{created.data['id']}/approve/", {}, format="json")
                self.assertEqual(approved.status_code, 201, approved.data)
                self.assertEqual(self.purchase.total_amount, expected)
                summary = self.client.get(self.url)
                self.assertEqual(summary.data["total_amount"], expected)
                self.assertEqual(summary.data["base_amount"], 100)
                profit = self.client.get(f"/api/orders/{self.a.pk}/workbench/").data["profit_summary"]
                self.assertEqual(profit["purchase_cost_rmb"], expected * 7)

    def test_signed_tail_and_multiple_attributions(self):
        self.assertEqual(split_amount(Decimal("-0.01"), [Decimal(1)] * 3), [Decimal("-0.01"), 0, 0])
        self.item.unit_price = Decimal("0.08")
        self.item.save()
        second = self.purchase.items.create(sku=self.item.sku, quantity=200, unit_price=Decimal("0.10"))
        ContractChangeRequest.objects.create(purchase_order=self.purchase, status="approved", amount_delta="-10")
        ContractChangeRequest.objects.create(purchase_order=self.purchase, status="pending", amount_delta="20")
        ContractChangeRequest.objects.create(purchase_order=self.purchase, status="rejected", amount_delta="30")
        payload = {"version": 0, "allocations": [
            {"purchase_item": self.item.pk, "target_type": "order", "order": self.a.pk, "quantity": "750"},
            {"purchase_item": self.item.pk, "target_type": "order", "order": self.b.pk, "quantity": "250"},
            {"purchase_item": second.pk, "target_type": "sample", "quantity": "100"},
        ], "expenses": [{"name": "Freight", "amount": "5", "method": "amount"}]}
        preview = self.client.post(self.url.replace("cost-allocation/", "cost-allocation-preview/"), payload, format="json")
        saved = self.client.post(self.url, payload, format="json")
        self.assertEqual(preview.status_code, 200, preview.data)
        self.assertEqual(saved.status_code, 200, saved.data)
        self.assertEqual(preview.data["allocations"], saved.data["allocations"])
        self.assertEqual(saved.data, self.client.get(self.url).data)
        self.assertEqual([row["contract_change_amount"] for row in saved.data["allocations"]], [-6, -2, -1, -1])
        self.assertEqual(saved.data["additional_amount"], 5)
        self.assertEqual(saved.data["total_amount"], 95)
        self.assertEqual(order_purchase_cost(self.a), (378, 21))
        self.assertEqual(order_purchase_cost(self.b), (126, 7))

    def test_zero_weight_with_approved_adjustment_exposes_incomplete_cost(self):
        self.item.unit_price = 0
        self.item.save()
        ContractChangeRequest.objects.create(purchase_order=self.purchase, status="approved", amount_delta="10")
        self.assertEqual(self.client.get(self.url).status_code, 400)
        self.assertEqual(self.client.get(f"/api/orders/{self.a.pk}/workbench/").status_code, 400)

    def test_adjusted_profit_overview_drill_export_and_cash_boundary(self):
        self.a.status = "confirmed"
        self.a.save(update_fields=["status"])
        self.item.unit_price = Decimal("0.10")
        self.item.save()
        ContractChangeRequest.objects.create(purchase_order=self.purchase, status="approved", amount_delta="20")
        for kind, direction, amount in [("supplier_payment", "expense", 35), ("supplier_refund", "income", 5)]:
            Transaction.objects.create(
                transaction_no=f"COST-{kind}", purchase_order=self.purchase, order=self.a,
                transaction_date=date.today(), direction=direction, kind=kind, status="confirmed",
                amount=amount, currency=self.purchase.currency, exchange_rate=self.purchase.exchange_rate,
            )
        tables = (PaymentPlan, Transaction, InventoryMovement)
        before = [list(model.objects.order_by("pk").values()) for model in tables]
        period = {"date_from": self.a.order_date.isoformat(), "date_to": self.a.order_date.isoformat()}
        workbench = self.client.get(f"/api/orders/{self.a.pk}/workbench/")
        profit = workbench.data["profit_summary"]["estimated_profit_rmb"]
        self.assertEqual(workbench.data["profit_summary"]["purchase_cost_rmb"], 840)
        self.assertEqual(profit, self.a.total_amount * self.a.exchange_rate - 840)
        dashboard = self.client.get("/api/finance-dashboard/", period)
        self.assertEqual(dashboard.data["metrics"]["estimated_profit_rmb"], profit)
        drill = self.client.get("/api/finance-dashboard/details/", {**period, "metric": "estimated_profit_rmb"})
        self.assertEqual(drill.data["total_amount"], profit)
        params = {**period, "source": "profit", "group_by": "customer"}
        report = self.client.get("/api/reports/data/", params)
        self.assertEqual(report.data["totals"]["amount"], profit)
        exported = self.client.get("/api/reports/data/", {**params, "export": "csv"})
        self.assertEqual(exported.status_code, 200)
        self.assertEqual(Decimal(list(reader(StringIO(exported.content.decode("utf-8-sig"))))[-1][1]), profit)
        self.assertEqual([list(model.objects.order_by("pk").values()) for model in tables], before)
