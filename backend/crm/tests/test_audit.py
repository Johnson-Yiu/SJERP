from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings

from crm.audit import record_operation
from crm.models import Customer, OperationLog


class AuditTrailTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="beta-user", password="secret")
        self.customer = Customer.objects.create(name="审计测试客户", code="AUDIT001")
        self.request = RequestFactory().post("/api/customers/")
        self.request.user = self.user

    @override_settings(AUDIT_LOG_ENABLED=False)
    def test_development_mode_does_not_record_operations(self):
        record_operation(request=self.request, instance=self.customer, action="create")
        self.assertFalse(OperationLog.objects.exists())

    @override_settings(AUDIT_LOG_ENABLED=True)
    def test_authenticated_operator_records_operation_with_snapshot(self):
        record_operation(request=self.request, instance=self.customer, action="custom", action_label="测试操作", metadata={"source": "test"})
        row = OperationLog.objects.get()
        self.assertEqual(row.operator, self.user)
        self.assertEqual(row.entity, "crm.customer")
        self.assertEqual(row.object_id, str(self.customer.id))
        self.assertEqual(row.action_label, "测试操作")
        self.assertEqual(row.after_data["name"], "审计测试客户")
        self.assertEqual(row.metadata["source"], "test")
