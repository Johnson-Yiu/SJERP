from datetime import date
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

from django.test import TestCase
from openpyxl import load_workbook

from crm.models import (
    Customer,
    InventoryMovement,
    Order,
    OrderItem,
    PaymentPlan,
    Product,
    PurchaseOrder,
    PurchaseOrderItem,
    SKU,
    Supplier,
    Transaction,
    ShipmentPackage,
    ShipmentPackageItem,
)
from crm.services.fulfillment import confirm_shipment
from crm.services.order_lifecycle import confirm_order
from crm.services.packing_list import render_packing_list_xlsx
from crm.services.purchase_costs import order_purchase_cost, save_costs
from crm.services.purchase_lifecycle import place_purchase_order


class Unified039037040IntegrationTests(TestCase):
    """Cross-module proof for snapshots, cost allocation, shipment and export."""

    def setUp(self):
        self.day = date(2026, 10, 24)
        self.customer = Customer.objects.create(
            code="INT-039-037-040-C",
            name="集成验收客户（历史名称）",
            country="Germany",
            address="集成验收地址",
        )
        product = Product.objects.create(code="INT-039-037-040-P", name="集成验收灯具")
        self.sku = SKU.objects.create(
            product=product,
            sku="INT-039-037-040-SKU",
            display_name_cn="集成验收灯具",
            description_en="Long English packing description for integration regression",
            unit="pcs",
        )
        self.supplier = Supplier.objects.create(
            code="INT-039-037-040-S",
            name="集成验收供应商（原始名称）",
            address="供应商历史地址",
        )
        self.order = Order.objects.create(
            order_no="INT-SO-039-037-040",
            customer=self.customer,
            order_date=self.day,
            currency="USD",
            exchange_rate="1",
        )
        self.order_item = OrderItem.objects.create(
            order=self.order,
            sku=self.sku,
            quantity="4",
            unit_price="25",
            description_snapshot="Long English packing description for integration regression",
        )

    def test_formal_purchase_cost_shipment_and_packing_list_preserve_history_and_bank_state(self):
        with patch("crm.services.order_lifecycle.allocate_order"):
            confirm_order(self.order)

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "confirmed")
        self.assertEqual(self.order.customer_name_snapshot, "集成验收客户（历史名称）")

        purchase = PurchaseOrder.objects.create(
            purchase_no="INT-PO-039-037-040",
            supplier=self.supplier,
            order=self.order,
            order_date=self.day,
            currency="USD",
            exchange_rate="1",
        )
        purchase_item = PurchaseOrderItem.objects.create(
            purchase_order=purchase,
            sku=self.sku,
            quantity="4",
            unit_price="40",
        )
        with patch("crm.services.purchase_lifecycle.ensure_default_payment_plans"):
            place_purchase_order(purchase)

        purchase.refresh_from_db()
        self.assertEqual(purchase.status, "ordered")
        self.assertEqual(purchase.supplier_name_snapshot, "集成验收供应商（原始名称）")

        self.customer.name = "集成验收客户（主档新名称）"
        self.customer.save(update_fields=["name"])
        self.supplier.name = "集成验收供应商（主档新名称）"
        self.supplier.save(update_fields=["name"])
        self.order.refresh_from_db()
        purchase.refresh_from_db()
        self.assertEqual(self.order.customer_name_snapshot, "集成验收客户（历史名称）")
        self.assertEqual(purchase.supplier_name_snapshot, "集成验收供应商（原始名称）")

        before_bank = {
            "transactions": Transaction.objects.count(),
            "payment_plans": PaymentPlan.objects.count(),
        }
        save_costs(
            purchase,
            {
                "version": purchase.cost_allocation_version,
                "allocations": [
                    {
                        "purchase_item": purchase_item.pk,
                        "target_type": "order",
                        "order": self.order,
                        "quantity": Decimal("4"),
                    }
                ],
                "expenses": [{"name": "公共运费", "amount": "8.00", "method": "amount"}],
            },
        )
        self.assertEqual(
            {
                "transactions": Transaction.objects.count(),
                "payment_plans": PaymentPlan.objects.count(),
            },
            before_bank,
        )
        self.assertEqual(order_purchase_cost(self.order), (Decimal("160.00"), Decimal("8.00")))

        InventoryMovement.objects.create(
            movement_no="INT-IN-039-037-040",
            movement_date=self.day,
            type="adjust_in",
            sku=self.sku,
            quantity="10",
        )
        with patch("crm.services.fulfillment.allocate_order"):
            shipment = confirm_shipment(
                self.order,
                {
                    "shipment_no": "INT-SH-039-037-040",
                    "shipment_date": self.day,
                    "items": [{"order_item": self.order_item.pk, "quantity": "4"}],
                },
            )
        package = ShipmentPackage.objects.create(
            shipment=shipment,
            carton_no=1,
            length="40",
            width="30",
            height="20",
            actual_net_weight="2.0",
            actual_gross_weight="2.5",
        )
        ShipmentPackageItem.objects.create(shipment_package=package, sku=self.sku, quantity="4")

        content = render_packing_list_xlsx(shipment)
        sheet = load_workbook(BytesIO(content), data_only=False).active
        self.assertEqual(sheet.max_column, 16)
        self.assertEqual(sheet["C1"].value, "INT-SH-039-037-040")
        self.assertEqual(sheet["F3"].value, "INT-SO-039-037-040")
        self.assertEqual(sheet["E6"].value, Decimal("4"))
        self.assertEqual(sheet["H6"].value, 1)
        self.assertEqual(sheet["P15"].value, "=SUM(P6:P14)")
        self.assertEqual(sheet.oddFooter.center.text, "Page &P of &N")

        self.assertEqual(Transaction.objects.count(), before_bank["transactions"])
        self.assertEqual(PaymentPlan.objects.count(), before_bank["payment_plans"])
        self.order.refresh_from_db()
        purchase.refresh_from_db()
        self.assertEqual(self.order.customer_name_snapshot, "集成验收客户（历史名称）")
        self.assertEqual(purchase.supplier_name_snapshot, "集成验收供应商（原始名称）")
