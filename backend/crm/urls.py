from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .context import entity_context
from .views import AccessRoleViewSet, CategoryAttributeViewSet, ContactViewSet, CustomerViewSet, EmployeeProfileViewSet, FollowUpViewSet, InventoryMovementViewSet, OrderViewSet, OrganizationUnitViewSet, PositionViewSet, ProductCategoryViewSet, ProductCertificateViewSet, ProductParameterViewSet, ProductViewSet, QuoteViewSet, RolePermissionViewSet, SKUViewSet, SupplierViewSet, TransactionViewSet, current_operator, dashboard, import_csv, import_templates, organization_overview

router = DefaultRouter()
router.register("customers", CustomerViewSet, basename="customer")
router.register("suppliers", SupplierViewSet, basename="supplier")
router.register("contacts", ContactViewSet)
router.register("follow-ups", FollowUpViewSet)
router.register("categories", ProductCategoryViewSet)
router.register("category-attributes", CategoryAttributeViewSet)
router.register("products", ProductViewSet)
router.register("skus", SKUViewSet)
router.register("product-parameters", ProductParameterViewSet)
router.register("product-certificates", ProductCertificateViewSet)
router.register("quotes", QuoteViewSet)
router.register("orders", OrderViewSet)
router.register("transactions", TransactionViewSet)
router.register("inventory-movements", InventoryMovementViewSet)
router.register("organization-units", OrganizationUnitViewSet)
router.register("positions", PositionViewSet)
router.register("access-roles", AccessRoleViewSet)
router.register("role-permissions", RolePermissionViewSet)
router.register("employees", EmployeeProfileViewSet)

urlpatterns = [
    path("dashboard/", dashboard),
    path("organization/overview/", organization_overview),
    path("session/current-operator/", current_operator),
    path("context/<str:entity>/<int:pk>/", entity_context),
    path("import/templates/", import_templates),
    path("import/csv/", import_csv),
    path("", include(router.urls)),
]
