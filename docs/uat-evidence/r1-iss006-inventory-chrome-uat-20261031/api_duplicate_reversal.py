"""Replay an already-reversed receipt over local HTTP and preserve the response."""
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener
from http.cookiejar import CookieJar

from crm.models import GoodsReceipt


evidence_dir = Path(__file__).parent
ids = json.loads((evidence_dir / "fixture-ids.json").read_text(encoding="utf-8"))
password = os.environ["ISS006_UAT_PASSWORD"]
base = "http://127.0.0.1:8127"
frontend_origin = "http://127.0.0.1:5237"
purchase_id = ids["purchase"]["receipt"]
receipt = GoodsReceipt.objects.filter(
    purchase_item__purchase_order_id=purchase_id,
    reversal_inventory_movement__isnull=False,
).order_by("pk").first()
assert receipt is not None, "No already-reversed receipt fixture was found"

cookies = CookieJar()
session = build_opener(HTTPCookieProcessor(cookies))
login_url = f"{base}/admin/login/"
with session.open(login_url, timeout=10) as login_page:
    assert login_page.status == 200, f"Admin login page failed: HTTP {login_page.status}"
csrf = next((cookie.value for cookie in cookies if cookie.name == "csrftoken"), None)
assert csrf, "Django admin did not issue a CSRF cookie"
login_body = urlencode({
        "username": "iss006-uat-synthetic",
        "password": password,
        "csrfmiddlewaretoken": csrf,
        "next": "/admin/",
    }).encode()
login_request = Request(login_url, data=login_body, headers={
    "Content-Type": "application/x-www-form-urlencoded",
    "Referer": login_url,
    "Origin": base,
})
with session.open(login_request, timeout=10) as login:
    assert "/admin/" in login.geturl() and "login" not in login.geturl(), "Synthetic account login was not accepted"
csrf = next((cookie.value for cookie in cookies if cookie.name == "csrftoken"), None) or csrf
url = f"{base}/api/purchase-orders/{purchase_id}/receipts/{receipt.pk}/reverse/"
request = Request(url, data=json.dumps({"reason": "ISS006 UAT duplicate reversal replay"}).encode(), headers={
    "Content-Type": "application/json",
    "X-CSRFToken": csrf,
    "Origin": frontend_origin,
    "Referer": f"{frontend_origin}/purchase-orders",
})
try:
    with session.open(request, timeout=10) as response:
        status_code = response.status
        response_text = response.read().decode("utf-8", errors="replace")
except HTTPError as response:
    status_code = response.code
    response_text = response.read().decode("utf-8", errors="replace")
try:
    body = json.loads(response_text)
except ValueError:
    body = {"raw": response_text[:1000]}

result = {
    "method": "POST",
    "path": f"/api/purchase-orders/{purchase_id}/receipts/{receipt.pk}/reverse/",
    "status": status_code,
    "body": body,
    "expected_status": 400,
    "assertion": "PASS" if status_code == 400 else "FAIL",
    "already_reversed_receipt_id": receipt.pk,
}
output = evidence_dir / "api-duplicate-reversal.json"
output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))
if status_code != 400:
    raise SystemExit(1)
