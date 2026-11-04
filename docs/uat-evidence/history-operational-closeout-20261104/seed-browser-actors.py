"""Add synthetic finance fixtures and two sessions to a disposable UAT SQLite database."""
import json
import os
import tempfile
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpRequest
from django.middleware.csrf import get_token
from django.test import Client
from crm.services import finance_closeout
from crm.models import FinanceAccount, FinanceVoucher

db = Path(settings.DATABASES["default"]["NAME"]).resolve()
root = Path(tempfile.gettempdir()).resolve()
if settings.DATABASES["default"]["ENGINE"] != "django.db.backends.sqlite3" or not db.is_relative_to(root) or not db.parent.name.startswith("sunjack-history-operational-closeout-"):
    raise RuntimeError("Refusing to seed anything except the marked temporary UAT database")
User = get_user_model()
maker = User.objects.get(username="synthetic-history-uploader")
reviewer, _ = User.objects.get_or_create(username="synthetic-history-reviewer", defaults={"is_active": True})
account = FinanceAccount.objects.filter(code="UAT-HISTORY-CNY").first() or finance_closeout.create_account({"code": "UAT-HISTORY-CNY", "name": "合成验收账户", "account_type": "bank", "ownership": "own", "ownership_reason": "合成验收"}, maker)
voucher = FinanceVoucher.objects.filter(original_name="synthetic-uat.pdf").first() or finance_closeout.upload(SimpleUploadedFile("synthetic-uat.pdf", b"%PDF-1.4\nsynthetic evidence\n%%EOF"), maker)
for actor, filename in ((maker, "session.json"), (reviewer, "reviewer-session.json")):
    client = Client()
    client.force_login(actor)
    csrf = get_token(HttpRequest())
    (db.parent / filename).write_text(json.dumps({"sessionid": client.cookies[settings.SESSION_COOKIE_NAME].value, "csrftoken": csrf}), encoding="utf-8")
print(json.dumps({"account_id": account.pk, "voucher_id": voucher.pk, "actors": "synthetic maker and reviewer", "database": "temporary SQLite"}))
