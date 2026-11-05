from datetime import date
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest import skipUnless

from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection, transaction
from django.test import TestCase, TransactionTestCase

from crm.models import Customer, Order, PurchaseOrder, Quote, Supplier


class FormalPartyGuardTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(code='PARTY-GUARD-C', name='Synthetic customer', country='Germany')
        self.supplier = Supplier.objects.create(code='PG', name='Synthetic supplier')
        self.day = date(2026, 11, 5)

    def test_formal_snapshots_cannot_be_overwritten_by_model_save(self):
        quote = Quote.objects.create(quote_no='PARTY-GUARD-Q', customer=self.customer, quote_date=self.day,
                                     status='sent', buyer_address='Original buyer address')
        order = Order.objects.create(order_no='PARTY-GUARD-O', customer=self.customer, order_date=self.day,
                                     status='confirmed', customer_address_snapshot='Original customer address')
        purchase = PurchaseOrder.objects.create(purchase_no='PARTY-GUARD-P', supplier=self.supplier,
            order_date=self.day, status='ordered', supplier_address_snapshot='Original supplier address')
        cases = [
            (quote, ('buyer_company_name', 'recipient_name', 'buyer_address', 'buyer_email', 'buyer_phone')),
            (order, ('customer_name_snapshot', 'customer_country_snapshot', 'customer_address_snapshot',
                     'customer_contact_name_snapshot', 'customer_phone_snapshot', 'customer_email_snapshot')),
            (purchase, ('supplier_name_snapshot', 'supplier_address_snapshot', 'supplier_contact_name_snapshot',
                        'supplier_phone_snapshot', 'supplier_email_snapshot')),
        ]
        for obj, fields in cases:
            for field in fields:
                with self.subTest(model=obj._meta.label, field=field):
                    original = getattr(obj, field)
                    setattr(obj, field, 'Unapproved replacement')
                    with self.assertRaisesMessage(ValidationError, '正式单据主体快照不能直接修改'):
                        obj.save(update_fields=[field])
                    obj.refresh_from_db()
                    self.assertEqual(getattr(obj, field), original)
        other_customer = Customer.objects.create(code='PARTY-GUARD-OTHER', name='Other customer')
        other_supplier = Supplier.objects.create(code='PT', name='Other supplier')
        for obj, field, replacement in ((quote, 'customer_id', other_customer.pk),
                                         (order, 'customer_id', other_customer.pk),
                                         (purchase, 'supplier_id', other_supplier.pk)):
            with self.subTest(model=obj._meta.label, field=field):
                original = getattr(obj, field)
                setattr(obj, field, replacement)
                with self.assertRaises(ValidationError):
                    obj.save(update_fields=[field])
                obj.refresh_from_db()
                self.assertEqual(getattr(obj, field), original)

        for obj in (quote, order, purchase):
            obj.notes = 'Unrelated note'
            obj.save(update_fields=['notes'])
            obj.refresh_from_db()
            self.assertEqual(obj.notes, 'Unrelated note')

    def test_drafts_still_allow_party_edits_before_confirmation(self):
        quote = Quote.objects.create(quote_no='PARTY-GUARD-DQ', customer=self.customer, quote_date=self.day)
        order = Order.objects.create(order_no='PARTY-GUARD-DO', customer=self.customer, order_date=self.day)
        purchase = PurchaseOrder.objects.create(purchase_no='PARTY-GUARD-DP', supplier=self.supplier, order_date=self.day)
        for obj, field in ((quote, 'buyer_address'), (order, 'customer_address_snapshot'),
                           (purchase, 'supplier_address_snapshot')):
            with self.subTest(model=obj._meta.label):
                setattr(obj, field, 'Draft address')
                obj.save(update_fields=[field])
                obj.refresh_from_db()
                self.assertEqual(getattr(obj, field), 'Draft address')


@skipUnless(connection.vendor == 'postgresql', 'Requires PostgreSQL row locks')
class FormalPartyGuardConcurrencyTests(TransactionTestCase):
    def test_stale_draft_cannot_overwrite_after_concurrent_confirmation(self):
        customer = Customer.objects.create(code='PARTY-GUARD-RACE', name='Synthetic', country='Germany')
        quote = Quote.objects.create(quote_no='PARTY-GUARD-RACE', customer=customer,
                                     quote_date=date(2026, 11, 5), buyer_address='Original')
        stale = Quote.objects.get(pk=quote.pk)
        locked, attempt, release = Event(), Event(), Event()

        def confirm():
            close_old_connections()
            try:
                with transaction.atomic():
                    current = Quote.objects.select_for_update().get(pk=quote.pk)
                    current.status = 'sent'
                    current.save(update_fields=['status'])
                    locked.set()
                    if not release.wait(20):
                        raise RuntimeError('Confirmation release timed out')
            finally:
                close_old_connections()

        def overwrite():
            close_old_connections()
            try:
                if not locked.wait(20):
                    raise RuntimeError('Confirmation lock timed out')
                stale.buyer_address = 'Unapproved'
                attempt.set()
                try:
                    stale.save(update_fields=['buyer_address'])
                except ValidationError:
                    return 'rejected'
                return 'saved'
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(confirm)
            second = pool.submit(overwrite)
            try:
                self.assertTrue(attempt.wait(20))
            finally:
                release.set()
            first.result(timeout=30)
            self.assertEqual(second.result(timeout=30), 'rejected')
        quote.refresh_from_db()
        self.assertEqual((quote.status, quote.buyer_address), ('sent', 'Original'))
