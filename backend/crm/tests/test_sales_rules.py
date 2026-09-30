from datetime import date
from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from crm.models import CategoryAttribute, Customer, Product, ProductCategory, Quote, SalesRule, SKU, SKUTradeUnit
from crm.sales_rules import check_rows


class SalesRulesTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        category = ProductCategory.objects.create(name='电源')
        CategoryAttribute.objects.create(category=category, name='颜色', key='color', include_in_sku=True)
        self.product = Product.objects.create(code='SALES', name='电源', category=category)
        self.white = SKU.objects.create(product=self.product, sku='WHITE', sales_model='WH', parameter_values={'color': '白色'}, unit='pcs')
        self.black = SKU.objects.create(product=self.product, sku='BLACK', sales_model='BK', parameter_values={'color': '黑色'}, unit='pcs')
        self.key = f'{category.pk}:color'
        self.rule = SalesRule.objects.create(product=self.product, name='白色起订量', filters={self.key: ['白色']}, minimum_quantity=100, unit='pcs')
        self.customer = Customer.objects.create(code='BUYER', name='Buyer', country='Germany')

    def check(self, sku, quantity, day=date(2026, 9, 16)):
        return check_rows(day, [{'sku': sku, 'quantity': Decimal(str(quantity))}])[0]

    def quote(self, quantity, sku=None):
        return self.client.post('/api/quotes/', {'customer': self.customer.pk, 'quote_date': '2026-09-16', 'items': [{'sku': (sku or self.white).pk, 'quantity': quantity, 'unit_price': 10}]}, format='json')

    def test_white_boundary_and_black_unrestricted(self):
        self.assertTrue(self.check(self.white, 99.99)['errors'])
        self.assertFalse(self.check(self.white, 100)['errors'])
        self.assertFalse(self.check(self.white, 200)['errors'])
        self.assertEqual(self.check(self.black, 1)['rules'], [])

    def test_dates_and_disabled(self):
        self.rule.effective_from = date(2026, 9, 16)
        self.rule.effective_until = date(2026, 9, 17)
        self.rule.save()
        for day, applies in [(15, False), (16, True), (17, True), (18, False)]:
            self.assertEqual(bool(self.check(self.white, 50, date(2026, 9, day))['errors']), applies)
        self.rule.is_active = False
        self.rule.save()
        self.assertEqual(self.check(self.white, 50)['rules'], [])

    def test_specific_sku_and_strictest_rule(self):
        SalesRule.objects.create(product=self.product, sku=self.white, name='特别限制', minimum_quantity=200, unit='pcs')
        self.assertTrue(self.check(self.white, 150)['errors'])
        self.assertFalse(self.check(self.white, 200)['errors'])
        self.assertFalse(self.check(self.black, 1)['errors'])

    def test_create_and_revision_enforced_and_snapshot_immutable(self):
        invalid = self.quote(50)
        self.assertEqual(invalid.status_code, 400, invalid.data)
        self.assertEqual(Quote.objects.count(), 0)
        response = self.quote(100)
        self.assertEqual(response.status_code, 201, response.data)
        quote = Quote.objects.get(pk=response.data['id'])
        snapshot = quote.items.get().sales_rules_snapshot
        self.assertEqual(snapshot[0]['minimum_quantity'], '100.00')
        self.rule.minimum_quantity = 200
        self.rule.save()
        revision = self.client.post(f'/api/quotes/{quote.pk}/revise/', {'revision_summary': '新规则'}, format='json')
        self.assertEqual(revision.status_code, 400, revision.data)
        self.assertEqual(Quote.objects.count(), 1)
        self.assertEqual(quote.items.get().sales_rules_snapshot, snapshot)
        revision = self.client.post(f'/api/quotes/{quote.pk}/revise/', {'revision_summary': '增加数量', 'items': [{'sku': self.white.pk, 'quantity': 200, 'unit_price': 10}]}, format='json')
        self.assertEqual(revision.status_code, 201, revision.data)
        self.assertEqual(revision.data['items'][0]['sales_rules_snapshot'][0]['minimum_quantity'], '200.00')

    def test_check_endpoint_and_unit_mismatch(self):
        response = self.client.post('/api/sales-rules/check-quote/', {'quote_date': '2026-09-16', 'items': [{'sku': self.white.pk, 'quantity': 50}]}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data[0]['errors'])
        self.rule.unit = 'meters'
        self.rule.save()
        self.assertIn('单位', self.check(self.white, 1000)['errors'][0])

    def test_rule_validation_and_management(self):
        payload = {'product': self.product.pk, 'name': '指定白色', 'sku': self.white.pk, 'minimum_quantity': 100, 'unit': 'pcs'}
        response = self.client.post('/api/sales-rules/', payload, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        url = f'/api/sales-rules/{response.data["id"]}/'
        for invalid in [{'minimum_quantity': 0}, {'unit': 'meters'}, {'effective_from': '2026-09-17', 'effective_until': '2026-09-16'}, {'filters': {'unknown': ['x']}}]:
            self.assertEqual(self.client.patch(url, invalid, format='json').status_code, 400)
        other = Product.objects.create(code='OTHER', name='其他产品')
        self.assertEqual(self.client.patch(url, {'product': other.pk}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(url, {'is_active': False}, format='json').status_code, 200)

    def test_multi_condition_unit_normalization_and_legacy_name(self):
        CategoryAttribute.objects.create(category=self.product.category, name='电压', key='voltage', unit='V', include_in_sku=True)
        self.white.parameter_values = {'颜色': '白色', 'voltage': '24'}
        self.white.save()
        self.rule.filters[f'{self.product.category_id}:voltage'] = ['24V']
        self.rule.save()
        self.assertTrue(self.check(self.white, 50)['errors'])
        self.white.parameter_values['voltage'] = '12'
        self.white.save()
        self.assertFalse(self.check(self.white, 50)['errors'])

    def test_product_filter_rule_rejects_mismatched_active_sku_base_unit(self):
        meter = SKU.objects.create(
            product=self.product, sku='GREEN-METER', sales_model='GM',
            parameter_values={'color': '绿色'}, unit='m',
        )
        rejected = self.client.post('/api/sales-rules/', {
            'product': self.product.pk, 'name': '绿色错误单位',
            'filters': {self.key: ['绿色']}, 'minimum_quantity': 10, 'unit': 'pcs',
        }, format='json')
        self.assertEqual(rejected.status_code, 400, rejected.data)
        self.assertIn(f'SKU {meter.sku}', str(rejected.data))
        self.assertIn('基础单位 m', str(rejected.data))

        no_current_match = self.client.post('/api/sales-rules/', {
            'product': self.product.pk, 'name': '未来绿色规则',
            'filters': {self.key: ['黄色']}, 'minimum_quantity': 10, 'unit': 'm',
        }, format='json')
        self.assertEqual(no_current_match.status_code, 201, no_current_match.data)

    def test_moq_uses_trade_converted_base_quantity_and_quote_snapshot_survives_deletion(self):
        rolls = SKUTradeUnit.objects.create(sku=self.white, name='10 pcs roll', unit='roll', factor=10)
        payload = lambda quantity: {
            'customer': self.customer.pk, 'quote_date': '2026-09-16',
            'items': [{'sku': self.white.pk, 'trade_unit': rolls.pk, 'trade_quantity': quantity, 'trade_unit_price': 10}],
        }
        self.assertEqual(self.client.post('/api/quotes/', payload(9), format='json').status_code, 400)
        created = self.client.post('/api/quotes/', payload(10), format='json')
        self.assertEqual(created.status_code, 201, created.data)
        quote = Quote.objects.get(pk=created.data['id'])
        snapshot = quote.items.get().sales_rules_snapshot
        self.assertEqual(snapshot[0]['minimum_quantity'], '100.00')

        self.rule.delete()
        quote.refresh_from_db()
        self.assertEqual(quote.items.get().sales_rules_snapshot, snapshot)
        self.assertEqual(self.client.post('/api/quotes/', payload(1), format='json').status_code, 201)
