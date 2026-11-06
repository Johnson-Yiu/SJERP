"""Candidate-only preflight and restore probes on a disposable PostgreSQL source."""
import csv
import hashlib
import io
import json
from pathlib import Path
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from crm.history_import_preflight import DOMAIN_VIEW_PERMISSIONS
from crm.models import AccessRole, EmployeeProfile, FollowUp, FollowUpAttachment, OrganizationUnit, Position, RolePermission
from crm.services.private_media import build_private_media_manifest
from crm.tests.iss018_drill_fixture import _assert_synthetic_database
from crm.tests.test_history_import_preflight import HistoryImportPreflightTests

ENDPOINT = "/api/import/history-preflight/"
HOST = "https://testserver"
FILE = b"synthetic private attachment\n"
ADMIN = "upload-readiness-named-operator"
DENIED = "upload-readiness-denied"


def snapshot():
    """Fingerprint every business table, including rows that could be updated in place."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
        names = [name for (name,) in cursor.fetchall() if name != "django_session"]
        state = {}
        for name in names:
            table = connection.ops.quote_name(name)
            cursor.execute(f"SELECT row_to_json(t)::text FROM {table} t ORDER BY 1")
            state[name] = cursor.fetchall()
    return hashlib.sha256(json.dumps(state, ensure_ascii=False).encode()).hexdigest(), len(names)


def login(username, password):
    client = Client(enforce_csrf_checks=True)
    assert client.get("/api/session/csrf/", secure=True).status_code == 200
    token = client.cookies["csrftoken"].value
    credentials = {"username": username, "password": password}
    assert client.post("/api/session/login/", credentials, content_type="application/json",
                       secure=True, HTTP_REFERER=HOST).status_code == 403
    response = client.post("/api/session/login/", credentials, content_type="application/json",
                           secure=True, HTTP_REFERER=HOST, HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 200, response.status_code
    assert str(client.session["_auth_user_id"]) == str(get_user_model().objects.get(username=username).pk)
    assert client.cookies["csrftoken"].value != token
    return client


def upload(client, workbook, *, report=False, csrf=True):
    headers = {"HTTP_REFERER": HOST}
    if csrf:
        headers["HTTP_X_CSRFTOKEN"] = client.cookies["csrftoken"].value
    return client.post(ENDPOINT + ("?report=csv" if report else ""), {
        "file": SimpleUploadedFile("synthetic-history.xlsx", workbook),
    }, secure=True, **headers)


def check_media(client, denied, attachment):
    protected = reverse("crm-protected-media", kwargs={"relative_path": attachment.file.name})
    response = client.get(protected, secure=True)
    assert response.status_code == 200, response.status_code
    assert response["Cache-Control"] == "private, no-store"
    try:
        assert b"".join(response.streaming_content) == FILE
    finally:
        response.close()
    assert Client().get(protected, secure=True).status_code in (403, 404)
    assert denied.get(protected, secure=True).status_code in (403, 404)
    assert client.get("/media/" + quote(attachment.file.name), secure=True).status_code in (403, 404)


def seed(password, output):
    _assert_synthetic_database()
    assert not settings.DEVELOPMENT_SUPERADMIN and settings.RBAC_ENFORCEMENT
    assert settings.AUDIT_LOG_ENABLED and not settings.DEBUG
    users = get_user_model()
    operator = users.objects.create_user(username=ADMIN, first_name="Synthetic named operator", password=password)
    users.objects.create_user(username=DENIED, password=password)
    unit = OrganizationUnit.objects.create(name="Synthetic import", code="SYN-UPLOAD")
    position = Position.objects.create(unit=unit, name="Operator", code="SYN-UPLOAD")
    role = AccessRole.objects.create(name="Synthetic preflight", code="synthetic-preflight", default_data_scope="all")
    employee = EmployeeProfile.objects.create(user=operator, display_name=operator.first_name, unit=unit, position=position)
    employee.roles.add(role)
    for module in (*DOMAIN_VIEW_PERMISSIONS, "followups"):
        RolePermission.objects.create(role=role, module=module, can_view=True)
    RolePermission.objects.create(role=role, module="imports", can_import=True)
    fixture = HistoryImportPreflightTests()
    customer, _, sku = fixture.create_masters()
    followup = FollowUp.objects.create(customer=customer, followed_at=timezone.now(), subject="Synthetic private fixture")
    attachment = FollowUpAttachment.objects.create(
        follow_up=followup, name="synthetic.txt", content_type="text/plain", size=len(FILE),
        file=SimpleUploadedFile("synthetic.txt", FILE),
    )
    clean_workbook = fixture.basic_sales_workbook(customer, sku)
    workbook = fixture.basic_sales_workbook(customer, sku, rows_extra={
        "销售订单": [fixture.sales_order_row(customer)],
    })
    client, denied = login(ADMIN, password), login(DENIED, password)
    check_media(client, denied, attachment)
    before = snapshot()
    media = build_private_media_manifest(settings.MEDIA_ROOT)
    assert upload(Client(), workbook, csrf=False).status_code == 403
    assert upload(denied, workbook).status_code == 403
    assert upload(client, workbook, csrf=False).status_code == 403
    clean = upload(client, clean_workbook)
    assert clean.status_code == 200
    clean_payload = clean.json()
    assert clean_payload["summary"]["blocked"] == 0
    assert clean_payload["preflight_only"] and not clean_payload["business_write_performed"]
    first, second = upload(client, workbook), upload(client, workbook)
    assert first.status_code == second.status_code == 200, (first.status_code, second.status_code)
    payload = first.json()
    assert payload["results"] == second.json()["results"]
    assert payload["preflight_only"] and not payload["business_write_performed"]
    sales = [row for row in payload["results"] if row["sheet"] == "销售订单"]
    assert len(sales) == 2 and all(row["status"] == "阻断" for row in sales)
    assert any("重复" in reason["message"] for row in sales for reason in row["reasons"])
    report = upload(client, workbook, report=True)
    assert report.status_code == 200
    assert report["Content-Disposition"] == 'attachment; filename="history-preflight.csv"'
    rows = list(csv.reader(io.StringIO(report.content.decode("utf-8-sig"))))
    assert len(rows) == 1 + len(payload["results"]) and len({row[1] for row in rows[1:] if row[0] == "销售订单"}) == 2
    assert any("重复" in row[5] for row in rows[1:] if row[0] == "销售订单")
    assert snapshot() == before
    assert build_private_media_manifest(settings.MEDIA_ROOT) == media
    output = Path(output)
    output.joinpath("synthetic.xlsx").write_bytes(clean_workbook)
    output.joinpath("synthetic-duplicates.xlsx").write_bytes(workbook)
    output.joinpath("history-preflight.csv").write_bytes(report.content)
    print(json.dumps({
        "attachment": attachment.file.name, "image": attachment.file.name,
        "sessions": [client.cookies["sessionid"].value, denied.cookies["sessionid"].value],
        "checks": {
            "password_login_csrf_and_session": "PASS", "operator_is_superuser": operator.is_superuser,
            "authorized_and_denied_private_file": "PASS",
            "anonymous_unauthorized_and_missing_csrf_upload": "PASS",
            "clean_summary": clean_payload["summary"], "duplicate_summary": payload["summary"],
            "repeat_results_equal": True, "duplicate_rows": len(sales),
            "download_rows": len(rows) - 1, "download_sha256": hashlib.sha256(report.content).hexdigest(),
            "database_snapshot_equal": True, "fingerprinted_tables": before[1], "media_manifest_equal": True,
        }
    }, ensure_ascii=False))


def verify_restore(sessions):
    _assert_synthetic_database()
    client, denied = Client(), Client()
    for browser, session in zip((client, denied), sessions, strict=True):
        browser.cookies["sessionid"] = session
    check_media(client, denied, FollowUpAttachment.objects.get(name="synthetic.txt"))
    print("RESTORED_PRIVATE_FILE_AUTHORIZATION=PASS")
