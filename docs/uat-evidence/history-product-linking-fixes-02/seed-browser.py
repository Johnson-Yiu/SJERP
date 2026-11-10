"""Seed a new isolated browser database with archival and pending H2 fixtures."""
from copy import deepcopy
import json
import os
from pathlib import Path

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings
from crm.history_product_models import ArchivedHistoryLine
from crm.tests.test_history_products import HistoricalProductLinkingTests

database = Path(settings.DATABASES["default"]["NAME"]).resolve()
assert database == Path(os.environ["ISOLATED_TEST_DATABASE"]).resolve()
assert Path(os.environ["ISOLATED_TEST_ROOT"]).resolve() in database.parents

settings.ALLOWED_HOSTS += ["testserver"]
fixture = HistoricalProductLinkingTests()
fixture.setUp()
b = fixture.target()
saved = fixture.submit(fixture.preview(fixture.sales_ids[:1], b, save_rule=True))
assert saved.data == {"updated": 1}, saved.data
manual = fixture.sources.get(pk=fixture.sales_ids[1])
line = ArchivedHistoryLine.objects.get(pk=manual.target_id)
line.facts = {**line.facts, "specification_snapshot": ""}
line.save(update_fields=["facts"])

rows = deepcopy(fixture.rows)
for sheet in ("销售订单", "采购订单", "销售明细", "采购明细"):
    for row in rows[sheet]:
        for key in ("order_no", "purchase_no", "source_record_id", "source_order_id", "source_purchase_id"):
            if row.get(key):
                row[key] += "-H2"
        row["group_id"] = "H2-CANDIDATE"
rows["分组"][0]["group_id"] = "H2-CANDIDATE"
app, group, _ = fixture.application_and_group(rows)
assert any(item.get("product_candidates") for item in group.preflight_result["results"])
print(json.dumps({"archived": fixture.application.pk, "candidate": app.pk}))
