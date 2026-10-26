from django.contrib.auth import get_user_model
from django.contrib.admin import site
from django.core.exceptions import ValidationError
from django.db import DatabaseError, connection, transaction
from django.test import RequestFactory, TestCase, override_settings
from rest_framework.test import APIClient

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

    @override_settings(AUDIT_LOG_ENABLED=True)
    def test_application_orm_cannot_mutate_or_delete_historical_rows(self):
        record_operation(request=self.request, instance=self.customer, action="custom", action_label="原始审计")
        row = OperationLog.objects.get()
        row.action_label = "篡改后的审计"
        with self.assertRaises(ValidationError):
            row.save()
        with self.assertRaises(ValidationError):
            row.delete()
        with self.assertRaises(ValidationError):
            OperationLog.objects.filter(pk=row.pk).update(action_label="批量篡改")
        with self.assertRaises(ValidationError):
            OperationLog.objects.filter(pk=row.pk).delete()
        row.refresh_from_db()
        self.assertEqual(row.action_label, "原始审计")

    def test_admin_is_read_only_even_for_superuser(self):
        admin_instance = site._registry[OperationLog]
        request = RequestFactory().get("/admin/crm/operationlog/")
        request.user = get_user_model().objects.create_superuser("audit-admin", "audit@example.com", "secret")
        self.assertFalse(admin_instance.has_add_permission(request))
        self.assertFalse(admin_instance.has_change_permission(request))
        self.assertFalse(admin_instance.has_delete_permission(request))

    @override_settings(AUDIT_LOG_ENABLED=True)
    def test_api_exposes_only_read_methods(self):
        record_operation(request=self.request, instance=self.customer, action="custom", action_label="只读验证")
        row = OperationLog.objects.get()
        client = APIClient()
        client.force_authenticate(self.user)
        self.assertEqual(client.post("/api/operation-logs/", {}, format="json").status_code, 405)
        self.assertEqual(client.patch(f"/api/operation-logs/{row.pk}/", {}, format="json").status_code, 405)
        self.assertEqual(client.delete(f"/api/operation-logs/{row.pk}/").status_code, 405)

    @override_settings(AUDIT_LOG_ENABLED=True)
    def test_audit_row_rolls_back_with_business_transaction(self):
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                record_operation(request=self.request, instance=self.customer, action="custom", action_label="应回滚")
                raise RuntimeError("rollback probe")
        self.assertFalse(OperationLog.objects.filter(action_label="应回滚").exists())

    @override_settings(AUDIT_LOG_ENABLED=True)
    def test_postgres_trigger_rejects_raw_update_and_delete(self):
        if connection.vendor != "postgresql":
            self.skipTest("requires a PostgreSQL database; SQLite cannot prove the production DB guard")
        record_operation(request=self.request, instance=self.customer, action="custom", action_label="数据库保护")
        table = connection.ops.quote_name(OperationLog._meta.db_table)
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(f"UPDATE {table} SET action_label = %s WHERE id = %s", ["原始审计被改写", OperationLog.objects.get().pk])
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(f"DELETE FROM {table} WHERE id = %s", [OperationLog.objects.get().pk])
        self.assertEqual(OperationLog.objects.count(), 1)
