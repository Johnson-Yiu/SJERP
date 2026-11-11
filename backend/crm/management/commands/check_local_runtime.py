"""Read-only readiness check for a pinned PostgreSQL/private-media instance."""

import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, connections
from django.db.migrations.executor import MigrationExecutor


class Command(BaseCommand):
    help = __doc__

    def handle(self, **options):
        if settings.APP_STAGE not in {"staging", "production"}:
            raise CommandError("The business runtime requires staging or production settings.")

        connection = connections["default"]
        for field in ("HOST", "PORT", "NAME", "USER"):
            expected = os.environ.get(f"SJERP_EXPECTED_DB_{field}")
            if not expected or str(connection.settings_dict[field]) != expected:
                raise CommandError(f"Configured database {field} differs from the instance configuration.")

        expected_media = Path(os.environ.get("SJERP_EXPECTED_MEDIA_ROOT", ""))
        media = settings.MEDIA_ROOT.resolve()
        source = settings.BASE_DIR.parent.resolve()
        if (
            not expected_media.is_absolute()
            or expected_media.resolve() != media
            or media == source
            or source in media.parents
            or not media.is_dir()
            or not os.access(media, os.R_OK | os.W_OK | os.X_OK)
            or settings.MEDIA_STORAGE_BACKEND != "django.core.files.storage.FileSystemStorage"
        ):
            raise CommandError("The configured private media directory differs from the instance or is unavailable.")

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_database(), current_user")
                if cursor.fetchone() != (os.environ["SJERP_EXPECTED_DB_NAME"], os.environ["SJERP_EXPECTED_DB_USER"]):
                    raise CommandError("Connected PostgreSQL database or role differs from the instance.")
            executor = MigrationExecutor(connection)
            executor.loader.check_consistent_history(connection)
            if executor.migration_plan(executor.loader.graph.leaf_nodes()):
                raise CommandError("Database migrations are pending. Use the separate maintenance procedure.")

            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT rolsuper OR rolcreaterole OR rolcreatedb OR rolreplication OR rolbypassrls,
                           has_table_privilege(current_user, 'crm_operationlog', 'UPDATE, DELETE, TRUNCATE'),
                           has_table_privilege(current_user, 'crm_operationlog', 'SELECT')
                           AND has_table_privilege(current_user, 'crm_operationlog', 'INSERT')
                    FROM pg_roles WHERE rolname = current_user
                    """
                )
                if cursor.fetchone() != (False, False, True):
                    raise CommandError("The runtime PostgreSQL role violates the audit table privilege boundary.")
        except DatabaseError as error:
            raise CommandError(f"Database readiness check failed ({type(error).__name__}).") from None

        self.stdout.write("Database, migration state and private media checks passed.")
