"""Create quote-editor UI fixtures in the isolated Playwright SQLite database."""

import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
database_url = os.environ.get("DATABASE_URL", "").strip()
if not database_url.startswith("sqlite:///") or not os.environ.get("ISOLATED_TEST_RUN_ID"):
    raise RuntimeError("Quote action evidence requires the isolated Playwright SQLite runner")

sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_support.isolated_settings")
import django

django.setup()

from crm.models import Customer, Product, SKU
from django.conf import settings
from test_support.isolated_runtime import verify_isolated_runtime

verify_isolated_runtime(settings=settings, database_must_exist=True)

customer = Customer.objects.create(
    code="R1-UX-QA-CUSTOMER",
    name="报价操作验收客户",
    country="Germany",
    address="Synthetic Test Address",
)
product = Product.objects.create(code="R1-UX-QA-PRODUCT", name="报价操作验收灯具")
sku = SKU.objects.create(
    sku="R1-UX-QA-SKU",
    product=product,
    sales_model="R1-QA-MODEL",
    unit="pcs",
    default_price="12.50",
)

evidence = Path(os.environ["R1_UX_QUOTE_ACTIONS_EVIDENCE_DIR"]).resolve()
evidence.mkdir(parents=True, exist_ok=True)
(evidence / "fixture.json").write_text(
    json.dumps(
        {
            "customer": customer.pk,
            "sku": sku.pk,
            "database": str(settings.DATABASES["default"]["NAME"]),
            "media_root": str(settings.MEDIA_ROOT),
            "run_id": os.environ["ISOLATED_TEST_RUN_ID"],
            "synthetic_only": True,
        },
        indent=2,
    ),
    encoding="utf-8",
)
print(json.dumps({"customer": customer.pk, "sku": sku.pk, "synthetic_only": True}))
