"""Seed one disposable local SQLite DB for the real Chrome takeover walkthrough.

Run through ``python manage.py shell < seed_synthetic_uat.py`` after pointing
DATABASE_URL to a newly-created temporary SQLite file. This creates only
synthetic records and writes the ephemeral browser session to a temp file.
"""

import json
import os
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.middleware.csrf import get_token
from django.test import Client
from django.http import HttpRequest

from crm.history_takeover import submit_workbook
from crm.models import Customer, Product, SKU, Supplier
from crm.tests.test_history_takeover import HistoryTakeoverFixtureMixin


if settings.DATABASES["default"]["ENGINE"] != "django.db.backends.sqlite3":
    raise ImproperlyConfigured("Synthetic browser UAT must use its disposable SQLite DATABASE_URL.")

User = get_user_model()
user = User.objects.create_user(username="synthetic-history-uploader", password="synthetic-only-password")
customer = Customer.objects.create(code="UAT-HT-C", name="Synthetic History Customer", country="US")
supplier = Supplier.objects.create(code="H1", name="Synthetic History Supplier")
product = Product.objects.create(code="UAT-HT-P1", name="Synthetic History Product", sales_model_prefix="HT")
sku = SKU.objects.create(sku="UAT-HT-S1", product=product, display_name_cn="Synthetic SKU", unit="pcs")

fixture = object.__new__(HistoryTakeoverFixtureMixin)
fixture.customer = customer
fixture.supplier = supplier
fixture.product = product
fixture.sku = sku
rows = HistoryTakeoverFixtureMixin.source_rows(fixture, source_system="Synthetic browser UAT")
workbook = HistoryTakeoverFixtureMixin.workbook_bytes(fixture, rows)
application, _preflight, reused = submit_workbook(workbook, "synthetic-history-uAT.xlsx", user)
if reused:
    raise RuntimeError("Unexpected prior application in the newly-created UAT database.")
group = application.groups.get()

browser_client = Client()
if not browser_client.login(username=user.username, password="synthetic-only-password"):
    raise RuntimeError("Could not establish the disposable UAT session.")
csrf_request = HttpRequest()
csrf_token = get_token(csrf_request)
session_file = os.environ.get("HISTORY_UAT_SESSION_FILE")
if not session_file:
    raise RuntimeError("Set HISTORY_UAT_SESSION_FILE to a temporary path.")
Path(session_file).write_text(json.dumps({
    "sessionid": browser_client.cookies[settings.SESSION_COOKIE_NAME].value,
    "csrftoken": csrf_token,
}, ensure_ascii=False), encoding="utf-8")

print(json.dumps({"application_id": application.pk, "group_id": group.pk, "status": group.status}, ensure_ascii=False))
