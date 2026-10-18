"""REAL_API_OBSERVATION + DATABASE_VERIFICATION, synthetic localhost only."""
import hashlib
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()
from django.conf import settings
from django.apps import apps
from django.core.serializers.json import DjangoJSONEncoder
from crm.models import RmbCashEvent, CashSourceAllocation

assert Path(settings.DATABASES["default"]["NAME"]).name == "r1-fin-p2-a-isolated.sqlite3"
p = Path(__file__).resolve().parent
payload = json.loads((p / "http-request.json").read_text(encoding="utf8"))
observations = []
def call(method, path, body=None, expected=200):
    request = urllib.request.Request("http://127.0.0.1:8138/api/" + path, data=None if body is None else json.dumps(body).encode(), method=method, headers={"Content-Type": "application/json"})
    try: response = urllib.request.urlopen(request)
    except urllib.error.HTTPError as error: response = error
    data = json.loads(response.read())
    observations.append(dict(method=method, path=path, request=body, status=response.status, response=data))
    assert response.status == expected, observations[-1]
    return data

legacy_finance = call("GET", "finance-dashboard/")
preview = call("POST", "rmb-cash-events/preview/", payload)
assert RmbCashEvent.objects.count() == 0
created = call("POST", "rmb-cash-events/", payload, 201)
pk = created["id"]
call("POST", f"rmb-cash-events/{pk}/confirm/", {"voucher_checked": True})
call("POST", "rmb-cash-events/", payload)
call("POST", f"rmb-cash-events/{pk}/confirm/", {"voucher_checked": True})
call("GET", "rmb-cash-events/by-request-key/?request_key=" + payload["request_key"])
call("POST", "rmb-cash-events/", dict(payload, bank_net_amount="706.00"), 409)
call("POST", "rmb-cash-events/", dict(payload, event_no="P2A-OVER", request_key="P2A-OVER"), 409)
call("POST", "transactions/" + str(payload["sources"][0]["transaction_id"]) + "/void/", {"reason": "Synthetic rejection check"}, 400)
call("POST", f"rmb-cash-events/{pk}/cancel/", {"reason": "Cannot cancel confirmed bank fact"}, 400)
call("POST", "rmb-cash-events/", dict(payload, event_no="P2A-CORRECTION", request_key="P2A-CORRECTION", correction_of=pk), 400)
assert call("GET", "finance-dashboard/") == legacy_finance
after = {m.__name__: list(m.objects.order_by("pk").values()) for m in apps.get_app_config("crm").get_models() if m not in {RmbCashEvent, CashSourceAllocation}}
raw = json.dumps(after, cls=DjangoJSONEncoder, sort_keys=True, indent=2)
before = (p / "legacy-before.json").read_text(encoding="utf8")
assert raw == before
(p / "legacy-after.json").write_text(raw, encoding="utf8")
assert RmbCashEvent.objects.count() == 1 and CashSourceAllocation.objects.count() == 2
event = RmbCashEvent.objects.get()
assert str(event.bank_net_amount) == "705.00" and str(event.fee_amount) == "5.00"
(p / "http-observations.json").write_text(json.dumps(observations, ensure_ascii=False, indent=2), encoding="utf8")
print("REAL_API_OBSERVATION PASS:", len(observations), "actual HTTP requests; 201/200/409/400 observed")
print("DATABASE_VERIFICATION PASS:", hashlib.sha256(raw.encode()).hexdigest(), "identical legacy rows; only 1 event and 2 source rows added, net CNY705.00; fee CNY5.00 informational")
