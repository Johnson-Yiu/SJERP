"""REAL_API_OBSERVATION: same request-key replay and conflicting payload."""
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from django.conf import settings
from crm.models import RmbCashEvent

assert Path(settings.DATABASES["default"]["NAME"]).name == "r1-fin-p2-b-isolated.sqlite3"
event = RmbCashEvent.objects.filter(status="confirmed").order_by("id").last()
assert event is not None
payload = event.request_payload

def post(body):
    req = Request("http://127.0.0.1:8139/api/rmb-cash-events/", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=10) as response:
            return response.status, json.loads(response.read().decode())
    except HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())

same_status, same_body = post(payload)
conflict = dict(payload)
conflict["bank_reference"] = f"{payload['bank_reference']}-CONFLICT"
conflict_status, conflict_body = post(conflict)
out = Path(__file__).resolve().parent / "idempotency-observation.json"
out.write_text(json.dumps({
    "same_request": {"status": same_status, "event_id": same_body.get("id"), "event_no": same_body.get("event_no"), "status_value": same_body.get("status")},
    "conflicting_payload": {"status": conflict_status, "detail": conflict_body.get("detail")},
    "database_event_count": RmbCashEvent.objects.count(),
}, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"REAL_API_OBSERVATION": {"same_status": same_status, "conflict_status": conflict_status, "event_count": RmbCashEvent.objects.count()}}, ensure_ascii=False))
