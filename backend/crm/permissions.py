from django.conf import settings
from rest_framework.permissions import BasePermission, SAFE_METHODS


def is_permission_admin(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    profile = getattr(user, "employee_profile", None)
    return bool(profile and profile.active and profile.roles.filter(code__in=["superadmin", "admin"], active=True).exists())


class PermissionAdminOnly(BasePermission):
    """Protect permission configuration after RBAC enforcement is enabled."""

    message = "只有超级管理员或管理员可以配置权限。"

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if not getattr(settings, "RBAC_ENFORCEMENT", False):
            return True
        return is_permission_admin(request.user)


class QuoteExportPermission(BasePermission):
    """Require a signed-in operator and honor quote export grants when RBAC is active."""

    message = "Authentication and quote export permission are required."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if not getattr(settings, "RBAC_ENFORCEMENT", False) or user.is_superuser:
            return True
        profile = getattr(user, "employee_profile", None)
        return bool(
            profile
            and profile.active
            and profile.roles.filter(
                active=True,
                permissions__module="quotes",
                permissions__can_export=True,
            ).exists()
        )
