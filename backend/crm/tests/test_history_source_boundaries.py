"""Synthetic history-source boundaries; never uses a real business database."""
from django.test import TestCase
from crm.history_operational_finance import _source_key
from crm.history_takeover import TakeoverRuleError, _truth_rows
from crm.models import FinanceInstruction, HistoryTakeoverApplication, HistoryTakeoverGroup, HistoryTakeoverSourceRecord
from crm.tests.test_history_takeover import HistoryTakeoverFixtureMixin


class HistorySourceBoundaryTests(HistoryTakeoverFixtureMixin, TestCase):
    def test_oversized_source_system_is_rejected_without_application(self):
        rows = self.source_rows(source_system="S" * 161)
        response = self.upload_application(rows)
        self.assertEqual(response.status_code, 400, getattr(response, "data", None))
        self.assertEqual(HistoryTakeoverApplication.objects.count(), 0)

    def test_oversized_group_id_is_rejected_without_application(self):
        rows = self.source_rows(group_id="G" * 121)
        response = self.upload_application(rows)
        self.assertEqual(response.status_code, 400, getattr(response, "data", None))
        self.assertEqual(HistoryTakeoverApplication.objects.count(), 0)

    def test_exact_group_system_and_source_limits_are_accepted(self):
        rows = self.source_rows(group_id="G" * 120, source_system="S" * 160)
        rows["收付款流水"][0]["source_record_id"] = "T" * 160
        response = self.upload_application(rows)
        self.assertEqual(response.status_code, 201, getattr(response, "data", None))
        self.assertEqual(HistoryTakeoverApplication.objects.count(), 1)

    def test_oversized_source_record_and_composite_line_are_rejected(self):
        for sheet, key, value in (("收付款流水", "source_record_id", "T" * 161),
                                  ("销售明细", "source_line_id", "L" * 153)):
            with self.subTest(sheet=sheet):
                rows = self.source_rows()
                rows[sheet][0][key] = value
                response = self.upload_application(rows)
                self.assertEqual(response.status_code, 400, getattr(response, "data", None))
                self.assertEqual(HistoryTakeoverApplication.objects.count(), 0)

    def test_cross_group_same_source_identity_is_rejected_but_other_system_is_distinct(self):
        app, group, _ = self.application_and_group()
        HistoryTakeoverSourceRecord.objects.create(group=group, source_system=group.source_system,
            record_type="收付款流水", source_record_id="TX-SO-1")
        other = HistoryTakeoverGroup.objects.create(application=app, source_group_id="SECOND",
            source_system=group.source_system, coverage_status="complete", truth_status="真实",
            source_rows={"收付款流水": [{"row": 2, "data": {"source_record_id": "TX-SO-1"}}]})
        with self.assertRaisesMessage(TakeoverRuleError, "来源记录已由其他承接批次登记"):
            _truth_rows(other)
        other.source_system = "Different source"
        _truth_rows(other)

    def test_maximum_source_identity_produces_bounded_stable_request_key(self):
        source = HistoryTakeoverSourceRecord(source_system="S" * 160, record_type="收付款流水",
                                             source_record_id="T" * 160)
        key = _source_key(source)
        self.assertEqual(len(key), 64)
        self.assertEqual(key, _source_key(source))
        self.assertLessEqual(len("history-cash:" + key + ":" + str(2**63 - 1)),
                             FinanceInstruction._meta.get_field("request_key").max_length)
        source.source_system = "X" * 160
        self.assertNotEqual(key, _source_key(source))

    def test_preflight_shows_specific_blocking_row(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        rows = self.source_rows(source_system="S" * 161)
        upload = SimpleUploadedFile("synthetic.xlsx", self.workbook_bytes(rows),
                                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response = self.client.post("/api/import/history-preflight/", {"file": upload}, format="multipart")
        self.assertEqual(response.status_code, 200, getattr(response, "data", None))
        row = next(item for item in response.data["results"] if item["sheet"] == "分组")
        self.assertEqual(row["status"], "阻断")
        self.assertTrue(any("160" in reason["message"] for reason in row["reasons"]))
        self.assertFalse(HistoryTakeoverApplication.objects.exists())

    def test_existing_oversized_source_record_cannot_execute(self):
        app, group, _ = self.application_and_group()
        group.source_rows = {"收付款流水": [{"row": 2, "data": {"source_record_id": "T" * 161}}]}
        with self.assertRaisesMessage(TakeoverRuleError, "超过 160 个字符"):
            _truth_rows(group)
        self.assertFalse(HistoryTakeoverSourceRecord.objects.exists())
