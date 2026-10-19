"""FIXTURE_SETUP only: snapshot isolated legacy rows after adding fee source."""
import json
import os
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()
from django.conf import settings
from django.apps import apps
from django.core.serializers.json import DjangoJSONEncoder
from crm.models import RmbCashEvent, CashSourceAllocation, Transaction
assert Path(settings.DATABASES["default"]["NAME"]).name == "r1-fin-p2-c-isolated.sqlite3"
assert RmbCashEvent.objects.count() == 0 and CashSourceAllocation.objects.count() == 0
out = Path(__file__).resolve().parent
models_before = {m.__name__: list(m.objects.order_by("pk").values()) for m in apps.get_app_config("crm").get_models() if m not in {RmbCashEvent, CashSourceAllocation}}
(out / "legacy-before.json").write_text(json.dumps(models_before, cls=DjangoJSONEncoder, sort_keys=True, indent=2), encoding="utf-8")
data = json.loads((out / "fixture.json").read_text(encoding="utf-8"))
data["sources"]["bank_fee"] = Transaction.objects.get(transaction_no="P2C-CNY-BANK-FEE").pk
(out / "fixture.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print({"DATABASE_VERIFICATION": {"legacy_models": len(models_before), "transactions": Transaction.objects.count(), "bank_events": 0}})
