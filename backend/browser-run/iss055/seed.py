import json
import os
from pathlib import Path

import django
django.setup()

from django.contrib.auth import get_user_model
from django.conf import settings

from crm.models import AccessRole, Customer, EmployeeProfile, OrganizationUnit, Position, RolePermission
from crm.permissions import development_superadmin_enabled
from test_support.isolated_runtime import verify_isolated_runtime


def main():
    verify_isolated_runtime(settings=settings, database_must_exist=True)
    if not settings.RBAC_ENFORCEMENT or development_superadmin_enabled():
        raise RuntimeError("ISS-055 requires controlled RBAC with development superadmin disabled")
    username = os.environ.get("ISS055_UI_USERNAME", "").strip()
    password = os.environ.get("ISS055_UI_PASSWORD", "")
    evidence_dir = Path(os.environ["ISS055_EVIDENCE_DIR"]).resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    if not username or not password:
        raise RuntimeError("ISS-055 isolated browser credentials must be supplied by the runner")

    User = get_user_model()
    unit = OrganizationUnit.objects.create(name="ISS-055 隔离销售部", code="ISS055-UNIT", type="department")
    position = Position.objects.create(unit=unit, name="隔离销售", code="ISS055-POS")
    role = AccessRole.objects.create(
        name="ISS-055 仅本人客户查看",
        code="iss055-self-customer-view",
        default_data_scope="self",
    )
    RolePermission.objects.create(role=role, module="customers", can_view=True)

    owner_user = User.objects.create_user(
        username=username,
        password=password,
        is_staff=True,
    )
    owner_profile = EmployeeProfile.objects.create(
        user=owner_user,
        display_name="ISS-055 隔离负责人",
        unit=unit,
        position=position,
    )
    owner_profile.roles.add(role)

    hidden_user = User.objects.create_user(username="iss055-hidden-owner")
    hidden_profile = EmployeeProfile.objects.create(
        user=hidden_user,
        display_name="ISS-055 其他负责人",
        unit=unit,
        position=position,
    )

    visible = Customer.objects.create(
        code="ISS055-VISIBLE",
        name="ISS-055 有权客户",
        country="中国",
        owner="ISS-055 隔离负责人",
        owner_profile=owner_profile,
    )
    hidden = Customer.objects.create(
        code="ISS055-HIDDEN",
        name="ISS-055 无权客户",
        country="中国",
        owner="ISS-055 其他负责人",
        owner_profile=hidden_profile,
    )
    fixture = {"visible_id": visible.pk, "hidden_id": hidden.pk, "username": username, "employee_profile_id": owner_profile.pk}
    (evidence_dir / "fixture.json").write_text(json.dumps(fixture, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(fixture, ensure_ascii=False))


if __name__ == "__main__":
    main()
