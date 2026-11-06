from datetime import date
from threading import Event, Thread
from unittest import skipUnless

from django.db import close_old_connections, connection, transaction
from django.test import TransactionTestCase

from crm.models import Customer, Quote
from crm.party_document_details import unknown_details
from crm.party_document_details_models import PartyDocumentDetailsStorage


@skipUnless(connection.vendor == 'postgresql', 'requires PostgreSQL row locks')
class PartyDetailsConcurrencyTests(TransactionTestCase):
    def test_formalization_waits_for_draft_write(self):
        customer = Customer.objects.create(code='DETAILS-LOCK', name='Synthetic')
        quote = Quote.objects.create(quote_no='DETAILS-LOCK', customer=customer, quote_date=date(2026, 1, 1))
        locked, release, started, finished = Event(), Event(), Event(), Event()
        errors = []

        def writer():
            close_old_connections()
            try:
                with transaction.atomic():
                    Quote.objects.select_for_update().get(pk=quote.pk)
                    PartyDocumentDetailsStorage.objects.create(quote_id=quote.pk, details=unknown_details())
                    locked.set()
                    if not release.wait(10): raise RuntimeError('writer release timed out')
            except Exception as exc: errors.append(exc)
            finally: close_old_connections()

        def formalize():
            close_old_connections()
            try:
                started.set()
                Quote.objects.filter(pk=quote.pk).update(status='sent')
            except Exception as exc: errors.append(exc)
            finally:
                finished.set()
                close_old_connections()

        a = Thread(target=writer); a.start()
        self.assertTrue(locked.wait(10))
        b = Thread(target=formalize); b.start()
        self.assertTrue(started.wait(10))
        self.assertFalse(finished.wait(0.5))
        release.set(); a.join(10); b.join(10)
        self.assertFalse(a.is_alive() or b.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(Quote.objects.get(pk=quote.pk).status, 'sent')
        self.assertEqual(PartyDocumentDetailsStorage.objects.get(quote=quote).details, unknown_details())
