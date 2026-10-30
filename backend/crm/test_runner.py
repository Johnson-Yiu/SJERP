from django.db import connections
from django.test import override_settings
from django.test.runner import DiscoverRunner


def guarded_csv_audit_flush_sql(
    db_connection,
    original_sql_flush,
    style,
    tables,
    *,
    reset_sequences=False,
    allow_cascade=False,
):
    statements = original_sql_flush(
        style,
        tables,
        reset_sequences=reset_sequences,
        allow_cascade=allow_cascade,
    )
    if db_connection.vendor != "postgresql":
        return statements

    audit_tables = {
        "crm_csvimportbatch": "crm_csv_import_batch_truncate_guard",
        "crm_csvimportrowaudit": "crm_csv_import_row_audit_truncate_guard",
    }
    requested_tables = set(tables)
    relevant = [
        (table_name, trigger_name)
        for table_name, trigger_name in audit_tables.items()
        if table_name in requested_tables
    ]
    if not relevant:
        return statements

    trigger_names = [trigger_name for _table_name, trigger_name in relevant]
    placeholders = ", ".join(["%s"] * len(trigger_names))
    with db_connection.cursor() as cursor:
        cursor.execute(
            "SELECT tgname FROM pg_trigger "
            f"WHERE NOT tgisinternal AND tgname IN ({placeholders})",
            trigger_names,
        )
        installed_triggers = {row[0] for row in cursor.fetchall()}

    guarded = [
        (table_name, trigger_name)
        for table_name, trigger_name in relevant
        if trigger_name in installed_triggers
    ]
    if not guarded:
        return statements

    disable = [
        "ALTER TABLE "
        f"{db_connection.ops.quote_name(table_name)} DISABLE TRIGGER "
        f"{db_connection.ops.quote_name(trigger_name)};"
        for table_name, trigger_name in guarded
    ]
    enable = [
        "ALTER TABLE "
        f"{db_connection.ops.quote_name(table_name)} ENABLE TRIGGER "
        f"{db_connection.ops.quote_name(trigger_name)};"
        for table_name, trigger_name in guarded
    ]
    return [*disable, *statements, *enable]


class DevelopmentAccessTestRunner(DiscoverRunner):
    """Preserve local development access for legacy API business-flow tests."""

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

    def setup_databases(self, **kwargs):
        old_config = super().setup_databases(**kwargs)
        self._original_sql_flush = {}

        for db_connection in connections.all():
            if db_connection.vendor != "postgresql":
                continue

            original_sql_flush = db_connection.ops.sql_flush
            self._original_sql_flush[db_connection.alias] = original_sql_flush

            def guarded_sql_flush(
                style,
                tables,
                *,
                reset_sequences=False,
                allow_cascade=False,
                _connection=db_connection,
                _original=original_sql_flush,
            ):
                return guarded_csv_audit_flush_sql(
                    _connection,
                    _original,
                    style,
                    tables,
                    reset_sequences=reset_sequences,
                    allow_cascade=allow_cascade,
                )

            db_connection.ops.sql_flush = guarded_sql_flush

        return old_config

    def teardown_databases(self, old_config, **kwargs):
        try:
            return super().teardown_databases(old_config, **kwargs)
        finally:
            for alias, original_sql_flush in getattr(self, "_original_sql_flush", {}).items():
                connections[alias].ops.sql_flush = original_sql_flush
