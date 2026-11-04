"""Isolated records for the controlled historical takeover workflow.

These models hold source facts and review evidence. They are deliberately not
the finance ledger, inventory ledger, or fulfillment ledger.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class HistoryTakeoverApplication(models.Model):
    STATUS_CHOICES = [
        ("submitted", "待审核"),
        ("in_review", "审核中"),
        ("rejected", "已拒绝"),
        ("partially_approved", "部分通过"),
        ("approved", "已批准"),
        ("executed", "已执行"),
        ("withdrawn", "已撤回"),
    ]
    ACTOR_CHOICES = [("identified", "实名账号"), ("development", "开发身份（非实名）")]

    source_file_name = models.CharField(max_length=240)
    source_sha256 = models.CharField(max_length=64, db_index=True)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default="submitted", db_index=True)
    preflight_summary = models.JSONField(default=dict, blank=True)
    preflight_payload = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="history_takeover_applications")
    created_by_label = models.CharField(max_length=200, blank=True)
    created_actor_kind = models.CharField(max_length=20, choices=ACTOR_CHOICES, default="identified")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="reviewed_history_takeover_applications")
    reviewed_by_label = models.CharField(max_length=200, blank=True)
    reviewed_actor_kind = models.CharField(max_length=20, choices=ACTOR_CHOICES, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-submitted_at", "-id"]


class HistoryTakeoverGroup(models.Model):
    STATUS_CHOICES = [
        ("pending", "待审核"),
        ("approved", "已批准"),
        ("rejected", "已拒绝"),
        ("blocked", "存在阻断"),
        ("needs_reapproval", "资料变化，需重新审核"),
        ("executed", "已承接历史记录"),
        ("withdrawn", "已撤回"),
    ]
    application = models.ForeignKey(HistoryTakeoverApplication, on_delete=models.PROTECT, related_name="groups")
    source_group_id = models.CharField(max_length=120)
    source_system = models.CharField(max_length=160)
    exported_at = models.DateField(null=True, blank=True)
    coverage_status = models.CharField(max_length=20)
    truth_status = models.CharField(max_length=20)
    evidence_reference = models.CharField(max_length=500, blank=True)
    notes = models.TextField(blank=True)
    source_rows = models.JSONField(default=dict)
    resolution_map = models.JSONField(default=dict, blank=True)
    source_fingerprint = models.CharField(max_length=64, blank=True)
    approved_fingerprint = models.CharField(max_length=64, blank=True)
    preflight_result = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default="pending", db_index=True)
    review_note = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="reviewed_history_takeover_groups")
    reviewed_by_label = models.CharField(max_length=200, blank=True)
    reviewed_actor_kind = models.CharField(max_length=20, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    execution_key = models.CharField(max_length=64, blank=True, unique=True, null=True)
    execution_result = models.JSONField(default=dict, blank=True)
    remainder_snapshot = models.JSONField(default=dict, blank=True)
    verified_correction_ids = models.JSONField(default=list, blank=True)
    finance_handoff_status = models.CharField(max_length=24, default="not_connected")
    inventory_handoff_status = models.CharField(max_length=24, default="not_connected")
    fulfillment_handoff_status = models.CharField(max_length=24, default="not_connected")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        constraints = [models.UniqueConstraint(fields=["application", "source_group_id"], name="history_takeover_group_unique")]


class HistoryTakeoverSourceRecord(models.Model):
    group = models.ForeignKey(HistoryTakeoverGroup, on_delete=models.PROTECT, related_name="source_records")
    source_system = models.CharField(max_length=160)
    record_type = models.CharField(max_length=40)
    source_record_id = models.CharField(max_length=160)
    source_snapshot = models.JSONField(default=dict)
    target_model = models.CharField(max_length=120, blank=True)
    target_id = models.PositiveBigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [models.UniqueConstraint(fields=["source_system", "record_type", "source_record_id"], name="history_takeover_source_identity_unique")]


class HistoryTakeoverHandoff(models.Model):
    KINDS = [("finance", "资金核实交接"), ("inventory", "库存盘点基准交接"), ("fulfillment", "履约与剩余业务交接")]
    group = models.ForeignKey(HistoryTakeoverGroup, on_delete=models.PROTECT, related_name="handoffs")
    kind = models.CharField(max_length=20, choices=KINDS)
    status = models.CharField(max_length=24, default="not_connected")
    contract_version = models.CharField(max_length=24, default="1")
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["group", "kind"], name="history_takeover_handoff_unique")]


class HistoryTakeoverEvent(models.Model):
    application = models.ForeignKey(HistoryTakeoverApplication, on_delete=models.PROTECT, related_name="events")
    group = models.ForeignKey(HistoryTakeoverGroup, null=True, blank=True, on_delete=models.PROTECT, related_name="events")
    event_type = models.CharField(max_length=40)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="history_takeover_events")
    actor_label = models.CharField(max_length=200, blank=True)
    actor_kind = models.CharField(max_length=20, choices=HistoryTakeoverApplication.ACTOR_CHOICES, default="identified")
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at", "id"]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("历史承接审计事件只允许追加。")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("历史承接审计事件不能删除。")
