import uuid
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.db import connection, close_old_connections
from django.db.models.deletion import ProtectedError
from django.core.exceptions import ValidationError as ModelValidationError
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from crm.models import (Customer, Contact, FollowUp, NewProductReminder, OperationLog, Product,
    OrganizationUnit, Position, EmployeeProfile, AccessRole, RolePermission)


class ReminderTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(code="REM-A", name="合成客户甲")
        self.other = Customer.objects.create(code="REM-B", name="合成客户乙")
        self.follow = FollowUp.objects.create(customer=self.customer, followed_at=timezone.now(), content="合成沟通")
        self.contact = Contact.objects.create(customer=self.customer, name="合成联系人")
        self.product = Product.objects.create(code="REM-P", name="合成产品")

    def create(self, **changes):
        data = dict(customer=self.customer.pk, requirement="户外壁灯", specification="IP65 3000K", request_key=str(uuid.uuid4()))
        data.update(changes)
        return self.client.post("/api/new-product-reminders/", data, format="json")

    def test_create_reopen_edit_and_mandatory_dev_history(self):
        result = self.create()
        self.assertEqual(result.status_code, 201, result.data)
        obj = NewProductReminder.objects.get()
        self.assertEqual(obj.created_by, "开发超级管理员（非实名员工）")
        self.assertEqual(result.data["tag"], "新品提醒")
        path = f"/api/new-product-reminders/{obj.pk}/"
        self.assertEqual(self.client.get(path).data["specification"], "IP65 3000K")
        result = self.client.patch(path, {"version": 1, "specification": "IP67"}, format="json")
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result.data["version"], 2)
        history = self.client.get(path + "history/").data
        self.assertEqual(len(history), 2)
        self.assertEqual(history[1]["before_data"]["specification"], "IP65 3000K")
        self.assertEqual(history[1]["after_data"]["specification"], "IP67")
        self.assertTrue(all(row.operator_id is None for row in OperationLog.objects.filter(entity="crm.newproductreminder")))

    def test_optional_links_and_cross_customer_rejection(self):
        self.assertEqual(self.create(contact=self.contact.pk, product=self.product.pk, follow_up=self.follow.pk).status_code, 201)
        self.assertEqual(self.create(customer=self.other.pk, contact=self.contact.pk).status_code, 400)
        self.assertEqual(self.create(customer=self.other.pk, follow_up=self.follow.pk).status_code, 400)
        self.assertEqual(self.create(requirement=" ").status_code, 400)
        self.assertEqual(self.create(requirement="x"*12001).status_code, 400)

    def test_idempotency_and_different_payload_conflict(self):
        key = str(uuid.uuid4())
        self.assertEqual(self.create(request_key=key).status_code, 201)
        self.assertEqual(self.create(request_key=key).status_code, 200)
        self.assertEqual(self.create(request_key=key, specification="different").status_code, 409)
        self.assertEqual(NewProductReminder.objects.count(), 1)
        self.assertEqual(OperationLog.objects.filter(entity="crm.newproductreminder").count(), 1)
        self.assertEqual(self.create(request_key="broken").status_code, 400)

    def test_search_multiple_requirements_pagination_tags_and_empty(self):
        for i in range(53):
            self.assertEqual(self.create(specification=f"IP65 {i}").status_code, 201)
        self.create(customer=self.other.pk, specification="IP67")
        result = self.client.get('/api/new-product-reminders/', {"tag":"新品提醒", "search":"壁灯 IP65"}).data
        self.assertEqual(result["count"], 53)
        self.assertEqual(len(result["results"]), 50)
        second = self.client.get('/api/new-product-reminders/', {"tag":"new-product-reminder", "search":"壁灯 IP65", "page":2}).data
        self.assertEqual(len(second["results"]), 3)
        self.assertFalse(set(r["id"] for r in result["results"]) & set(r["id"] for r in second["results"]))
        for params in ({"search":"never-match"}, {"tag":"other"}):
            self.assertEqual(self.client.get('/api/new-product-reminders/', params).data["count"], 0)
        self.assertEqual(self.client.get('/api/new-product-reminders/', {"search":"壁灯"}).data["count"], 54)
        self.assertEqual(self.client.get('/api/new-product-reminders/', {"customer":self.other.pk}).data["count"], 1)

    def test_void_history_state_and_stale_edits(self):
        obj = self.create().data
        path = f'/api/new-product-reminders/{obj["id"]}/'
        self.assertEqual(self.client.post(path+'void/', {"version":1,"reason":" "}, format="json").status_code, 400)
        self.assertEqual(self.client.post(path+'void/', {"version":1,"reason":"客户调整用途"}, format="json").status_code, 200)
        self.assertEqual(self.client.get('/api/new-product-reminders/').data["count"], 0)
        self.assertEqual(self.client.get('/api/new-product-reminders/', {"state":"void"}).data["count"], 1)
        self.assertEqual(self.client.get('/api/new-product-reminders/', {"state":"all"}).data["count"], 1)
        self.assertEqual(self.client.get(path).status_code, 200)
        for version in (1, 2):
            self.assertEqual(self.client.patch(path, {"version":version,"requirement":"变更"}, format="json").status_code, 409)
            self.assertEqual(self.client.post(path+'void/', {"version":version,"reason":"再次"}, format="json").status_code, 409)
        self.assertEqual(len(self.client.get(path+'history/').data), 2)
        self.assertEqual(self.client.post(path+'restore/', {}, format="json").status_code, 404)

    def test_protected_fields_versions_delete_and_links(self):
        obj = self.create(contact=self.contact.pk, product=self.product.pk, follow_up=self.follow.pk).data
        path = f'/api/new-product-reminders/{obj["id"]}/'
        for data in ({"voided_at":None}, {"void_reason":"x"}, {"created_by":"real"}, {"tag":"other"}, {"customer":self.other.pk}):
            self.assertEqual(self.client.patch(path, {"version":1,**data}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(path, {"requirement":"x"}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(path, {"version":1,"requirement":"x"}, format="json").status_code, 200)
        self.assertEqual(self.client.patch(path, {"version":1,"requirement":"stale"}, format="json").status_code, 409)
        self.assertEqual(self.client.delete(path).status_code, 405)
        self.assertEqual(self.client.delete('/api/new-product-reminders/', {"ids":[obj["id"]]}, format="json").status_code, 405)
        self.assertEqual(self.client.post('/api/new-product-reminders/bulk-delete/', {"ids":[obj["id"]]}, format="json").status_code, 405)
        for resource, linked in (("customers", self.customer), ("contacts", self.contact), ("products", self.product), ("follow-ups", self.follow)):
            rejected = self.client.delete(f'/api/{resource}/{linked.pk}/')
            self.assertEqual(rejected.status_code, 400)
            if resource in ('contacts', 'products'):
                self.assertIn('新品提醒', rejected.data['detail'])
        for linked in (self.customer, self.contact, self.product, self.follow):
            with self.assertRaises(ProtectedError):
                linked.delete()
        with self.assertRaises(ModelValidationError):
            NewProductReminder.objects.all().delete()

    def test_audit_failure_rolls_back_create_edit_void(self):
        with patch('crm.new_product_reminders.write_history', side_effect=RuntimeError('audit failure')):
            with self.assertRaises(RuntimeError):
                self.create()
        self.assertEqual(NewProductReminder.objects.count(), 0)
        obj = self.create().data
        path = f'/api/new-product-reminders/{obj["id"]}/'
        for endpoint, data, method in ((path, {"version":1,"requirement":"changed"}, 'patch'), (path+'void/', {"version":1,"reason":"void"}, 'post')):
            with patch('crm.new_product_reminders.OperationLog.objects.create', side_effect=RuntimeError('audit failure')):
                with self.assertRaises(RuntimeError):
                    getattr(self.client, method)(endpoint, data, format='json')
            saved = NewProductReminder.objects.get()
            self.assertEqual(saved.version, 1)
            self.assertIsNone(saved.voided_at)
            self.assertEqual(saved.requirement, '户外壁灯')

    @override_settings(APP_STAGE="production", DEBUG=False, DEVELOPMENT_SUPERADMIN=False, RBAC_ENFORCEMENT=True)
    def test_scope_permissions_lists_detail_search_edit_void_history_and_links(self):
        # Synthetic restricted sessions exist only in this isolated test.
        unit = OrganizationUnit.objects.create(name="合成部门", code="REM-UNIT")
        position = Position.objects.create(unit=unit, name="合成岗位", code="REM-POS")
        role = AccessRole.objects.create(name="合成角色", code="rem-test", default_data_scope="self")
        for module in ("customers", "followups"):
            RolePermission.objects.create(role=role, module=module, can_view=True, can_create=True, can_update=True)
        user = get_user_model().objects.create_user(username="rem-test")
        profile = EmployeeProfile.objects.create(user=user, display_name="合成测试身份", unit=unit, position=position)
        profile.roles.add(role)
        self.customer.owner_profile = profile; self.customer.save()
        own = NewProductReminder.objects.create(customer=self.customer, requirement="shared", created_by="test", contact=self.contact, product=self.product)
        foreign = NewProductReminder.objects.create(customer=self.other, requirement="shared", created_by="test")
        self.assertEqual(self.client.get('/api/new-product-reminders/').status_code, 403)
        self.client.force_authenticate(user)
        for params in ({}, {"search":"shared"}, {"tag":"新品提醒","search":"shared"}):
            data = self.client.get('/api/new-product-reminders/', params).data
            self.assertEqual([r["id"] for r in data["results"]], [own.pk])
            self.assertIsNone(data["results"][0]["contact"])
            self.assertIsNone(data["results"][0]["product"])
        self.assertEqual(self.create(customer=self.other.pk).status_code, 403)
        for suffix, method, data in (("", "get", {}),("history/", "get", {}),("", "patch", {"version":1,"requirement":"bad"}),("void/","post",{"version":1,"reason":"bad"})):
            response = getattr(self.client,method)(f'/api/new-product-reminders/{foreign.pk}/'+suffix,data,format="json")
            self.assertEqual(response.status_code, 404)
        self.assertEqual(self.client.get(f'/api/customers/{self.other.pk}/').status_code, 404)
        self.assertEqual(self.client.get(f'/api/follow-ups/{self.follow.pk}/').status_code, 200)
        RolePermission.objects.filter(role=role,module="followups").update(can_update=False)
        self.assertEqual(self.client.patch(f'/api/new-product-reminders/{own.pk}/', {"version":1,"requirement":"no"},format="json").status_code,403)
        self.assertEqual(self.client.post(f'/api/new-product-reminders/{own.pk}/void/', {"version":1,"reason":"no"},format="json").status_code,403)
        RolePermission.objects.filter(role=role,module="customers").update(can_view=False)
        self.assertEqual(self.client.get('/api/new-product-reminders/').status_code,403)


class ReminderConcurrencyTests(TransactionTestCase):
    def test_postgres_competing_edit_void_and_duplicate(self):
        if connection.vendor != 'postgresql':
            self.skipTest('Requires real PostgreSQL concurrent connections')
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        customer = Customer.objects.create(code="REM-CONCURRENT", name="合成并发客户")
        barrier = Barrier(2)
        key = str(uuid.uuid4())
        payload = {"customer":customer.pk,"requirement":"并发产品","request_key":key}
        def create():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return APIClient().post('/api/new-product-reminders/',payload,format='json').status_code
            finally:
                close_old_connections()
        with ThreadPoolExecutor(2) as pool:
            statuses = list(pool.map(lambda _: create(), range(2)))
        self.assertEqual(sorted(statuses), [200,201])
        obj = NewProductReminder.objects.get()
        self.assertEqual(OperationLog.objects.filter(entity='crm.newproductreminder').count(), 1)
        barrier = Barrier(2)
        def change(void):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                path = f'/api/new-product-reminders/{obj.pk}/'
                return (APIClient().post(path+'void/', {"version":1,"reason":"并发作废"},format='json') if void else APIClient().patch(path,{"version":1,"specification":"并发修改"},format='json')).status_code
            finally:
                close_old_connections()
        with ThreadPoolExecutor(2) as pool:
            statuses = list(pool.map(change, [False,True]))
        self.assertEqual(sorted(statuses), [200,409])
        obj.refresh_from_db()
        self.assertEqual(obj.version, 2)
        self.assertEqual(OperationLog.objects.filter(entity='crm.newproductreminder').count(), 2)
