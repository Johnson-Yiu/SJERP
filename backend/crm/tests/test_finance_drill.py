from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from crm.models import Customer, Order, PaymentPlan, Product, PurchaseOrder, SKU, Supplier, Transaction


class FinanceDashboardDrillTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(code="FIN-DRILL-C", name="明细客户")
        product = Product.objects.create(code="FIN-DRILL-P", name="明细产品")
        self.sku = SKU.objects.create(product=product, sku="FIN-DRILL-SKU")
        self.order = Order.objects.create(
            order_no="FIN-DRILL-SO",
            customer=self.customer,
            order_date=date(2026, 9, 1),
            currency="USD",
            exchange_rate=Decimal("2"),
            status="confirmed",
        )
        self.order.items.create(sku=self.sku, quantity=Decimal("2"), unit_price=Decimal("10"))
        self.historical = Order.objects.create(
            order_no="FIN-DRILL-HISTORY",
            customer=self.customer,
            order_date=date(2026, 9, 2),
            currency="CNY",
            exchange_rate=1,
            status="confirmed",
            historical_only=True,
        )
        self.historical.items.create(sku=self.sku, quantity=1, unit_price=999)
        for number, status, order_date, amount in (
            ("FIN-DRILL-DRAFT", "draft", date(2026, 9, 3), 800),
            ("FIN-DRILL-FUTURE", "confirmed", date(2026, 10, 1), 700),
        ):
            order = Order.objects.create(
                order_no=number, customer=self.customer, order_date=order_date,
                currency="CNY", exchange_rate=1, status=status,
            )
            order.items.create(sku=self.sku, quantity=1, unit_price=amount)
        self.plan = PaymentPlan.objects.create(
            order=self.order, direction="receivable", currency="USD",
            planned_amount=Decimal("100"), settled_amount=Decimal("10"), status="open",
        )
        PaymentPlan.objects.create(
            order=self.order, direction="receivable", currency="USD",
            planned_amount=Decimal("25"), status="open",
        )
        Transaction.objects.create(
            transaction_no="FIN-DRILL-IN", transaction_date=date(2026, 9, 5),
            direction="income", kind="other_income", category="收款",
            amount=Decimal("30"), rmb_amount=Decimal("30"), currency="USD", exchange_rate=7,
        )
        Transaction.objects.create(
            transaction_no="FIN-DRILL-OUT", transaction_date=date(2026, 9, 6),
            direction="expense", kind="other", category="费用",
            amount=Decimal("4"), rmb_amount=Decimal("4"), currency="CNY", exchange_rate=1,
        )
        Transaction.objects.create(
            transaction_no="FIN-DRILL-FUTURE-CASH", transaction_date=date(2026, 10, 1),
            direction="income", kind="other_income", category="未来收款",
            amount=Decimal("90"), rmb_amount=Decimal("90"), currency="CNY", exchange_rate=1,
        )
        Transaction.objects.create(
            transaction_no="FIN-DRILL-PENDING", transaction_date=date(2026, 9, 7),
            direction="income", kind="other_income", category="待确认",
            amount=Decimal("80"), rmb_amount=Decimal("80"), currency="CNY", exchange_rate=1,
            status="pending",
        )

    def get_detail(self, metric, **params):
        response = self.client.get(
            "/api/finance-dashboard/details/",
            {"metric": metric, "date_from": "2026-09-01", "date_to": "2026-09-30", **params},
        )
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def test_sales_drill_matches_dashboard_and_excludes_history_status_and_future(self):
        dashboard = self.client.get("/api/finance-dashboard/", {"date_from": "2026-09-01", "date_to": "2026-09-30"})
        detail = self.get_detail("sales_rmb")
        self.assertEqual(dashboard.data["metrics"]["sales_rmb"], Decimal("40"))
        self.assertEqual(detail["total_amount"], dashboard.data["metrics"]["sales_rmb"])
        self.assertEqual(detail["total_count"], 1)
        self.assertEqual([row["record_label"] for row in detail["rows"]], ["FIN-DRILL-SO"])
        self.assertEqual(detail["date_basis"], "order_date")
        self.assertEqual(detail["rows"][0]["detail_url"], f"/orders?detail={self.order.pk}")

    def test_book_cash_drill_matches_confirmed_transaction_date_scope(self):
        dashboard = self.client.get("/api/finance-dashboard/", {"date_from": "2026-09-01", "date_to": "2026-09-30"})
        income = self.get_detail("income_rmb")
        expense = self.get_detail("expense_rmb")
        net = self.get_detail("net_cash_rmb")
        self.assertEqual(income["total_amount"], dashboard.data["metrics"]["income_rmb"])
        self.assertEqual(expense["total_amount"], dashboard.data["metrics"]["expense_rmb"])
        self.assertEqual(net["total_amount"], dashboard.data["metrics"]["net_cash_rmb"])
        self.assertEqual([row["record_label"] for row in income["rows"]], ["FIN-DRILL-IN"])
        self.assertEqual([row["record_label"] for row in expense["rows"]], ["FIN-DRILL-OUT"])
        self.assertEqual(net["rows"][0]["amount"] + net["rows"][1]["amount"], Decimal("26"))
        self.assertTrue(all(row["status_label"] == "已确认" for row in net["rows"]))

    def test_current_balance_drill_is_explicit_and_paginated(self):
        detail = self.get_detail("receivable_rmb", page=2, page_size=1)
        self.assertTrue(detail["current_balance"])
        self.assertEqual(detail["date_basis"], "current_balance")
        self.assertEqual(detail["total_count"], 2)
        self.assertEqual(detail["total_amount"], Decimal("230"))
        self.assertEqual(detail["page"], 2)
        self.assertFalse(detail["has_more"])
        self.assertEqual(len(detail["rows"]), 1)
        self.assertEqual(detail["rows"][0]["detail_url"], f"/orders?detail={self.order.pk}")

    def test_profit_drill_uses_the_same_order_profit_service_as_the_card(self):
        Transaction.objects.create(
            transaction_no="FIN-DRILL-ORDER-EXP", transaction_date=date(2026, 9, 8),
            direction="expense", kind="other", category="订单费用", order=self.order,
            amount=Decimal("3"), rmb_amount=Decimal("3"), currency="CNY", exchange_rate=1,
        )
        dashboard = self.client.get("/api/finance-dashboard/", {"date_from": "2026-09-01", "date_to": "2026-09-30"})
        detail = self.get_detail("estimated_profit_rmb")
        self.assertEqual(dashboard.data["metrics"]["order_expense_rmb"], Decimal("3"))
        self.assertEqual(dashboard.data["metrics"]["estimated_profit_rmb"], Decimal("37"))
        self.assertEqual(detail["total_amount"], dashboard.data["metrics"]["estimated_profit_rmb"])
        self.assertEqual(detail["rows"][0]["amount"], Decimal("37"))

    def test_payable_drill_links_to_the_existing_purchase_order(self):
        supplier = Supplier.objects.create(code="FD", name="明细供应商")
        purchase = PurchaseOrder.objects.create(
            purchase_no="FIN-DRILL-PO", supplier=supplier, order_date=date(2026, 9, 4),
            currency="USD", exchange_rate=Decimal("3"), status="ordered",
        )
        PaymentPlan.objects.create(
            purchase_order=purchase, direction="payable", currency="USD", planned_amount=Decimal("10"), status="open",
        )
        detail = self.get_detail("payable_rmb")
        self.assertEqual(detail["total_amount"], Decimal("30"))
        self.assertEqual(detail["rows"][0]["detail_url"], f"/purchase-orders?detail={purchase.pk}")

    def test_drill_supports_stable_amount_sorting(self):
        detail = self.get_detail("income_rmb", sort_by="amount", sort_order="desc")
        self.assertEqual(detail["sort_by"], "amount")
        self.assertEqual(detail["sort_order"], "desc")
        self.assertEqual(detail["rows"][0]["record_label"], "FIN-DRILL-IN")

    def test_invalid_metric_and_page_size_are_rejected(self):
        self.assertEqual(self.client.get("/api/finance-dashboard/details/", {"metric": "actual_cash"}).status_code, 400)
        self.assertEqual(self.client.get("/api/finance-dashboard/details/", {"metric": "sales_rmb", "page_size": 101}).status_code, 400)
