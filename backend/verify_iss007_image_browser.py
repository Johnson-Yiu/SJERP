"""Verify ISS-007 isolated database/media snapshots and exported workbook."""

import argparse
import hashlib
import io
import json
import os
import zipfile
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.serializers.json import DjangoJSONEncoder
from openpyxl import load_workbook

from crm.models import Customer, Order, OrderItem, Product, Quote, QuoteItem, SKU
from test_support.isolated_runtime import verify_isolated_runtime


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def field_sha256(field):
    if not field:
        return None
    with field.open("rb") as stream:
        return sha256_bytes(stream.read())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["before", "after"], required=True)
    parser.add_argument("--workbook")
    args = parser.parse_args()

    identity = verify_isolated_runtime(settings=settings, database_must_exist=True)
    evidence_dir = Path(os.environ["ISS007_EVIDENCE_DIR"])
    fixture = json.loads((evidence_dir / "fixture.json").read_text(encoding="utf-8"))
    if not fixture.get("synthetic_only"):
        raise SystemExit("Refusing to inspect a non-synthetic ISS-007 fixture.")

    customer = Customer.objects.get(pk=fixture["customer_id"])
    product = Product.objects.get(pk=fixture["product_id"])
    sku = SKU.objects.get(pk=fixture["sku_id"])
    quote = Quote.objects.get(pk=fixture["quote_id"])
    quote_item = QuoteItem.objects.get(pk=fixture["quote_item_id"], quote=quote)
    order = Order.objects.get(pk=fixture["order_id"])
    order_item = OrderItem.objects.get(pk=fixture["order_item_id"], order=order)
    order_quote_item = order.quote.items.order_by("id").first()
    missing_item = QuoteItem.objects.get(pk=fixture["missing_quote_item_id"])

    sku_digest = field_sha256(sku.image)
    quote_digest = field_sha256(quote_item.image_snapshot)
    order_quote_digest = field_sha256(order_quote_item.image_snapshot) if order_quote_item else None
    expected_sku = fixture["original_image_sha256"] if args.stage == "before" else fixture["replacement_image_sha256"]
    if sku_digest != expected_sku:
        raise SystemExit(f"SKU image hash mismatch at {args.stage}: {sku_digest}")
    if quote_digest != fixture["original_image_sha256"]:
        raise SystemExit("Formal quote image snapshot changed or is missing.")
    if order.status != "confirmed" or not order.quote_id or order_quote_digest != fixture["original_image_sha256"]:
        raise SystemExit("Confirmed order does not retain its accepted quote's image snapshot.")
    if order_item.sku_code_snapshot != sku.sku:
        raise SystemExit("Confirmed order SKU identity snapshot changed.")
    if missing_item.image_snapshot.name != fixture["missing_image_path"] or default_storage.exists(missing_item.image_snapshot.name):
        raise SystemExit("Missing historical image fixture is unexpectedly present or changed.")

    state = {
        "stage": args.stage,
        "isolated_database": identity["database"],
        "isolated_media_root": identity["mediaRoot"],
        "synthetic_records_only": True,
        "row_counts": {
            "customers": Customer.objects.count(),
            "products": Product.objects.count(),
            "skus": SKU.objects.count(),
            "quotes": Quote.objects.count(),
            "quote_items": QuoteItem.objects.count(),
            "orders": Order.objects.count(),
            "order_items": OrderItem.objects.count(),
        },
        "customer_id": customer.pk,
        "product_id": product.pk,
        "sku": {"id": sku.pk, "code": sku.sku, "image_path": sku.image.name, "sha256": sku_digest},
        "formal_quote": {
            "id": quote.pk, "number": quote.quote_no, "status": quote.status,
            "item_id": quote_item.pk, "image_snapshot_path": quote_item.image_snapshot.name,
            "image_snapshot_sha256": quote_digest,
        },
        "confirmed_order": {
            "id": order.pk, "number": order.order_no, "status": order.status,
            "quote_id": order.quote_id, "item_id": order_item.pk,
            "item_sku_code_snapshot": order_item.sku_code_snapshot,
            "order_item_has_own_image_snapshot_field": hasattr(order_item, "image_snapshot"),
            "linked_quote_image_snapshot_path": order_quote_item.image_snapshot.name if order_quote_item else None,
            "linked_quote_image_snapshot_sha256": order_quote_digest,
        },
        "missing_history": {
            "quote_item_id": missing_item.pk,
            "referenced_path": missing_item.image_snapshot.name,
            "file_exists": default_storage.exists(missing_item.image_snapshot.name),
        },
        "hash_checks": {
            "sku_matches_expected_stage": True,
            "formal_quote_matches_original": True,
            "confirmed_order_quote_matches_original": True,
        },
    }

    if args.workbook:
        workbook_path = Path(args.workbook)
        content = workbook_path.read_bytes()
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            media = {
                name: sha256_bytes(archive.read(name))
                for name in archive.namelist()
                if name.startswith("xl/media/")
            }
        if not media or fixture["original_image_sha256"] not in media.values():
            raise SystemExit("Exported quote/PI workbook does not embed the original saved image snapshot.")
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=False)
        if not workbook.sheetnames:
            raise SystemExit("Exported quote/PI workbook has no worksheet.")
        workbook.close()
        state["export"] = {
            "path": str(workbook_path),
            "bytes": len(content),
            "worksheet_names": workbook.sheetnames,
            "embedded_media_sha256": media,
            "original_snapshot_embedded": True,
        }

    state_path = evidence_dir / f"database-{args.stage}.json"
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2, cls=DjangoJSONEncoder), encoding="utf-8")
    print(json.dumps(state, ensure_ascii=False, indent=2, cls=DjangoJSONEncoder))


if __name__ == "__main__":
    main()
