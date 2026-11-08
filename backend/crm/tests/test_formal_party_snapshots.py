from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from crm.models import Contact, Customer, Order, OrderItem, Product, ProductCategory, PurchaseOrder, PurchaseOrderItem, Quote, SKU, Supplier
from crm.serializers import OrderSerializer, PurchaseOrderSerializer, SupplierSerializer
from crm.services.order_lifecycle import confirm_order
from crm.services.purchase_lifecycle import place_purchase_order


class FormalPartySnapshotTests(TestCase):
    def setUp(self):
        self.day = date(2026, 10, 21)
        self.customer = Customer.objects.create(
            code="C-FORMAL-SNAPSHOT",
            name="客户 A 原始名称",
            country="Germany",
            address="原始客户地址",
        )
        self.contact = Contact.objects.create(
            customer=self.customer,
            name="原始联系人",
            phone="+49 111",
            email="original@example.com",
            is_primary=True,
        )
        self.category = ProductCategory.objects.create(name="快照旧分类")
        self.product = Product.objects.create(code="P-FORMAL-SNAPSHOT", name="快照产品", category=self.category)
        self.sku = SKU.objects.create(product=self.product, sku="SKU-FORMAL-SNAPSHOT", default_price="10")
        self.supplier = Supplier.objects.create(
            code="FS",
            name="供应商 S 原始名称",
            country="Germany",
            address="原始供应商地址",
            contact_name="供应商原始联系人",
            phone="+86 111",
            email="supplier-original@example.com",
        )

    def _order(self, *, quote=None, order_no="SO-FORMAL-SNAPSHOT"):
        order = Order.objects.create(
            order_no=order_no,
            customer=self.customer,
            quote=quote,
            order_date=self.day,
            currency="USD",
            exchange_rate="1",
        )
        OrderItem.objects.create(order=order, sku=self.sku, quantity="2", unit_price="10")
        return order

    def _purchase(self, purchase_no="PO-FORMAL-SNAPSHOT"):
        purchase = PurchaseOrder.objects.create(
            purchase_no=purchase_no,
            supplier=self.supplier,
            order_date=self.day,
            currency="USD",
            exchange_rate="1",
        )
        PurchaseOrderItem.objects.create(purchase_order=purchase, sku=self.sku, quantity="2", unit_price="4")
        return purchase

    def test_confirmed_order_freezes_quote_party_fields_and_is_not_overwritten_by_master_edit(self):
        quote = Quote.objects.create(
            quote_no="SJ20261021DE901",
            customer=self.customer,
            quote_date=self.day,
            buyer_company_name="报价中的交易主体",
            recipient_name="报价联系人",
            buyer_address="报价地址",
            buyer_phone="+49 222",
            buyer_email="quote@example.com",
        )
        quote.items.create(sku=self.sku, quantity="2", unit_price="10")
        order = self._order(quote=quote)

        with patch("crm.services.order_lifecycle.allocate_order"):
            confirm_order(order)

        order.refresh_from_db()
        self.assertEqual(order.status, "confirmed")
        self.assertEqual(order.customer_name_snapshot, "报价中的交易主体")
        self.assertEqual(order.customer_country_snapshot, "Germany")
        item = order.items.get()
        self.assertEqual(item.product_category_reference_snapshot, str(self.category.pk))
        self.assertEqual(item.product_category_name_snapshot, "快照旧分类")
        self.assertEqual(order.customer_address_snapshot, "报价地址")
        self.assertEqual(order.customer_contact_name_snapshot, "报价联系人")
        self.assertEqual(order.customer_phone_snapshot, "+49 222")
        self.assertEqual(order.customer_email_snapshot, "quote@example.com")

        self.customer.name = "客户 A 新名称"
        self.customer.country = "France"
        self.customer.address = "客户新地址"
        self.contact.name = "新联系人"
        self.contact.phone = "+49 333"
        self.contact.email = "new@example.com"
        self.customer.save(update_fields=["name", "country", "address"])
        self.contact.save(update_fields=["name", "phone", "email"])
        order.refresh_from_db()

        self.assertEqual(order.customer_name_snapshot, "报价中的交易主体")
        self.assertEqual(order.customer_country_snapshot, "Germany")
        self.assertEqual(order.customer_address_snapshot, "报价地址")
        self.assertEqual(order.customer_contact_name_snapshot, "报价联系人")
        self.assertEqual(order.customer_phone_snapshot, "+49 222")
        self.assertEqual(order.customer_email_snapshot, "quote@example.com")
        self.assertEqual(order.items.get().product_category_name_snapshot, "快照旧分类")

        new_category = ProductCategory.objects.create(name="快照新分类")
        self.product.category = new_category
        self.product.save(update_fields=["category"])
        self.assertEqual(order.items.get().product_category_name_snapshot, "快照旧分类")
        with self.assertRaises(ValidationError):
            item.product_category_name_snapshot = "快照新分类"
            item.save(update_fields=["product_category_name_snapshot"])

        new_order = self._order(order_no="SO-FORMAL-NEW-CATEGORY")
        with patch("crm.services.order_lifecycle.allocate_order"):
            confirm_order(new_order)
        new_order.refresh_from_db()
        self.assertEqual(new_order.items.get().product_category_name_snapshot, "快照新分类")
        self.assertEqual(new_order.customer_country_snapshot, "France")
        serialized = OrderSerializer(order).data
        self.assertEqual(serialized["customer_name"], "客户 A 新名称")
        self.assertEqual(serialized["customer_name_snapshot"], "报价中的交易主体")

    def test_confirmed_order_without_quote_uses_current_customer_contact_once(self):
        order = self._order(order_no="SO-FORMAL-NO-QUOTE")

        with patch("crm.services.order_lifecycle.allocate_order"):
            confirm_order(order)

        order.refresh_from_db()
        self.assertEqual(order.customer_name_snapshot, "客户 A 原始名称")
        self.assertEqual(order.customer_country_snapshot, "Germany")
        self.assertEqual(order.customer_address_snapshot, "原始客户地址")
        self.assertEqual(order.customer_contact_name_snapshot, "原始联系人")
        self.assertEqual(order.customer_phone_snapshot, "+49 111")
        self.assertEqual(order.customer_email_snapshot, "original@example.com")

    def test_confirmed_purchase_freezes_supplier_party_fields_and_supplier_address_is_editable(self):
        purchase = self._purchase()
        response = SupplierSerializer(self.supplier, data={"address": "资料编辑后的地址"}, partial=True)
        self.assertTrue(response.is_valid(), response.errors)
        response.save()
        purchase.refresh_from_db()
        self.assertEqual(purchase.status, "draft")

        # The address change is made before placement and therefore is the
        # actual supplier data used by the formal purchase order.
        with patch("crm.services.purchase_lifecycle.ensure_default_payment_plans"):
            place_purchase_order(purchase)
        purchase.refresh_from_db()
        self.assertEqual(purchase.status, "ordered")
        self.assertEqual(purchase.supplier_name_snapshot, "供应商 S 原始名称")
        self.assertEqual(purchase.supplier_address_snapshot, "资料编辑后的地址")
        self.assertEqual(purchase.supplier_contact_name_snapshot, "供应商原始联系人")
        self.assertEqual(purchase.supplier_phone_snapshot, "+86 111")
        self.assertEqual(purchase.supplier_email_snapshot, "supplier-original@example.com")
        self.assertEqual(purchase.supplier_country_snapshot, "Germany")
        item = purchase.items.get()
        self.assertEqual(item.product_category_reference_snapshot, str(self.category.pk))
        self.assertEqual(item.product_category_name_snapshot, "快照旧分类")

        self.supplier.name = "供应商 S 新名称"
        self.supplier.country = "France"
        self.supplier.address = "供应商新地址"
        self.supplier.contact_name = "供应商新联系人"
        self.supplier.phone = "+86 222"
        self.supplier.email = "supplier-new@example.com"
        self.supplier.save(update_fields=["name", "country", "address", "contact_name", "phone", "email"])
        purchase.refresh_from_db()

        self.assertEqual(purchase.supplier_name_snapshot, "供应商 S 原始名称")
        self.assertEqual(purchase.supplier_address_snapshot, "资料编辑后的地址")
        self.assertEqual(purchase.supplier_contact_name_snapshot, "供应商原始联系人")
        self.assertEqual(purchase.supplier_phone_snapshot, "+86 111")
        self.assertEqual(purchase.supplier_email_snapshot, "supplier-original@example.com")
        self.assertEqual(purchase.supplier_country_snapshot, "Germany")
        self.assertEqual(purchase.items.get().product_category_name_snapshot, "快照旧分类")
        serialized = PurchaseOrderSerializer(purchase).data
        self.assertEqual(serialized["supplier_name"], "供应商 S 新名称")
        self.assertEqual(serialized["supplier_name_snapshot"], "供应商 S 原始名称")

    def test_formal_snapshot_fields_are_read_only_and_legacy_unknown_stays_unknown(self):
        order = self._order(order_no="SO-FORMAL-LEGACY")
        order.status = "confirmed"
        order.save(update_fields=["status"])
        order.refresh_from_db()
        serializer = OrderSerializer(order, data={"customer_name_snapshot": "伪造历史名称"}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        order.refresh_from_db()
        self.assertEqual(order.customer_name_snapshot, "")

        purchase = self._purchase("PO-FORMAL-LEGACY")
        purchase.status = "ordered"
        purchase.save(update_fields=["status"])
        purchase.refresh_from_db()
        serializer = PurchaseOrderSerializer(purchase, data={"supplier_name_snapshot": "伪造历史名称"}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        purchase.refresh_from_db()
        self.assertEqual(purchase.supplier_name_snapshot, "")

        self.customer.name = "当前客户主档名称"
        self.customer.save(update_fields=["name"])
        self.supplier.name = "当前供应商主档名称"
        self.supplier.save(update_fields=["name"])
        order_data = OrderSerializer(order).data
        purchase_data = PurchaseOrderSerializer(purchase).data
        self.assertEqual(order_data["customer_name_snapshot"], "")
        self.assertEqual(purchase_data["supplier_name_snapshot"], "")
        self.assertEqual(order_data["customer_name"], "当前客户主档名称")
        self.assertEqual(purchase_data["supplier_name"], "当前供应商主档名称")

    @override_settings(APP_STAGE="production", DEBUG=False, DEVELOPMENT_SUPERADMIN=False, RBAC_ENFORCEMENT=True)
    def test_party_snapshots_are_redacted_without_customer_or_supplier_view_permission(self):
        order = self._order(order_no="SO-FORMAL-REDACT")
        order.customer_name_snapshot = "历史客户主体"
        order.save(update_fields=["customer_name_snapshot"])
        purchase = self._purchase("PO-FORMAL-REDACT")
        purchase.supplier_name_snapshot = "历史供应商主体"
        purchase.save(update_fields=["supplier_name_snapshot"])

        order_data = OrderSerializer(order, context={"user": AnonymousUser()}).data
        purchase_data = PurchaseOrderSerializer(purchase, context={"user": AnonymousUser()}).data
        self.assertEqual(order_data["customer_name_snapshot"], "")
        self.assertEqual(order_data["customer_name"], "")
        self.assertEqual(purchase_data["supplier_name_snapshot"], "")
        self.assertEqual(purchase_data["supplier_name"], "")
