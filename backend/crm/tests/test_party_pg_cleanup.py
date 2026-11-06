"""0114 cleanup protection: mock control flow and real PostgreSQL trigger."""
from contextlib import nullcontext
from unittest import skipUnless
from unittest.mock import MagicMock, Mock, patch

from django.core.exceptions import ImproperlyConfigured
from django.db import DatabaseError, connection, transaction
from django.test import SimpleTestCase, TransactionTestCase
from crm.postgres_test_cleanup import (
    GUARD_FUNCTION, PARTY_FUNCTION, PARTY_TABLE, PARTY_TRIGGER, REPLACEMENT_FUNCTION, REPLACEMENT_GUARDS,
    TERMINAL_FUNCTION, TERMINAL_TABLE, TERMINAL_TRIGGER, TRUNCATE_GUARDS,
    active_truncate_guards, assert_truncate_guards_enabled,
    bind_created_test_database, execute_test_flush,
)


class PartyCleanupControlTests(SimpleTestCase):
    def setUp(self):
        self.name = 'test_sunjack_' + 'e' * 32
        self.conn = MagicMock()
        self.conn.vendor = 'postgresql'; self.conn.alias = 'default'
        self.conn.in_atomic_block = False; self.conn.get_autocommit.return_value = True
        self.conn.settings_dict = {'NAME': self.name, 'HOST': '127.0.0.1', 'PORT': '5432', 'USER': 'owner', 'OPTIONS': {}}
        self.conn.ops.quote_name.side_effect = lambda name: f'"{name}"'
        self.cursor = self.conn.cursor.return_value.__enter__.return_value
        def fetchone():
            sql = self.cursor.execute.call_args.args[0]
            if 'crm_partyreplacementtarget' in sql:
                return (True, True, True)
            if 'to_regclass' in sql:
                return (False, False, False, True, True, True, True)
            return (self.name, 'public')
        self.cursor.fetchone.side_effect = fetchone
        guards = {**TRUNCATE_GUARDS, **REPLACEMENT_GUARDS, PARTY_TABLE: PARTY_TRIGGER, TERMINAL_TABLE: TERMINAL_TRIGGER}
        self.cursor.fetchall.return_value = [
            (table, trigger, 'O', 34, REPLACEMENT_FUNCTION if table in REPLACEMENT_GUARDS else PARTY_FUNCTION if table == PARTY_TABLE else TERMINAL_FUNCTION if table == TERMINAL_TABLE else GUARD_FUNCTION, 'public')
            for table, trigger in guards.items()]
        self.binding = bind_created_test_database(self.conn, 'source_db', self.name)

    def test_exact_trigger_checked_and_test_flush_restores_it(self):
        self.assertEqual(active_truncate_guards(self.conn)[PARTY_TABLE], PARTY_TRIGGER)
        assert_truncate_guards_enabled(self.conn)
        events = []
        self.cursor.execute.side_effect = lambda sql, *args: events.append(sql)
        native = Mock(side_effect=lambda sql: events.append('native flush'))
        with patch('crm.postgres_test_cleanup.transaction.atomic', return_value=nullcontext()):
            execute_test_flush(self.conn, self.binding, native, ['TRUNCATE synthetic'])
        disabled = next(i for i, sql in enumerate(events) if PARTY_TRIGGER in sql and 'DISABLE TRIGGER' in sql)
        enabled = next(i for i, sql in enumerate(events) if PARTY_TRIGGER in sql and 'ENABLE TRIGGER' in sql)
        self.assertLess(disabled, events.index('native flush'))
        self.assertGreater(enabled, events.index('native flush'))
        self.assertTrue(any(TERMINAL_TRIGGER in sql and 'DISABLE TRIGGER' in sql for sql in events))
        self.assertTrue(any(TERMINAL_TRIGGER in sql and 'ENABLE TRIGGER' in sql for sql in events))
        for trigger in REPLACEMENT_GUARDS.values():
            self.assertTrue(any(trigger in sql and 'DISABLE TRIGGER' in sql for sql in events))
            self.assertTrue(any(trigger in sql and 'ENABLE TRIGGER' in sql for sql in events))

    def test_migration_table_mismatch_refuses_cleanup(self):
        for exists, applied in ((True, False), (False, True)):
            with self.subTest(exists=exists, applied=applied):
                self.cursor.fetchone.side_effect = lambda: (False, False, False, exists, applied, True, True)
                with self.assertRaises(ImproperlyConfigured):
                    active_truncate_guards(self.conn)

    def test_terminal_migration_table_mismatch_refuses_cleanup(self):
        for exists, applied in ((True, False), (False, True)):
            with self.subTest(exists=exists, applied=applied):
                self.cursor.fetchone.side_effect = lambda: (False, False, False, True, True, exists, applied)
                with self.assertRaises(ImproperlyConfigured):
                    active_truncate_guards(self.conn)

    def test_replacement_migration_table_mismatch_refuses_cleanup(self):
        for state in ((False, True, False), (False, False, True), (True, False, True), (True, True, False)):
            with self.subTest(state=state):
                self.cursor.fetchone.side_effect = lambda: (state if 'crm_partyreplacementtarget' in self.cursor.execute.call_args.args[0]
                    else (False, False, False, True, True, True, True))
                with self.assertRaises(ImproperlyConfigured):
                    active_truncate_guards(self.conn)

    def test_wrong_trigger_function_or_type_refused(self):
        expected = self.cursor.fetchall.return_value
        for wrong in (('wrong_function', 34), (PARTY_FUNCTION, 35)):
            with self.subTest(wrong=wrong):
                self.cursor.fetchall.return_value = [
                    (t, g, state, wrong[1], wrong[0], schema) if t == PARTY_TABLE else (t, g, state, typ, fn, schema)
                    for t, g, state, typ, fn, schema in expected]
                with self.assertRaises(ImproperlyConfigured):
                    assert_truncate_guards_enabled(self.conn)


@skipUnless(connection.vendor == 'postgresql', 'PostgreSQL trigger and teardown required')
class PartyCleanupPostgresTests(TransactionTestCase):
    def test_a_truncate_is_rejected_and_guard_enabled(self):
        self.assertEqual(active_truncate_guards(connection)[PARTY_TABLE], PARTY_TRIGGER)
        self.assertEqual(active_truncate_guards(connection)[TERMINAL_TABLE], TERMINAL_TRIGGER)
        assert_truncate_guards_enabled(connection)
        with self.assertRaises(DatabaseError), transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('TRUNCATE TABLE crm_partydocumentversion')
        with self.assertRaises(DatabaseError), transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('TRUNCATE TABLE crm_partyversionterminalevent')

    def test_b_guard_remains_enabled_after_previous_test_flush(self):
        self.assertEqual(active_truncate_guards(connection)[PARTY_TABLE], PARTY_TRIGGER)
        assert_truncate_guards_enabled(connection)
