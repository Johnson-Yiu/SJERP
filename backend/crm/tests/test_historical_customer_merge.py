from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection, connections
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework.test import APIClient
from rest_framework.exceptions import ValidationError

from crm.tests.test_history_takeover import HistoryTakeoverFixtureMixin
from crm.models import Customer, CustomerMergeEvent, Order, Transaction
from crm.party_document_details_models import PartyDocumentDetailsStorage


class HistoricalCustomerTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(username="synthetic-admin")
        self.client.force_authenticate(self.user)
        self.endpoint = "/api/customers/history-customers/"

    def test_preview_merge_and_undo(self):
        payload = {"names": ["张三", "广州张三"]}
        self.assertEqual(self.client.post(self.endpoint, payload, format="json").status_code, 200)
        self.assertFalse(Customer.objects.exists())
        payload["confirm"] = True
        for _ in range(2):
            self.assertEqual(self.client.post(self.endpoint, payload, format="json").status_code, 200)
        source, target = Customer.objects.order_by("pk")
        for customer in [source, target]:
            Order.objects.create(customer=customer, customer_name_snapshot=customer.name, order_no=customer.code,
                                 order_date="2026-01-01", historical_only=True, status="historical")
        formal = Order.objects.create(customer=source, customer_name_snapshot="合同签约主体", order_no="formal",
                                      order_date="2026-01-01", status="draft", shipping_fee=17)
        PartyDocumentDetailsStorage.objects.create(order=formal, details={"signed_name": "合同签约主体"})
        formal.status = "confirmed"
        formal.save(update_fields=["status"])
        Transaction.objects.create(transaction_no="receipt", customer=source, order=formal, transaction_date="2026-01-03",
                                   direction="income", category="货款", amount="17.00", currency="USD")
        finance_before = list(Transaction.objects.values())
        documents_before = list(PartyDocumentDetailsStorage.objects.values())
        before = list(Order.objects.order_by("pk").values())
        url = f"/api/customers/{source.pk}/merge/"
        data = {"target": target.pk, "reason": "已核对合成凭证"}
        self.assertEqual(self.client.post(url, data).status_code, 200)
        self.assertEqual(self.client.post(url, data).status_code, 400)
        response = self.client.get("/api/customers/", {"search": source.code})
        self.assertEqual(response.status_code, 200)
        results = response.data["results"] if isinstance(response.data, dict) else response.data
        self.assertEqual([row["id"] for row in results], [target.pk])
        self.assertEqual(results[0]["order_count"], 1)
        self.assertEqual(float(results[0]["sales_amount"]), 17)
        with self.assertRaises(ValidationError):
            Order.objects.create(customer=source, order_no="invalid", order_date="2026-01-02")
        self.assertEqual(self.client.post(f"/api/customers/{target.pk}/merge/", {"target": source.pk, "reason": "环"}).status_code, 400)
        self.assertEqual(self.client.post(url, {"target": source.pk, "reason": "自身"}).status_code, 400)
        self.assertEqual(list(Transaction.objects.values()), finance_before)
        self.assertEqual(list(PartyDocumentDetailsStorage.objects.values()), documents_before)
        report = self.client.get("/api/reports/historical/", {"date_from": "2026-01-01", "date_to": "2026-01-31"})
        self.assertEqual(report.status_code, 200, report.data)
        self.assertEqual([(row["id"], row["count"]) for row in report.data["sales"]["by_customer"]], [(target.pk, 2)])
        self.assertEqual(list(Order.objects.order_by("pk").values()), before)
        self.assertEqual(self.client.post(self.endpoint, payload, format="json").data[0]["code"], target.code)
        self.assertEqual(self.client.post(url, dict(data, undo=True), format="json").status_code, 200)
        self.assertEqual(list(CustomerMergeEvent.objects.order_by("pk").values_list("merged", flat=True)), [True, False])

    def test_failed_event_rolls_back(self):
        source = Customer.objects.create(name="来源", code="S")
        target = Customer.objects.create(name="主客户", code="T")
        with patch.object(CustomerMergeEvent.objects, "create", side_effect=RuntimeError("rollback")):
            with self.assertRaises(RuntimeError):
                self.client.post(f"/api/customers/{source.pk}/merge/", {"target": target.pk, "reason": "测试"})
        source.refresh_from_db()
        self.assertIsNone(source.merged_into_id)

    @override_settings(APP_STAGE="staging", DEVELOPMENT_SUPERADMIN=False, RBAC_ENFORCEMENT=True)
    def test_unprivileged_user_cannot_merge_or_create(self):
        source = Customer.objects.create(name="受限来源", code="X")
        target = Customer.objects.create(name="受限主档", code="Y")
        self.client.force_authenticate(get_user_model().objects.create_user(username="restricted"))
        self.assertEqual(self.client.post(f"/api/customers/{source.pk}/merge/", {"target": target.pk, "reason": "测试"}).status_code, 403)
        self.assertEqual(self.client.post(self.endpoint, {"names": ["受限"], "confirm": True}, format="json").status_code, 403)
        self.assertFalse(CustomerMergeEvent.objects.exists())


class TakeoverCustomerTests(HistoryTakeoverFixtureMixin, TestCase):
    def test_group_confirmation_rechecks_and_maps_multiple_source_rows(self):
        rows = self.source_rows()
        first = rows["销售订单"][0]
        first.update(customer_code="OLD-A", customer_name_snapshot="张三")
        rows["销售订单"].append(dict(first, source_record_id="OTHER", order_no="OTHER", customer_code="OLD-B", customer_name_snapshot="广州张三"))
        app, group, _ = self.application_and_group(rows)
        endpoint = f"/api/import/history-takeovers/{app.pk}/groups/{group.pk}/history-customers/"
        payload = {"names": ["张三", "广州张三"]}
        self.assertEqual(self.client.post(endpoint, payload, format="json").status_code, 200)
        self.assertFalse(Customer.objects.filter(history_pending=True).exists())
        result = self.client.post(endpoint, dict(payload, confirm=True), format="json")
        self.assertEqual(result.status_code, 200, result.data)
        group.refresh_from_db()
        self.assertEqual(group.resolution_map["销售订单:2:customer_code"], result.data[0]["code"])
        self.assertEqual(group.resolution_map["销售订单:3:customer_code"], result.data[1]["code"])
        self.assertEqual(group.source_rows["销售订单"][0]["data"]["customer_code"], "OLD-A")


class ConcurrentCustomerMergeTests(TransactionTestCase):
    @skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL row locks")
    def test_opposite_requests_only_commit_one_edge(self):
        operator = get_user_model().objects.create_superuser(username="parallel-merge")
        first = Customer.objects.create(name="一号合成客户", code="C1")
        second = Customer.objects.create(name="二号合成客户", code="C2")
        start = Barrier(2)

        def merge(source, target):
            close_old_connections()
            try:
                client = APIClient()
                client.force_authenticate(operator)
                start.wait(timeout=10)
                return client.post(f"/api/customers/{source.pk}/merge/", {"target": target.pk, "reason": "并发核对"}).status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [pool.submit(merge, first, second), pool.submit(merge, second, first)]
            self.assertEqual(sorted(job.result(timeout=30) for job in jobs), [200, 400])
        self.assertEqual(CustomerMergeEvent.objects.count(), 1)
        self.assertEqual(Customer.objects.filter(merged_into__isnull=False).count(), 1)
