from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
import unittest
from unittest.mock import patch

from django.db import DatabaseError, close_old_connections, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework.test import APIClient

from crm.models import CashDuplicateReview, RmbCashEvent
from crm.services.finance import record_transaction
from crm.services.cash_events import actor
from crm.tests.test_cash_events import ACCOUNTS, URL, CashFixture, CashPermissionsTests, payload


@override_settings(RMB_CASH_ACCOUNT_IDS=ACCOUNTS)
class DuplicateReviewTests(CashFixture, TestCase):
    def setUp(self):
        self.setup_cash()

    def second_source(self):
        return record_transaction(dict(transaction_no="DUP-OTHER", kind="other_income", direction="income", category="合成", amount="100", currency="USD", exchange_rate="7"))

    def test_distinct_keys_sources_and_review_with_missing_evidence(self):
        first = self.register(payload([self.receipt], key="DUP-FIRST", bank_counterparty="合成甲", bank_summary="合成摘要", bank_transaction_id="SYNTH-1"))
        self.confirm(first)
        p = payload([self.second_source()], key="DUP-SECOND")
        preview = self.client.post(URL + "preview/", p, format="json")
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.data["duplicate_candidates"]["count"], 1)
        self.assertEqual(preview.data["duplicate_candidates"]["items"][0]["bank_counterparty"], "合成甲")
        second = self.register(p)
        self.confirm(second, 409)
        candidates = self.client.get(f"{URL}{second}/duplicate-candidates/").data
        result = self.client.post(f"{URL}{second}/confirm/", {"voucher_checked": True, "duplicate_token": candidates["token"], "duplicate_reason": "核对银行凭证为另一笔交易"}, format="json")
        self.assertEqual(result.status_code, 200, result.data)
        review = CashDuplicateReview.objects.get(event_id=second)
        self.assertEqual(review.candidate_ids, [first])
        self.assertEqual(review.actor["kind"], "development_superadmin")
        self.assertEqual(RmbCashEvent.objects.get(pk=second).bank_counterparty, "")
        self.assertEqual(RmbCashEvent.objects.filter(status="confirmed").count(), 2)
        self.confirm(second)
        self.assertEqual(CashDuplicateReview.objects.count(), 1)

    def test_release_failure_rolls_back_confirmation(self):
        first = self.register(payload([self.receipt], key="ROLL-FIRST"))
        self.confirm(first)
        second = self.register(payload([self.second_source()], key="ROLL-SECOND"))
        candidates = self.client.get(f"{URL}{second}/duplicate-candidates/").data
        with patch("crm.services.cash_events.CashDuplicateReview.objects.create", side_effect=RuntimeError("audit failed")):
            with self.assertRaises(RuntimeError):
                self.client.post(f"{URL}{second}/confirm/", {"voucher_checked": True, "duplicate_token": candidates["token"], "duplicate_reason": "不同交易"}, format="json")
        self.assertEqual(RmbCashEvent.objects.get(pk=second).status, "pending")
        self.assertFalse(CashDuplicateReview.objects.exists())

    def test_stale_candidate_token_rejected(self):
        first = self.register(payload([self.receipt], key="STALE-A"))
        second = self.register(payload([self.second_source()], key="STALE-B"))
        token = self.client.get(f"{URL}{second}/duplicate-candidates/").data["token"]
        self.confirm(first)
        self.confirm(second, 409, voucher_checked=True, duplicate_token=token, duplicate_reason="核实为不同交易")
        self.assertEqual(RmbCashEvent.objects.get(pk=second).status, "pending")
        self.assertFalse(CashDuplicateReview.objects.exists())

    def test_authenticated_actor_is_not_development_identity(self):
        user = get_user_model().objects.create_user(username="synthetic-auditor")
        self.assertEqual(actor(user, "release_duplicate_candidate"), {"kind": "authenticated_user", "action": "release_duplicate_candidate", "user_id": user.pk})
        self.client.force_authenticate(user)
        first = self.register(payload([self.receipt], key="AUTH-A"))
        self.confirm(first)
        second = self.register(payload([self.second_source()], key="AUTH-B"))
        token = self.client.get(f"{URL}{second}/duplicate-candidates/").data["token"]
        self.confirm(second, voucher_checked=True, duplicate_token=token, duplicate_reason="不同银行交易")
        self.assertEqual(CashDuplicateReview.objects.get(event_id=second).actor["user_id"], user.pk)

    def test_matching_bank_identifier_warns_even_on_another_date(self):
        first = self.register(payload([self.receipt], key="ID-A", bank_transaction_id="SYNTH-BANK-ID"))
        self.confirm(first)
        second = self.register(payload([self.second_source()], key="ID-B", bank_date="2026-10-19", bank_transaction_id="SYNTH-BANK-ID"))
        candidates = self.client.get(f"{URL}{second}/duplicate-candidates/").data
        self.assertEqual([item["id"] for item in candidates["items"]], [first])
        self.confirm(second, 409)

    def test_failure_after_review_insert_rolls_back_review_and_event(self):
        first = self.register(payload([self.receipt], key="ROLL-SAVE-A"))
        self.confirm(first)
        second = self.register(payload([self.second_source()], key="ROLL-SAVE-B"))
        token = self.client.get(f"{URL}{second}/duplicate-candidates/").data["token"]
        with patch.object(RmbCashEvent, "save", side_effect=RuntimeError("event save failed")):
            with self.assertRaises(RuntimeError):
                self.client.post(f"{URL}{second}/confirm/", {"voucher_checked": True, "duplicate_token": token, "duplicate_reason": "不同交易"}, format="json")
        self.assertEqual(RmbCashEvent.objects.get(pk=second).status, "pending")
        self.assertFalse(CashDuplicateReview.objects.exists())


class DuplicatePermissionTests(CashPermissionsTests):
    def test_release_requires_update_permission(self):
        from crm.models import RolePermission
        self.client.force_authenticate(self.all_user.user)
        p = payload([self.receipts[0]], key="PERM-DUP", currency="CNY", kind="cny_direct", bank_net_amount="10", fee_mode="none", fee_amount="0", quoted_rate=None)
        response = self.client.post(URL, p, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        pk = response.data["id"]
        self.client.force_authenticate(self.employee_a.user)
        RolePermission.objects.filter(role=self.roles["self"], module="finance").update(can_update=False)
        response = self.client.post(f"{URL}{pk}/confirm/", {"voucher_checked": True, "duplicate_token": "x", "duplicate_reason": "不同交易"}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(CashDuplicateReview.objects.exists())


@override_settings(RMB_CASH_ACCOUNT_IDS=ACCOUNTS)
class DuplicateMigrationTests(CashFixture, TransactionTestCase):
    def test_reverse_refuses_existing_audit_and_preserves_row(self):
        self.setup_cash()
        pk = self.register(payload([self.receipt], key="MIGRATION-REVIEW"))
        review = CashDuplicateReview.objects.create(event_id=pk, candidate_ids=[123], reason="合成核实", actor={"kind": "development_superadmin"})
        executor = MigrationExecutor(connection)
        try:
            with self.assertRaisesRegex(RuntimeError, "Refusing to remove duplicate review audit history"):
                executor.migrate([("crm", "0095_merge_fulfillment_idempotency")])
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
        self.assertEqual(CashDuplicateReview.objects.get(pk=review.pk).reason, "合成核实")


@unittest.skipUnless(connection.vendor == "postgresql", "Real PostgreSQL required")
@override_settings(RMB_CASH_ACCOUNT_IDS=ACCOUNTS)
class DuplicateConcurrencyTests(CashFixture, TransactionTestCase):
    def setUp(self):
        self.setup_cash()

    def test_distinct_sources_same_bank_fact_serialize(self):
        other = record_transaction(dict(transaction_no="DUP-PG-OTHER", kind="other_income", direction="income", category="合成", amount="100", currency="USD", exchange_rate="7"))
        ids = [self.register(payload([self.receipt], key="DUP-PG-A")), self.register(payload([other], key="DUP-PG-B"))]
        barrier = Barrier(2)
        def confirm(pk):
            close_old_connections()
            try:
                client = APIClient()
                barrier.wait(timeout=20)
                response = client.post(f"{URL}{pk}/confirm/", {"voucher_checked": True}, format="json")
                return response.status_code
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(confirm, ids))
        self.assertEqual(sorted(results), [200, 409])
        self.assertEqual(RmbCashEvent.objects.filter(pk__in=ids, status="confirmed").count(), 1)
        self.assertEqual(RmbCashEvent.objects.filter(pk__in=ids, status="pending").count(), 1)
        self.assertEqual(CashDuplicateReview.objects.count(), 0)

    def test_same_bank_identifier_different_dates_serializes(self):
        other = record_transaction(dict(transaction_no="DUP-ID-OTHER", kind="other_income", direction="income", category="合成", amount="100", currency="USD", exchange_rate="7"))
        ids = [self.register(payload([self.receipt], key="DUP-ID-A", bank_transaction_id="SYNTH-ID")), self.register(payload([other], key="DUP-ID-B", bank_date="2026-10-19", bank_transaction_id="SYNTH-ID"))]
        barrier = Barrier(2)
        def confirm(pk):
            close_old_connections()
            try:
                barrier.wait(timeout=20)
                return APIClient().post(f"{URL}{pk}/confirm/", {"voucher_checked": True}, format="json").status_code
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(confirm, ids)), [200, 409])
        self.assertEqual(RmbCashEvent.objects.filter(pk__in=ids, status="confirmed").count(), 1)

    def test_postgres_rejects_raw_update_delete_and_truncate_of_review(self):
        pk = self.register(payload([self.receipt], key="DUP-IMMUTABLE"))
        review = CashDuplicateReview.objects.create(event_id=pk, candidate_ids=[123], reason="合成核实", actor={"kind": "development_superadmin"})
        for sql in ("UPDATE crm_cashduplicatereview SET reason = 'changed' WHERE id = %s", "DELETE FROM crm_cashduplicatereview WHERE id = %s"):
            with self.assertRaises(DatabaseError), transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(sql, [review.pk])
        self.assertEqual(CashDuplicateReview.objects.get(pk=review.pk).reason, "合成核实")
        with self.assertRaises(DatabaseError), transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("TRUNCATE TABLE crm_cashduplicatereview CASCADE")
        self.assertEqual(CashDuplicateReview.objects.get(pk=review.pk).reason, "合成核实")
