from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from crm.models import Customer, Order, Product, PurchaseCostAllocation, PurchaseMOQException, PurchaseOrder, SKU, SKUTradeUnit, Supplier, SupplierSKU
from crm.services.procurement import build_procurement_plan


class PurchaseMOQTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            username="iss022-operator",
            email="iss022@example.com",
            password="test-password",
            first_name="ISS-022 操作员",
        )
        self.client.force_authenticate(self.user)
        self.supplier = Supplier.objects.create(code="ISS022-S", name="ISS-022 供应商")
        self.product = Product.objects.create(code="ISS022-P", name="ISS-022 产品")
        self.sku = SKU.objects.create(product=self.product, sku="ISS022-SKU", unit="pcs")
        self.source = SupplierSKU.objects.create(
            supplier=self.supplier,
            sku=self.sku,
            supplier_sku_code="ISS022-SOURCE",
            purchase_price=Decimal("12.00"),
            currency="CNY",
            moq=Decimal("10"),
        )
        self.customer = Customer.objects.create(code="ISS022-C", name="ISS-022 客户")

    def purchase_payload(self, items, currency="CNY"):
        return {
            "supplier": self.supplier.pk,
            "order_date": date.today().isoformat(),
            "currency": currency,
            "exchange_rate": "1" if currency == "CNY" else "7",
            "items": items,
        }

    def create_purchase(self, quantities, *, source="default", currency="CNY"):
        if source == "default":
            source = self.source
        items = [
            {
                "sku": self.sku.pk,
                "supplier_sku": source.pk if source else None,
                "quantity": str(quantity),
                "unit_price": "8.00",
            }
            for quantity in quantities
        ]
        response = self.client.post("/api/purchase-orders/", self.purchase_payload(items, currency), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response

    def place(self, purchase_id, reason=None):
        payload = {} if reason is None else {"moq_exception_reason": reason}
        return self.client.post(f"/api/purchase-orders/{purchase_id}/place/", payload, format="json")

    def test_low_moq_is_a_soft_warning_and_persists_reason_operator_time_and_po(self):
        created = self.create_purchase([9])

        blocked = self.place(created.data["id"])
        self.assertEqual(blocked.status_code, 400, blocked.data)
        self.assertEqual(blocked.data["code"], "purchase_moq_exception_required", blocked.data)
        self.assertEqual(PurchaseOrder.objects.get(pk=created.data["id"]).status, "draft")
        self.assertFalse(PurchaseMOQException.objects.exists())

        placed = self.place(created.data["id"], "客户指定小批量试单")
        self.assertEqual(placed.status_code, 200, placed.data)
        purchase = PurchaseOrder.objects.get(pk=created.data["id"])
        exception = PurchaseMOQException.objects.get(purchase_order=purchase)
        self.assertEqual(purchase.status, "ordered")
        self.assertEqual(exception.reason, "客户指定小批量试单")
        self.assertEqual(exception.operator, self.user)
        self.assertIsNotNone(exception.created_at)
        self.assertEqual(exception.details[0]["actual_quantity"], "9.00")
        self.assertEqual(exception.details[0]["moq"], "10.00")
        self.assertEqual(exception.details[0]["shortage"], "1.00")
        self.assertEqual(purchase.items.get().unit_price, Decimal("8.00"))
        self.assertEqual(self.source.purchase_price, Decimal("12.0000"))
        self.assertEqual(placed.data["moq_exception"]["reason"], "客户指定小批量试单")
        self.assertEqual(placed.data["moq_exception"]["operator_name"], "ISS-022 操作员")

    def test_equal_and_high_moq_place_without_exception(self):
        for quantity in ("10", "11"):
            with self.subTest(quantity=quantity):
                created = self.create_purchase([quantity])
                placed = self.place(created.data["id"])
                self.assertEqual(placed.status_code, 200, placed.data)
                self.assertIsNone(PurchaseMOQException.objects.filter(purchase_order_id=created.data["id"]).first())

    def test_same_supplier_sku_lines_are_aggregated_in_one_real_po(self):
        created = self.create_purchase(["4", "6"])
        placed = self.place(created.data["id"])
        self.assertEqual(placed.status_code, 200, placed.data)
        purchase = PurchaseOrder.objects.get(pk=created.data["id"])
        self.assertEqual(sum(purchase.items.values_list("quantity", flat=True), Decimal("0")), Decimal("10"))
        self.assertFalse(PurchaseMOQException.objects.filter(purchase_order=purchase).exists())

    def test_two_sales_order_allocations_share_one_po_moq_total(self):
        first = Order.objects.create(
            customer=self.customer,
            order_no="ISS022-SO-A",
            order_date=date.today(),
            status="confirmed",
        )
        second = Order.objects.create(
            customer=self.customer,
            order_no="ISS022-SO-B",
            order_date=date.today(),
            status="confirmed",
        )
        purchase = PurchaseOrder.objects.create(
            purchase_no="ISS022-PO-SHARED",
            supplier=self.supplier,
            order=first,
            order_date=date.today(),
            currency="CNY",
            exchange_rate=1,
        )
        first_item = purchase.items.create(sku=self.sku, supplier_sku=self.source, quantity=4, unit_price=8)
        second_item = purchase.items.create(sku=self.sku, supplier_sku=self.source, quantity=6, unit_price=8)
        PurchaseCostAllocation.objects.filter(purchase_item__in=[first_item, second_item]).delete()
        PurchaseCostAllocation.objects.bulk_create([
            PurchaseCostAllocation(purchase_item=first_item, target_type="order", order=first, quantity=4),
            PurchaseCostAllocation(purchase_item=second_item, target_type="order", order=second, quantity=6),
        ])

        placed = self.place(purchase.pk)

        self.assertEqual(placed.status_code, 200, placed.data)
        self.assertFalse(PurchaseMOQException.objects.filter(purchase_order=purchase).exists())

    def test_trade_units_are_compared_as_base_quantity_and_do_not_invent_extra_qty(self):
        unit = SKUTradeUnit.objects.create(
            sku=self.sku,
            name="十件装",
            unit="box",
            factor=10,
            allow_fraction=True,
        )
        created = self.client.post(
            "/api/purchase-orders/",
            self.purchase_payload([
                {"sku": self.sku.pk, "supplier_sku": self.source.pk, "trade_unit": unit.pk, "trade_quantity": "0.4", "trade_unit_price": "80"},
                {"sku": self.sku.pk, "supplier_sku": self.source.pk, "trade_unit": unit.pk, "trade_quantity": "0.6", "trade_unit_price": "80"},
            ]),
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        placed = self.place(created.data["id"])
        self.assertEqual(placed.status_code, 200, placed.data)
        purchase = PurchaseOrder.objects.get(pk=created.data["id"])
        self.assertEqual(sum(purchase.items.values_list("quantity", flat=True), Decimal("0")), Decimal("10.00"))
        self.assertEqual(sum(purchase.items.values_list("trade_quantity", flat=True), Decimal("0")), Decimal("1.00"))

    def test_missing_moq_does_not_create_an_invented_threshold(self):
        self.source.moq = Decimal("0")
        self.source.save(update_fields=["moq"])
        created = self.create_purchase([1])
        placed = self.place(created.data["id"])
        self.assertEqual(placed.status_code, 200, placed.data)
        self.assertFalse(PurchaseMOQException.objects.filter(purchase_order_id=created.data["id"]).exists())

        without_source = self.create_purchase([1], source=None)
        placed_without_source = self.place(without_source.data["id"])
        self.assertEqual(placed_without_source.status_code, 200, placed_without_source.data)

    def test_single_sales_order_plan_aggregates_repeated_source_lines_before_warning(self):
        order = Order.objects.create(
            customer=self.customer,
            order_no="ISS022-SO-001",
            order_date=date.today(),
            status="confirmed",
        )
        order.items.create(sku=self.sku, supplier_sku=self.source, quantity=Decimal("4"), unit_price=Decimal("10"))
        order.items.create(sku=self.sku, supplier_sku=self.source, quantity=Decimal("6"), unit_price=Decimal("10"))
        plan = build_procurement_plan(order)
        self.assertEqual([row["warnings"] for row in plan["items"]], [[], []])
