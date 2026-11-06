"""Cleanup for newly created Django test databases; never installed by app startup."""

from contextlib import ExitStack
from copy import deepcopy
from dataclasses import dataclass
import re
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.db import connections, transaction
from django.test import TransactionTestCase


TRUNCATE_GUARDS = {
    "crm_csvimportbatch": "crm_csvimportbatch_truncate_guard",
    "crm_csvimportrowaudit": "crm_csvimportrowaudit_truncate_guard",
    "crm_csvimportpreviewaudit": "crm_csvimportpreviewaudit_truncate_guard",
}
HISTORY_GUARDS = {
    "crm_historyinventorybaseline": "crm_historyinventorybaseline_truncate_guard",
    "crm_historyinventorybaselinereversal": "crm_historyinventorybaselinereversal_truncate_guard",
    "crm_historyoperationalcontract": "crm_historyoperationalcontract_truncate_guard",
}
HISTORY_MIGRATION = "0108_history_append_only_truncate"
HISTORY_FUNCTION = "crm_reject_history_truncate"
REVIEW_TABLE = "crm_cashduplicatereview"
REVIEW_TRIGGER = "crm_cashduplicatereview_truncate_guard"
REVIEW_MIGRATION = "0096_rmbcashevent_bank_counterparty_and_more"
GUARD_FUNCTION = "crm_reject_csv_import_audit_truncate"
PARTY_TABLE = "crm_partydocumentversion"
PARTY_TRIGGER = "crm_party_document_version_truncate_guard"
PARTY_FUNCTION = "crm_party_document_version_immutable"
PARTY_MIGRATION = "0114_party_document_version"
TERMINAL_TABLE = "crm_partyversionterminalevent"
TERMINAL_TRIGGER = "crm_party_terminal_truncate_guard"
TERMINAL_FUNCTION = "crm_party_terminal_immutable"
TERMINAL_MIGRATION = "0113_party_request_lifecycle"
REPLACEMENT_MIGRATION = "0115_party_replacement"
REPLACEMENT_FUNCTION = "crm_party_replacement_immutable"
REPLACEMENT_GUARDS = {"crm_partyreplacementtarget": "crm_partyreplacementtarget_truncate_guard", "crm_partyreplacementlink": "crm_partyreplacementlink_truncate_guard"}
TEST_NAME = re.compile(r"test_sunjack_[0-9a-f]{32}\Z")
IDENTITY_FIELDS = ("NAME", "HOST", "PORT", "USER", "OPTIONS")


@dataclass(frozen=True)
class TestDatabaseBinding:
    connection: object
    name: str
    original_name: str
    settings: dict


def bind_created_test_database(connection, original_name, generated_name):
    """Called only after DiscoverRunner has created its random, disposable DB."""
    if (
        connection.vendor != "postgresql"
        or not TEST_NAME.fullmatch(generated_name)
        or not original_name
        or original_name == generated_name
        or connection.settings_dict["NAME"] != generated_name
    ):
        raise ImproperlyConfigured("Refusing to enroll an unrecognized PostgreSQL test database.")
    return TestDatabaseBinding(
        connection, generated_name, original_name,
        deepcopy({key: connection.settings_dict.get(key) for key in IDENTITY_FIELDS}),
    )


def _assert_identity(connection, binding):
    if (
        connection is not binding.connection
        or connection.vendor != "postgresql"
        or binding.name == binding.original_name
        or not TEST_NAME.fullmatch(binding.name)
        or {key: connection.settings_dict.get(key) for key in IDENTITY_FIELDS} != binding.settings
        or connection.settings_dict["NAME"] != binding.name
    ):
        raise ImproperlyConfigured("PostgreSQL test database identity changed; cleanup refused.")
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database(), current_schema()")
        if cursor.fetchone() != (binding.name, "public"):
            raise ImproperlyConfigured("Cleanup requires the enrolled test database and public schema.")


def active_truncate_guards(connection):
    """Migration state and table presence must agree before teardown can proceed."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT to_regclass('public.crm_cashduplicatereview') IS NOT NULL, "
            "EXISTS (SELECT 1 FROM django_migrations WHERE app = %s AND name = %s), "
            "EXISTS (SELECT 1 FROM django_migrations WHERE app = %s AND name = %s), "
            "to_regclass('public.crm_partydocumentversion') IS NOT NULL, "
            "EXISTS (SELECT 1 FROM django_migrations WHERE app = %s AND name = %s), "
            "to_regclass('public.crm_partyversionterminalevent') IS NOT NULL, "
            "EXISTS (SELECT 1 FROM django_migrations WHERE app = %s AND name = %s)",
            ["crm", REVIEW_MIGRATION, "crm", HISTORY_MIGRATION, "crm", PARTY_MIGRATION, "crm", TERMINAL_MIGRATION],
        )
        table_exists, migration_applied, history_applied, party_table_exists, party_migration_applied, terminal_table_exists, terminal_migration_applied = cursor.fetchone()
    if table_exists != migration_applied:
        raise ImproperlyConfigured("Duplicate review migration and table disagree; cleanup refused.")
    if party_table_exists != party_migration_applied:
        raise ImproperlyConfigured("Party document migration and table disagree; cleanup refused.")
    if terminal_table_exists != terminal_migration_applied:
        raise ImproperlyConfigured("Party terminal migration and table disagree; cleanup refused.")
    guards = dict(TRUNCATE_GUARDS)
    with connection.cursor() as cursor:
        cursor.execute("SELECT EXISTS (SELECT 1 FROM django_migrations WHERE app=%s AND name=%s), to_regclass('public.crm_partyreplacementtarget') IS NOT NULL, to_regclass('public.crm_partyreplacementlink') IS NOT NULL", ['crm', REPLACEMENT_MIGRATION])
        replacement_applied, target_exists, link_exists = cursor.fetchone()
    if replacement_applied != target_exists or replacement_applied != link_exists:
        raise ImproperlyConfigured('Party replacement migration and tables disagree; cleanup refused.')
    if replacement_applied:
        guards.update(REPLACEMENT_GUARDS)
    if migration_applied:
        guards[REVIEW_TABLE] = REVIEW_TRIGGER
    if history_applied:
        guards.update(HISTORY_GUARDS)
    if party_migration_applied:
        guards[PARTY_TABLE] = PARTY_TRIGGER
    if terminal_migration_applied:
        guards[TERMINAL_TABLE] = TERMINAL_TRIGGER
    return guards


def assert_truncate_guards_enabled(connection, guards=None):
    """Check the exact BEFORE STATEMENT TRUNCATE guards, without repairing them."""
    guards = active_truncate_guards(connection) if guards is None else guards
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT c.relname, t.tgname, t.tgenabled, t.tgtype, p.proname, pn.nspname
            FROM pg_trigger t
            JOIN pg_class c ON c.oid = t.tgrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            JOIN pg_proc p ON p.oid = t.tgfoid
            JOIN pg_namespace pn ON pn.oid = p.pronamespace
            WHERE n.nspname = 'public' AND NOT t.tgisinternal
              AND c.relname = ANY(%s) AND t.tgname = ANY(%s)
            """,
            [list(guards), list(guards.values())],
        )
        actual = set(cursor.fetchall())
    expected = {
        (table, trigger, "O", 34, REPLACEMENT_FUNCTION if table in REPLACEMENT_GUARDS else PARTY_FUNCTION if table == PARTY_TABLE else TERMINAL_FUNCTION if table == TERMINAL_TABLE else HISTORY_FUNCTION if table in HISTORY_GUARDS else GUARD_FUNCTION, "public")
        for table, trigger in guards.items()
    }
    if actual != expected:
        raise ImproperlyConfigured("Audit TRUNCATE guards missing or changed; cleanup refused.")


def execute_test_flush(connection, binding, original_execute, sql_list):
    """Atomically restore guards on success, or roll all DDL/data back on failure.

    ACCESS EXCLUSIVE locks are held until commit. No disabled guard state is
    committed, and other connections cannot access these tables during cleanup.
    UPDATE/DELETE guards and all constraints remain installed and enabled.
    """
    _assert_identity(connection, binding)
    if connection.in_atomic_block or not connection.get_autocommit():
        raise ImproperlyConfigured("Test flush must start outside an existing transaction.")
    with transaction.atomic(using=connection.alias):
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL lock_timeout = '5s'")
            cursor.execute("SET LOCAL statement_timeout = '20s'")
            guards = active_truncate_guards(connection)
            tables = ", ".join(f'"public".{connection.ops.quote_name(table)}' for table in sorted(guards))
            cursor.execute(f"LOCK TABLE {tables} IN ACCESS EXCLUSIVE MODE")
            if guards != active_truncate_guards(connection):
                raise ImproperlyConfigured("Audit migration state changed during cleanup; cleanup refused.")
            assert_truncate_guards_enabled(connection, guards)
            for table, trigger in guards.items():
                cursor.execute(
                    f'ALTER TABLE "public".{connection.ops.quote_name(table)} '
                    f'DISABLE TRIGGER {connection.ops.quote_name(trigger)}'
                )
            original_execute(sql_list)
            for table, trigger in guards.items():
                cursor.execute(
                    f'ALTER TABLE "public".{connection.ops.quote_name(table)} '
                    f'ENABLE TRIGGER {connection.ops.quote_name(trigger)}'
                )
            assert_truncate_guards_enabled(connection, guards)
    # No recovery SQL in finally: an aborted transaction cannot execute it.
    # The enclosing atomic rollback restores both the DDL and truncated data.


def test_teardown_patch(bindings):
    """Scope the SQL hook to the fixture teardown call, never the test body."""
    original_teardown = TransactionTestCase._fixture_teardown

    def teardown(case):
        with ExitStack() as stack:
            for alias in case._databases_names(include_mirrors=False):
                connection = connections[alias]
                if connection.vendor != "postgresql":
                    continue
                binding = bindings.get(alias)
                if binding is None:
                    raise ImproperlyConfigured("No runner-created test database binding for cleanup.")
                native_execute = connection.ops.execute_sql_flush

                def execute(sql_list, conn=connection, enrolled=binding, native=native_execute):
                    return execute_test_flush(conn, enrolled, native, sql_list)

                stack.enter_context(patch.object(connection.ops, "execute_sql_flush", execute))
            return original_teardown(case)

    return patch.object(TransactionTestCase, "_fixture_teardown", teardown)
