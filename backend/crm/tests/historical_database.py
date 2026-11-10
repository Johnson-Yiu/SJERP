from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from django.db import DEFAULT_DB_ALIAS, connections
from django.test import TransactionTestCase

from crm.postgres_test_cleanup import TEST_NAME


@contextmanager
def historical_database():
    """Route migrations and historical ORM models to a disposable empty database."""
    alias = DEFAULT_DB_ALIAS
    original = connections[alias]
    with TemporaryDirectory(prefix="sunjack-migrations-") as directory:
        if original.vendor == "sqlite":
            name = str(Path(directory) / "history.sqlite3")
        elif original.vendor == "postgresql" and TEST_NAME.fullmatch(original.settings_dict["NAME"]):
            name = f"test_sunjack_{uuid4().hex}"
        else:
            raise RuntimeError("Historical migration tests require an isolated Django test database.")

        isolated = type(original)({**original.settings_dict, "NAME": name}, alias)
        if original.vendor == "postgresql":
            with original.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE {original.ops.quote_name(name)} TEMPLATE template0")

        connections[alias] = isolated
        try:
            yield isolated
        finally:
            connections[alias] = original
            try:
                isolated.close()
            finally:
                if original.vendor == "postgresql":
                    with original.cursor() as cursor:
                        cursor.execute(f"DROP DATABASE {original.ops.quote_name(name)}")


class HistoricalMigrationTestCase(TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.enterContext(historical_database())
