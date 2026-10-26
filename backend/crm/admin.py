from django.contrib import admin

from .models import AccessRole, Contact, Customer, EmployeeProfile, FollowUp, FollowUpAttachment, HSCode, InventoryMovement, OperationLog, Order, OrderItem, OrganizationUnit, Position, Product, ProductCategory, ProductCertificate, ProductParameter, Quote, QuoteItem, RolePermission, SKU, Transaction

for model in [OrganizationUnit, Position, AccessRole, RolePermission, EmployeeProfile, Customer, Contact, FollowUp, FollowUpAttachment, ProductCategory, SKU, ProductParameter, ProductCertificate, Quote, QuoteItem, Order, OrderItem, InventoryMovement, Transaction]:
    admin.site.register(model)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    readonly_fields = ('hs_code',)


@admin.register(HSCode)
class HSCodeAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        from .permissions import is_permission_admin
        return is_permission_admin(request.user)

    def has_change_permission(self, request, obj=None):
        return self.has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_add_permission(request)


@admin.register(OperationLog)
class OperationLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action_label", "entity", "object_label", "operator", "request_method", "request_path")
    list_filter = ("action", "entity", "operator")
    search_fields = ("entity", "object_id", "object_label", "action_label", "operator__username")
    readonly_fields = tuple(field.name for field in OperationLog._meta.fields)

    def has_add_permission(self, request):
        # Audit rows are created only by the authenticated business operation
        # hooks; the admin must never become a second write path.
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
