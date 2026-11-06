"""Regression coverage for currently implemented party snapshot boundaries."""

from datetime import date
from io import BytesIO
from unittest.mock import patch

from django.test import TestCase
from openpyxl import load_workbook
from rest_framework.test import APIClient

from crm.models import Contact, Customer, Order, OrderItem, Product, PurchaseOrder, PurchaseOrderItem, Quote, SKU, Supplier
from crm.quote_snapshots import create_quote_items
from crm.services.order_lifecycle import confirm_order
from crm.services.purchase_lifecycle import place_purchase_order


class PartyVersionCurrentBaselineTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.day = date(2026, 11, 5)
        self.customer = Customer.objects.create(code="PV-C", name="Buyer Original", country="Germany", address="Master Address")
        self.contact = Contact.objects.create(customer=self.customer, name="Master Contact", phone="111", email="master@example.com", is_primary=True)
        self.supplier = Supplier.objects.create(code="PV", name="Supplier Original", address="Supplier Address", contact_name="Supplier Contact", phone="222", email="supplier@example.com")
        product = Product.objects.create(code="PV-P", name="Synthetic Product")
        self.sku = SKU.objects.create(product=product, sku="PV-SKU", default_price="10")
        self.quote = Quote.objects.create(
            quote_no="PV-QUOTE", customer=self.customer, quote_date=self.day,
            buyer_company_name="Saved Buyer", recipient_name="Saved Contact", buyer_address="Saved Address",
            buyer_phone="333", buyer_email="saved@example.com",
        )
        create_quote_items(self.quote, [{"sku": self.sku, "quantity": 2, "unit_price": 10}])

    def test_quote_api_and_xlsx_consume_saved_buyer_and_seller(self):
        before = self.client.get(f"/api/quotes/{self.quote.pk}/pi-data/")
        self.assertEqual(before.status_code, 200, before.data)
        self.customer.name = "Changed Buyer"
        self.customer.address = "Changed Address"
        self.customer.save(update_fields=["name", "address"])
        with patch("crm.quotation_template_config.quotation_templates", {}):
            api = self.client.get(f"/api/quotes/{self.quote.pk}/pi-data/")
            exported = self.client.get(f"/api/quotes/{self.quote.pk}/export/")
        self.assertEqual(api.status_code, 200, api.data)
        self.assertEqual(exported.status_code, 200)
        self.assertEqual(api.data["seller"], before.data["seller"])
        expected = {"company_name": "Saved Buyer", "name": "Saved Contact", "address": "Saved Address", "phone": "333", "email": "saved@example.com"}
        for field, value in expected.items():
            self.assertEqual(api.data["buyer"][field], value)
        workbook = load_workbook(BytesIO(exported.content))
        try:
            sheet = workbook["PI"]
            for cell, value in {"B3": "Saved Buyer", "B4": "Saved Contact", "B5": "Saved Address", "B7": "saved@example.com", "B8": "333", "I3": before.data["seller"]["name"]}.items():
                self.assertEqual(sheet[cell].value, value)
        finally:
            workbook.close()

    def test_unknown_quote_buyer_survives_revision_and_export_rejects(self):
        Quote.objects.filter(pk=self.quote.pk).update(buyer_company_name="")
        self.customer.name = "Current Buyer"
        self.customer.save(update_fields=["name"])
        response = self.client.post(f"/api/quotes/{self.quote.pk}/revise/", {"revision_summary": "Synthetic revision"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["buyer_company_name"], "")
        for quote_id in (self.quote.pk, response.data["id"]):
            for action in ("pi-data", "export"):
                with self.subTest(quote_id=quote_id, action=action):
                    result = self.client.get(f"/api/quotes/{quote_id}/{action}/")
                    self.assertEqual(result.status_code, 422)
                    self.assertIn("buyer_company_name", result.data["fields"])

    def test_formal_order_and_purchase_api_show_frozen_fields_after_master_changes(self):
        order = Order.objects.create(order_no="PV-SO", customer=self.customer, quote=self.quote, order_date=self.day, currency="USD", exchange_rate=1)
        OrderItem.objects.create(order=order, sku=self.sku, quantity=2, unit_price=10)
        purchase = PurchaseOrder.objects.create(purchase_no="PV-PO", supplier=self.supplier, order_date=self.day, currency="USD", exchange_rate=1)
        PurchaseOrderItem.objects.create(purchase_order=purchase, sku=self.sku, quantity=2, unit_price=4)
        with patch("crm.services.order_lifecycle.allocate_order"), patch("crm.services.purchase_lifecycle.ensure_default_payment_plans"):
            confirm_order(order)
            place_purchase_order(purchase)
        self.customer.name, self.customer.country = "Changed Buyer", "France"
        self.customer.save(update_fields=["name", "country"])
        self.supplier.name, self.supplier.address = "Changed Supplier", "Changed Supplier Address"
        self.supplier.save(update_fields=["name", "address"])
        so = self.client.get(f"/api/orders/{order.pk}/")
        po = self.client.get(f"/api/purchase-orders/{purchase.pk}/")
        self.assertEqual((so.status_code, po.status_code), (200, 200))
        self.assertEqual(so.data["customer_name"], "Changed Buyer")
        for field, value in {"customer_name_snapshot": "Saved Buyer", "customer_country_snapshot": "Germany", "customer_address_snapshot": "Saved Address", "customer_contact_name_snapshot": "Saved Contact", "customer_phone_snapshot": "333", "customer_email_snapshot": "saved@example.com"}.items():
            self.assertEqual(so.data[field], value)
        self.assertEqual(po.data["supplier_name"], "Changed Supplier")
        for field, value in {"supplier_name_snapshot": "Supplier Original", "supplier_address_snapshot": "Supplier Address", "supplier_contact_name_snapshot": "Supplier Contact", "supplier_phone_snapshot": "222", "supplier_email_snapshot": "supplier@example.com"}.items():
            self.assertEqual(po.data[field], value)

    def test_legacy_order_and_purchase_empty_snapshots_remain_unknown_in_api(self):
        order = Order.objects.create(order_no="PV-OLD-SO", customer=self.customer, order_date=self.day, currency="USD", exchange_rate=1, status="confirmed")
        purchase = PurchaseOrder.objects.create(purchase_no="PV-OLD-PO", supplier=self.supplier, order_date=self.day, currency="USD", exchange_rate=1, status="ordered")
        for path, fields in ((f"/api/orders/{order.pk}/", ("customer_name_snapshot", "customer_country_snapshot", "customer_address_snapshot", "customer_contact_name_snapshot", "customer_phone_snapshot", "customer_email_snapshot")), (f"/api/purchase-orders/{purchase.pk}/", ("supplier_name_snapshot", "supplier_address_snapshot", "supplier_contact_name_snapshot", "supplier_phone_snapshot", "supplier_email_snapshot"))):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, response.data)
            for field in fields:
                self.assertEqual(response.data[field], "", field)
