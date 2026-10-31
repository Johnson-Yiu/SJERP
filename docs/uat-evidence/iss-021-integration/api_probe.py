"""Capture real HTTP requests/responses against the isolated ISS-021 server."""
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

evidence = Path(__file__).resolve().parent
records = []

def call(path, payload=None, expected=200):
    data = json.dumps(payload).encode() if payload is not None else None
    req = Request("http://127.0.0.1:28321/api/" + path, data=data, headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=30) as response:
            code, body = response.status, response.read().decode()
    except HTTPError as response:
        code, body = response.code, response.read().decode()
    record = {"path": path, "request": payload, "status": code, "response": json.loads(body)}
    records.append(record)
    (evidence / "api-evidence.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    assert code == expected, record
    return record["response"]

def payload(item, quantity, version=0, key="probe"):
    return {"version": version, "request_key": key, "reason": "ISS-021 隔离 API 验收", "items": [{"order_item": item, "new_quantity": quantity}]}

increase = payload(1, "150", key="iss021-http-increase")
preview = call("orders/1/quantity-adjustments/preview/", increase)
assert preview["financial"]["after_total"] == "1500.0000"
call("orders/1/quantity-adjustments/", increase, 201)
call("orders/1/quantity-adjustments/", increase)
call("orders/1/quantity-adjustments/", payload(1, "120", key="stale"), 409)
call("orders/1/quantity-adjustments/", payload(1, "60", version=1, key="iss021-http-decrease"), 201)
call("orders/1/quantity-adjustments/")
call("orders/2/quantity-adjustments/preview/", payload(2, "60"), 400)
call("orders/2/quantity-adjustments/", payload(2, "60"), 400)
call("orders/2/quantity-adjustments/", payload(2, "100"), 400)
paid = call("orders/3/quantity-adjustments/preview/", payload(3, "60"))
assert not paid["can_submit"]
call("orders/3/quantity-adjustments/", payload(3, "60"), 400)
workbench = call("orders/1/workbench/")
assert workbench["order"]["customer_name_snapshot"] == "ISS021 原确认客户"
assert workbench["order"]["total_amount"] == "600.00"
assert len(workbench["quantity_adjustments"]) == 2
print(json.dumps({"http_checks": len(records), "results": [{"path": row["path"], "status": row["status"]} for row in records]}, ensure_ascii=False))
