"""Create the real history continuation in a disposable browser database."""
import json

import django
from django.conf import settings
from django.test.utils import override_settings

django.setup()

from crm.models import HistoryOperationalContract, Order
from crm.services.order_lifecycle import confirm_order
from crm.tests.test_history_operational_contracts import HistoricalOperationalContractTests
from crm import history_operational_contracts as contracts
from test_support.isolated_runtime import verify_isolated_runtime

verify_isolated_runtime(settings=settings, database_must_exist=True)
fixture = HistoricalOperationalContractTests("test_snapshot_quantity_whole")
try:
    with override_settings(ALLOWED_HOSTS=[*settings.ALLOWED_HOSTS, 'testserver']):
        fixture.setUp()
    fixture.approve_contracts()
    contracts.execute(fixture.group.pk, fixture.maker)
    original = Order.objects.get(order_no="HIST-SO-HT-1")
    order = confirm_order(HistoryOperationalContract.objects.get(archived_order=original).continuation_order)
    print(json.dumps({"order": order.pk, "number": order.order_no, "original": original.pk}))
finally:
    fixture.doCleanups()
