from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .context import entity_context
from .sku_management import ProductCombinationRulesView, SupplierCapabilityViewSet, SupplierCandidatesView, ProductSKUPlanView, ProductSKUPlanActionView, ProductSupplierCandidatePoolView, OrderItemSupplierAllocationView
from .views import AccessRoleViewSet, CategoryAttributeViewSet, ContactViewSet, ContractChangeRequestViewSet, CustomerViewSet, EmployeeProfileViewSet, FollowUpViewSet, HSCodeViewSet, InventoryMovementViewSet, OperationLogViewSet, OrderViewSet, OrganizationUnitViewSet, PackagingTemplateViewSet, PaymentPlanViewSet, PositionViewSet, ProductCategoryViewSet, ProductCertificateViewSet, ProductParameterViewSet, ProductViewSet, PurchaseOrderViewSet, QuoteViewSet, RolePermissionViewSet, ShipmentViewSet, SKUPackagingProfileViewSet, SKUViewSet, SupplierSKUViewSet, SupplierViewSet, TransactionViewSet, current_operator, dashboard, finance_dashboard, import_csv, import_csv_execute, import_csv_preview, import_templates, organization_overview, usd_cny_reference_rate

from .sales_rules import SalesRuleViewSet

from .trade_units import SKUTradeUnitViewSet
from .file_access import protected_media

router = DefaultRouter()
from .cash_api import RmbCashEventViewSet
router.register("rmb-cash-events", RmbCashEventViewSet, basename="rmb-cash-event")
router.register("sku-trade-units", SKUTradeUnitViewSet)
router.register("sales-rules", SalesRuleViewSet, basename="sales-rule")
router.register("supplier-capabilities", SupplierCapabilityViewSet, basename="supplier-capability")
router.register("customers", CustomerViewSet, basename="customer")
router.register("suppliers", SupplierViewSet, basename="supplier")
router.register("purchase-orders", PurchaseOrderViewSet, basename="purchase-order")
router.register("contacts", ContactViewSet)
router.register("follow-ups", FollowUpViewSet)
router.register("categories", ProductCategoryViewSet)
router.register("category-attributes", CategoryAttributeViewSet)
router.register("products", ProductViewSet)
router.register("hs-codes", HSCodeViewSet, basename="hs-code")
router.register("skus", SKUViewSet)
router.register("supplier-skus", SupplierSKUViewSet, basename="supplier-sku")
router.register("packaging-templates", PackagingTemplateViewSet)
router.register("sku-packaging-profiles", SKUPackagingProfileViewSet)
router.register("shipments", ShipmentViewSet)
router.register("product-parameters", ProductParameterViewSet)
router.register("product-certificates", ProductCertificateViewSet)
router.register("quotes", QuoteViewSet)
router.register("orders", OrderViewSet)
router.register("transactions", TransactionViewSet)
router.register("payment-plans", PaymentPlanViewSet, basename="payment-plan")
router.register("contract-changes", ContractChangeRequestViewSet, basename="contract-change")
router.register("inventory-movements", InventoryMovementViewSet)
router.register("organization-units", OrganizationUnitViewSet)
router.register("positions", PositionViewSet)
router.register("access-roles", AccessRoleViewSet)
router.register("role-permissions", RolePermissionViewSet)
router.register("employees", EmployeeProfileViewSet)
router.register("operation-logs", OperationLogViewSet, basename="operation-log")

from .reporting import historical_analysis, report_catalog, report_data
from .actual_cash_api import actual_cash_report

urlpatterns = [
    path("media/<path:relative_path>", protected_media, name="crm-protected-media"),
    path("products/<int:pk>/combination-rules/", ProductCombinationRulesView.as_view()),
    path("products/<int:pk>/sku-plan/", ProductSKUPlanView.as_view()),
    path("products/<int:pk>/sku-plan/<str:operation>/", ProductSKUPlanActionView.as_view()),
    path("products/<int:pk>/supplier-candidate-pool/", ProductSupplierCandidatePoolView.as_view()),
    path("skus/<int:pk>/supplier-candidates/", SupplierCandidatesView.as_view()),
    path("orders/<int:order_id>/items/<int:item_id>/supplier-allocation/", OrderItemSupplierAllocationView.as_view()),
    path("reports/catalog/", report_catalog),
    path("reports/data/", report_data),
    path("reports/historical/", historical_analysis),
    path("dashboard/", dashboard),
    path("finance-dashboard/", finance_dashboard),
    path("actual-rmb-cash/", actual_cash_report),
    path("organization/overview/", organization_overview),
    path("session/current-operator/", current_operator),
    path("exchange-rates/usd-cny/", usd_cny_reference_rate),
    path("context/<str:entity>/<int:pk>/", entity_context),
    path("import/templates/", import_templates),
    path("import/csv/", import_csv),
    path("import/csv/preview/", import_csv_preview),
    path("import/csv/execute/", import_csv_execute),
    path("", include(router.urls)),
]
