from django.conf import settings
from rest_framework.permissions import BasePermission, SAFE_METHODS


def development_superadmin_enabled():
    """Server-owned development access; beta/production and RBAC never inherit it."""
    return bool(
        getattr(settings, "APP_STAGE", "production") == "development"
        and settings.DEBUG
        and getattr(settings, "DEVELOPMENT_SUPERADMIN", False)
        and not getattr(settings, "RBAC_ENFORCEMENT", False)
    )


def is_permission_admin(user):
    if development_superadmin_enabled():
        return True
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


class HSCodeMaintenancePermission(BasePermission):
    """HS catalog reads are public to the app; any maintenance is admin-only."""

    message = "只有超级管理员或管理员可以维护 HS 编码。"

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or is_permission_admin(request.user)


class QuoteExportPermission(BasePermission):
    """Allow local development exports; protect production exports with operator permissions."""

    message = "Authentication and quote export permission are required."

    def has_permission(self, request, view):
        if development_superadmin_enabled():
            return True
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
