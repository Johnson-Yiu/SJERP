import json

from django.contrib.auth import get_user_model

from crm.models import AccessRole, Customer, EmployeeProfile, OrganizationUnit, Position, RolePermission


def main():
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
        username="iss055-owner-ui",
        password="iss055-local-only-password",
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
    print(json.dumps({"visible_id": visible.pk, "hidden_id": hidden.pk}, ensure_ascii=False))


if __name__ == "__main__":
    main()
