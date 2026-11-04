"""Seed marked synthetic history UAT through isolated runtime, APIs and services."""

from __future__ import annotations

import json
import os
import argparse
from pathlib import Path

import django

django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpRequest
from django.middleware.csrf import get_token
from django.test import Client
from rest_framework.test import APIClient

from test_support.isolated_runtime import verify_isolated_runtime
from crm.models import Customer, Product, ProductCategory, SKU, Supplier
from crm.services import finance_closeout
from crm.tests.test_history_takeover import HistoryTakeoverFixtureMixin


ROOT = Path(os.environ["ISOLATED_TEST_ROOT"]).resolve(strict=True)
RUN_ID = os.environ["ISOLATED_TEST_RUN_ID"]
DEFAULT_SESSION_DIR = ROOT / f"sunjack-history-operational-closeout-447d-{RUN_ID}"
SESSION_DIR = Path(os.environ.get("ISOLATED_HISTORY_SESSION_DIR", str(DEFAULT_SESSION_DIR))).resolve()
if SESSION_DIR.parent != ROOT or not SESSION_DIR.name.startswith("sunjack-history-operational-closeout-"):
    raise RuntimeError("Synthetic browser session directory must be a marked direct child of the isolated temp root.")


def require_status(response, expected: int, label: str):
    if response.status_code != expected:
        payload = getattr(response, "data", None)
        raise RuntimeError(f"{label} returned HTTP {response.status_code}; body={payload!r}")
    return response.data


def session_file(user, filename: str) -> None:
    request = HttpRequest()
    csrf = get_token(request)
    client = Client()
    client.force_login(user)
    cookie = client.cookies.get(settings.SESSION_COOKIE_NAME)
    if cookie is None or not cookie.value:
        raise RuntimeError(f"Django did not create the session for {filename}.")
    if SESSION_DIR.is_symlink():
        raise RuntimeError("Refusing a linked synthetic browser session directory.")
    if not SESSION_DIR.exists():
        SESSION_DIR.mkdir(mode=0o700, parents=False, exist_ok=False)
    elif not SESSION_DIR.is_dir():
        raise RuntimeError("Synthetic browser session path is not a directory.")
    target = SESSION_DIR / filename
    with target.open("x", encoding="utf-8") as session_output:
        session_output.write(json.dumps({"sessionid": cookie.value, "csrftoken": csrf}))
    try:
        target.chmod(0o600)
    except OSError:
        # The session directory is under this run's user-owned system TEMP root.
        pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--migrate-only", action="store_true")
    args = parser.parse_args()
    identity = verify_isolated_runtime(settings=settings, database_must_exist=not args.migrate_only)
    if identity["database"] != str((ROOT / "db.sqlite3").resolve()):
        raise RuntimeError("Isolation helper returned an unexpected database path.")
    if settings.DATABASES["default"]["ENGINE"] != "django.db.backends.sqlite3":
        raise RuntimeError("Refusing to seed a non-SQLite database.")
    if not settings.DEVELOPMENT_SUPERADMIN or settings.RBAC_ENFORCEMENT:
        raise RuntimeError("Expected the explicitly enabled isolated development access mode.")
    if not settings.AUDIT_LOG_ENABLED:
        raise RuntimeError("Audit logging must be enabled for this synthetic acceptance run.")

    if args.migrate_only:
        from django.core.management import call_command

        call_command("migrate", interactive=False, verbosity=0)
        verify_isolated_runtime(settings=settings, database_must_exist=True)
        print(json.dumps({"migration": "completed", "database_path": identity["database"],
                          "database_engine": settings.DATABASES["default"]["ENGINE"]}, sort_keys=True))
        return

    if SESSION_DIR.exists() or SESSION_DIR.is_symlink():
        raise RuntimeError("Refusing to reuse an existing synthetic browser session directory.")

    User = get_user_model()
    maker = User.objects.create_user(
        username="synthetic-history-uploader",
        email="synthetic-history-uploader@example.test",
        password=os.environ["SYNTHETIC_TEST_PASSWORD"],
    )
    reviewer = User.objects.create_user(
        username="synthetic-history-reviewer",
        email="synthetic-history-reviewer@example.test",
        password=os.environ["SYNTHETIC_TEST_PASSWORD"],
    )
    if maker.is_superuser or reviewer.is_superuser:
        raise RuntimeError("Synthetic session actors must not be real or superuser accounts.")
    session_file(maker, "session.json")
    session_file(reviewer, "reviewer-session.json")

    # The live isolated API identity accepted 127.0.0.1; keep APIClient on the
    # same host instead of Django's default testserver, which may be excluded
    # by an inherited host allowlist.
    api = APIClient(HTTP_HOST="127.0.0.1")
    api.force_authenticate(user=maker)
    category = require_status(
        api.post("/api/categories/", {"name": "Synthetic Browser UAT Category"}, format="json"),
        201,
        "Create synthetic category through API",
    )
    customer = require_status(
        api.post(
            "/api/customers/",
            {
                "name": "Synthetic Browser UAT Customer",
                "country": "US",
                "contacts": [{"name": "Synthetic Buyer", "email": "synthetic-buyer@example.test", "is_primary": True}],
            },
            format="json",
        ),
        201,
        "Create synthetic customer and contact through API",
    )
    supplier = require_status(
        api.post(
            "/api/suppliers/",
            {"name": "Synthetic Browser UAT Supplier", "code": "ZU", "supply_categories": [category["id"]]},
            format="json",
        ),
        201,
        "Create synthetic supplier through API",
    )
    product = require_status(
        api.post(
            "/api/products/",
            {
                "name": "Synthetic Browser UAT Product",
                "sales_model_prefix": "UT447D",
                "category": category["id"],
                "status": "active",
            },
            format="json",
        ),
        201,
        "Create synthetic product through API",
    )
    sku_rows = require_status(
        api.post(
            "/api/skus/batch-create/",
            {"items": [{"product": product["id"], "display_name_cn": "Synthetic Browser UAT SKU", "unit": "pcs"}]},
            format="json",
        ),
        201,
        "Create generated SKU through API",
    )
    if len(sku_rows) != 1 or not sku_rows[0].get("sku"):
        raise RuntimeError(f"SKU API did not return one generated SKU: {sku_rows!r}")

    fixture = object.__new__(HistoryTakeoverFixtureMixin)
    fixture.customer = Customer.objects.get(pk=customer["id"])
    fixture.supplier = Supplier.objects.get(pk=supplier["id"])
    fixture.sku = SKU.objects.get(pk=sku_rows[0]["id"])
    rows = fixture.source_rows(group_id="HT-UAT-447D-1", source_system="Synthetic browser UAT")
    content = fixture.workbook_bytes(rows)
    response = api.post(
        "/api/import/history-takeovers/",
        {
            "file": SimpleUploadedFile(
                "synthetic-history-uAT.xlsx",
                content,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        format="multipart",
    )
    application = require_status(response, 201, "Submit synthetic workbook through formal API")
    if application.get("source_file_name") != "synthetic-history-uAT.xlsx":
        raise RuntimeError("Formal history API did not retain the expected synthetic workbook filename.")
    if not application.get("preflight_only") or application.get("approval_or_migration") is not False:
        raise RuntimeError("History submission did not remain at preflight-only state before browser review.")
    if len(application.get("groups", [])) != 1 or application["groups"][0].get("source_system") != "Synthetic browser UAT":
        raise RuntimeError("Formal history API did not create the single marked source group.")

    account = finance_closeout.create_account(
        {
            "code": "UAT-HISTORY-CNY",
            "name": "合成验收账户",
            "account_type": "bank",
            "ownership": "own",
            "ownership_reason": "隔离 SQLite 浏览器验收合成账户",
        },
        maker,
    )
    voucher_bytes = b"%PDF-1.4\nSynthetic isolated browser UAT voucher.\n%%EOF\n"
    voucher = finance_closeout.upload(
        SimpleUploadedFile("synthetic-uat.pdf", voucher_bytes, content_type="application/pdf"),
        maker,
    )
    if voucher.original_name != "synthetic-uat.pdf":
        raise RuntimeError("Finance service did not retain the synthetic voucher name.")

    summary = {
        "database_engine": settings.DATABASES["default"]["ENGINE"],
        "database_path": identity["database"],
        "media_root": identity["mediaRoot"],
        "audit_log_enabled": settings.AUDIT_LOG_ENABLED,
        "rbac_enforcement": settings.RBAC_ENFORCEMENT,
        "development_superadmin_enabled": settings.DEVELOPMENT_SUPERADMIN,
        "synthetic_session_actors": [maker.get_username(), reviewer.get_username()],
        "actors_are_superusers": [maker.is_superuser, reviewer.is_superuser],
        "master_ids": {
            "category": category["id"],
            "customer": customer["id"],
            "supplier": supplier["id"],
            "product": product["id"],
            "sku": sku_rows[0]["id"],
        },
        "generated_sku": fixture.sku.sku,
        "history_application_id": application["id"],
        "history_group_id": application["groups"][0]["id"],
        "history_source_system": application["groups"][0]["source_system"],
        "history_source_file_name": application["source_file_name"],
        "history_submission_preflight_only": application["preflight_only"],
        "finance_account_id": account.pk,
        "finance_account_code": account.code,
        "finance_voucher_id": voucher.pk,
        "finance_voucher_name": voucher.original_name,
        "finance_voucher_sha256": voucher.sha256,
        "finance_voucher_size": voucher.size,
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
