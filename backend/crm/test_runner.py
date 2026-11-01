from unittest.mock import patch

from django.db import connections, transaction
from django.db.backends.base.operations import BaseDatabaseOperations
from django.test import override_settings
from django.test.runner import DiscoverRunner


CSV_AUDIT_TRUNCATE_GUARDS = (
    ("crm_csvimportbatch", "crm_csvimportbatch_truncate_guard"),
    ("crm_csvimportrowaudit", "crm_csvimportrowaudit_truncate_guard"),
    ("crm_csvimportpreviewaudit", "crm_csvimportpreviewaudit_truncate_guard"),
)


class DevelopmentAccessTestRunner(DiscoverRunner):
    """Preserve local development access for legacy API business-flow tests."""

    def setup_databases(self, **kwargs):
        aliases = kwargs.get("aliases")
        if aliases is None:
            aliases = tuple(connections)
        aliases = tuple(aliases)
        self._configured_database_names = {
            alias: connections[alias].settings_dict["NAME"] for alias in aliases
        }
        self._generated_test_databases = {
            alias: not connections[alias].settings_dict.get("TEST", {}).get("NAME")
            for alias in aliases
        }

        old_config = super().setup_databases(**kwargs)
        self._test_database_names = {
            alias: connections[alias].settings_dict["NAME"] for alias in aliases
        }
        return old_config

    def _is_generated_postgres_test_database(self, connection):
        alias = connection.alias
        original_name = getattr(self, "_configured_database_names", {}).get(alias)
        test_name = getattr(self, "_test_database_names", {}).get(alias)
        return (
            connection.vendor == "postgresql"
            and self._generated_test_databases.get(alias, False)
            and bool(original_name)
            and test_name == connection.settings_dict["NAME"]
            and test_name == f"test_{original_name}"
            and test_name != original_name
        )

    def run_suite(self, suite, **kwargs):
        execute_sql_flush = BaseDatabaseOperations.execute_sql_flush

        def execute_sql_flush_with_temporary_audit_guard_window(operations, sql_list):
            connection = operations.connection
            if not sql_list or not self._is_generated_postgres_test_database(connection):
                return execute_sql_flush(operations, sql_list)

            quote = connection.ops.quote_name
            # Django's TransactionTestCase cleanup reaches this method through
            # `flush`, whose PostgreSQL implementation uses TRUNCATE ... CASCADE.
            # Keep the narrow, test-only exception in the same transaction as
            # the cleanup so PostgreSQL rolls it all back if any step fails.
            with transaction.atomic(using=connection.alias):
                with connection.cursor() as cursor:
                    for table_name, trigger_name in CSV_AUDIT_TRUNCATE_GUARDS:
                        cursor.execute(
                            f"ALTER TABLE {quote(table_name)} DISABLE TRIGGER {quote(trigger_name)}"
                        )

                execute_sql_flush(operations, sql_list)

                with connection.cursor() as cursor:
                    for table_name, trigger_name in CSV_AUDIT_TRUNCATE_GUARDS:
                        cursor.execute(
                            f"ALTER TABLE {quote(table_name)} ENABLE TRIGGER {quote(trigger_name)}"
                        )

        # Raw SQL issued by application code or security tests does not pass
        # through this Django cleanup hook and continues to hit the guards.
        with patch.object(
            BaseDatabaseOperations,
            "execute_sql_flush",
            new=execute_sql_flush_with_temporary_audit_guard_window,
        ):
            return super().run_suite(suite, **kwargs)

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        self._development_access = override_settings(
            APP_STAGE="development",
            DEBUG=True,
            DEVELOPMENT_SUPERADMIN=True,
            RBAC_ENFORCEMENT=False,
        )
        self._development_access.enable()

    def teardown_test_environment(self, **kwargs):
        self._development_access.disable()
        super().teardown_test_environment(**kwargs)
