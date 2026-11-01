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
GUARD_FUNCTION = "crm_reject_csv_import_audit_truncate"
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


def assert_truncate_guards_enabled(connection):
    """Check the exact three BEFORE STATEMENT TRUNCATE guards, without repairing them."""
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
            [list(TRUNCATE_GUARDS), list(TRUNCATE_GUARDS.values())],
        )
        actual = set(cursor.fetchall())
    expected = {
        (table, trigger, "O", 34, GUARD_FUNCTION, "public")
        for table, trigger in TRUNCATE_GUARDS.items()
    }
    if actual != expected:
        raise ImproperlyConfigured("CSV audit TRUNCATE guards missing or changed; cleanup refused.")


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
            tables = ", ".join(f'"public".{connection.ops.quote_name(table)}' for table in sorted(TRUNCATE_GUARDS))
            cursor.execute(f"LOCK TABLE {tables} IN ACCESS EXCLUSIVE MODE")
            assert_truncate_guards_enabled(connection)
            for table, trigger in TRUNCATE_GUARDS.items():
                cursor.execute(
                    f'ALTER TABLE "public".{connection.ops.quote_name(table)} '
                    f'DISABLE TRIGGER {connection.ops.quote_name(trigger)}'
                )
            original_execute(sql_list)
            for table, trigger in TRUNCATE_GUARDS.items():
                cursor.execute(
                    f'ALTER TABLE "public".{connection.ops.quote_name(table)} '
                    f'ENABLE TRIGGER {connection.ops.quote_name(trigger)}'
                )
            assert_truncate_guards_enabled(connection)
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
