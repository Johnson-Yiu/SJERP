from django.conf import settings
from rest_framework.permissions import BasePermission, SAFE_METHODS
from .models import AccessRole, EmployeeProfile


ACTION_FIELDS = {
    "view": "can_view",
    "create": "can_create",
    "update": "can_update",
    "delete": "can_delete",
    "export": "can_export",
    "import": "can_import",
}

PATH_MODULES = {
    "customers": "customers", "contacts": "contacts", "follow-ups": "followups",
    "quotes": "quotes", "orders": "orders", "suppliers": "suppliers",
    "supplier-skus": "suppliers", "supplier-capabilities": "suppliers",
    "purchase-orders": "purchases", "goods-receipts": "purchases",
    "inventory-movements": "inventory", "shipments": "inventory",
    "products": "products", "categories": "categories", "category-attributes": "categories",
    "skus": "skus", "sku-trade-units": "trade_units", "trade-units": "trade_units",
    "packaging-templates": "packaging", "sku-packaging-profiles": "packaging",
    "product-parameters": "parameters", "product-certificates": "certificates",
    "hs-codes": "hs_codes", "transactions": "transactions", "payment-plans": "finance",
    "contract-changes": "orders", "sales-rules": "quotes", "reports": "reports",
    "dashboard": "dashboard", "finance-dashboard": "finance", "import": "imports",
    "exchange-rates": "finance",
    "organization": "organization", "organization-units": "organization",
    "positions": "organization", "employees": "employees", "access-roles": "permissions",
    "role-permissions": "permissions",
}

CONTEXT_MODULES = {
    "customers": "customers", "suppliers": "suppliers", "contacts": "contacts",
    "follow-ups": "followups", "categories": "categories", "products": "products",
    "skus": "skus", "sku-versions": "skus", "supplier-skus": "suppliers",
    "product-parameters": "parameters", "product-certificates": "certificates",
    "quotes": "quotes", "orders": "orders", "purchase-orders": "purchases",
    "transactions": "transactions", "inventory-movements": "inventory",
    "sales-periods": "reports",
}

OPERATION_ENTITY_MODULES = {
    "crm.customer": "customers", "crm.contact": "contacts", "crm.followup": "followups",
    "crm.quote": "quotes", "crm.order": "orders", "crm.supplier": "suppliers",
    "crm.suppliersku": "suppliers", "crm.purchaseorder": "purchases",
    "crm.goodsreceipt": "purchases", "crm.inventorymovement": "inventory",
    "crm.shipment": "inventory", "crm.product": "products", "crm.productcategory": "categories",
    "crm.categoryattribute": "categories", "crm.sku": "skus", "crm.skutradeunit": "trade_units",
    "crm.packagingtemplate": "packaging", "crm.skupackagingprofile": "packaging",
    "crm.productparameter": "parameters", "crm.productcertificate": "certificates",
    "crm.hscode": "hs_codes", "crm.transaction": "transactions", "crm.paymentplan": "finance",
    "crm.contractchangerequest": "orders", "crm.organizationunit": "organization",
    "crm.position": "organization", "crm.employeeprofile": "employees", "crm.accessrole": "permissions",
    "crm.rolepermission": "permissions", "crm.sharedreporttemplate": "reports",
}


def development_superadmin_enabled():
    """Server-owned development access; beta/production and RBAC never inherit it."""
    return bool(
        getattr(settings, "APP_STAGE", "production") == "development"
        and settings.DEBUG
        and getattr(settings, "DEVELOPMENT_SUPERADMIN", False)
        and not getattr(settings, "RBAC_ENFORCEMENT", False)
    )


def _profile_for(user):
    try:
        return user.employee_profile
    except (AttributeError, EmployeeProfile.DoesNotExist):
        return None


def _active_roles(user):
    profile = _profile_for(user)
    return profile.roles.filter(active=True) if profile and profile.active else AccessRole.objects.none()


def has_all_permissions(user):
    if not getattr(settings, "RBAC_ENFORCEMENT", False):
        return development_superadmin_enabled() or bool(user and user.is_authenticated)
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return _active_roles(user).filter(code="superadmin").exists()


def effective_permission_matrix(user):
    from .models import RolePermission

    complete = {module: {action: False for action in ACTION_FIELDS} for module, _ in RolePermission.MODULE_CHOICES}
    if has_all_permissions(user):
        return {module: {action: True for action in ACTION_FIELDS} for module in complete}
    roles = _active_roles(user)
    if not roles.exists():
        return complete
    for row in RolePermission.objects.filter(role__in=roles):
        target = complete.get(row.module)
        if target:
            for action, field in ACTION_FIELDS.items():
                target[action] = target[action] or bool(getattr(row, field))
    return complete


def is_permission_admin(user):
    if development_superadmin_enabled():
        return True
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return _active_roles(user).filter(code__in=["superadmin", "admin"], active=True).exists()


def module_for_request(request, view=None):
    module = getattr(view, "permission_module", None) if view is not None else None
    path = request.path_info.strip("/")
    parts = path.split("/") if path else []
    if parts and parts[0] == "api":
        parts = parts[1:]
    if parts and parts[0] == "context":
        return CONTEXT_MODULES.get(parts[1]) if len(parts) > 1 else None
    if parts and parts[0] == "operation-logs":
        entity = request.query_params.get("entity") or request.GET.get("entity")
        if (entity or "").lower() == "crm.contractchangerequest":
            return "orders" if user_can(request.user, "orders", "view") else ("purchases" if user_can(request.user, "purchases", "view") else None)
        return OPERATION_ENTITY_MODULES.get((entity or "").lower()) or CONTEXT_MODULES.get(entity) or PATH_MODULES.get(entity or "")
    if module:
        return module
    if not parts:
        return None
    first = parts[0]
    if first == "products" and "sku-plan" in parts:
        return "skus"
    if first == "skus" and ("inventory-detail" in parts or "inventory-list" in parts):
        return "inventory"
    if first == "products" and "combination-rules" in parts:
        return "skus"
    if first == "products" and "supplier-candidate-pool" in parts:
        return "suppliers"
    if first == "skus" and "supplier-candidates" in parts:
        return "suppliers"
    if first == "orders" and "supplier-allocation" in parts:
        return "orders"
    if first == "orders" and ("procurement-drafts" in parts or "generate-purchase-drafts" in parts):
        return "purchases"
    return PATH_MODULES.get(first)


def action_for_request(request, view=None):
    path = request.path_info.lower()
    action = getattr(view, "action", None) if view is not None else None
    if request.query_params.get("export", "").lower() in {"1", "true", "csv", "xlsx"}:
        return "export"
    if "export" in path or (action and "export" in action):
        return "export"
    if "/import/templates/" in f"{path}/":
        return "view"
    if "/import/csv/" in f"{path}/" or path.rstrip("/").endswith("/import/csv"):
        return "import"
    if request.method in SAFE_METHODS:
        return "view"
    if request.method == "DELETE":
        return "delete"
    if request.method == "POST" and (action == "create" or action in {"batch_create", "create_batch", "historical", "create_historical"}):
        return "create"
    if request.method == "POST" and ("batch-create" in path or path.rstrip("/").endswith("/batch")):
        return "create"
    if request.method == "POST" and path.rstrip("/").endswith("/generate-purchase-drafts"):
        return "create"
    if request.method == "POST" and "procurement-drafts" in path:
        return "create"
    if request.method == "POST" and action is None and view is not None:
        return "create" if view.__class__.__name__.endswith("ViewSet") and getattr(view, "detail", False) is False and request.path_info.rstrip("/").split("/")[-1] == "" else "update"
    if request.method in {"POST", "PUT", "PATCH"}:
        return "update"
    return "view"


def user_can(user, module, action="view"):
    if action not in ACTION_FIELDS or not module:
        return False
    return bool(effective_permission_matrix(user).get(module, {}).get(action, False))


class SecureDefaultPermission(BasePermission):
    """Keep development usable, require authentication once enforcement is enabled."""

    def has_permission(self, request, view):
        if development_superadmin_enabled():
            return True
        if getattr(view, "permission_public", False):
            return True
        return bool(request.user and request.user.is_authenticated)


class ModuleActionPermission(BasePermission):
    message = "你没有权限执行此操作。"

    def has_permission(self, request, view):
        if development_superadmin_enabled():
            return True
        if getattr(view, "permission_public", False):
            return True
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if not getattr(settings, "RBAC_ENFORCEMENT", False):
            return True
        if has_all_permissions(user):
            return True
        module = module_for_request(request, view)
        if module == "permissions" and is_permission_admin(user):
            return True
        if not module:
            # Public routes must opt in explicitly. An authenticated-only
            # fallback still bypasses the module permission boundary.
            return False
        return user_can(user, module, action_for_request(request, view))


class HistoricalAnalysisPermission(BasePermission):
    """Allow the history ledger when either underlying business scope is readable.

    Historical analysis is deliberately not a gateway to the general reports
    module.  The endpoint applies its own per-dimension redaction, while this
    permission only establishes that the caller may read sales or purchasing
    history at all.
    """

    message = "你没有历史订单分析权限。"

    def has_permission(self, request, view):
        if development_superadmin_enabled():
            return True
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if not getattr(settings, "RBAC_ENFORCEMENT", False):
            return True
        if has_all_permissions(user):
            return True
        return user_can(user, "orders", "view") or user_can(user, "purchases", "view")


class OrganizationOverviewPermission(BasePermission):
    """Allow permission administrators to read the matrix without organization.view."""

    message = "你没有权限查看组织与权限。"

    def has_permission(self, request, view):
        if development_superadmin_enabled():
            return True
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if not getattr(settings, "RBAC_ENFORCEMENT", False):
            return True
        if has_all_permissions(user) or is_permission_admin(user):
            return True
        return user_can(user, "organization", "view")


class PermissionAdminOnly(BasePermission):
    """Restrict permission changes to administrators while allowing module reads."""

    message = "只有超级管理员或管理员可以配置权限。"

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if not getattr(settings, "RBAC_ENFORCEMENT", False):
            return True
        return is_permission_admin(request.user)


class HSCodeMaintenancePermission(BasePermission):
    """Keep HS maintenance admin-only in addition to ordinary module permissions."""

    message = "只有超级管理员或管理员可以维护 HS 编码。"

    def has_permission(self, request, view):
        if not ModuleActionPermission().has_permission(request, view):
            return False
        if request.method in SAFE_METHODS:
            return True
        return is_permission_admin(request.user)


class QuoteExportPermission(BasePermission):
    message = "你没有报价导出权限。"

    def has_permission(self, request, view):
        if development_superadmin_enabled():
            return True
        user = request.user
        if not getattr(settings, "RBAC_ENFORCEMENT", False):
            return bool(user and user.is_authenticated)
        return bool(user and user.is_authenticated and user_can(user, "quotes", "export"))
