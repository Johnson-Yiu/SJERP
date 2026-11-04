import copy
import tempfile
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.exceptions import APIException

from crm.models import (
    FinanceFact,
    HistoryTakeoverHandoff,
    HistoryTakeoverSourceRecord,
    InventoryMovement,
    InventoryReservation,
    OperationLog,
    PaymentPlan,
    Transaction,
)
from crm.services import finance_closeout
from crm.tests.test_history_takeover import HistoryTakeoverFixtureMixin


@override_settings(AUDIT_LOG_ENABLED=True)
class HistoryFinanceContractTests(HistoryTakeoverFixtureMixin, TestCase):
    """Exercise the explicit bridge from a real history handoff to finance v1."""

    def _submit_review_execute(self):
        application, group, submission = self.application_and_group()
        review = self.client.post(
            f"/api/import/history-takeovers/{application.pk}/groups/{group.pk}/review/",
            {
                "decision": "approve",
                "note": "Synthetic source workbook and master links reviewed for contract test.",
                "confirm_manual": True,
            },
            format="json",
        )
        self.assertEqual(review.status_code, 200, review.data)
        execution = self.client.post(
            f"/api/import/history-takeovers/{application.pk}/groups/{group.pk}/execute/",
            {},
            format="json",
        )
        self.assertEqual(execution.status_code, 200, execution.data)
        group.refresh_from_db()
        return application, group, submission, review, execution

    def _finance_user(self, username):
        return get_user_model().objects.create_superuser(
            username=username,
            email=f"{username}@example.test",
            password="test-only",
        )

    def test_history_handoff_requires_explicit_finance_v1_mapping(self):
        before = {
            "finance_facts": FinanceFact.objects.count(),
            "transactions": Transaction.objects.count(),
            "plans": PaymentPlan.objects.count(),
            "inventory_movements": InventoryMovement.objects.count(),
            "inventory_reservations": InventoryReservation.objects.count(),
        }
        application, group, submission, _review, execution = self._submit_review_execute()

        self.assertEqual(group.status, "executed")
        self.assertEqual(group.finance_handoff_status, "not_connected")
        self.assertEqual(group.execution_result["finance_records_posted"], 0)
        self.assertEqual(group.execution_result["inventory_movements_posted"], 0)
        self.assertFalse(submission.data["approval_or_migration"])

        handoff = HistoryTakeoverHandoff.objects.get(group=group, kind="finance")
        self.assertEqual(handoff.status, "not_connected")
        self.assertEqual(handoff.payload["contract_version"], "1")
        self.assertEqual(len(handoff.payload["source_transactions"]), 2)
        source_row = next(
            row for row in handoff.payload["source_transactions"]
            if row["source_record_id"] == "TX-SO-1"
        )
        self.assertEqual(source_row["currency"], "USD")
        self.assertEqual(source_row["amount"], "40.0000")
        source_record = HistoryTakeoverSourceRecord.objects.get(
            group=group,
            record_type="收付款流水",
            source_record_id=source_row["source_record_id"],
        )

        # History execution records the source and handoff only. It must not
        # create a second actual finance event, old Transaction, or stock entry.
        self.assertEqual(FinanceFact.objects.count(), before["finance_facts"])
        self.assertEqual(Transaction.objects.count(), before["transactions"])
        self.assertEqual(PaymentPlan.objects.count(), before["plans"])
        self.assertEqual(InventoryMovement.objects.count(), before["inventory_movements"])
        self.assertEqual(InventoryReservation.objects.count(), before["inventory_reservations"])

        source_rows_before = copy.deepcopy(group.source_rows)
        handoff_payload_before = copy.deepcopy(handoff.payload)
        source_snapshot_before = copy.deepcopy(source_record.source_snapshot)
        source_record_id = source_row["source_record_id"]
        maker = self._finance_user("history-finance-maker")
        reviewer = self._finance_user("history-finance-reviewer")
        operator = self._finance_user("history-finance-poster")
        self.assertEqual(len({maker.pk, reviewer.pk, operator.pk}), 3)

        with tempfile.TemporaryDirectory(prefix="history-finance-contract-") as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                account = finance_closeout.create_account(
                    {
                        "code": "SYNTH-HISTORY-CNY-BANK",
                        "name": "合成历史承接人民币银行账户",
                        "account_type": "bank",
                        "ownership": "own",
                        "ownership_reason": "仅用于隔离契约测试的合成账户",
                    },
                    maker,
                )
                self.assertEqual(account.currency, "CNY")
                self.assertEqual(account.ownership, "own")
                voucher = finance_closeout.upload(
                    SimpleUploadedFile(
                        "synthetic-history-bank-proof.pdf",
                        b"%PDF-1.4\nSynthetic proof for isolated contract test only\n%%EOF",
                        content_type="application/pdf",
                    ),
                    maker,
                )

                # Explicit synthetic CNY fact and actual date. The old handoff
                # row is USD; this test does not convert its amount or rate.
                actual_date = "2024-09-03"
                actual_cny_amount = "287.43"
                source_system = "HISTORY_TAKEOVER_CONTRACT_TEST"
                source_key = f"{group.source_group_id}:收付款流水:{source_record_id}"
                request_key = f"HT-FIN-{application.pk}-{group.pk}-{source_record_id}"
                payload = {
                    "request_key": request_key,
                    "kind": "cash",
                    "account": account.pk,
                    "voucher": voucher.pk,
                    "actual_date": actual_date,
                    "amount": actual_cny_amount,
                    "direction": "income",
                    "nature": "unclassified",
                    "truth": "verified",
                    "source_system": source_system,
                    "source_key": source_key,
                    "reason": "人工将合成历史来源映射到明确的合成实际人民币凭证",
                    "allocations": [],
                }

                instruction, created = finance_closeout.submit(payload, maker)
                self.assertTrue(created)
                replay, replay_created = finance_closeout.submit(payload, maker)
                self.assertFalse(replay_created)
                self.assertEqual(replay.pk, instruction.pk)
                with self.assertRaises(APIException):
                    finance_closeout.submit({**payload, "amount": "287.44"}, maker)

                approved = finance_closeout.approve(instruction.pk, reviewer)
                fact = finance_closeout.post(instruction.pk, operator, voucher_checked=True)
                replay_fact = finance_closeout.post(instruction.pk, operator, voucher_checked=True)
                self.assertEqual(replay_fact.pk, fact.pk)
                fact.refresh_from_db()
                self.assertEqual(fact.source_system, source_system)
                self.assertEqual(fact.source_key, source_key)
                self.assertEqual(fact.actual_date.isoformat(), actual_date)
                self.assertEqual(fact.amount, Decimal(actual_cny_amount))
                self.assertEqual(fact.truth, "verified")
                self.assertEqual(fact.voucher_id, voucher.pk)
                self.assertTrue(voucher.file.storage.exists(voucher.file.name))

                instruction.refresh_from_db()
                approved_actor = instruction.approved_actor
                self.assertEqual(instruction.created_actor["kind"], "authenticated_user")
                self.assertEqual(instruction.created_actor["user_id"], maker.pk)
                self.assertEqual(approved_actor["kind"], "authenticated_user")
                self.assertEqual(approved_actor["user_id"], reviewer.pk)
                self.assertEqual(fact.actor["kind"], "authenticated_user")
                self.assertEqual(fact.actor["user_id"], operator.pk)
                self.assertEqual(approved.pk, instruction.pk)

                submit_audit = OperationLog.objects.get(
                    entity="crm.financeinstruction",
                    object_id=str(instruction.pk),
                    action_label="发起资金指令",
                )
                approve_audit = OperationLog.objects.get(
                    entity="crm.financeinstruction",
                    object_id=str(instruction.pk),
                    action_label="复核资金指令",
                )
                post_audit = OperationLog.objects.get(
                    entity="crm.financefact",
                    object_id=str(fact.pk),
                    action_label="记入实际资金事实",
                )
                self.assertEqual(submit_audit.operator_id, maker.pk)
                self.assertEqual(approve_audit.operator_id, reviewer.pk)
                self.assertEqual(post_audit.operator_id, operator.pk)

                # A new request key cannot count the same handoff source twice.
                duplicate_source, _ = finance_closeout.submit(
                    {**payload, "request_key": request_key + "-DUP"}, maker
                )
                with self.assertRaises(APIException):
                    finance_closeout.post(duplicate_source.pk, operator, voucher_checked=True)
                self.assertEqual(
                    FinanceFact.objects.filter(source_system=source_system, source_key=source_key).count(),
                    1,
                )

                posted_events = finance_closeout.reporting_events(
                    operator, "2024-01-01", "2024-12-31"
                )
                self.assertEqual(len(posted_events), 1)
                self.assertEqual(posted_events[0].bank_reference, source_key)
                self.assertEqual(posted_events[0].bank_net_amount, Decimal(actual_cny_amount))

                for truth in ("needs_verification", "simulated"):
                    pending_payload = {
                        **payload,
                        "request_key": request_key + "-" + truth.upper(),
                        "source_key": source_key + ":" + truth,
                        "actual_date": "2024-09-04",
                        "amount": "19.00",
                        "truth": truth,
                    }
                    pending, pending_created = finance_closeout.submit(pending_payload, maker)
                    self.assertTrue(pending_created)
                    with self.assertRaises(APIException):
                        finance_closeout.approve(pending.pk, reviewer)
                    with self.assertRaises(APIException):
                        finance_closeout.post(pending.pk, operator, voucher_checked=True)
                    pending.refresh_from_db()
                    self.assertEqual(pending.status, "pending")
                    self.assertFalse(FinanceFact.objects.filter(instruction=pending).exists())

                self.assertEqual(FinanceFact.objects.count(), before["finance_facts"] + 1)
                final_events = finance_closeout.reporting_events(
                    operator, "2024-01-01", "2024-12-31"
                )
                self.assertEqual(len(final_events), 1)
                self.assertEqual(final_events[0].bank_reference, source_key)

                group.refresh_from_db()
                handoff.refresh_from_db()
                source_record.refresh_from_db()
                self.assertEqual(group.source_rows, source_rows_before)
                self.assertEqual(group.finance_handoff_status, "not_connected")
                self.assertEqual(handoff.status, "not_connected")
                self.assertEqual(handoff.payload, handoff_payload_before)
                self.assertEqual(source_record.source_snapshot, source_snapshot_before)

                # Finance posting is separate from legacy business settlement
                # and inventory ledgers; it never changes those source records.
                self.assertEqual(Transaction.objects.count(), before["transactions"])
                self.assertEqual(PaymentPlan.objects.count(), before["plans"])
                self.assertEqual(InventoryMovement.objects.count(), before["inventory_movements"])
                self.assertEqual(InventoryReservation.objects.count(), before["inventory_reservations"])
