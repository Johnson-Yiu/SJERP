from django.contrib.auth import get_user_model
from crm.tests.historical_database import HistoricalMigrationTestCase
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test.utils import CaptureQueriesContext

from crm.models import Customer, PartyVersionRequest, Quote
from crm.party_version import _content, _digest


class ReplacementMigrationCompatibilityTests(HistoricalMigrationTestCase):
    def test_legacy_fingerprints_are_readable_before_and_after_0115(self):
        executor = MigrationExecutor(connection)
        executor.migrate([('crm', '0114_party_document_version')])
        try:
            customer = Customer.objects.create(code='MIG-REPL', name='Synthetic Migration')
            user = get_user_model().objects.create_user(username='synthetic-migration')
            quote = Quote.objects.create(quote_no='MIG-REPL', customer=customer, quote_date='2026-11-05')
            records = []
            for kind in ('correction', 'replacement'):
                obj = PartyVersionRequest(quote=quote, initiator=user, base_snapshot={}, proposed_snapshot={},
                    base_fingerprint=_digest({}), change_type=kind, reason='Synthetic', evidence='Synthetic', source_trust='unknown', is_active=False)
                with CaptureQueriesContext(connection) as queries:
                    obj.content_fingerprint = _digest(_content(obj))
                    obj.save()
                    expected = _digest(_content(obj))
                self.assertEqual(obj.content_fingerprint, expected)
                self.assertFalse(any('FROM "crm_partyreplacementtarget"' in q['sql'] for q in queries))
                records.append((obj.pk, expected))
        finally:
            MigrationExecutor(connection).migrate([('crm', '0115_party_replacement')])
        for pk, expected in records:
            obj = PartyVersionRequest.objects.get(pk=pk)
            self.assertEqual(_digest(_content(obj)), expected)
