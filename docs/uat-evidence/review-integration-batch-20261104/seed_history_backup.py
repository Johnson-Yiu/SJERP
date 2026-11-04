"""Owned PG drill only: archive synthetic history via the official workflow."""
import hashlib
import json

from django.contrib.auth import get_user_model
from django.db import connection
from psycopg import sql

from crm.history_takeover import submit_workbook, review_group, execute_group
from crm.models import Customer, Supplier, SKU
from crm.tests.iss018_drill_fixture import _assert_synthetic_database
from crm.tests.test_history_takeover import HistoryTakeoverFixtureMixin


TABLES = ("crm_historytakeoverapplication", "crm_historytakeovergroup",
          "crm_historytakeoversourcerecord", "crm_historytakeoverhandoff", "crm_historytakeoverevent")


def verify():
    _assert_synthetic_database()
    tables = {}
    with connection.cursor() as cursor:
        for table in TABLES:
            cursor.execute(sql.SQL("SELECT row_to_json(t)::text FROM {} t ORDER BY id").format(sql.Identifier(table)))
            rows = [row[0] for row in cursor.fetchall()]
            tables[table] = {"rows": len(rows), "sha256": hashlib.sha256(json.dumps(rows, ensure_ascii=False).encode()).hexdigest()}
    return {"tables": tables, "scope": "Synthetic archived history; formal finance/inventory/fulfillment remain unconnected"}


def seed():
    _assert_synthetic_database()
    fixture = object.__new__(HistoryTakeoverFixtureMixin)
    fixture.customer = Customer.objects.get(code="ISS018-C")
    fixture.supplier = Supplier.objects.get(code="D8")
    fixture.sku = SKU.objects.get(sku="ISS018-SKU")
    fixture.product = fixture.sku.product
    owner = get_user_model().objects.get(username="iss018-drill-owner")
    rows = fixture.source_rows(source_system="ISS018_SYNTH_HISTORY")
    application, _, reused = submit_workbook(fixture.workbook_bytes(rows), "synthetic-backup-history.xlsx", owner)
    if reused:
        raise RuntimeError("History drill seed must run once in a new owned database")
    group = application.groups.get()
    review_group(group, owner, "approve", "Synthetic owned drill source and dependency verification", confirm_manual=True)
    group.refresh_from_db()
    group, reused = execute_group(group, owner)
    if reused or group.status != "executed":
        raise RuntimeError("Synthetic history execution did not complete")
    if group.execution_result["finance_records_posted"] != 0:
        raise RuntimeError("History archive unexpectedly posted financial records")
    return verify()
