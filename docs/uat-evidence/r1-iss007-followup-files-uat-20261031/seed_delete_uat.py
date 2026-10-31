"""Seed disposable ISS-007 attachment-delete data in a guarded SQLite runtime."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import django

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.core.files.base import ContentFile  # noqa: E402

from crm.models import (  # noqa: E402
    AccessRole,
    Customer,
    EmployeeProfile,
    FollowUp,
    FollowUpAttachment,
    OrganizationUnit,
    Position,
    RolePermission,
)
from test_support.isolated_runtime import verify_isolated_runtime  # noqa: E402


SUBJECT = "ISS007附件流程核验 2026-10-31"
OPERATOR_DISPLAY_NAME = "ISS007合成测试操作员"
LEGACY_NAME = "ISS007-legacy-history.txt"
LEGACY_BYTES = b"Synthetic legacy attachment; preserve during delete UAT.\n"


def main() -> None:
    identity = verify_isolated_runtime(settings=settings, database_must_exist=True)
    if not settings.RBAC_ENFORCEMENT or settings.DEVELOPMENT_SUPERADMIN:
        raise RuntimeError("UAT requires isolated RBAC and a disabled development-superadmin identity.")
    if not settings.AUDIT_LOG_ENABLED:
        raise RuntimeError("UAT requires audit logging in the isolated runtime.")

    evidence_dir = Path(os.environ["ISS007_UAT_EVIDENCE_DIR"]).resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    username = os.environ["ISS007_UAT_USERNAME"].strip()
    password = os.environ["ISS007_UAT_PASSWORD"]
    no_permission_username = os.environ["ISS007_UAT_NO_PERMISSION_USERNAME"].strip()
    if not username or not password or not no_permission_username:
        raise RuntimeError("Isolated UAT usernames/password must be provided by the runner.")
    if get_user_model().objects.exists() or Customer.objects.exists() or FollowUpAttachment.objects.exists():
        raise RuntimeError("Fresh isolated database is not empty; refusing to seed over existing records.")

    run_suffix = identity["runId"].replace("-", "")[-10:]
    unit = OrganizationUnit.objects.create(
        name="ISS-007 一次性隔离测试组",
        code=f"ISS007-UAT-{run_suffix}",
        type="department",
    )
    position = Position.objects.create(
        unit=unit,
        name="附件验收操作人",
        code=f"ISS007-POS-{run_suffix}",
    )
    role = AccessRole.objects.create(
        name="ISS-007 隔离附件验收角色",
        code=f"iss007-attachment-uat-{run_suffix}",
        default_data_scope="self",
    )
    RolePermission.objects.create(role=role, module="customers", can_view=True)
    RolePermission.objects.create(
        role=role,
        module="followups",
        can_view=True,
        can_create=True,
        can_update=True,
        can_delete=True,
    )

    User = get_user_model()
    operator = User.objects.create_user(username=username, password=password, is_staff=True)
    profile = EmployeeProfile.objects.create(
        user=operator,
        display_name=OPERATOR_DISPLAY_NAME,
        unit=unit,
        position=position,
    )
    profile.roles.add(role)
    no_permission_user = User.objects.create_user(username=no_permission_username, password=password, is_staff=True)

    customer = Customer.objects.create(
        code=f"ISS007-DEL-{run_suffix}",
        name=f"ISS007 一次性合成客户 {run_suffix}",
        owner=OPERATOR_DISPLAY_NAME,
        owner_profile=profile,
    )
    follow_up = FollowUp.objects.create(
        customer=customer,
        followed_at="2026-10-31T02:00:00Z",
        type="email",
        subject=SUBJECT,
        content="仅用于 ISS-007 附件删除/替换 UAT 的合成跟进记录。",
        owner=OPERATOR_DISPLAY_NAME,
    )
    legacy = FollowUpAttachment(
        follow_up=follow_up,
        name=LEGACY_NAME,
        content_type="text/plain",
        size=len(LEGACY_BYTES),
    )
    legacy.file.save(LEGACY_NAME, ContentFile(LEGACY_BYTES), save=False)
    legacy.save()

    fixture = {
        "runId": identity["runId"],
        "customerId": customer.pk,
        "followUpId": follow_up.pk,
        "operatorUsername": operator.username,
        "operatorDisplayName": profile.display_name,
        "operatorIsSuperuser": operator.is_superuser,
        "noPermissionUsername": no_permission_user.username,
        "subject": SUBJECT,
        "syntheticLegacyAttachment": {
            "id": legacy.pk,
            "name": legacy.name,
            "file": legacy.file.name,
            "size": len(LEGACY_BYTES),
            "sha256": hashlib.sha256(LEGACY_BYTES).hexdigest(),
        },
        "database": identity["database"],
        "mediaRoot": identity["mediaRoot"],
        "recordsCreated": "Synthetic records only; no production database or media path is configured.",
    }
    (evidence_dir / "fixture.json").write_text(json.dumps(fixture, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(fixture, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
