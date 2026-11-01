from contextlib import ExitStack
from copy import deepcopy
import os
import re
from unittest.mock import patch
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import connections
from django.db.backends.base.base import BaseDatabaseWrapper
from django.test import override_settings
from django.test.runner import DiscoverRunner

from .postgres_test_cleanup import TEST_NAME, bind_created_test_database, test_teardown_patch


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
        selected = kwargs.get("aliases")
        postgres = [conn for conn in connections.all() if conn.vendor == "postgresql"]
        if postgres and (len(postgres) != 1 or postgres[0].settings_dict["TEST"].get("MIRROR")):
            raise ImproperlyConfigured("PostgreSQL audit cleanup currently supports one non-mirror alias only.")
        candidates = [
            conn for conn in connections.all()
            if conn.vendor == "postgresql"
            and (selected is None or conn.alias in selected)
            and not conn.settings_dict["TEST"].get("MIRROR")
        ]
        # A fresh random database is mandatory: never enroll an existing test DB,
        # an explicit TEST.NAME, a parallel clone, or a remote server by guesswork.
        for conn in candidates:
            if (
                self.keepdb or self.parallel not in (0, 1)
                or conn.settings_dict["TEST"].get("NAME")
                or conn.settings_dict.get("HOST") not in ("127.0.0.1", "::1")
                or not conn.settings_dict.get("USER")
                or conn.settings_dict.get("OPTIONS")
                or not re.fullmatch(r"[A-Za-z0-9_]+", conn.settings_dict.get("NAME") or "")
                or any(key.startswith("PG") for key in os.environ)
            ):
                raise ImproperlyConfigured(
                    "PostgreSQL audit cleanup requires a new local serial test database "
                    "(numeric loopback HOST, explicit USER, simple source name, empty OPTIONS; "
                    "no libpq PG* environment, --keepdb, --parallel, or custom TEST.NAME)."
                )
        self._pg_test_targets = {
            conn.alias: (conn, conn.settings_dict["NAME"], f"test_sunjack_{uuid4().hex}")
            for conn in candidates
        }
        self._pg_name_settings = {
            conn.alias: (
                conn.settings_dict["NAME"], conn.settings_dict["TEST"].get("NAME"),
                settings.DATABASES[conn.alias]["NAME"], settings.DATABASES[conn.alias]["TEST"].get("NAME"),
            )
            for conn in candidates
        }
        self._pg_lifecycle = ExitStack()
        self._pg_created = []
        self._pg_teardown_hook = None
        try:
            for conn, _source, target in self._pg_test_targets.values():
                if target == _source:
                    raise ImproperlyConfigured("Generated test database must differ from the source database.")
                conn.settings_dict["TEST"]["NAME"] = target
                settings.DATABASES[conn.alias]["TEST"]["NAME"] = target
                # Django's PostgreSQL override may fall back to the configured
                # source DB if maintenance connection fails. Never allow that.
                strict_maintenance = BaseDatabaseWrapper._nodb_cursor.__get__(conn, type(conn))
                self._pg_lifecycle.enter_context(patch.object(conn, "_nodb_cursor", strict_maintenance))

                def create(verbosity, autoclobber, keepdb=False, conn=conn, target=target):
                    if keepdb or conn.creation._get_test_db_name() != target:
                        raise ImproperlyConfigured("Unexpected test database creation target.")
                    params = {
                        "dbname": conn.ops.quote_name(target),
                        "suffix": conn.creation.sql_table_creation_suffix(),
                    }
                    # One CREATE attempt only. A collision/error must never
                    # invoke Django's autoclobber DROP-existing-DB retry.
                    with conn.creation._nodb_cursor() as cursor:
                        conn.creation._execute_create_test_db(cursor, params, False)
                        self._pg_created.append((conn, target, deepcopy(conn.settings_dict)))
                    return target

                self._pg_lifecycle.enter_context(patch.object(conn.creation, "_create_test_db", create))
            old_config = super().setup_databases(**kwargs)
            bindings = {
                alias: bind_created_test_database(conn, source, target)
                for alias, (conn, source, target) in self._pg_test_targets.items()
            }
            self._pg_teardown_hook = test_teardown_patch(bindings) if bindings else None
            if self._pg_teardown_hook:
                self._pg_teardown_hook.start()
            return old_config
        except BaseException as error:
            hook = getattr(self, "_pg_teardown_hook", None)
            if hook:
                hook.stop()
            # Only databases whose CREATE returned successfully are ours to drop.
            # This also covers migration/serialization failure inside Django setup.
            for record in reversed(self._pg_created.copy()):
                try:
                    self._destroy_owned_database(record)
                    self._pg_created.remove(record)
                except Exception as cleanup_error:
                    error.add_note(
                        f"Temporary test database {record[1]} could not be removed "
                        f"({type(cleanup_error).__name__}); manual isolated cleanup required."
                    )
            self._restore_test_names()
            self._pg_lifecycle.close()
            raise

    def _restore_test_names(self):
        for alias, (name, test_name, global_name, global_test_name) in getattr(self, "_pg_name_settings", {}).items():
            connections[alias].close()
            connections[alias].settings_dict["NAME"] = name
            connections[alias].settings_dict["TEST"]["NAME"] = test_name
            settings.DATABASES[alias]["NAME"] = global_name
            settings.DATABASES[alias]["TEST"]["NAME"] = global_test_name

    def _destroy_owned_database(self, record):
        conn, target, enrolled_settings = record
        # Never derive a DROP target or server from post-test connection state.
        config = deepcopy(enrolled_settings)
        if (
            not TEST_NAME.fullmatch(target)
            or target != config["TEST"].get("NAME")
            or target == config.get("NAME")
            or config.get("HOST") not in ("127.0.0.1", "::1")
            or not config.get("USER") or config.get("OPTIONS")
            or any(key.startswith("PG") for key in os.environ)
        ):
            raise ImproperlyConfigured("Owned test database cleanup identity is unsafe; DROP refused.")
        conn.close()
        config["NAME"] = target
        cleanup_connection = type(conn)(config, alias=f"_cleanup_{conn.alias}")
        try:
            strict_maintenance = BaseDatabaseWrapper._nodb_cursor.__get__(cleanup_connection, type(cleanup_connection))
            with patch.object(cleanup_connection, "_nodb_cursor", strict_maintenance):
                cleanup_connection.creation._destroy_test_db(target, self.verbosity)
        finally:
            cleanup_connection.close()

    def teardown_databases(self, old_config, **kwargs):
        try:
            hook = getattr(self, "_pg_teardown_hook", None)
            if hook:
                hook.stop()
            errors = []
            for record in reversed(getattr(self, "_pg_created", []).copy()):
                try:
                    self._destroy_owned_database(record)
                    self._pg_created.remove(record)
                except Exception as error:
                    errors.append((record[1], error))
            # PostgreSQL uses only the explicit owned records above, even if a
            # test has changed NAME/HOST/OPTIONS or Django's old_config entries.
            try:
                enrolled_objects = {id(conn) for conn, _source, _target in getattr(self, "_pg_test_targets", {}).values()}
                other_databases = [row for row in old_config if id(row[0]) not in enrolled_objects and row[0].vendor != "postgresql"]
                super().teardown_databases(other_databases, **kwargs)
            except Exception as error:
                errors.append(("other test database", error))
            if errors:
                failure = RuntimeError("Some temporary test databases could not be destroyed.")
                for target, error in errors:
                    failure.add_note(f"{target}: {type(error).__name__}; manual isolated cleanup required.")
                raise failure from errors[0][1]
        finally:
            self._restore_test_names()
            lifecycle = getattr(self, "_pg_lifecycle", None)
            if lifecycle:
                lifecycle.close()
