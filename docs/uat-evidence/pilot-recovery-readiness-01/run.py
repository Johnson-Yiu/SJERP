"""Extend the owned ISS-018 fixture with a payment and restored HTTP readback."""

import hashlib
import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


backend = Path(__file__).resolve().parents[3] / "backend"
sys.path.insert(0, str(backend))
# The existing module validates development settings before Django is initialized.
from isolated_postgres_drill import IsolatedPostgresDrill, main


ADD_PAYMENT = """
from crm.tests.iss018_drill_fixture import _assert_synthetic_database
from crm.models import PurchaseOrder
from crm.services.finance import record_transaction

_assert_synthetic_database()
purchase = PurchaseOrder.objects.get(purchase_no="ISS018-PO")
record_transaction({
    "transaction_no": "PILOT-B-OUT",
    "transaction_date": purchase.order_date,
    "plan": purchase.payment_plans.first(),
    "direction": "expense",
    "amount": 3,
    "currency": "USD",
    "exchange_rate": 7,
    "category": "Synthetic payment",
})
"""


READBACK = """
import json
from crm.models import Customer, InventoryMovement, Order, SKU, Transaction
from crm.tests.iss018_drill_fixture import _assert_synthetic_database

_assert_synthetic_database()
def readback():
    order = Order.objects.get(order_no="ISS018-SO")
    sku = SKU.objects.get(sku="ISS018-SKU")
    movements = InventoryMovement.objects.filter(sku=sku)
    return {
        "customers": Customer.objects.count(),
        "orders": Order.objects.count(),
        "stock_movements": movements.count(),
        "stock_quantity": str(sum(row.signed_quantity for row in movements)),
        "order": [order.currency, str(order.total_amount)],
        "transactions": [
            [row.direction, row.currency, str(row.amount)]
            for row in Transaction.objects.order_by("direction")
        ],
    }
"""


def restored_http(drill, restored, fixture, paths):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    process = subprocess.Popen(
        [sys.executable, str(backend / "manage.py"), "runserver", f"127.0.0.1:{port}", "--noreload"],
        cwd=backend, env=drill._environment(restored["database"], restored["media"]),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    def read(path):
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}{path}",
            headers={"Cookie": "sessionid=" + drill.pilot_session_key},
        )
        with urllib.request.urlopen(request, timeout=3) as response:
            return response.status, response.read()

    try:
        for _ in range(100):
            if process.poll() is not None:
                raise RuntimeError("Restored loopback application exited before HTTP readback")
            try:
                status, body = read(f"/api/orders/{fixture['order']}/")
                break
            except urllib.error.HTTPError:
                raise
            except urllib.error.URLError:
                time.sleep(0.1)
        else:
            raise RuntimeError("Restored loopback application did not start")
        if status != 200 or json.loads(body)["order_no"] != "ISS018-SO":
            raise RuntimeError("Restored order could not be identified")
        return status, {
            path: hashlib.sha256(read("/api/media/" + path)[1]).hexdigest() for path in paths
        }
    finally:
        process.terminate()
        process.wait(timeout=10)


def run():
    original_restore = IsolatedPostgresDrill.restore
    source_manage = IsolatedPostgresDrill._manage

    def seed_and_snapshot(drill, *args):
        output = source_manage(drill, *args)
        if args[-1] == "from crm.tests.iss018_drill_fixture import seed; seed()":
            source_manage(drill, "shell", "--no-imports", "-c", ADD_PAYMENT)
            sessions = json.loads(source_manage(
                drill, "shell", "--no-imports", "-c",
                "from crm.tests.iss018_drill_fixture import sessions; sessions()",
            ))
            drill.pilot_session_key = sessions["iss018-drill-owner"]
            fixture = json.loads(output)
            drill.pilot_fixture = fixture
            drill.pilot_before = json.loads(source_manage(
                drill, "shell", "--no-imports", "-c", READBACK + "\nprint(json.dumps(readback()))"
            ))
        return output

    def restore_and_read(drill, **kwargs):
        restored = original_restore(drill, **kwargs)
        fixture = drill.pilot_fixture
        paths = (fixture["attachment"], fixture["image"])
        expected = {path: hashlib.sha256((drill.media / path).read_bytes()).hexdigest() for path in paths}
        business = json.loads(drill._manage_database(
            restored["database"], restored["media"], "shell", "--no-imports", "-c",
            READBACK + "\nprint(json.dumps(readback()))",
        ))
        status, downloads = restored_http(drill, restored, fixture, paths)
        if business != drill.pilot_before or downloads != expected:
            raise RuntimeError("Restored business values or HTTP attachment SHA256 differ")
        if {tuple(row) for row in business["transactions"]} != {
            ("expense", "USD", "3.0000"), ("income", "USD", "5.0000")
        }:
            raise RuntimeError("Expected synthetic receipt and payment were not restored")
        result = {"business": business, "order_http": status, "downloads": downloads}
        print(json.dumps({"pilot_readback": result}, sort_keys=True))
        return restored

    IsolatedPostgresDrill._manage = seed_and_snapshot
    IsolatedPostgresDrill.restore = restore_and_read
    return main()


if __name__ == "__main__":
    sys.exit(run())
