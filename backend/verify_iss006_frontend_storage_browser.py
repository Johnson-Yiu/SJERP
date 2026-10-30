import json
import os
from pathlib import Path

import django

django.setup()

from django.conf import settings
from crm.models import GoodsReceipt, InventoryMovement, Shipment, ShipmentItem
from test_support.isolated_runtime import verify_isolated_runtime


verify_isolated_runtime(settings=settings, database_must_exist=True)
evidence_dir = Path(os.environ["ISS006_STORAGE_EVIDENCE_DIR"])
fixture = json.loads((evidence_dir / "fixture.json").read_text(encoding="utf-8"))
browser_results = json.loads((evidence_dir / "browser-results.json").read_text(encoding="utf-8"))
results_by_key = {row["case_key"]: row for row in browser_results["cases"]}
expected_case_names = {"property-getter", "get-item", "set-item-recovery", "remove-item-recovery", "lost-response"}
expected_keys = {f"{operation}:{name}" for operation in ("receive", "ship") for name in expected_case_names}
if set(results_by_key) != expected_keys:
    raise SystemExit(f"Browser evidence does not contain exactly the 10 expected cases: {sorted(results_by_key)}")

successful_cases = {"set-item-recovery", "remove-item-recovery", "lost-response"}
verification = {"database": str(settings.DATABASES["default"]["NAME"]), "media_root": str(settings.MEDIA_ROOT), "cases": []}
failures = []

for operation in ("receive", "ship"):
    for name, row in fixture[operation].items():
        case_key = f"{operation}:{name}"
        result = results_by_key[case_key]
        should_create_record = name in successful_cases
        if result.get("status") != "passed":
            failures.append(f"{case_key}: browser test status is {result.get('status')!r}")
        if result.get("request_count") != (0 if name in {"property-getter", "get-item"} else (1 if name == "set-item-recovery" else 2)):
            failures.append(f"{case_key}: unexpected observed POST request count {result.get('request_count')!r}")
        if name in {"set-item-recovery", "remove-item-recovery", "lost-response"}:
            keys = result.get("idempotency_keys", [])
            if not keys or len(set(keys)) != 1 or not keys[0]:
                failures.append(f"{case_key}: retry did not reuse a single non-empty idempotency key")
        if name == "set-item-recovery" and result.get("candidate_id") != (result.get("idempotency_keys") or [None])[0]:
            failures.append(f"{case_key}: recovered storage did not persist the original in-memory request ID")
        if name == "lost-response" and result.get("upstream_status") != 201:
            failures.append(f"{case_key}: intercepted request did not complete successfully at the API before response loss")

        if operation == "receive":
            receipt_count = GoodsReceipt.objects.filter(purchase_item_id=row["purchase_item_id"]).count()
            movement_count = InventoryMovement.objects.filter(source_type="receipt", source_no=row["purchase_no"], is_automatic=True).count()
            actual = receipt_count == 1 and movement_count == 1
            expected = should_create_record
            verification["cases"].append({
                "case_key": case_key,
                "purchase_id": row["purchase_id"],
                "purchase_item_id": row["purchase_item_id"],
                "goods_receipt_count": receipt_count,
                "automatic_receipt_movement_count": movement_count,
                "expected_business_record": expected,
                "pass": actual == expected,
            })
        else:
            shipment_count = Shipment.objects.filter(order_id=row["order_id"], status="confirmed", reversed_at__isnull=True).count()
            shipment_item_count = ShipmentItem.objects.filter(shipment__order_id=row["order_id"], shipment__status="confirmed", shipment__reversed_at__isnull=True).count()
            movement_count = InventoryMovement.objects.filter(order_id=row["order_id"], source_type="shipment", is_automatic=True).count()
            actual = shipment_count == 1 and shipment_item_count == 1 and movement_count == 1
            expected = should_create_record
            verification["cases"].append({
                "case_key": case_key,
                "order_id": row["order_id"],
                "order_item_id": row["order_item_id"],
                "confirmed_shipment_count": shipment_count,
                "shipment_item_count": shipment_item_count,
                "automatic_shipment_movement_count": movement_count,
                "expected_business_record": expected,
                "pass": actual == expected,
            })
        if actual != expected:
            failures.append(f"{case_key}: isolated database record counts do not match expected {expected}")

verification["pass"] = not failures and all(row["pass"] for row in verification["cases"])
verification["failures"] = failures
(evidence_dir / "database-verification.json").write_text(json.dumps(verification, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"database_verification": str(evidence_dir / "database-verification.json"), "pass": verification["pass"], "case_count": len(verification["cases"]), "failures": failures}, ensure_ascii=False))
if failures:
    raise SystemExit(1)
