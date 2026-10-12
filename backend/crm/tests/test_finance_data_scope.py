from datetime import date
from decimal import Decimal
import csv
import io

from django.test import TestCase, override_settings
from crm.models import AdvanceAllocation, ContractChangeRequest, Order, PaymentPlan, Product, PurchaseOrder, PurchaseOrderItem, RolePermission, SKU, Supplier, Transaction
from crm.tests import test_sales_data_scope as sales_fixture
RBAC_SETTINGS = sales_fixture.RBAC_SETTINGS


@override_settings(**RBAC_SETTINGS, PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class FinanceDataScopeTests(TestCase):
    make_employee = sales_fixture.SalesDataScopeTests.make_employee

    def setUp(self):
        sales_fixture.SalesDataScopeTests.setUp(self)
        for role in self.roles.values():
            for module in ('transactions', 'finance', 'purchases'):
                RolePermission.objects.create(role=role, module=module, can_view=True, can_create=True, can_update=True, can_delete=True, can_export=True)
        self.sku = SKU.objects.create(product=Product.objects.create(code='FP', name='Finance product'), sku='FS')
        self.orders, self.plans, self.receipts = [], [], []
        for index, customer in enumerate((self.customer_a, self.customer_b, self.customer_team, self.customer_c)):
            order = Order.objects.create(order_no=f'F-SO-{index}', customer=customer, order_date=date(2026, 10, 12), status='confirmed', currency='CNY', exchange_rate=1)
            order.items.create(sku=self.sku, quantity=1, unit_price=100)
            plan = PaymentPlan.objects.create(order=order, direction='receivable', currency='CNY', planned_amount=100)
            row = Transaction.objects.create(transaction_no=f'F-T-{index}', customer=customer, order=order, direction='income', kind='other_income', amount=10, currency='CNY', exchange_rate=1, transaction_date=date(2026, 10, 12))
            self.orders.append(order); self.plans.append(plan); self.receipts.append(row)
        self.supplier = Supplier.objects.create(name='Shared supplier', code='ZZ')
        self.purchase = PurchaseOrder.objects.create(purchase_no='F-PO', supplier=self.supplier, order=self.orders[3], order_date=date(2026, 10, 12), currency='CNY', exchange_rate=1, status='ordered')
        PurchaseOrderItem.objects.create(purchase_order=self.purchase, sku=self.sku, quantity=1, unit_price=100)
        self.purchase_plan = PaymentPlan.objects.create(purchase_order=self.purchase, direction='payable', currency='CNY', planned_amount=100)
        self.shared = Transaction.objects.create(transaction_no='F-SHARED', supplier=self.supplier, purchase_order=self.purchase, direction='expense', kind='other', amount=5, currency='CNY', exchange_rate=1, transaction_date=date(2026, 10, 12))
        self.public = Transaction.objects.create(transaction_no='F-PUBLIC', direction='expense', kind='other', amount=2, currency='CNY', exchange_rate=1, transaction_date=date(2026, 10, 12))
        self.client.force_authenticate(self.employee_a.user)

    def rows(self, response):
        self.assertEqual(response.status_code, 200, response.data)
        return response.data.get('results', response.data) if isinstance(response.data, dict) else response.data

    def payload(self, **values):
        return dict(direction='income', kind='other_income', category='收款', amount='10', currency='CNY', exchange_rate='1', transaction_date='2026-10-12', **values)

    def test_four_scopes_preserve_shared_finance(self):
        for employee, count in ((self.employee_a, 1), (self.manager, 2), (self.tree_manager, 3), (self.all_user, 4)):
            with self.subTest(scope=employee.display_name):
                self.client.force_authenticate(employee.user)
                rows = self.rows(self.client.get('/api/transactions/'))
                self.assertEqual(len(rows), count + 2)
                self.assertTrue({self.shared.pk, self.public.pk}.issubset({r['id'] for r in rows}))
                self.assertEqual(len(self.rows(self.client.get('/api/payment-plans/'))), count + 1)

    def test_foreign_reads_and_context_are_hidden(self):
        for route in (f'/api/transactions/{self.receipts[1].pk}/', f'/api/context/transactions/{self.receipts[1].pk}/', f'/api/payment-plans/{self.plans[1].pk}/'):
            self.assertEqual(self.client.get(route).status_code, 404)
        context = self.client.get(f'/api/context/transactions/{self.shared.pk}/')
        self.assertEqual(context.status_code, 200)
        self.assertNotIn(self.orders[3].order_no, str(context.data))
        context = self.client.get(f'/api/context/purchase-orders/{self.purchase.pk}/')
        self.assertNotIn(self.orders[3].order_no, str(context.data))

    def test_creation_cannot_bind_foreign_customer_order_or_plan(self):
        for values in ({'customer': self.customer_b.pk}, {'order': self.orders[1].pk}, {'plan': self.plans[1].pk}, {'replaces': self.receipts[1].pk}):
            response = self.client.post('/api/transactions/', self.payload(**values), format='json')
            self.assertEqual(response.status_code, 403, response.data)
        good = self.client.post('/api/transactions/', self.payload(customer=self.customer_a.pk), format='json')
        self.assertEqual(good.status_code, 201, good.data)

    def test_foreign_actions_and_rebinding_are_denied(self):
        self.assertEqual(self.client.post(f'/api/payment-plans/{self.plans[1].pk}/settle/', {'amount': '10', 'transaction_date': '2026-10-12'}, format='json').status_code, 404)
        self.assertEqual(self.client.patch(f'/api/payment-plans/{self.plans[0].pk}/', {'order': self.orders[1].pk}, format='json').status_code, 403)
        self.assertEqual(self.client.post(f'/api/transactions/{self.receipts[1].pk}/void/', {'reason': '越权'}, format='json').status_code, 404)
        self.plans[1].refresh_from_db(); self.assertEqual(self.plans[1].settled_amount, 0)
        self.receipts[1].refresh_from_db(); self.assertEqual(self.receipts[1].status, 'confirmed')

    def test_normal_settle_refund_void_and_purchase_payment(self):
        settled = self.client.post(f'/api/payment-plans/{self.plans[0].pk}/settle/', {'amount': '20', 'transaction_date': '2026-10-12'}, format='json')
        self.assertEqual(settled.status_code, 201, settled.data)
        refund = self.client.post('/api/transactions/', {**self.payload(order=self.orders[0].pk), 'direction': 'expense', 'kind': 'refund', 'amount': '5'}, format='json')
        self.assertEqual(refund.status_code, 201, refund.data)
        self.assertEqual(self.client.post(f"/api/transactions/{refund.data['id']}/void/", {'reason': '重记'}, format='json').status_code, 200)
        self.assertEqual(self.client.post(f"/api/transactions/{settled.data['id']}/void/", {'reason': '重记'}, format='json').status_code, 200)
        self.plans[0].refresh_from_db(); self.assertEqual(self.plans[0].settled_amount, 0)
        paid = self.client.post(f'/api/payment-plans/{self.purchase_plan.pk}/settle/', {'amount': '10', 'transaction_date': '2026-10-12'}, format='json')
        self.assertEqual(paid.status_code, 201, paid.data)

    def test_void_requires_finance_update_even_without_plan_or_allocations(self):
        RolePermission.objects.filter(role=self.roles['self'], module='finance').update(can_update=False)
        response = self.client.post(f'/api/transactions/{self.public.pk}/void/', {'reason': '权限回归'}, format='json')
        self.assertEqual(response.status_code, 403, response.data)
        self.public.refresh_from_db()
        self.assertEqual(self.public.status, 'confirmed')

    def test_finance_allocation_totals_are_hidden_without_finance_view(self):
        RolePermission.objects.filter(role=self.roles['self'], module='finance').update(can_view=False)
        response = self.client.get(f'/api/transactions/{self.receipts[0].pk}/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIsNone(response.data['allocated_amount'])
        self.assertIsNone(response.data['plan'])
        self.assertEqual(response.data['allocations'], [])

    def test_unallocated_advance_creation_requires_finance_update(self):
        RolePermission.objects.filter(role=self.roles['self'], module='finance').update(can_update=False)
        response = self.client.post('/api/transactions/', {
            **self.payload(customer=self.customer_a.pk), 'kind': 'unallocated_advance',
        }, format='json')
        self.assertEqual(response.status_code, 403, response.data)
        self.assertFalse(Transaction.objects.filter(kind='unallocated_advance', customer=self.customer_a).exists())

    def test_advance_allocation_and_split_family_guard(self):
        advance = self.client.post('/api/transactions/', {**self.payload(customer=self.customer_a.pk), 'kind': 'unallocated_advance'}, format='json')
        self.assertEqual(advance.status_code, 201, advance.data)
        url = f"/api/transactions/{advance.data['id']}/allocate/"
        self.assertEqual(self.client.post(url, {'plan': self.plans[1].pk, 'amount': '5'}, format='json').status_code, 404)
        self.assertEqual(self.client.post(url, {'plan': self.plans[0].pk, 'amount': '5'}, format='json').status_code, 200)
        root = Transaction.objects.get(pk=advance.data['id'])
        child = Transaction.objects.create(transaction_no='F-LEGACY', split_from=root, customer=self.customer_b, direction='income', amount=1, currency='CNY', exchange_rate=1, transaction_date=date(2026, 10, 12))
        self.assertEqual(self.client.post(f'/api/transactions/{root.pk}/void/', {'reason': '不可跨范围'}, format='json').status_code, 404)
        root.refresh_from_db(); self.assertEqual(root.status, 'confirmed')

    def test_allocation_history_cannot_disclose_or_modify_foreign_plan(self):
        AdvanceAllocation.objects.create(advance=self.public, plan=self.plans[1], amount=1, is_active=False)
        self.assertEqual(self.client.get(f'/api/transactions/{self.public.pk}/').status_code, 404)

    def test_contract_sales_and_shared_purchase_changes(self):
        bad = self.client.post('/api/contract-changes/', {'order': self.orders[1].pk, 'amount_delta': '5', 'notes': '测试合同变更'}, format='json')
        self.assertEqual(bad.status_code, 403)
        for field, contract in (('order', self.orders[0]), ('purchase_order', self.purchase)):
            response = self.client.post('/api/contract-changes/', {field: contract.pk, 'amount_delta': '5', 'notes': '测试合同变更'}, format='json')
            self.assertEqual(response.status_code, 201, response.data)
            response = self.client.post(f"/api/contract-changes/{response.data['id']}/approve/", {}, format='json')
            self.assertEqual(response.status_code, 201, response.data)

    def test_dashboard_report_and_csv_share_cash_scope(self):
        params = {'source': 'cash', 'group_by': 'direction', 'date_from': '2026-10-01', 'date_to': '2026-10-31'}
        dashboard = self.client.get('/api/finance-dashboard/', params)
        self.assertEqual(dashboard.status_code, 200, dashboard.data)
        self.assertEqual(Decimal(str(dashboard.data['metrics']['net_cash_rmb'])), 3)
        overview = self.client.get('/api/dashboard/')
        self.assertEqual(Decimal(str(overview.data['summary']['receipts_rmb'])), 10)
        self.assertEqual(Decimal(str(overview.data['summary']['payments_rmb'])), 7)
        report = self.client.get('/api/reports/data/', params)
        self.assertEqual(report.status_code, 200, report.data)
        self.assertEqual(Decimal(str(report.data['totals']['amount'])), 3)
        export = self.client.get('/api/reports/data/', {**params, 'export': 'csv'})
        self.assertEqual(export.status_code, 200)
        self.assertNotIn(self.customer_b.name, export.content.decode('utf-8-sig'))

    def test_unowned_legacy_sales_cash_requires_all_scope(self):
        row = Transaction.objects.create(transaction_no='F-ORPHAN', direction='expense', kind='order_expense', amount=1, currency='CNY', exchange_rate=1, transaction_date=date(2026, 10, 12))
        self.assertEqual(self.client.get(f'/api/transactions/{row.pk}/').status_code, 404)
        self.client.force_authenticate(self.all_user.user)
        self.assertEqual(self.client.get(f'/api/transactions/{row.pk}/').status_code, 200)

    def test_shared_purchase_contract_does_not_require_sales_module(self):
        RolePermission.objects.filter(role=self.roles['self'], module='orders').update(can_view=False, can_create=False, can_update=False)
        response = self.client.post('/api/contract-changes/', {'purchase_order': self.purchase.pk, 'amount_delta': '5', 'notes': '采购变更'}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self.client.post(f"/api/contract-changes/{response.data['id']}/approve/", {}, format='json').status_code, 201)

    def test_advance_payment_cross_purchase_and_void_restores_balances(self):
        advance = self.client.post('/api/transactions/', {**self.payload(supplier=self.supplier.pk), 'kind': 'unallocated_payment', 'direction': 'expense'}, format='json')
        self.assertEqual(advance.status_code, 201, advance.data)
        response = self.client.post(f"/api/transactions/{advance.data['id']}/allocate/", {'plan': self.purchase_plan.pk, 'amount': '10'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.client.post(f"/api/transactions/{advance.data['id']}/void/", {'reason': '恢复预付'}, format='json').status_code, 200)
        self.purchase_plan.refresh_from_db(); self.assertEqual(self.purchase_plan.settled_amount, 0)

    def test_finance_export_is_authorized_on_server(self):
        params = {'date_from': '2026-10-01', 'date_to': '2026-10-31', 'export': 'csv'}
        response = self.client.get('/api/finance-dashboard/', params)
        self.assertEqual(response.status_code, 200)
        rows = list(csv.reader(io.StringIO(response.content.decode('utf-8-sig'))))
        self.assertEqual([Decimal(value) for value in rows[2][1:]], [Decimal(10), Decimal(7), Decimal(3)])
        RolePermission.objects.filter(role=self.roles['self'], module='finance').update(can_export=False)
        self.assertEqual(self.client.get('/api/finance-dashboard/', params).status_code, 403)
        self.assertEqual(self.client.get('/api/finance-dashboard/').status_code, 200)

    def test_finance_dashboard_masks_counterparty_names_without_party_module_access(self):
        self.plans[0].due_date = date.today()
        self.plans[0].save(update_fields=['due_date', 'updated_at'])
        self.purchase_plan.due_date = date.today()
        self.purchase_plan.save(update_fields=['due_date', 'updated_at'])
        RolePermission.objects.filter(role=self.roles['self'], module__in=['customers', 'suppliers']).update(can_view=False)

        response = self.client.get('/api/finance-dashboard/')
        self.assertEqual(response.status_code, 200, response.data)
        parties = {row['counterparty_name'] for row in response.data['due_items']}
        self.assertEqual(parties, {'客户', '供应商'})
        self.assertNotIn(self.customer_a.name, repr(response.data))
        self.assertNotIn(self.supplier.name, repr(response.data))

    def test_module_permissions_are_required_alongside_all_scope(self):
        self.client.force_authenticate(self.all_user.user)
        RolePermission.objects.filter(role=self.roles['all'], module='transactions').update(can_create=False, can_view=False)
        self.assertEqual(self.client.get('/api/transactions/').status_code, 403)
        self.assertEqual(self.client.get('/api/finance-dashboard/').status_code, 403)
        self.assertEqual(self.client.get('/api/reports/data/', {'source': 'cash'}).status_code, 403)
        self.assertEqual(self.client.post(f'/api/payment-plans/{self.purchase_plan.pk}/settle/', {'amount': '10', 'transaction_date': '2026-10-12'}, format='json').status_code, 403)
        self.assertEqual(self.client.post(f'/api/purchase-orders/{self.purchase.pk}/pay/', {'amount': '10', 'transaction_date': '2026-10-12'}, format='json').status_code, 403)
