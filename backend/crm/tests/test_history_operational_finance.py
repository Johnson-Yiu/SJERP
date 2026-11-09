import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections, connection, connections
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework.exceptions import APIException

from crm import history_operational_finance as bridge, history_takeover
from crm.models import FinanceFact, FinanceInstruction, HistoryTakeoverEvent, HistoryTakeoverSourceRecord
from crm.services import finance_closeout
from crm.tests.test_history_takeover import HistoryTakeoverFixtureMixin


@override_settings(AUDIT_LOG_ENABLED=True)
class HistoricalFinanceBridgeTests(HistoryTakeoverFixtureMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.application, self.group, _ = self.application_and_group()
        review = self.client.post(
            f"/api/import/history-takeovers/{self.application.pk}/groups/{self.group.pk}/review/",
            {"decision": "approve", "note": "Verified synthetic source and voucher references.", "confirm_manual": True}, format="json")
        self.assertEqual(review.status_code, 200, review.data)
        result = self.client.post(
            f"/api/import/history-takeovers/{self.application.pk}/groups/{self.group.pk}/execute/", {}, format="json")
        self.assertEqual(result.status_code, 200, result.data)
        self.source = HistoryTakeoverSourceRecord.objects.get(group=self.group, record_type="收付款流水", source_record_id="TX-SO-1")
        self.maker = get_user_model().objects.create_superuser(username="history-finance-bridge-maker", password="test-only")
        self.reviewer = get_user_model().objects.create_superuser(username="history-finance-bridge-reviewer", password="test-only")
        self.temp_media = tempfile.TemporaryDirectory(prefix="history-operational-finance-")
        self.addCleanup(self.temp_media.cleanup)
        self.media_override = override_settings(MEDIA_ROOT=self.temp_media.name)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.account = finance_closeout.create_account({"code": "HIST-BRIDGE", "name": "合成账户", "account_type": "bank", "ownership": "own", "ownership_reason": "合成凭证"}, self.maker)
        self.voucher = finance_closeout.upload(SimpleUploadedFile("synthetic.pdf", b"%PDF-1.4\nsynthetic\n%%EOF"), self.maker)
        self.mapping = {"account": self.account.pk, "voucher": self.voucher.pk, "actual_date": "2024-09-03", "amount": "287.43", "reason": "核对合成银行凭证"}

    def test_explicit_amount_review_post_and_idempotent_replay(self):
        instruction, created = bridge.submit_source(self.group.pk, self.source.pk, self.mapping, self.maker)
        self.assertTrue(created)
        replay, created = bridge.submit_source(self.group.pk, self.source.pk, self.mapping, self.maker)
        self.assertFalse(created)
        self.assertEqual(replay.pk, instruction.pk)
        with self.assertRaises(APIException):
            bridge.submit_source(self.group.pk, self.source.pk, {**self.mapping, "amount": "287.44"}, self.maker)
        with self.assertRaises(APIException):
            finance_closeout.post(instruction.pk, self.maker, voucher_checked=True)
        with self.assertRaises(APIException):
            bridge.advance_source(self.group.pk, self.source.pk, "approve", self.maker)
        bridge.advance_source(self.group.pk, self.source.pk, "approve", self.reviewer)
        fact = bridge.advance_source(self.group.pk, self.source.pk, "post", self.maker, voucher_checked=True)
        replay_fact = bridge.advance_source(self.group.pk, self.source.pk, "post", self.maker, voucher_checked=True)
        self.assertEqual(fact.pk, replay_fact.pk)
        self.assertEqual(FinanceFact.objects.count(), 1)
        self.assertEqual(FinanceInstruction.objects.count(), 1)
        self.assertEqual(HistoryTakeoverEvent.objects.filter(group=self.group, event_type="finance_instruction_post").count(), 1)
        self.assertEqual(bridge.source_status(self.group, self.maker)[0]["status"], "posted")
        self.group.refresh_from_db()
        self.assertEqual(self.group.finance_handoff_status, "pending_review")

    def test_duplicate_review_is_required_and_retained_across_history_post(self):
        other = {**self.mapping, "request_key": "other-synthetic", "kind": "cash", "direction": "income",
                 "nature": "unclassified", "truth": "verified", "source_system": "OTHER", "source_key": "OTHER-1", "allocations": []}
        existing, _ = finance_closeout.submit(other, self.maker)
        finance_closeout.post(existing.pk, self.maker, voucher_checked=True)
        candidates = bridge.preview_source(self.group.pk, self.source.pk, self.mapping, self.maker)
        self.assertEqual(len(candidates["items"]), 1)
        self.assertNotIn("OTHER-1", candidates["items"][0]["label"])
        mapping = {**self.mapping, "duplicate_review_token": candidates["token"], "duplicate_review_reason": "凭证核实为另一笔"}
        instruction, created = bridge.submit_source(self.group.pk, self.source.pk, mapping, self.maker)
        self.assertTrue(created)
        replay, created = bridge.submit_source(self.group.pk, self.source.pk, mapping, self.maker)
        self.assertFalse(created)
        self.assertEqual(replay.pk, instruction.pk)
        bridge.advance_source(self.group.pk, self.source.pk, "approve", self.reviewer)
        fact = bridge.advance_source(self.group.pk, self.source.pk, "post", self.maker, voucher_checked=True)
        self.assertEqual(fact.instruction_id, instruction.pk)
        self.assertEqual(FinanceFact.objects.count(), 2)

    def test_new_duplicate_after_preview_blocks_post_without_partial_write(self):
        candidates = bridge.preview_source(self.group.pk, self.source.pk, self.mapping, self.maker)
        self.assertFalse(candidates["items"])
        instruction, _ = bridge.submit_source(self.group.pk, self.source.pk, self.mapping, self.maker)
        bridge.advance_source(self.group.pk, self.source.pk, "approve", self.reviewer)
        other = {**self.mapping, "request_key": "later-synthetic", "kind": "cash", "direction": "income",
                 "nature": "unclassified", "truth": "verified", "source_system": "OTHER", "source_key": "OTHER-2", "allocations": []}
        existing, _ = finance_closeout.submit(other, self.maker)
        finance_closeout.post(existing.pk, self.maker, voucher_checked=True)
        with self.assertRaises(APIException):
            bridge.advance_source(self.group.pk, self.source.pk, "post", self.maker, voucher_checked=True)
        instruction.refresh_from_db()
        self.assertEqual(instruction.status, "approved")
        self.assertFalse(FinanceFact.objects.filter(instruction=instruction).exists())

    @override_settings(RMB_CASH_ACCOUNT_IDS=("SYNTH_FX", "SYNTH_CNY"))
    def test_existing_bank_event_links_once_without_reapplying_receivable(self):
        from decimal import Decimal
        from crm.models import FinanceBankFactMatch
        from crm.services import cash_events
        from crm.tests.test_cash_events import CashFixture, payload
        CashFixture.setup_cash(self)
        self.voucher = finance_closeout.upload(SimpleUploadedFile("history.pdf", b"%PDF-1.4\nsynthetic history\n%%EOF"), self.maker)
        mapping = {**self.mapping, "voucher": self.voucher.pk, "actual_date": "2026-10-18", "amount": "700.00"}
        event, _ = cash_events.register_event(payload([self.receipt], key="HIST-LINK", bank_net_amount="700.00", fee_amount="5.00"), self.maker)
        cash_events.confirm_event(event.pk, self.maker, voucher_checked=True)
        finance_closeout.map_account({"account": self.account.pk, "legacy_code": "SYNTH_CNY", "reason": "核对合成账户"}, self.maker)
        self.plan.refresh_from_db()
        settled_before = self.plan.settled_amount
        candidates = bridge.preview_source(self.group.pk, self.source.pk, mapping, self.maker)
        self.assertIn(-event.pk, candidates["ids"])
        mapping.update(duplicate_review_token=candidates["token"], duplicate_review_reason="核对凭证为同一笔", same_legacy_event=event.pk)
        instruction, _ = bridge.submit_source(self.group.pk, self.source.pk, mapping, self.maker)
        bridge.advance_source(self.group.pk, self.source.pk, "approve", self.reviewer)
        fact = bridge.advance_source(self.group.pk, self.source.pk, "post", self.maker, voucher_checked=True)
        self.assertTrue(FinanceBankFactMatch.objects.filter(fact=fact, event=event).exists())
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.settled_amount, settled_before)
        rows = finance_closeout.reporting_events(self.maker, "2026-10-01", "2026-10-31")
        self.assertEqual(sum(row.bank_net_amount for row in rows), Decimal("700"))

    def test_posted_source_correction_preserves_fact_and_auditable_event_link(self):
        instruction, _ = bridge.submit_source(self.group.pk, self.source.pk, self.mapping, self.maker)
        bridge.advance_source(self.group.pk, self.source.pk, "approve", self.reviewer)
        fact = bridge.advance_source(self.group.pk, self.source.pk, "post", self.maker, voucher_checked=True)
        history_takeover.submit_correction(self.group, self.maker, kind="correction", occurred_at="2024-09-03",
            details={"source_id": self.source.pk, "fact_id": fact.pk, "voucher_reference": "synthetic://correction"},
            reason="核对合成更正凭证")
        event = HistoryTakeoverEvent.objects.get(group=self.group, event_type="correction_submitted")
        self.assertEqual(event.details["details"]["source_id"], self.source.pk)
        self.assertEqual(event.details["details"]["fact_id"], fact.pk)
        history_takeover.review_correction(self.group, self.reviewer, event_id=event.pk, decision="approve", note="合成凭证已核对")
        reviewed = HistoryTakeoverEvent.objects.get(group=self.group, event_type="correction_reviewed")
        self.assertEqual(reviewed.details["source_event_id"], event.pk)
        self.assertEqual(FinanceFact.objects.count(), 1)
        self.assertEqual(FinanceInstruction.objects.count(), 1)
        self.assertEqual(bridge.source_status(self.group, self.maker)[0]["fact_id"], fact.pk)
        with self.assertRaises(APIException):
            bridge.submit_source(self.group.pk, self.source.pk, self.mapping, self.maker, replace_id=instruction.pk)
        self.assertEqual(FinanceFact.objects.count(), 1)

    def test_unconfirmed_source_cannot_create_instruction(self):
        source_row = dict(self.source.source_snapshot["resolved"], source_status="pending")
        with patch("crm.history_operational_finance.verified_source", return_value=source_row):
            with self.assertRaisesMessage(APIException, "只有已确认"):
                bridge.submit_source(self.group.pk, self.source.pk, self.mapping, self.maker)
        self.assertFalse(FinanceInstruction.objects.exists())
        self.assertFalse(FinanceFact.objects.exists())

    def test_missing_amount_and_foreign_source_leave_no_instruction(self):
        with self.assertRaises(APIException):
            bridge.submit_source(self.group.pk, self.source.pk, {**self.mapping, "amount": ""}, self.maker)
        with self.assertRaises(APIException):
            bridge.submit_source(self.group.pk, 999999, self.mapping, self.maker)
        self.assertFalse(FinanceInstruction.objects.exists())

    def test_changed_source_does_not_create_finance_instruction(self):
        snapshot = dict(self.source.source_snapshot)
        snapshot["resolved"] = {**snapshot["resolved"], "amount": "99.00"}
        HistoryTakeoverSourceRecord.objects.filter(pk=self.source.pk).update(source_snapshot=snapshot)
        with self.assertRaises(APIException):
            bridge.submit_source(self.group.pk, self.source.pk, self.mapping, self.maker)
        self.assertFalse(FinanceInstruction.objects.exists())

    def test_audit_failure_rolls_back_instruction_and_mapping(self):
        with patch("crm.history_operational_finance._event", side_effect=RuntimeError("audit failure")):
            with self.assertRaisesRegex(RuntimeError, "audit failure"):
                bridge.submit_source(self.group.pk, self.source.pk, self.mapping, self.maker)
        self.assertFalse(FinanceInstruction.objects.exists())
        self.assertNotIn("operational_instructions", self.group.handoffs.get(kind="finance").payload)

    def test_unknown_result_cannot_be_marked_failed_and_revision_replays(self):
        original, _ = bridge.submit_source(self.group.pk, self.source.pk, self.mapping, self.maker)
        with self.assertRaises(APIException):
            bridge.advance_source(self.group.pk, self.source.pk, "fail", self.maker, reason="尚未核实")
        bridge.advance_source(self.group.pk, self.source.pk, "cancel", self.maker, reason="来源信息有误，重新核对")
        replacement_mapping = {**self.mapping, "amount": "287.44", "reason": "更正后的合成银行凭证"}
        revised, created = bridge.submit_source(self.group.pk, self.source.pk, replacement_mapping, self.maker, replace_id=original.pk)
        self.assertTrue(created)
        replay, created = bridge.submit_source(self.group.pk, self.source.pk, replacement_mapping, self.maker, replace_id=original.pk)
        self.assertFalse(created)
        self.assertEqual(replay.pk, revised.pk)
        self.assertEqual(revised.replaces_id, original.pk)
        self.assertEqual(self.group.handoffs.get(kind="finance").payload["operational_history"][str(self.source.pk)], [original.pk, revised.pk])
        self.assertFalse(FinanceFact.objects.exists())

    def test_api_enforces_separate_review_and_permission(self):
        base = f"/api/import/history-takeovers/{self.application.pk}/groups/{self.group.pk}/"
        self.client.force_authenticate(self.maker)
        submitted = self.client.post(base + "finance-submit/", {"source_id": self.source.pk, "mapping": self.mapping}, format="json")
        self.assertEqual(submitted.status_code, 201, submitted.data)
        forbidden_post = self.client.post(base + "finance-post/", {"source_id": self.source.pk, "voucher_checked": True}, format="json")
        self.assertEqual(forbidden_post.status_code, 400, forbidden_post.data)
        self.client.force_authenticate(self.reviewer)
        approved = self.client.post(base + "finance-approve/", {"source_id": self.source.pk}, format="json")
        self.assertEqual(approved.status_code, 200, approved.data)
        self.client.force_authenticate(self.maker)
        posted = self.client.post(base + "finance-post/", {"source_id": self.source.pk, "voucher_checked": True}, format="json")
        self.assertEqual(posted.status_code, 200, posted.data)
        staff = get_user_model().objects.create_user(username="historical-finance-restricted", password="test-only")
        with override_settings(APP_STAGE="production", DEBUG=False, DEVELOPMENT_SUPERADMIN=False, RBAC_ENFORCEMENT=True):
            self.client.force_authenticate(staff)
            denied = self.client.post(base + "finance-status/", {}, format="json")
            self.assertEqual(denied.status_code, 403)


@unittest.skipUnless(connection.vendor == "postgresql", "requires real PostgreSQL row locks")
@override_settings(FILE_UPLOAD_TEMP_DIR=tempfile.gettempdir())
class HistoricalFinancePostgresTests(HistoryTakeoverFixtureMixin, TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.application, self.group, _ = self.application_and_group()
        base = f"/api/import/history-takeovers/{self.application.pk}/groups/{self.group.pk}/"
        reviewed = self.client.post(base + "review/", {"decision": "approve", "note": "核实合成资料", "confirm_manual": True}, format="json")
        self.assertEqual(reviewed.status_code, 200, reviewed.data)
        executed = self.client.post(base + "execute/", {}, format="json")
        self.assertEqual(executed.status_code, 200, executed.data)
        self.source = HistoryTakeoverSourceRecord.objects.get(group=self.group, record_type="收付款流水", source_record_id="TX-SO-1")
        self.maker = get_user_model().objects.create_superuser(username="history-finance-pg-maker", password="test-only")
        self.reviewer = get_user_model().objects.create_superuser(username="history-finance-pg-reviewer", password="test-only")
        self.temp_media = tempfile.TemporaryDirectory(prefix="history-finance-pg-")
        self.addCleanup(self.temp_media.cleanup)
        override = override_settings(MEDIA_ROOT=self.temp_media.name)
        override.enable()
        self.addCleanup(override.disable)
        account = finance_closeout.create_account({"code": "HIST-PG", "name": "合成账户", "account_type": "bank", "ownership": "own", "ownership_reason": "合成数据"}, self.maker)
        voucher = finance_closeout.upload(SimpleUploadedFile("synthetic.pdf", b"%PDF-1.4\nsynthetic\n%%EOF"), self.maker)
        self.mapping = {"account": account.pk, "voucher": voucher.pk, "actual_date": "2024-09-03", "amount": "287.43", "reason": "合成凭证"}

    def _race(self, func):
        gate = Barrier(2)
        def worker(_index):
            close_old_connections()
            try:
                user = get_user_model().objects.get(pk=self.maker.pk)
                gate.wait(timeout=20)
                return func(user)
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(worker, range(2)))

    def test_concurrent_same_source_submission_is_idempotent(self):
        results = self._race(lambda user: bridge.submit_source(self.group.pk, self.source.pk, self.mapping, user)[1])
        self.assertCountEqual(results, [True, False])
        self.assertEqual(FinanceInstruction.objects.count(), 1)
        self.assertEqual(HistoryTakeoverEvent.objects.filter(group=self.group, event_type="finance_instruction_submitted").count(), 1)
        self.assertFalse(FinanceFact.objects.exists())

    def test_concurrent_post_creates_one_fact_and_one_history_event(self):
        bridge.submit_source(self.group.pk, self.source.pk, self.mapping, self.maker)
        bridge.advance_source(self.group.pk, self.source.pk, "approve", self.reviewer)
        ids = self._race(lambda user: bridge.advance_source(self.group.pk, self.source.pk, "post", user, voucher_checked=True).pk)
        self.assertEqual(ids[0], ids[1])
        self.assertEqual(FinanceFact.objects.count(), 1)
        self.assertEqual(HistoryTakeoverEvent.objects.filter(group=self.group, event_type="finance_instruction_post").count(), 1)
