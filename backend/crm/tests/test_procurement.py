from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from crm.models import Customer, DocumentNumberSequence, InventoryMovement, Order, Product, PurchaseOrder, SKU, Supplier, SupplierSKU
from crm.services.fulfillment import allocate_order
from crm.services.procurement import build_procurement_plan, create_purchase_drafts
from crm.services.purchase_lifecycle import cancel_purchase_order, place_purchase_order


class ProcurementWorkflowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(code="PC", name="Procurement Customer")
        self.supplier_a = Supplier.objects.create(code="PA", name="Procurement Supplier A")
        self.supplier_b = Supplier.objects.create(code="PB", name="Procurement Supplier B")
        self.sku_a = self.make_sku("A")
        self.sku_b = self.make_sku("B")
        self.sku_c = self.make_sku("C")
        self.source_a_usd = self.make_source(self.supplier_a, self.sku_a, "USD", "2.15", "100", 10)
        self.source_b_usd = self.make_source(self.supplier_a, self.sku_b, "USD", "3.40", "0", 5)
        self.source_a_cny = self.make_source(self.supplier_a, self.sku_c, "CNY", "9.50", "0", 0)
        self.order = Order.objects.create(order_no="SO-PROCUREMENT", customer=self.customer, order_date=date(2031, 1, 1), status="confirmed")

    def make_sku(self, suffix):
        return SKU.objects.create(
            sku=f"PC-SKU-{suffix}",
            product=Product.objects.create(code=f"PC-P-{suffix}", name=f"Procurement Product {suffix}"),
        )

    def make_source(self, supplier, sku, currency, price, moq, lead_time):
        return SupplierSKU.objects.create(
            supplier=supplier, sku=sku, supplier_sku_code=f"{supplier.code}-{sku.sku}",
            currency=currency, purchase_price=Decimal(price), moq=Decimal(moq), lead_time_days=lead_time,
        )

    def add_item(self, sku, source, quantity="100"):
        return self.order.items.create(sku=sku, supplier_sku=source, quantity=Decimal(quantity), unit_price=Decimal("10"))

    def payload(self, groups):
        return {"groups": groups}

    def group(self, supplier, currency, items, exchange_rate=None):
        payload = {"supplier": supplier.id, "currency": currency, "items": items}
        if exchange_rate is not None:
            payload["exchange_rate"] = exchange_rate
        return payload

    def test_plan_separates_shortage_draft_coverage_and_draftable_quantity(self):
        item = self.add_item(self.sku_a, self.source_a_usd)
        InventoryMovement.objects.create(movement_no="PC-STOCK", movement_date=date(2031, 1, 1), type="purchase_in", sku=self.sku_a, quantity=Decimal("20"), warehouse="默认仓")
        allocate_order(self.order)

        plan = build_procurement_plan(self.order)
        row = plan["items"][0]
        self.assertEqual(row["to_procure_quantity"], Decimal("80"))
        self.assertEqual(row["draft_procurement_quantity"], Decimal("0"))
        self.assertEqual(row["draftable_quantity"], Decimal("80"))

        purchase = PurchaseOrder.objects.create(purchase_no="PO-PC-DRAFT", supplier=self.supplier_a, order=self.order, order_date=date(2031, 1, 1), currency="USD")
        purchase.items.create(sku=self.sku_a, supplier_sku=self.source_a_usd, quantity=Decimal("30"), unit_price=Decimal("2.15"))
        row = build_procurement_plan(self.order)["items"][0]
        self.assertEqual(row["draft_procurement_quantity"], Decimal("30"))
        self.assertEqual(row["draftable_quantity"], Decimal("50"))

        purchase.delete()
        self.assertEqual(build_procurement_plan(self.order)["items"][0]["draftable_quantity"], Decimal("80"))
        self.assertEqual(item.pk, item.pk)

    def test_draft_coverage_for_repeated_sku_is_distributed_once_in_item_order(self):
        first = self.add_item(self.sku_a, self.source_a_usd, "60")
        second = self.add_item(self.sku_a, self.source_a_usd, "40")
        purchase = PurchaseOrder.objects.create(purchase_no="PO-PC-SHARED", supplier=self.supplier_a, order=self.order, order_date=date(2031, 1, 1), currency="USD")
        purchase.items.create(sku=self.sku_a, supplier_sku=self.source_a_usd, quantity=Decimal("70"), unit_price=Decimal("2.15"))

        rows = {row["order_item"]: row for row in build_procurement_plan(self.order)["items"]}
        self.assertEqual(rows[first.id]["draft_procurement_quantity"], Decimal("60"))
        self.assertEqual(rows[second.id]["draft_procurement_quantity"], Decimal("10"))
        self.assertEqual(rows[first.id]["draft_procurement_quantity"] + rows[second.id]["draft_procurement_quantity"], Decimal("70"))

    def test_draft_coverage_prefers_matching_supplier_sku_for_repeated_sku(self):
        source_b_sku_a = self.make_source(self.supplier_b, self.sku_a, "USD", "2.35", "0", 5)
        first = self.add_item(self.sku_a, self.source_a_usd, "60")
        second = self.add_item(self.sku_a, source_b_sku_a, "40")
        purchase = PurchaseOrder.objects.create(
            purchase_no="PO-PC-SOURCE-B", supplier=self.supplier_b, order=self.order,
            order_date=date(2031, 1, 1), currency="USD",
        )
        purchase.items.create(sku=self.sku_a, supplier_sku=source_b_sku_a, quantity=Decimal("40"), unit_price=Decimal("2.35"))

        rows = {row["order_item"]: row for row in build_procurement_plan(self.order)["items"]}
        self.assertEqual(rows[first.id]["draft_procurement_quantity"], Decimal("0"))
        self.assertEqual(rows[first.id]["draftable_quantity"], Decimal("60"))
        self.assertEqual(rows[second.id]["draft_procurement_quantity"], Decimal("40"))
        self.assertEqual(rows[second.id]["draftable_quantity"], Decimal("0"))

        rejected = self.client.post(
            f"/api/orders/{self.order.id}/generate-purchase-drafts/",
            self.payload([self.group(self.supplier_b, "USD", [{"order_item": second.id, "quantity": "1", "unit_price": "2.35"}], "7")]),
            format="json",
        )
        self.assertEqual(rejected.status_code, status.HTTP_400_BAD_REQUEST)
        accepted = self.client.post(
            f"/api/orders/{self.order.id}/generate-purchase-drafts/",
            self.payload([self.group(self.supplier_a, "USD", [{"order_item": first.id, "quantity": "60", "unit_price": "2.15"}], "7")]),
            format="json",
        )
        self.assertEqual(accepted.status_code, status.HTTP_201_CREATED, accepted.data)

    def test_source_less_draft_falls_back_to_sku_level_coverage(self):
        first = self.add_item(self.sku_a, self.source_a_usd, "60")
        second = self.add_item(self.sku_a, self.source_a_usd, "40")
        purchase = PurchaseOrder.objects.create(
            purchase_no="PO-PC-LEGACY", supplier=self.supplier_a, order=self.order,
            order_date=date(2031, 1, 1), currency="USD",
        )
        purchase.items.create(sku=self.sku_a, quantity=Decimal("70"), unit_price=Decimal("2.15"))

        rows = {row["order_item"]: row for row in build_procurement_plan(self.order)["items"]}
        self.assertEqual(rows[first.id]["draft_procurement_quantity"], Decimal("60"))
        self.assertEqual(rows[second.id]["draft_procurement_quantity"], Decimal("10"))

    def test_excess_source_specific_draft_falls_back_to_remaining_same_sku_demand(self):
        source_b_sku_a = self.make_source(self.supplier_b, self.sku_a, "USD", "2.35", "0", 5)
        first = self.add_item(self.sku_a, self.source_a_usd, "20")
        second = self.add_item(self.sku_a, source_b_sku_a, "80")
        purchase = PurchaseOrder.objects.create(
            purchase_no="PO-PC-EXCESS", supplier=self.supplier_a, order=self.order,
            order_date=date(2031, 1, 1), currency="USD",
        )
        purchase.items.create(sku=self.sku_a, supplier_sku=self.source_a_usd, quantity=Decimal("50"), unit_price=Decimal("2.15"))

        rows = {row["order_item"]: row for row in build_procurement_plan(self.order)["items"]}
        self.assertEqual(rows[first.id]["draft_procurement_quantity"], Decimal("20"))
        self.assertEqual(rows[second.id]["draft_procurement_quantity"], Decimal("30"))

    def test_generate_groups_by_supplier_and_currency_and_uses_order_snapshots(self):
        first = self.add_item(self.sku_a, self.source_a_usd, "20")
        second = self.add_item(self.sku_b, self.source_b_usd, "30")
        third = self.add_item(self.sku_c, self.source_a_cny, "40")
        response = self.client.post(
            f"/api/orders/{self.order.id}/generate-purchase-drafts/",
            self.payload([
                self.group(self.supplier_a, "USD", [
                    {"order_item": first.id, "quantity": "20", "unit_price": "2.50"},
                    {"order_item": second.id, "quantity": "30", "unit_price": "3.40"},
                ], "7.120000"),
                self.group(self.supplier_a, "CNY", [
                    {"order_item": third.id, "quantity": "40", "unit_price": "9.80"},
                ], "1"),
            ]),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["created_count"], 2)
        purchases = PurchaseOrder.objects.filter(order=self.order).order_by("currency")
        self.assertEqual(purchases.count(), 2)
        self.assertEqual(purchases.get(currency="USD").items.count(), 2)
        self.assertEqual(purchases.get(currency="CNY").exchange_rate, Decimal("1"))
        self.assertEqual(purchases.get(currency="USD").items.get(sku=self.sku_a).unit_price, Decimal("2.50"))

    def test_generation_revalidates_quantities_and_currency_exchange_rules(self):
        item = self.add_item(self.sku_a, self.source_a_usd, "20")
        response = self.client.post(
            f"/api/orders/{self.order.id}/generate-purchase-drafts/",
            self.payload([self.group(self.supplier_a, "USD", [{"order_item": item.id, "quantity": "20", "unit_price": "2.15"}])]),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("汇率", response.data["detail"])

        response = self.client.post(
            f"/api/orders/{self.order.id}/generate-purchase-drafts/",
            self.payload([self.group(self.supplier_a, "USD", [{"order_item": item.id, "quantity": "21", "unit_price": "2.15"}], "7")]),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("不能超过", response.data["detail"])
        self.assertEqual(PurchaseOrder.objects.count(), 0)

    def test_only_confirmed_or_production_orders_can_generate_and_cancelled_order_purchase_cannot_place(self):
        item = self.add_item(self.sku_a, self.source_a_usd, "20")
        payload = self.payload([self.group(self.supplier_a, "USD", [{"order_item": item.id, "quantity": "20", "unit_price": "2.15"}], "7")])
        for state in ("draft", "shipped", "completed", "cancelled"):
            self.order.status = state
            self.order.save(update_fields=["status"])
            response = self.client.post(f"/api/orders/{self.order.id}/generate-purchase-drafts/", payload, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.order.status = "confirmed"
        self.order.save(update_fields=["status"])
        purchase = create_purchase_drafts(self.order, payload)[0]
        self.order.status = "cancelled"
        self.order.save(update_fields=["status"])
        response = self.client.post(f"/api/purchase-orders/{purchase.id}/place/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("关联销售订单", response.data["detail"])

    def test_non_generatable_status_keeps_plan_amounts_but_blocks_every_item(self):
        item = self.add_item(self.sku_a, self.source_a_usd, "20")
        for state in ("draft", "shipped", "completed", "cancelled"):
            self.order.status = state
            self.order.save(update_fields=["status"])
            row = build_procurement_plan(self.order)["items"][0]
            self.assertEqual(row["order_item"], item.id)
            self.assertEqual(row["to_procure_quantity"], Decimal("20"))
            self.assertEqual(row["draftable_quantity"], Decimal("20"))
            self.assertFalse(row["can_generate"])
            self.assertEqual(row["blocking_reason"], "当前销售订单状态不允许生成采购草稿。")

    def test_missing_inactive_mismatched_or_currency_changed_source_is_blocked(self):
        item = self.order.items.create(sku=self.sku_a, quantity=Decimal("10"), unit_price=Decimal("10"))
        self.assertIn("请先选择", build_procurement_plan(self.order)["items"][0]["blocking_reason"])
        item.supplier_sku = self.source_a_usd
        item.supplier_currency_snapshot = "CNY"
        item.save(update_fields=["supplier_sku", "supplier_currency_snapshot"])
        self.assertIn("币种", build_procurement_plan(self.order)["items"][0]["blocking_reason"])
        item.supplier_currency_snapshot = "USD"
        item.save(update_fields=["supplier_currency_snapshot"])
        self.source_a_usd.is_active = False
        self.source_a_usd.save(update_fields=["is_active"])
        self.assertIn("已停用", build_procurement_plan(self.order)["items"][0]["blocking_reason"])

    def test_generation_rechecks_the_currently_locked_supplier_source(self):
        item = self.add_item(self.sku_a, self.source_a_usd, "10")
        self.source_a_usd.is_active = False
        self.source_a_usd.save(update_fields=["is_active"])
        with self.assertRaisesRegex(ValidationError, "已停用"):
            create_purchase_drafts(
                self.order,
                self.payload([self.group(self.supplier_a, "USD", [{"order_item": item.id, "quantity": "10", "unit_price": "2.15"}], "7")]),
            )

    def test_place_moves_draft_coverage_to_formal_procurement_and_cancel_restores_shortage(self):
        item = self.add_item(self.sku_a, self.source_a_usd, "30")
        purchase = PurchaseOrder.objects.create(purchase_no="PO-PC-PLACE", supplier=self.supplier_a, order=self.order, order_date=date(2031, 1, 1), currency="USD", exchange_rate=Decimal("7"))
        purchase.items.create(sku=self.sku_a, supplier_sku=self.source_a_usd, quantity=Decimal("30"), unit_price=Decimal("2.15"))
        self.assertEqual(build_procurement_plan(self.order)["items"][0]["draft_procurement_quantity"], Decimal("30"))

        place_purchase_order(purchase, moq_exception_reason="本次采购按客户小批量需求执行。")
        row = build_procurement_plan(self.order)["items"][0]
        self.assertEqual(row["draft_procurement_quantity"], Decimal("0"))
        self.assertEqual(row["to_procure_quantity"], Decimal("0"))
        cancel_purchase_order(purchase, "订单取消")
        self.assertEqual(build_procurement_plan(self.order)["items"][0]["to_procure_quantity"], Decimal("30"))
        self.assertEqual(item.id, item.id)

    def test_batch_failure_rolls_back_all_drafts_and_purchase_number_sequence(self):
        first = self.add_item(self.sku_a, self.source_a_usd, "10")
        second = self.add_item(self.sku_b, self.source_b_usd, "10")
        with self.assertRaises(ValidationError):
            create_purchase_drafts(self.order, self.payload([
                self.group(self.supplier_a, "USD", [{"order_item": first.id, "quantity": "10", "unit_price": "2"}], "7"),
                self.group(self.supplier_b, "USD", [{"order_item": second.id, "quantity": "10", "unit_price": "3"}], "7"),
            ]))
        self.assertEqual(PurchaseOrder.objects.count(), 0)
        self.assertFalse(DocumentNumberSequence.objects.filter(document_type="PO", year=date.today().year).exists())


class PurchaseOrderListFilterTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        customer = Customer.objects.create(code="PO-FILTER-C", name="Filter Customer")
        self.supplier_a = Supplier.objects.create(code="FA", name="Filter Supplier Alpha")
        self.supplier_b = Supplier.objects.create(code="FB", name="Filter Supplier Beta")
        self.order_a = Order.objects.create(
            order_no="SO-FILTER-001", customer=customer, order_date=date(2031, 1, 1), status="confirmed",
        )
        self.order_b = Order.objects.create(
            order_no="SO-FILTER-002", customer=customer, order_date=date(2031, 1, 2), status="confirmed",
        )
        self.order_c = Order.objects.create(
            order_no="SO-FILTER-003", customer=customer, order_date=date(2031, 1, 3), status="confirmed",
        )
        self.purchase("PO-FILTER-001", self.supplier_a, self.order_a, "draft")
        self.purchase("PO-FILTER-002", self.supplier_a, self.order_b, "ordered")
        self.purchase("PO-FILTER-003", self.supplier_b, self.order_b, "partial")
        self.purchase("PO-FILTER-004", self.supplier_b, self.order_c, "completed")
        self.purchase("PO-FILTER-005", self.supplier_a, self.order_c, "cancelled")

    @staticmethod
    def purchase(purchase_no, supplier, order, purchase_status):
        return PurchaseOrder.objects.create(
            purchase_no=purchase_no,
            supplier=supplier,
            order=order,
            order_date=date(2031, 1, 1),
            status=purchase_status,
        )

    def purchase_numbers(self, **params):
        response = self.client.get("/api/purchase-orders/", params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = response.data.get("results", response.data)
        return {row["purchase_no"] for row in rows}

    def test_search_matches_purchase_number(self):
        self.assertEqual(self.purchase_numbers(search="PO-FILTER-001"), {"PO-FILTER-001"})

    def test_search_matches_supplier_name(self):
        self.assertEqual(
            self.purchase_numbers(search="Filter Supplier Beta"),
            {"PO-FILTER-003", "PO-FILTER-004"},
        )

    def test_search_matches_source_order_number(self):
        self.assertEqual(
            self.purchase_numbers(search="SO-FILTER-002"),
            {"PO-FILTER-002", "PO-FILTER-003"},
        )

    def test_status_filter_is_exact(self):
        self.assertEqual(self.purchase_numbers(status="ordered"), {"PO-FILTER-002"})

    def test_pending_receipt_includes_only_ordered_and_partial(self):
        self.assertEqual(
            self.purchase_numbers(pending_receipt="1"),
            {"PO-FILTER-002", "PO-FILTER-003"},
        )

    def test_search_combines_with_pending_receipt_filter(self):
        self.assertEqual(
            self.purchase_numbers(search="PO-FILTER-00", pending_receipt="1"),
            {"PO-FILTER-002", "PO-FILTER-003"},
        )
