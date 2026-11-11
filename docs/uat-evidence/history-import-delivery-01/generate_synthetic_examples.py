"""Generate synthetic examples from the current schema; no database writes."""
import csv
import os
from pathlib import Path
from types import SimpleNamespace
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()
from crm.tests.test_history_takeover import HistoryTakeoverFixtureMixin
from crm.views import IMPORT_FIELDS
out = Path(__file__).resolve().parent
fixture = SimpleNamespace(customer=SimpleNamespace(code="HT-C1"), supplier=SimpleNamespace(code="H1"), sku=SimpleNamespace(sku="HT-S1"))
rows = HistoryTakeoverFixtureMixin.source_rows(fixture, truth="模拟")
(out / "synthetic-history-example.xlsx").write_bytes(HistoryTakeoverFixtureMixin.workbook_bytes(fixture, rows))
with (out / "synthetic-customers-example.csv").open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=IMPORT_FIELDS["customers"])
    writer.writeheader()
    writer.writerow({"code": "HT-C1", "name": "合成客户", "country": "US", "notes": "仅供隔离演示"})
