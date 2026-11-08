"""Synthetic ISS-018 drill fixture; invoked only on the owned source database."""

import json
import hashlib
import os
import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.utils import timezone
from rest_framework.test import APIClient

from crm.models import (CSVImportBatch, CSVImportRowAudit, Customer, FollowUp, FollowUpAttachment,
                        FinanceVoucher, OperationLog, Order, Product, PurchaseOrder, Quote, SKU, Supplier)
from crm.services.finance import record_transaction
from crm.services.order_lifecycle import confirm_order
from crm.services.purchase_lifecycle import place_purchase_order


def _assert_synthetic_database():
    name = connection.settings_dict["NAME"]
    if settings.APP_STAGE != "development" or not name.startswith(("iss018_src_", "iss018_dst_")):
        raise RuntimeError("ISS-018 fixture requires an isolated synthetic database")
    if connection.settings_dict["HOST"] != "127.0.0.1" or str(connection.settings_dict["PORT"]) == "5432":
        raise RuntimeError("ISS-018 fixture requires the dedicated local cluster")
    root = Path(os.environ["ISS018_DRILL_ROOT"]).resolve(strict=True)
    if root.parent != Path(tempfile.gettempdir()).resolve() or not root.name.startswith("sunjack-iss018-pg17-"):
        raise RuntimeError("ISS-018 fixture requires a task-owned temporary root")
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('data_directory')")
        if Path(cursor.fetchone()[0]).resolve() != root / "cluster-host":
            raise RuntimeError("ISS-018 fixture connected to the wrong cluster")
    if Path(settings.MEDIA_ROOT).resolve().parent != root:
        raise RuntimeError("ISS-018 media root must belong to the temporary drill")


def seed():
    _assert_synthetic_database()
    users = get_user_model()
    owner = users.objects.create_superuser(username="iss018-drill-owner", email="iss018@example.invalid", password=None)
    users.objects.create_user(username="iss018-drill-denied", password=None)
    client = APIClient()
    client.force_authenticate(owner)

    content = b"code,name\nISS018-CSV,Imported synthetic customer\n"
    preview = client.post("/api/import/csv/preview/", {
        "entity": "customers", "file": SimpleUploadedFile("fixture.csv", content, content_type="text/csv"),
    }, format="multipart")
    if preview.status_code != 200 or preview.data.get("errors"):
        raise RuntimeError(f"Synthetic CSV preview failed: {preview.status_code}")
    imported = client.post("/api/import/csv/execute/", {
        "entity": "customers", "preview_token": preview.data["preview_token"],
        "file": SimpleUploadedFile("fixture.csv", content, content_type="text/csv"),
    }, format="multipart")
    if imported.status_code != 200:
        raise RuntimeError(f"Synthetic CSV import failed: {imported.status_code}")
    batch = CSVImportBatch.objects.get(batch_id=imported.data["import_batch_id"])
    if batch.operator_id != owner.pk or not CSVImportRowAudit.objects.filter(batch=batch, result="created").exists():
        raise RuntimeError("Synthetic CSV audit association is missing")

    day = date(2026, 11, 3)
    customer = Customer.objects.create(code="ISS018-C", name="Synthetic buyer", country="Germany", address="Original buyer address")
    supplier = Supplier.objects.create(code="D8", name="Synthetic supplier", address="Original supplier address")
    product = Product.objects.create(code="ISS018-P", name="Synthetic product")
    sku = SKU.objects.create(product=product, sku="ISS018-SKU", unit="pcs")
    quote = Quote.objects.create(quote_no="SJ20261103DE901", customer=customer, quote_date=day,
                                 buyer_company_name="Snapshot buyer", buyer_address="Snapshot address",
                                 currency="USD", exchange_rate=7, deposit_ratio=1)
    image = b"GIF87a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
    quote_item = quote.items.create(sku=sku, quantity=2, unit_price=10,
                                    image_snapshot=SimpleUploadedFile("history.gif", image, content_type="image/gif"))
    order = Order.objects.create(order_no="ISS018-SO", customer=customer, quote=quote, order_date=day,
                                 currency="USD", exchange_rate=7)
    order.items.create(sku=sku, quantity=2, unit_price=10)
    order = confirm_order(order)
    purchase = PurchaseOrder.objects.create(purchase_no="ISS018-PO", supplier=supplier, order=order,
                                            order_date=day, currency="USD", exchange_rate=7)
    purchase_item = purchase.items.create(sku=sku, quantity=2, unit_price=4)
    purchase = place_purchase_order(purchase, operator=owner)
    received = client.post(f"/api/purchase-orders/{purchase.pk}/receive/", {
        "purchase_item": purchase_item.pk, "receipt_date": day.isoformat(), "quantity": "2", "unit_cost": "4",
    }, format="json", HTTP_IDEMPOTENCY_KEY="iss018-drill-receipt")
    if received.status_code != 201:
        raise RuntimeError(f"Synthetic receipt failed: {received.status_code} {received.data}")
    plan = order.payment_plans.order_by("id").first()
    if not plan:
        raise RuntimeError("Order confirmation did not create a payment plan")
    receipt = record_transaction({"transaction_no": "ISS018-TX", "transaction_date": day, "plan": plan,
                                  "amount": Decimal("5"), "currency": "USD", "exchange_rate": Decimal("7"),
                                  "category": "Synthetic receipt"})
    voucher_bytes = b"%PDF-1.4\nSynthetic bank voucher\n%%EOF"
    voucher = FinanceVoucher.objects.create(
        file=SimpleUploadedFile("synthetic-bank-voucher.pdf", voucher_bytes, content_type="application/pdf"),
        original_name="synthetic-bank-voucher.pdf", sha256=hashlib.sha256(voucher_bytes).hexdigest(),
        size=len(voucher_bytes), actor={"kind": "synthetic_fixture"}, scope="bank", bank_sources=[receipt.pk],
    )
    followup = FollowUp.objects.create(customer=customer, followed_at=timezone.now(), subject="Synthetic follow-up")
    attachment_bytes = b"synthetic private file\n"
    attachment = FollowUpAttachment.objects.create(
        follow_up=followup, name="synthetic.txt", content_type="text/plain", size=len(attachment_bytes),
        file=SimpleUploadedFile("synthetic.txt", attachment_bytes, content_type="text/plain"),
    )
    if not OperationLog.objects.filter(operator=owner).exists():
        raise RuntimeError("Authenticated operation audit was not persisted")
    print(json.dumps({"attachment": attachment.file.name, "image": quote_item.image_snapshot.name,
                      "voucher": voucher.file.name, "voucher_sha256": voucher.sha256,
                      "owner": owner.pk, "customer": customer.pk, "order": order.pk,
                      "purchase": purchase.pk, "quote": quote.pk, "sku": sku.pk}, sort_keys=True))


def sessions():
    """Return synthetic session keys only to the parent process, never to logs."""
    _assert_synthetic_database()
    values = {}
    for username in ("iss018-drill-owner", "iss018-drill-denied"):
        user = get_user_model().objects.get(username=username)
        session = SessionStore()
        session["_auth_user_id"] = str(user.pk)
        session["_auth_user_backend"] = "django.contrib.auth.backends.ModelBackend"
        session["_auth_user_hash"] = user.get_session_auth_hash()
        session.save()
        values[username] = session.session_key
    print(json.dumps(values))
