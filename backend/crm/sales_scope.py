"""Shared server-side data scope for customer and sales records."""

from django.conf import settings

from .models import Customer, EmployeeProfile, OrganizationUnit
from .permissions import development_superadmin_enabled


SCOPE_RANK = {"self": 1, "department": 2, "department_tree": 3, "all": 4}


def employee_profile_for(user):
    if not user or not getattr(user, "is_authenticated", False):
        return None
    try:
        profile = user.employee_profile
    except (AttributeError, EmployeeProfile.DoesNotExist):
        return None
    return profile if profile.active else None


def effective_data_scope(user):
    """Return all/self/department/department_tree, or none for an unscoped user."""
    if development_superadmin_enabled() or bool(user and getattr(user, "is_superuser", False)):
        return "all"
    profile = employee_profile_for(user)
    if profile and profile.roles.filter(active=True, code="superadmin").exists():
        return "all"
    # With enforcement disabled, preserve the existing authenticated-user
    # behavior. Development superadmins are still decided by the server entrypoint above.
    if not getattr(settings, "RBAC_ENFORCEMENT", False):
        return "all"
    if not profile:
        return "none"
    if profile.data_scope_override != "inherit":
        return profile.data_scope_override
    scopes = list(profile.roles.filter(active=True).values_list("default_data_scope", flat=True))
    return max(scopes, key=lambda scope: SCOPE_RANK.get(scope, 0), default="none")


def _profile_for_scope(user):
    return employee_profile_for(user)


def allowed_unit_ids(user):
    scope = effective_data_scope(user)
    profile = _profile_for_scope(user)
    if scope == "all":
        return list(OrganizationUnit.objects.filter(active=True).values_list("id", flat=True))
    if scope == "department" and profile:
        return [profile.unit_id] if profile.unit.active else []
    if scope != "department_tree" or not profile:
        return []
    units = list(OrganizationUnit.objects.values_list("id", "parent_id", "active"))
    children = {}
    for unit_id, parent_id, _active in units:
        children.setdefault(parent_id, []).append(unit_id)
    included, pending = set(), [profile.unit_id]
    while pending:
        current = pending.pop()
        if current in included:
            continue
        included.add(current)
        pending.extend(children.get(current, ()))
    return [unit_id for unit_id, _parent_id, active in units if active and unit_id in included]


def allowed_employee_ids(user):
    scope = effective_data_scope(user)
    profile = _profile_for_scope(user)
    employees = EmployeeProfile.objects.filter(active=True)
    if scope == "all":
        return list(employees.values_list("id", flat=True))
    if scope == "self":
        return [profile.pk] if profile else []
    if scope in {"department", "department_tree"}:
        return list(employees.filter(unit_id__in=allowed_unit_ids(user)).values_list("id", flat=True))
    return []


def scope_customer_queryset(queryset, user):
    scope = effective_data_scope(user)
    if scope == "all":
        return queryset
    profile = _profile_for_scope(user)
    if scope == "self" and profile:
        return queryset.filter(owner_profile_id=profile.pk)
    if scope in {"department", "department_tree"}:
        units = allowed_unit_ids(user)
        return queryset.filter(owner_profile__unit_id__in=units) if units else queryset.none()
    return queryset.none()


def scope_customer_related_queryset(queryset, user, relation="customer"):
    """Apply customer ownership through a related sales record."""
    scoped_customers = scope_customer_queryset(Customer.objects.all(), user)
    return queryset.filter(**{f"{relation}__in": scoped_customers})


def customer_in_scope(customer_id, user):
    return scope_customer_queryset(Customer.objects.all(), user).filter(pk=customer_id).exists()


def data_scope_display(scope):
    return {
        "all": "全部数据",
        "department_tree": "本部门及下级",
        "department": "本部门",
        "self": "仅本人负责",
        "none": "未分配数据范围",
    }.get(scope, "未分配数据范围")

