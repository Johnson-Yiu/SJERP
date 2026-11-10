from crm.tests.historical_database import HistoricalMigrationTestCase
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test.utils import CaptureQueriesContext

from crm.party_version import _content, _digest


class ReplacementMigrationCompatibilityTests(HistoricalMigrationTestCase):
    def test_legacy_fingerprints_are_readable_before_and_after_0115(self):
        executor = MigrationExecutor(connection)
        before = [("crm", "0114_party_document_version")]
        after = [("crm", "0115_party_replacement")]
        executor.migrate(before)
        apps = executor.loader.project_state(before).apps
        request_model = apps.get_model("crm", "PartyVersionRequest")
        records = []
        try:
            customer = apps.get_model("crm", "Customer").objects.create(code='MIG-REPL', name='Synthetic Migration')
            user = apps.get_model("auth", "User").objects.create(username="synthetic-migration")
            quote = apps.get_model("crm", "Quote").objects.create(quote_no='MIG-REPL', customer=customer, quote_date='2026-11-05')
            for kind in ('correction', 'replacement'):
                obj = request_model(quote=quote, initiator=user, base_snapshot={}, proposed_snapshot={},
                    base_fingerprint=_digest({}), change_type=kind, reason='Synthetic', evidence='Synthetic', source_trust='unknown', is_active=False)
                with CaptureQueriesContext(connection) as queries:
                    obj.content_fingerprint = _digest(_content(obj))
                    obj.save()
                    expected = _digest(_content(obj))
                self.assertEqual(obj.content_fingerprint, expected)
                self.assertFalse(any('FROM "crm_partyreplacementtarget"' in q['sql'] for q in queries))
                records.append((obj.pk, expected))
        finally:
            MigrationExecutor(connection).migrate(after)
        apps = MigrationExecutor(connection).loader.project_state(after).apps
        request_model = apps.get_model("crm", "PartyVersionRequest")
        for pk, expected in records:
            obj = request_model.objects.get(pk=pk)
            self.assertEqual(_digest(_content(obj)), expected)
