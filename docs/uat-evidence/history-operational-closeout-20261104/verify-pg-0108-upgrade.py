"""Read and test migration protections only in the explicitly named synthetic PG17 DB."""
from django.db import DatabaseError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from crm.models import HistoryOperationalContract

config = connection.settings_dict
if connection.vendor != "postgresql" or config["HOST"] != "127.0.0.1" or str(config["PORT"]) != "9037" or config["NAME"] != "sunjack_history_isolated" or config["USER"] != "sunjack_test":
    raise RuntimeError("Refusing to operate outside the named disposable PostgreSQL cluster")
with connection.cursor() as cursor:
    cursor.execute("SELECT current_database(), current_user, current_setting('server_version_num')")
    db, user, version = cursor.fetchone()
if (db, user) != ("sunjack_history_isolated", "sunjack_test") or not (170000 <= int(version) < 180000):
    raise RuntimeError("Unexpected PostgreSQL database or version")
ids = list(HistoryOperationalContract.objects.values_list("pk", flat=True))
if not ids:
    raise RuntimeError("Expected synthetic contract data created before the migration")
try:
    MigrationExecutor(connection).migrate([("crm", "0107_inventory_movement_location")])
except RuntimeError as exc:
    assert "Refusing to remove historical append-only TRUNCATE protection" in str(exc), str(exc)
    print("PASS 0108 refuses downgrade with pre-existing synthetic history")
else:
    raise AssertionError("0108 downgrade unexpectedly succeeded")
assert list(HistoryOperationalContract.objects.values_list("pk", flat=True)) == ids
try:
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE crm_historyoperationalcontract CASCADE")
except DatabaseError as exc:
    assert "append-only" in str(exc), str(exc)
    print("PASS 0108 TRUNCATE trigger blocks populated upgraded table")
else:
    raise AssertionError("TRUNCATE unexpectedly succeeded")
assert list(HistoryOperationalContract.objects.values_list("pk", flat=True)) == ids
print("PASS pre-existing synthetic contracts remain intact")
