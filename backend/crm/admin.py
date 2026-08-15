from django.contrib import admin

from .models import AccessRole, Contact, Customer, EmployeeProfile, FollowUp, InventoryMovement, Order, OrderItem, OrganizationUnit, Position, Product, ProductCategory, ProductCertificate, ProductParameter, Quote, QuoteItem, RolePermission, SKU, Transaction

for model in [OrganizationUnit, Position, AccessRole, RolePermission, EmployeeProfile, Customer, Contact, FollowUp, ProductCategory, Product, SKU, ProductParameter, ProductCertificate, Quote, QuoteItem, Order, OrderItem, InventoryMovement, Transaction]:
    admin.site.register(model)
