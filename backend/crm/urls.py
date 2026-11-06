from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .context import entity_context
from .sku_management import ProductCombinationRulesView, SupplierCapabilityViewSet, SupplierCandidatesView, ProductSKUPlanView, ProductSKUPlanActionView, ProductSupplierCandidatePoolView, OrderItemSupplierAllocationView
from .views import AccessRoleViewSet, CategoryAttributeViewSet, ContactViewSet, ContractChangeRequestViewSet, CustomerViewSet, EmployeeProfileViewSet, FollowUpViewSet, HSCodeViewSet, InventoryMovementViewSet, OperationLogViewSet, OrderViewSet, OrganizationUnitViewSet, PackagingTemplateViewSet, PaymentPlanViewSet, PositionViewSet, ProductCategoryViewSet, ProductCertificateViewSet, ProductParameterViewSet, ProductViewSet, PurchaseOrderViewSet, QuoteViewSet, RolePermissionViewSet, ShipmentViewSet, SKUPackagingProfileViewSet, SKUViewSet, SupplierSKUViewSet, SupplierViewSet, TransactionViewSet, current_operator, dashboard, finance_dashboard, finance_dashboard_details, import_csv, import_csv_execute, import_csv_preview, import_templates, organization_overview, usd_cny_reference_rate

from .sales_rules import SalesRuleViewSet

from .trade_units import SKUTradeUnitViewSet
from .file_access import protected_media
from .report_templates import SharedReportTemplateViewSet
from .history_import_preflight import HistoryImportPreflightView
from .history_takeover_api import HistoryTakeoverDetailView, HistoryTakeoverGroupActionView, HistoryTakeoverListCreateView, HistoryTakeoverReportView, HistoryTakeoverTemplateView
from .session_views import csrf, sign_in, sign_out

from .new_product_reminders import ReminderViewSet
from .party_version_api import (PartyDetailsView, QuotePartyChangeView, QuotePartyChangeDecisionView,
    DocumentPartyChangeView, DocumentPartyChangeDecisionView)

router = DefaultRouter()
router.register("new-product-reminders", ReminderViewSet, basename="new-product-reminder")
from .finance_closeout_api import FinanceCloseoutViewSet
router.register("finance-ledger", FinanceCloseoutViewSet, basename="finance-ledger")
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
router.register("reports/templates", SharedReportTemplateViewSet, basename="shared-report-template")

from .reporting import historical_analysis, report_catalog, report_data, report_details
from .actual_cash_api import actual_cash_report

urlpatterns = [
    path("session/csrf/", csrf),
    path("session/login/", sign_in),
    path("session/logout/", sign_out),
    path('quotes/<int:document_id>/party-details/', PartyDetailsView.as_view(), {'target_type': 'quote'}),
    path('orders/<int:document_id>/party-details/', PartyDetailsView.as_view(), {'target_type': 'order'}),
    path('purchase-orders/<int:document_id>/party-details/', PartyDetailsView.as_view(), {'target_type': 'purchase_order'}),
    path('quotes/<int:quote_id>/party-change/', QuotePartyChangeView.as_view()),
    path('quotes/<int:quote_id>/party-change/<int:request_id>/<str:operation>/', QuotePartyChangeDecisionView.as_view()),
    path('orders/<int:document_id>/party-change/', DocumentPartyChangeView.as_view(), {'target_type': 'order'}),
    path('orders/<int:document_id>/party-change/<int:request_id>/<str:operation>/', DocumentPartyChangeDecisionView.as_view(), {'target_type': 'order'}),
    path('purchase-orders/<int:document_id>/party-change/', DocumentPartyChangeView.as_view(), {'target_type': 'purchase_order'}),
    path('purchase-orders/<int:document_id>/party-change/<int:request_id>/<str:operation>/', DocumentPartyChangeDecisionView.as_view(), {'target_type': 'purchase_order'}),
    path("media/<path:relative_path>", protected_media, name="crm-protected-media"),
    path("products/<int:pk>/combination-rules/", ProductCombinationRulesView.as_view()),
    path("products/<int:pk>/sku-plan/", ProductSKUPlanView.as_view()),
    path("products/<int:pk>/sku-plan/<str:operation>/", ProductSKUPlanActionView.as_view()),
    path("products/<int:pk>/supplier-candidate-pool/", ProductSupplierCandidatePoolView.as_view()),
    path("skus/<int:pk>/supplier-candidates/", SupplierCandidatesView.as_view()),
    path("orders/<int:order_id>/items/<int:item_id>/supplier-allocation/", OrderItemSupplierAllocationView.as_view()),
    path("reports/catalog/", report_catalog),
    path("reports/data/", report_data),
    path("reports/details/", report_details),
    path("reports/historical/", historical_analysis),
    path("dashboard/", dashboard),
    path("finance-dashboard/", finance_dashboard),
    path("finance-dashboard/details/", finance_dashboard_details),
    path("actual-rmb-cash/", actual_cash_report),
    path("organization/overview/", organization_overview),
    path("session/current-operator/", current_operator),
    path("exchange-rates/usd-cny/", usd_cny_reference_rate),
    path("context/<str:entity>/<int:pk>/", entity_context),
    path("import/templates/", import_templates),
    path("import/csv/", import_csv),
    path("import/csv/preview/", import_csv_preview),
    path("import/csv/execute/", import_csv_execute),
    path("import/history-preflight/", HistoryImportPreflightView.as_view(), name="history-import-preflight"),
    path("import/history-takeovers/", HistoryTakeoverListCreateView.as_view(), name="history-takeover-list-create"),
    path("import/history-takeovers/template/", HistoryTakeoverTemplateView.as_view(), name="history-takeover-template"),
    path("import/history-takeovers/<int:application_id>/", HistoryTakeoverDetailView.as_view(), name="history-takeover-detail"),
    path("import/history-takeovers/<int:application_id>/review-report.csv", HistoryTakeoverReportView.as_view(), name="history-takeover-report"),
    path("import/history-takeovers/<int:application_id>/groups/<int:group_id>/<str:operation>/", HistoryTakeoverGroupActionView.as_view(), name="history-takeover-group-action"),
    path("", include(router.urls)),
]
