from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from crm.models import Customer, InventoryMovement, InventoryReservation, Order, Product, PurchaseOrder, SKU, Supplier
from crm.services.finance import ensure_default_payment_plans
from crm.services.fulfillment import record_receipt, reverse_receipt, sku_metrics


class PurchaseOverageProjectionTests(TestCase):
    def setUp(self):
        self.day = date(2031, 1, 2)
        self.customer = Customer.objects.create(code="C-OVERAGE", name="Overage Buyer")
        self.supplier = Supplier.objects.create(code="OG", name="Overage Supplier")
        self.sku = SKU.objects.create(product=Product.objects.create(code="P-OVERAGE", name="Overage Light"), sku="SKU-OVERAGE")
        self.order = Order.objects.create(order_no="SO-OVERAGE", customer=self.customer, order_date=self.day, status="confirmed")
        self.purchase = PurchaseOrder.objects.create(
            purchase_no="PO-OVERAGE", supplier=self.supplier, order=self.order,
            order_date=self.day, status="ordered", currency="USD", exchange_rate=Decimal("1"),
            payment_terms_snapshot=[{"label": "全款", "ratio": "1", "due_basis": "no_date", "offset_days": 0}],
        )
        self.item = self.purchase.items.create(sku=self.sku, quantity=Decimal("10"), unit_price=Decimal("5"))

    def test_mixed_overage_is_projected_separately_and_receipt_reversal_restores_contract_progress(self):
        plan = ensure_default_payment_plans(self.purchase)[0]
        planned_amount = plan.planned_amount
        receipt = record_receipt(self.item, {
            "receipt_date": self.day, "quantity": Decimal("15"), "unit_cost": Decimal("5"),
            "is_overage": True, "overage_reason": "gift",
        })
        self.item.refresh_from_db()
        self.purchase.refresh_from_db()
        plan.refresh_from_db()

        self.assertEqual(self.item.received_quantity, Decimal("15"))
        self.assertEqual(self.item.remaining_quantity, Decimal("0"))
        self.assertEqual(self.item.overage_quantity, Decimal("5"))
        self.assertEqual(receipt.overage_quantity, Decimal("5"))
        self.assertEqual(receipt.inventory_movement.overage_quantity, Decimal("5"))
        self.assertEqual(self.purchase.status, "completed")
        self.assertEqual(plan.planned_amount, planned_amount)

        reverse_receipt(receipt, "验收时发现赠品数量录错")
        self.item.refresh_from_db()
        self.purchase.refresh_from_db()
        plan.refresh_from_db()

        self.assertEqual(self.item.received_quantity, Decimal("0"))
        self.assertEqual(self.item.remaining_quantity, Decimal("10"))
        self.assertEqual(self.item.overage_quantity, Decimal("0"))
        self.assertEqual(receipt.overage_quantity, Decimal("5"))
        self.assertEqual(self.purchase.status, "ordered")
        self.assertEqual(plan.planned_amount, planned_amount)

    def test_reversed_receipt_ledger_resolves_explicit_link_without_changing_source(self):
        from crm.serializers import InventoryMovementSerializer
        receipt = record_receipt(self.item, {"receipt_date": self.day, "quantity": Decimal("2"), "unit_cost": Decimal("5")})
        original = receipt.inventory_movement
        reverse_receipt(receipt, "核对原流水冲销标识")
        receipt.refresh_from_db()
        result = InventoryMovementSerializer(original).data
        self.assertTrue(result["is_reversed"])
        self.assertEqual(result["reversal_movement"]["id"], receipt.reversal_inventory_movement_id)
        self.assertIn("已冲销", result["reversal_status"])
        self.assertEqual(result["source_no"], self.purchase.purchase_no)


    def test_overage_after_a_reversed_overage_and_partial_re_receipt_uses_creation_time_active_quantity(self):
        receipt_a = record_receipt(self.item, {
            "receipt_date": self.day, "quantity": Decimal("15"), "unit_cost": Decimal("5"),
            "is_overage": True, "overage_reason": "gift",
        })
        reverse_receipt(receipt_a, "超到历史冲销")
        receipt_b = record_receipt(self.item, {
            "receipt_date": self.day, "quantity": Decimal("5"), "unit_cost": Decimal("5"),
        })
        receipt_c = record_receipt(self.item, {
            "receipt_date": self.day, "quantity": Decimal("10"), "unit_cost": Decimal("5"),
            "is_overage": True, "overage_reason": "overprocurement",
        })

        origin = timezone.now()
        type(receipt_a).objects.filter(pk=receipt_a.pk).update(created_at=origin, reversed_at=origin + timedelta(seconds=1))
        type(receipt_b).objects.filter(pk=receipt_b.pk).update(created_at=origin + timedelta(seconds=2))
        type(receipt_c).objects.filter(pk=receipt_c.pk).update(created_at=origin + timedelta(seconds=3))
        receipt_a.refresh_from_db()
        receipt_b.refresh_from_db()
        receipt_c.refresh_from_db()
        self.item.refresh_from_db()

        self.assertEqual(receipt_a.overage_quantity, Decimal("5"))
        self.assertEqual(receipt_b.overage_quantity, Decimal("0"))
        self.assertEqual(receipt_c.overage_quantity, Decimal("5"))
        self.assertEqual(self.item.received_quantity, Decimal("15"))
        self.assertEqual(self.item.remaining_quantity, Decimal("0"))
        self.assertEqual(self.item.overage_quantity, Decimal("5"))

    def test_later_reversal_does_not_rewrite_a_later_receipts_historical_overage(self):
        receipt_a = record_receipt(self.item, {
            "receipt_date": self.day, "quantity": Decimal("8"), "unit_cost": Decimal("5"),
        })
        receipt_b = record_receipt(self.item, {
            "receipt_date": self.day, "quantity": Decimal("5"), "unit_cost": Decimal("5"),
            "is_overage": True, "overage_reason": "gift",
        })
        reverse_receipt(receipt_a, "后续发现数量有误")

        origin = timezone.now()
        type(receipt_a).objects.filter(pk=receipt_a.pk).update(created_at=origin, reversed_at=origin + timedelta(seconds=2))
        type(receipt_b).objects.filter(pk=receipt_b.pk).update(created_at=origin + timedelta(seconds=1))
        receipt_b.refresh_from_db()

        self.assertEqual(receipt_b.overage_quantity, Decimal("3"))


class InventoryMovementReversalApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.day = "2031-01-02"
        self.customer = Customer.objects.create(code="C-IM-REV", name="Inventory Reversal Buyer")
        self.sku = SKU.objects.create(product=Product.objects.create(code="P-IM-REV", name="Inventory Reversal Light"), sku="SKU-IM-REV")

    def create_manual(self, movement_type, quantity):
        response = self.client.post("/api/inventory-movements/", {
            "movement_date": self.day, "type": movement_type, "sku": self.sku.id, "quantity": str(quantity),
        }, format="json", HTTP_IDEMPOTENCY_KEY=f"reversal-fixture-{uuid4()}")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return InventoryMovement.objects.get(pk=response.data["id"])

    def test_manual_inbound_reversal_preserves_original_and_blocks_delete_and_duplicate(self):
        original = self.create_manual("adjust_in", Decimal("10"))
        deleted = self.client.delete(f"/api/inventory-movements/{original.id}/")
        self.assertEqual(deleted.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(deleted.data["detail"], "库存流水属于库存审计记录，不能直接删除，请使用冲销。")
        self.assertTrue(InventoryMovement.objects.filter(pk=original.pk).exists())

        response = self.client.post(f"/api/inventory-movements/{original.id}/reverse/", {"reason": "盘点登记错误"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        reversal = InventoryMovement.objects.get(pk=response.data["id"])
        self.assertEqual(reversal.type, "adjust_out")
        self.assertEqual(reversal.source_type, "reversal")
        self.assertEqual(reversal.source_no, original.movement_no)
        self.assertTrue(reversal.is_automatic)
        self.assertIn("盘点登记错误", reversal.notes)
        self.assertEqual(sku_metrics(self.sku)["actual_quantity"], Decimal("0"))

        duplicate = self.client.post(f"/api/inventory-movements/{original.id}/reverse/", {"reason": "重复"}, format="json")
        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("已经冲销", duplicate.data["detail"])

    def test_manual_outbound_reversal_restores_stock(self):
        self.create_manual("adjust_in", Decimal("10"))
        outgoing = self.create_manual("adjust_out", Decimal("4"))
        response = self.client.post(f"/api/inventory-movements/{outgoing.id}/reverse/", {"reason": "盘亏复核撤回"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["type"], "adjust_in")
        self.assertEqual(sku_metrics(self.sku)["actual_quantity"], Decimal("10"))

    def test_reversal_cannot_consume_stock_reserved_for_an_active_order(self):
        order = Order.objects.create(order_no="SO-IM-RES", customer=self.customer, order_date=date(2031, 1, 2), status="confirmed")
        order.items.create(sku=self.sku, quantity=Decimal("8"), unit_price=Decimal("1"))
        original = self.create_manual("adjust_in", Decimal("10"))
        self.assertEqual(InventoryReservation.objects.filter(sku=self.sku).count(), 1)
        response = self.client.post(f"/api/inventory-movements/{original.id}/reverse/", {"reason": "需要撤回"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("当前可用库存不足", response.data["detail"])
        self.assertEqual(InventoryMovement.objects.filter(source_type="reversal", source_no=original.movement_no).count(), 0)
        self.assertEqual(sku_metrics(self.sku)["actual_quantity"], Decimal("10"))
        self.assertEqual(sku_metrics(self.sku)["reserved_quantity"], Decimal("8"))

    def test_automatic_purchase_and_sale_movements_require_their_business_documents(self):
        purchase = InventoryMovement.objects.create(movement_no="IM-AUTO-PURCHASE", movement_date=date(2031, 1, 2), type="purchase_in", sku=self.sku, quantity=Decimal("3"), is_automatic=True, source_type="receipt")
        sale = InventoryMovement.objects.create(movement_no="IM-AUTO-SALE", movement_date=date(2031, 1, 2), type="sale_out", sku=self.sku, quantity=Decimal("1"), is_automatic=True, source_type="shipment")
        purchase_response = self.client.post(f"/api/inventory-movements/{purchase.id}/reverse/", {"reason": "错误"}, format="json")
        sale_response = self.client.post(f"/api/inventory-movements/{sale.id}/reverse/", {"reason": "错误"}, format="json")
        self.assertEqual(purchase_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(purchase_response.data["detail"], "采购入库请从采购到货记录执行冲销。")
        self.assertEqual(sale_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(sale_response.data["detail"], "销售出库请从发货记录执行冲销。")
