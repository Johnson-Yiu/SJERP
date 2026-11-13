"""Synthetic fixture, guarded against use outside the owned browser database."""
import json
import os
from pathlib import Path
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from django.conf import settings
from crm.tests.test_history_operational_contracts import HistoricalOperationalContractTests
from crm import history_operational_contracts as contracts

database = Path(settings.DATABASES["default"]["NAME"]).resolve()
assert database == Path(os.environ["ISOLATED_TEST_DATABASE"]).resolve()
assert Path(os.environ["ISOLATED_TEST_ROOT"]).resolve() in database.parents
settings.ALLOWED_HOSTS += ["testserver"]
fixture = HistoricalOperationalContractTests()
fixture.setUp()
fixture.sku.currency = "USD"
fixture.sku.cost_currency = "CNY"
fixture.sku.save()
fixture.payload["contracts"][0]["line_options"][0].update(unit_cost="7.1250", cost_currency="USD" if os.environ.get("COST_BASELINE") == "1" else "EUR")
contracts.propose(fixture.group.pk, fixture.payload, fixture.maker)
print(json.dumps({"application": fixture.application.pk, "group": fixture.group.pk,
    "sku": fixture.sku.pk, "base": fixture.base}))
