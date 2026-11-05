"""Regression coverage for changing tax on unformalized quote revisions."""
from datetime import date
from django.test import TestCase
from rest_framework.test import APIClient
from crm.models import Customer, Product, Quote, SKU

class DraftTaxRevisionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(code='DTR-C', name='Synthetic buyer', country='Germany')
        product = Product.objects.create(code='DTR-P', name='Synthetic product')
        self.sku = SKU.objects.create(product=product, sku='DTR-S')

    def root(self, tax=''):
        q = Quote.objects.create(quote_no='DTR-Q', customer=self.customer, quote_date=date(2026, 1, 1), buyer_tax_id=tax)
        q.items.create(sku=self.sku, quantity=1, unit_price=10)
        return q

    def revise(self, source, tax):
        return self.client.post(f'/api/quotes/{source.pk}/revise/', {'revision_summary':'Correct draft tax', 'buyer_tax_id':tax}, format='json')

    def test_draft_revision_can_change_tax_without_mutating_source(self):
        q = self.root()
        response = self.revise(q, '00123')
        self.assertEqual(response.status_code, 201, response.data)
        q.refresh_from_db()
        self.assertEqual(q.buyer_tax_id, '')
        self.assertEqual(response.data['buyer_tax_id'], '00123')
        self.assertTrue(response.data['can_revise_buyer_tax_id'])

    def test_unknown_remains_unchangeable(self):
        q = self.root(None)
        self.assertFalse(self.client.get(f'/api/quotes/{q.pk}/').data['can_revise_buyer_tax_id'])
        self.assertEqual(self.revise(q, '00123').status_code, 400)

    def test_formal_ancestor_blocks_multi_level_draft(self):
        q = self.root('OLD')
        Quote.objects.filter(pk=q.pk).update(status='sent')
        child = self.client.post(f'/api/quotes/{q.pk}/revise/', {'revision_summary':'unchanged'}, format='json')
        self.assertEqual(child.status_code, 201, child.data)
        draft = Quote.objects.get(pk=child.data['id'])
        self.assertFalse(self.client.get(f'/api/quotes/{draft.pk}/').data['can_revise_buyer_tax_id'])
        self.assertEqual(self.revise(draft, 'NEW').status_code, 400)

    def test_unformalized_multiple_drafts_remain_editable_and_source_unchanged(self):
        root = self.root('OLD')
        first = self.revise(root, 'ONE')
        self.assertEqual(first.status_code, 201, first.data)
        second = self.revise(Quote.objects.get(pk=first.data['id']), 'TWO')
        self.assertEqual(second.status_code, 201, second.data)
        root.refresh_from_db()
        self.assertEqual(root.buyer_tax_id, 'OLD')
        self.assertEqual(Quote.objects.get(pk=first.data['id']).buyer_tax_id, 'ONE')
        self.assertEqual(second.data['buyer_tax_id'], 'TWO')

    def test_formal_ancestor_after_ui_flag_prevents_stale_submission(self):
        root = self.root('OLD')
        self.assertTrue(self.client.get(f'/api/quotes/{root.pk}/').data['can_revise_buyer_tax_id'])
        Quote.objects.filter(pk=root.pk).update(status='sent')
        self.assertEqual(self.revise(root, 'NEW').status_code, 400)

    def test_unknown_ancestor_is_not_overwritten_by_known_child(self):
        root = self.root(None)
        child = Quote.objects.create(quote_no='DTR-NULL-CHILD', customer=self.customer,
            quote_date=date(2026, 1, 1), root_quote=root, parent_quote=root, revision_no=1,
            buyer_country_snapshot=root.buyer_country_snapshot, buyer_tax_id='KNOWN')
        self.assertFalse(self.client.get(f'/api/quotes/{child.pk}/').data['can_revise_buyer_tax_id'])
        self.assertEqual(self.revise(child, 'NEW').status_code, 400)

    def test_orphaned_root_pointer_is_not_eligible(self):
        root = self.root('OLD')
        Quote.objects.filter(pk=root.pk).update(status='sent')
        unrelated = Quote.objects.create(quote_no='DTR-BAD', customer=self.customer, quote_date=date(2026, 1, 1), root_quote=root, buyer_tax_id='OLD')
        self.assertFalse(self.client.get(f'/api/quotes/{unrelated.pk}/').data['can_revise_buyer_tax_id'])
        self.assertEqual(self.revise(unrelated, 'NEW').status_code, 400)


from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from threading import Event
from unittest import skipUnless
from django.db import close_old_connections, connection, transaction
from django.test import TransactionTestCase

@skipUnless(connection.vendor == 'postgresql', 'requires PostgreSQL row locks')
class DraftTaxRevisionConcurrencyTests(TransactionTestCase):
    def test_ancestor_formalization_serializes_and_rejects_tax_change(self):
        customer=Customer.objects.create(code='DTR-LOCK', name='Lock buyer', country='Germany')
        root=Quote.objects.create(quote_no='DTR-LOCK-ROOT', customer=customer, quote_date=date(2026, 1, 1), buyer_tax_id='OLD')
        child=Quote.objects.create(quote_no='DTR-LOCK-CHILD', customer=customer, quote_date=date(2026, 1, 1),
            parent_quote=root, root_quote=root, revision_no=1, buyer_company_name=root.buyer_company_name,
            buyer_country_snapshot=root.buyer_country_snapshot, buyer_tax_id='OLD')
        held, release, attempting = Event(), Event(), Event()
        def formalize():
            close_old_connections()
            try:
                with transaction.atomic():
                    locked=Quote.objects.select_for_update().get(pk=root.pk)
                    locked.status='sent'
                    locked.save(update_fields=['status'])
                    held.set()
                    if not release.wait(15): raise RuntimeError('test failed to release lock')
            finally: close_old_connections()
        def revise():
            close_old_connections()
            try:
                if not held.wait(15): raise RuntimeError('test failed to acquire lock')
                client=APIClient()
                attempting.set()
                result=client.post(f'/api/quotes/{child.pk}/revise/', {'revision_summary':'tax','buyer_tax_id':'NEW'}, format='json')
                return result.status_code
            finally: close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            writer=pool.submit(formalize); reader=pool.submit(revise)
            self.assertTrue(attempting.wait(15))
            try:
                with self.assertRaises(FutureTimeout): reader.result(timeout=0.3)
            finally: release.set()
            writer.result(timeout=20)
            self.assertEqual(reader.result(timeout=20),400)
        self.assertFalse(Quote.objects.filter(parent_quote=child).exists())
        child.refresh_from_db(); self.assertEqual(child.buyer_tax_id, 'OLD')

