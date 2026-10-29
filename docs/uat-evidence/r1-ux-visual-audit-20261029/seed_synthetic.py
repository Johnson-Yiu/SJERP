"""Seed disposable, clearly synthetic rows for the R1 visual audit only."""
import json
import os
import sys
from pathlib import Path

backend_root = Path(__file__).resolve().parents[3] / "backend"
if not backend_root.is_dir():
    raise SystemExit("Refusing to seed: expected repository backend directory is missing.")
sys.path.insert(0, str(backend_root))

import django
from django.conf import settings

django.setup()

from django.db import transaction
from test_support.isolated_runtime import verify_isolated_runtime

run_id = os.environ.get("ISOLATED_TEST_RUN_ID", "")
token = os.environ.get("ISOLATED_TEST_TOKEN", "")
root = Path(os.environ.get("ISOLATED_TEST_ROOT", "")).resolve()
database = Path(settings.DATABASES["default"]["NAME"]).resolve()
media_root = Path(settings.MEDIA_ROOT).resolve()
marker_path = root / ".sunjack-playwright-isolation.json"
if not run_id or not token or not root.is_dir() or not marker_path.is_file():
    raise SystemExit("Refusing to seed without this run's isolation identity and ownership marker.")
marker = json.loads(marker_path.read_text(encoding="utf-8"))
if marker.get("runId") != run_id or marker.get("token") != token or Path(marker.get("root", "")).resolve() != root:
    raise SystemExit("Refusing to seed: isolation ownership marker does not match this run.")
if database != (root / "db.sqlite3").resolve() or media_root != (root / "media").resolve():
    raise SystemExit("Refusing to seed: database or MEDIA_ROOT is outside this isolated run.")
verify_isolated_runtime(settings=settings, database_must_exist=True)

from crm.models import (
    Customer,
    InventoryMovement,
    Order,
    OrderItem,
    Shipment,
    ShipmentItem,
    ShipmentPackage,
    ShipmentPackageItem,
    SKU,
)

if Customer.objects.exists() or SKU.objects.exists() or Order.objects.exists():
    raise SystemExit("Refusing to seed: the isolated database is not empty.")

repo_root = Path(settings.BASE_DIR).parent
legacy_script = repo_root / "docs" / "uat-evidence" / "r0-f9" / "seed_isolated.py"
legacy_source = legacy_script.read_text(encoding="utf-8")
expected_guard = "(settings.BASE_DIR/'r0f9-ux.sqlite3').resolve()"
if expected_guard not in legacy_source:
    raise SystemExit("Refusing to seed: the reviewed synthetic fixture guard changed.")
adapted_source = legacy_source.replace(
    expected_guard,
    "(Path(settings.MEDIA_ROOT).parent/'db.sqlite3').resolve()",
).replace("'r0f7b-ux.sqlite3','r0f9-ux.sqlite3'", "'r0f7b-ux.sqlite3','db.sqlite3'").replace("R0F9", "R1UXA")
if adapted_source == legacy_source:
    raise SystemExit("Refusing to seed: the isolated fixture path was not adapted.")

with transaction.atomic():
    exec(compile(adapted_source, str(legacy_script), "exec"), globals())

    today = timezone.localdate()
    for index in range(3, 31):
        Customer.objects.create(
            name=f"R1UXA 分页合成客户 {index:02d} · 照明采购有限公司",
            code=f"R1UXA-C{index:03d}",
            status="customer" if index % 2 else "opportunity",
            country="中国" if index % 2 else "德国",
            owner="R1UXA 合成验收",
        )

    order = Order.objects.get(order_no="R1UXA-O001")
    sku = SKU.objects.get(sku="R1UXA-EXISTING")
    order_item = OrderItem.objects.get(order=order, sku=sku)
    shipment = Shipment.objects.create(
        shipment_no="R1UXA-S001",
        order=order,
        shipment_date=today,
        logistics_provider="合成物流",
        waybill_no="R1UXA-WB-001",
        status="confirmed",
        notes="仅供隔离界面视觉验收。",
    )
    ShipmentItem.objects.create(shipment=shipment, order_item=order_item, sku=sku, quantity=10)
    package = ShipmentPackage.objects.create(
        shipment=shipment,
        carton_no=1,
        length="50",
        width="40",
        height="30",
        actual_net_weight="8.000",
        actual_gross_weight="9.500",
        notes="R1UXA 合成实际箱单",
    )
    ShipmentPackageItem.objects.create(shipment_package=package, sku=sku, quantity=10)

print(
    "R1-UX visual audit synthetic seed ready: "
    f"customers={Customer.objects.count()}, products={Product.objects.count()}, "
    f"skus={SKU.objects.count()}, orders={Order.objects.count()}, shipments={Shipment.objects.count()}; "
    "isolated SQLite and MEDIA_ROOT verified."
)
