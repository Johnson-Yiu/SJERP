from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from crm.models import Customer, OperationLog, PaymentPlan, Product, PurchaseMOQException, PurchaseOrder, SKU, SKUTradeUnit, Supplier, SupplierSKU


class PurchaseMOQTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.operator = get_user_model().objects.create_user(username="moq-operator")
        self.client.force_authenticate(user=self.operator)
        # The published historical schema stores country as an ISO-style two-character
        # value even though the current model accepts longer display names.
        self.supplier = Supplier.objects.create(code="MS", name="MOQ 供应商", country="CN")
        self.other_supplier = Supplier.objects.create(code="MT", name="另一供应商", country="CN")
        self.product = Product.objects.create(code="MOQ-P", name="MOQ 测试产品")
        self.sku = SKU.objects.create(sku="MOQ-SKU", product=self.product, unit="pcs", display_name_cn="MOQ 测试 SKU")
        self.source = SupplierSKU.objects.create(
            supplier=self.supplier,
            sku=self.sku,
            supplier_sku_code="MOQ-SOURCE-A",
            purchase_price=Decimal("2.50"),
            currency="CNY",
            moq=Decimal("100"),
        )

    def create_purchase(self, *, quantity="100", supplier_sku=None, supplier=None, items=None):
        payload_items = items or [{
            "sku": self.sku.pk,
            "supplier_sku": supplier_sku.pk if supplier_sku else None,
            "quantity": quantity,
            "unit_price": "2.50",
        }]
        response = self.client.post("/api/purchase-orders/", {
            "supplier": (supplier or self.supplier).pk,
            "order_date": date(2031, 1, 1).isoformat(),
            "currency": "CNY",
            "exchange_rate": "1",
            "items": payload_items,
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return PurchaseOrder.objects.get(pk=response.data["id"])

    def place(self, purchase, reason=None):
        payload = {} if reason is None else {"moq_exception_reason": reason}
        return self.client.post(f"/api/purchase-orders/{purchase.pk}/place/", payload, format="json")

    def test_zero_equal_above_and_manual_source_purchases_are_not_blocked(self):
        self.source.moq = 0
        self.source.save(update_fields=["moq"])
        self.assertEqual(self.place(self.create_purchase(quantity="1", supplier_sku=self.source)).status_code, status.HTTP_200_OK)

        self.source.moq = 10
        self.source.save(update_fields=["moq"])
        self.assertEqual(self.place(self.create_purchase(quantity="10", supplier_sku=self.source)).status_code, status.HTTP_200_OK)
        self.assertEqual(self.place(self.create_purchase(quantity="11", supplier_sku=self.source)).status_code, status.HTTP_200_OK)
        self.assertEqual(self.place(self.create_purchase(quantity="1", supplier=self.other_supplier)).status_code, status.HTTP_200_OK)

    def test_below_moq_requires_reason_and_does_not_change_draft_or_payment(self):
        purchase = self.create_purchase(quantity="30", supplier_sku=self.source)

        response = self.place(purchase)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertEqual(response.data["code"], "purchase_moq_exception_required")
        self.assertEqual(response.data["exceptions"][0]["actual_quantity"], "30.00")
        self.assertEqual(response.data["exceptions"][0]["moq"], "100.00")
        self.assertEqual(response.data["exceptions"][0]["shortage"], "70.00")
        purchase.refresh_from_db()
        self.assertEqual(purchase.status, "draft")
        self.assertFalse(PaymentPlan.objects.filter(purchase_order=purchase).exists())
        self.assertFalse(PurchaseMOQException.objects.filter(purchase_order=purchase).exists())

    @override_settings(AUDIT_LOG_ENABLED=True)
    def test_reason_places_and_preserves_exception_and_operation_evidence(self):
        purchase = self.create_purchase(quantity="30", supplier_sku=self.source)

        response = self.place(purchase, "客户要求先做小批量试单，采购已确认需求量。")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        purchase.refresh_from_db()
        exception = PurchaseMOQException.objects.get(purchase_order=purchase)
        self.assertEqual(purchase.status, "ordered")
        self.assertEqual(exception.reason, "客户要求先做小批量试单，采购已确认需求量。")
        self.assertEqual(exception.operator_id, self.operator.pk)
        self.assertEqual(exception.details[0]["purchase_item_ids"], [purchase.items.get().pk])
        self.assertEqual(response.data["moq_exception"]["details"][0]["base_unit"], "pcs")
        log = OperationLog.objects.filter(entity="crm.purchaseorder", object_id=str(purchase.pk), action_label="确认采购下单").first()
        self.assertIsNotNone(log)
        self.assertEqual(log.metadata["moq_exception_id"], exception.pk)
        self.assertEqual(log.metadata["moq_exception_details"][0]["shortage"], "70.00")

    def test_same_supplier_sku_lines_are_summed_in_base_units(self):
        unit = SKUTradeUnit.objects.create(
            sku=self.sku,
            supplier=self.supplier,
            name="10 件/箱",
            unit="箱",
            factor=10,
            is_default=True,
        )
        purchase = self.create_purchase(
            supplier_sku=self.source,
            items=[
                {"sku": self.sku.pk, "supplier_sku": self.source.pk, "trade_unit": unit.pk, "trade_quantity": "2", "trade_unit_price": "25"},
                {"sku": self.sku.pk, "supplier_sku": self.source.pk, "trade_unit": unit.pk, "trade_quantity": "3", "trade_unit_price": "25"},
            ],
        )

        response = self.place(purchase)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertEqual(len(response.data["exceptions"]), 1)
        self.assertEqual(response.data["exceptions"][0]["actual_quantity"], "50.00")
        self.assertEqual(response.data["exceptions"][0]["base_unit"], "pcs")
        self.assertEqual(response.data["exceptions"][0]["shortage"], "50.00")
        self.assertEqual(set(response.data["exceptions"][0]["purchase_item_ids"]), set(purchase.items.values_list("pk", flat=True)))

    def test_different_supplier_skus_are_not_merged(self):
        source_b = SupplierSKU.objects.create(
            supplier=self.supplier,
            sku=self.sku,
            supplier_sku_code="MOQ-SOURCE-B",
            purchase_price=Decimal("2.60"),
            currency="CNY",
            moq=Decimal("100"),
        )
        purchase = self.create_purchase(
            items=[
                {"sku": self.sku.pk, "supplier_sku": self.source.pk, "quantity": "60", "unit_price": "2.50"},
                {"sku": self.sku.pk, "supplier_sku": source_b.pk, "quantity": "60", "unit_price": "2.60"},
            ],
        )

        response = self.place(purchase)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertEqual({row["supplier_sku_code"] for row in response.data["exceptions"]}, {"MOQ-SOURCE-A", "MOQ-SOURCE-B"})
        self.assertEqual({row["actual_quantity"] for row in response.data["exceptions"]}, {"60.00"})

    def test_recheck_uses_saved_quantity_and_failure_is_atomic(self):
        purchase = self.create_purchase(quantity="30", supplier_sku=self.source)
        self.assertEqual(self.place(purchase).status_code, status.HTTP_400_BAD_REQUEST)
        purchase.items.update(quantity=Decimal("100"))
        self.assertEqual(self.place(purchase).status_code, status.HTTP_200_OK)
        self.assertFalse(PurchaseMOQException.objects.filter(purchase_order=purchase).exists())

        failed = self.create_purchase(quantity="30", supplier_sku=self.source)
        with patch("crm.services.purchase_lifecycle.ensure_default_payment_plans", side_effect=ValidationError("付款计划失败")):
            response = self.place(failed, "采购测试失败回滚")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        failed.refresh_from_db()
        self.assertEqual(failed.status, "draft")
        self.assertFalse(PaymentPlan.objects.filter(purchase_order=failed).exists())
        self.assertFalse(PurchaseMOQException.objects.filter(purchase_order=failed).exists())

    @override_settings(RBAC_ENFORCEMENT=True, DEVELOPMENT_SUPERADMIN=False)
    def test_user_without_purchase_update_cannot_bypass_place_endpoint(self):
        purchase = PurchaseOrder.objects.create(
            purchase_no="PO-MOQ-AUTH", supplier=self.supplier, order_date=date(2031, 1, 1), currency="CNY", exchange_rate=1,
        )
        purchase.items.create(sku=self.sku, supplier_sku=self.source, quantity=30, unit_price=2.5)
        limited = get_user_model().objects.create_user(username="moq-limited")
        client = APIClient()
        client.force_authenticate(user=limited)

        response = client.post(f"/api/purchase-orders/{purchase.pk}/place/", {"moq_exception_reason": "绕过权限"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        purchase.refresh_from_db()
        self.assertEqual(purchase.status, "draft")
