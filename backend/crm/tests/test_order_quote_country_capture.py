"""SO confirmation must use the saved quote country, never today's master."""
from datetime import date
from django.test import TestCase
from crm.models import Customer, Order, Quote
from crm.services.order_lifecycle import _capture_order_party_snapshot


class OrderQuoteCountryCaptureTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(code='SO-COUNTRY', name='Synthetic buyer', country='France')
        self.order = Order.objects.create(order_no='SO-COUNTRY', customer=self.customer, order_date=date(2026, 1, 1))

    def quote(self, country):
        return Quote.objects.create(quote_no='SO-COUNTRY-Q', customer=self.customer,
            quote_date=date(2026, 1, 1), buyer_country_snapshot=country)

    def test_quote_saved_country_wins_over_changed_customer(self):
        _capture_order_party_snapshot(self.order, self.quote('Germany'))
        self.assertEqual(self.order.customer_country_snapshot, 'Germany')

    def test_quote_unknown_country_does_not_fall_back_to_customer(self):
        _capture_order_party_snapshot(self.order, self.quote(None))
        self.assertEqual(self.order.customer_country_snapshot, '')

    def test_no_quote_keeps_current_customer_country(self):
        _capture_order_party_snapshot(self.order)
        self.assertEqual(self.order.customer_country_snapshot, 'France')

    def test_actual_confirmation_freezes_quote_country_after_master_changes(self):
        from unittest.mock import patch
        from crm.models import OrderItem, Product, SKU
        from crm.services.order_lifecycle import confirm_order
        product = Product.objects.create(code='SO-C-P', name='Synthetic product')
        sku = SKU.objects.create(product=product, sku='SO-C-SKU', default_price='10')
        quote = self.quote('Germany')
        quote.items.create(sku=sku, quantity='2', unit_price='10')
        self.order.quote = quote
        self.order.save(update_fields=['quote'])
        OrderItem.objects.create(order=self.order, sku=sku, quantity='2', unit_price='10')
        with patch('crm.services.order_lifecycle.allocate_order'):
            confirm_order(self.order)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'confirmed')
        self.assertEqual(self.order.customer_country_snapshot, 'Germany')
