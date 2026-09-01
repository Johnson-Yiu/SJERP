from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from ..models import AccessRole, CategoryAttribute, Contact, Customer, CustomerCodeSequence, FollowUp, InventoryMovement, Order, OrganizationUnit, Product, ProductCategory, ProductCertificate, ProductCodeSequence, ProductParameter, PurchaseOrder, Quote, RolePermission, SKU, Supplier, Transaction


class BusinessFlowTests(APITestCase):
    def setUp(self):
        self.customer = Customer.objects.create(code="T-C001", name="Test Buyer", country="Germany", status="contact")
        self.product = Product.objects.create(code="T-P001", name="Test Downlight")
        self.sku = SKU.objects.create(product=self.product, sku="T-SKU-001", cost_price=3, default_price=6, currency="USD")

    def test_order_transaction_and_dashboard_flow(self):
        order_payload = {
            "order_no": "T-SO-001",
            "customer": self.customer.id,
            "order_date": str(date.today()),
            "status": "confirmed",
            "currency": "USD",
            "exchange_rate": "7.200000",
            "shipping_fee": "0",
            "discount": "0",
            "notes": "API flow test",
            "items": [{"sku": self.sku.id, "quantity": "100", "unit_price": "6", "cost_price": "3", "notes": ""}],
        }
        response = self.client.post("/api/orders/", order_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        order = Order.objects.get(order_no="T-SO-001")
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.total_amount, 600)

        payment_payload = {
            "transaction_no": "T-TX-001",
            "transaction_date": str(date.today()),
            "direction": "income",
            "category": "订单收款",
            "amount": "300",
            "currency": "USD",
            "exchange_rate": "7.200000",
            "order": order.id,
            "status": "confirmed",
        }
        response = self.client.post("/api/transactions/", payment_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        transaction = Transaction.objects.get(transaction_no="T-TX-001")
        self.assertEqual(transaction.customer, self.customer)

        response = self.client.get(f"/api/orders/{order.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["paid_amount"], "300.00")
        self.assertEqual(str(response.data["balance_amount"]), "300.00")

        response = self.client.get("/api/dashboard/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(float(response.data["summary"]["sales_ytd"]), 4320)

    def test_product_customer_reverse_lookup(self):
        order = Order.objects.create(order_no="T-SO-002", customer=self.customer, order_date=date.today(), exchange_rate=7.2)
        order.items.create(sku=self.sku, quantity=10, unit_price=6, cost_price=3)
        response = self.client.get(f"/api/products/{self.product.id}/customers/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["order__customer__name"], "Test Buyer")
        self.assertEqual(float(response.data[0]["sales"]), 432)

    def test_category_tree_inherits_attributes_and_prevents_cycles(self):
        root = ProductCategory.objects.create(name="灯具", sort_order=0)
        child = ProductCategory.objects.create(name="筒灯", parent=root, sort_order=0)
        CategoryAttribute.objects.create(category=root, name="色温", key="CCT", default_value="4000k", include_in_sku=True, uppercase=True)
        CategoryAttribute.objects.create(category=child, name="功率", key="WATT", default_value="12w", include_in_sku=True, uppercase=True)

        response = self.client.get("/api/categories/tree/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        child_row = next(row for row in response.data if row["id"] == child.id)
        self.assertEqual([row["key"] for row in child_row["effective_attributes"]], ["CCT", "WATT"])
        self.assertEqual(child_row["sku_name_preview"], "4000K-12W")
        self.assertTrue(child_row["effective_attributes"][0]["inherited"])

        cycle = self.client.post("/api/categories/reorder/", {"id": root.id, "parent": child.id, "index": 0}, format="json")
        self.assertEqual(cycle.status_code, status.HTTP_400_BAD_REQUEST)
        direct_cycle = self.client.patch(f"/api/categories/{root.id}/", {"parent": child.id}, format="json")
        self.assertEqual(direct_cycle.status_code, status.HTTP_400_BAD_REQUEST)

    def test_category_attribute_reorder_applies_to_sku_preview(self):
        root = ProductCategory.objects.create(name="电源", sort_order=0)
        first = CategoryAttribute.objects.create(category=root, name="输入电压", key="VIN", default_value="AC", include_in_sku=True, sort_order=0)
        second = CategoryAttribute.objects.create(category=root, name="输出电压", key="VOUT", default_value="DC", include_in_sku=True, sort_order=1)

        response = self.client.post("/api/category-attributes/reorder/", {"category": root.id, "ids": [second.id, first.id]}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tree = self.client.get("/api/categories/tree/")
        row = next(item for item in tree.data if item["id"] == root.id)
        self.assertEqual([item["key"] for item in row["effective_attributes"]], ["VOUT", "VIN"])
        self.assertEqual(row["sku_name_preview"], "DC-AC")

    def test_product_code_is_created_server_side_with_additional_categories(self):
        primary = ProductCategory.objects.create(name="主分类")
        secondary = ProductCategory.objects.create(name="附加分类")
        response = self.client.post("/api/products/", {"code": "MANUAL", "name": "自动编号产品", "sales_model_prefix": "AUTO12", "category": primary.id, "additional_categories": [secondary.id], "status": "active"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertRegex(response.data["code"], r"^SPU\d{9}$")
        self.assertNotEqual(response.data["code"], "MANUAL")
        self.assertEqual(response.data["additional_categories"], [secondary.id])
        self.assertEqual(ProductCodeSequence.objects.count(), 1)

    def test_customer_csv_import_updates_by_code(self):
        csv_file = SimpleUploadedFile(
            "customers.csv",
            "code,name,country,status\nT-C002,CSV Buyer,France,lead\n".encode("utf-8"),
            content_type="text/csv",
        )
        response = self.client.post("/api/import/csv/", {"entity": "customers", "file": csv_file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["created"], 1)
        self.assertTrue(Customer.objects.filter(code="T-C002", country="France").exists())

    def test_product_assets_inventory_and_context(self):
        ProductParameter.objects.create(product=self.product, group="光学", name="色温", value="4000", unit="K")
        ProductCertificate.objects.create(product=self.product, name="CE", certificate_no="TEST-CE-001")
        InventoryMovement.objects.create(movement_no="T-IM-001", movement_date=date.today(), type="purchase_in", sku=self.sku, quantity=120)
        InventoryMovement.objects.create(movement_no="T-IM-002", movement_date=date.today(), type="sample_out", sku=self.sku, quantity=5)

        sku_response = self.client.get("/api/skus/")
        sku_row = next(row for row in sku_response.data["results"] if row["id"] == self.sku.id)
        self.assertEqual(sku_row["stock_quantity"], "115.00")

        product_response = self.client.get(f"/api/context/products/{self.product.id}/")
        self.assertEqual(product_response.status_code, status.HTTP_200_OK)
        self.assertEqual({section["key"] for section in product_response.data["sections"]}, {"skus", "suppliers", "sales-summary", "sales", "inventory", "parameters", "certificates"})
        self.assertEqual(product_response.data["metrics"][2][1], 115)

        customer_response = self.client.get(f"/api/context/customers/{self.customer.id}/")
        self.assertEqual(customer_response.status_code, status.HTTP_200_OK)
        self.assertIn("采购记录", [section["title"] for section in customer_response.data["sections"]])
        followup_section = next(section for section in customer_response.data["sections"] if section["key"] == "followups")
        self.assertIn(["content", "跟进记录 / 解决方案", "excerpt"], followup_section["columns"])
        self.assertIn(["result", "客户回复 / 客户疑问", "excerpt"], followup_section["columns"])

    def test_supplier_and_purchase_order_context(self):
        supplier = Supplier.objects.create(name="Test Supplier", contact_name="Ming", currency="CNY")
        supplier.products.add(self.product)
        order = Order.objects.create(order_no="T-SO-SUPPLIER", customer=self.customer, order_date=date.today(), exchange_rate=7.2)
        purchase = PurchaseOrder.objects.create(purchase_no="T-PO-001", supplier=supplier, order=order, order_date=date.today(), currency="CNY", exchange_rate=1)
        purchase.items.create(sku=self.sku, quantity=10, unit_price=3)

        response = self.client.get(f"/api/context/suppliers/{supplier.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["entity"], "suppliers")
        self.assertEqual({section["key"] for section in response.data["sections"]}, {"products", "purchases", "payments"})
        self.assertEqual(response.data["metrics"][2][1], 30)

        purchase_response = self.client.get(f"/api/context/purchase-orders/{purchase.id}/")
        self.assertEqual(purchase_response.status_code, status.HTTP_200_OK, purchase_response.data)
        self.assertEqual(purchase_response.data["title"], "T-PO-001")

    def test_create_customer_with_multiple_contacts_and_one_primary(self):
        preview = self.client.get("/api/customers/next-code/")
        self.assertEqual(preview.status_code, status.HTTP_200_OK)
        self.assertEqual(preview.data["code"], f"{date.today():%Y%m%d}0000")

        response = self.client.post("/api/customers/", {
            "name": "Nested Contact Buyer",
            "source": "展会",
            "status": "lead",
            "contacts": [
                {"name": "First Contact", "email": "first@example.com", "is_primary": False},
                {"name": "Main Contact", "phone": "+86 13800000000", "is_primary": True},
            ],
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        customer = Customer.objects.get(name="Nested Contact Buyer")
        self.assertEqual(customer.code, f"{date.today():%Y%m%d}0000")
        self.assertEqual(customer.contacts.count(), 2)
        self.assertEqual(customer.contacts.get(is_primary=True).name, "Main Contact")

        sources = self.client.get("/api/customers/sources/")
        self.assertIn({"value": "展会", "label": "展会"}, sources.data)

    def test_customer_code_carries_from_9999_to_a000_and_first_contact_is_primary(self):
        CustomerCodeSequence.objects.create(pk=1, last_value=9998)
        for name, suffix in [("Buyer 9999", "9999"), ("Buyer A000", "A000")]:
            response = self.client.post("/api/customers/", {
                "name": name,
                "contacts": [{"name": "Buyer"}],
            }, format="json")
            self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
            customer = Customer.objects.get(name=name)
            self.assertEqual(customer.code, f"{date.today():%Y%m%d}{suffix}")
            self.assertTrue(customer.contacts.get().is_primary)

    def test_sales_documents_advance_customer_stage(self):
        customer = Customer.objects.create(code="T-C004", name="Stage Buyer", status="contact")
        Contact.objects.create(customer=customer, name="Buyer")
        Quote.objects.create(quote_no="T-Q-001", customer=customer, quote_date=date.today())
        customer.refresh_from_db()
        self.assertEqual(customer.status, "opportunity")

        Order.objects.create(order_no="T-SO-010", customer=customer, order_date=date.today())
        customer.refresh_from_db()
        self.assertEqual(customer.status, "customer")

        Order.objects.create(order_no="T-SO-011", customer=customer, order_date=date.today())
        customer.refresh_from_db()
        self.assertEqual(customer.status, "company")

    def test_organization_and_permission_templates(self):
        response = self.client.get("/api/organization/overview/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["summary"]["departments"], 5)
        self.assertGreaterEqual(response.data["summary"]["positions"], 13)
        self.assertTrue(OrganizationUnit.objects.filter(code="SALES", parent__code="SENJU").exists())

        superadmin = AccessRole.objects.get(code="superadmin")
        self.assertEqual(superadmin.default_data_scope, "all")
        self.assertEqual(RolePermission.objects.filter(role=superadmin, can_view=True, can_create=True, can_update=True, can_delete=True).count(), 17)

    def test_admin_can_save_role_permission_matrix_in_configuration_mode(self):
        role = AccessRole.objects.get(code="salesperson")
        response = self.client.post(f"/api/access-roles/{role.id}/permission-matrix/", {
            "permissions": [
                {"module": "customers", "can_view": True, "can_create": True, "can_update": False},
                {"module": "quotes", "can_view": True, "can_create": False, "can_update": False},
            ],
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(RolePermission.objects.get(role=role, module="customers").can_create)
        self.assertFalse(RolePermission.objects.filter(role=role, module="orders").exists())

        superadmin = AccessRole.objects.get(code="superadmin")
        response = self.client.post(f"/api/access-roles/{superadmin.id}/permission-matrix/", {"permissions": []}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_follow_up_subject_optional_and_current_operator_available(self):
        operator = self.client.get("/api/session/current-operator/")
        self.assertEqual(operator.status_code, status.HTTP_200_OK)
        self.assertEqual(operator.data["name"], "Johnson")

        response = self.client.post("/api/follow-ups/", {
            "customer": self.customer.id,
            "followed_at": "2026-08-07T10:00:00+08:00",
            "type": "email",
            "subject": "",
            "content": "**发送报价**\n- 确认交期",
            "result": "_客户有兴趣_",
            "owner": operator.data["name"],
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(FollowUp.objects.get(pk=response.data["id"]).subject, "")

        custom = self.client.post("/api/follow-ups/", {
            "customer": self.customer.id,
            "followed_at": "2026-08-07T11:00:00+08:00",
            "type": "WhatsApp视频",
            "content": "演示产品",
            "owner": operator.data["name"],
        }, format="json")
        self.assertEqual(custom.status_code, status.HTTP_201_CREATED, custom.data)

        methods = self.client.get("/api/follow-ups/methods/")
        self.assertEqual(methods.status_code, status.HTTP_200_OK)
        self.assertIn(
            {"value": "WhatsApp视频", "label": "WhatsApp视频"},
            methods.data,
        )
