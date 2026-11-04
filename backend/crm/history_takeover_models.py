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


class _InventoryBaselineQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("库存基准记录只允许追加。")

    def delete(self):
        raise ValidationError("库存基准记录不可删除。")


class HistoryInventoryBaseline(models.Model):
    """A reviewed physical count; its warehouse and cost evidence remain intact."""

    group = models.ForeignKey(HistoryTakeoverGroup, on_delete=models.PROTECT, related_name="inventory_baselines")
    source = models.OneToOneField(HistoryTakeoverSourceRecord, on_delete=models.PROTECT, related_name="inventory_baseline")
    sku = models.ForeignKey("crm.SKU", on_delete=models.PROTECT, related_name="historical_inventory_baselines")
    count_date = models.DateField()
    warehouse_type = models.CharField(max_length=20)
    warehouse = models.CharField(max_length=100)
    lot_reference = models.CharField(max_length=160, blank=True)
    goods_ownership = models.CharField(max_length=20)
    unit_snapshot = models.CharField(max_length=30)
    quantity = models.DecimalField(max_digits=14, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=24, decimal_places=12)
    cost_currency = models.CharField(max_length=10)
    evidence_reference = models.CharField(max_length=500)
    approval_snapshot = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    objects = _InventoryBaselineQuerySet.as_manager()

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gte=0), name="history_inventory_qty_nonnegative"),
            models.CheckConstraint(condition=models.Q(unit_cost__gte=0), name="history_inventory_cost_nonnegative"),
            models.CheckConstraint(condition=models.Q(goods_ownership__in=["own", "third_party"]), name="history_inventory_owner_valid"),
            models.CheckConstraint(condition=models.Q(warehouse_type__in=["自有仓", "第三方仓"]), name="history_inventory_warehouse_valid"),
        ]

    def save(self, *args, **kwargs):
        if self.pk and not self._state.adding:
            raise ValidationError("库存启用基准只允许追加；请使用受控撤销。")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("库存启用基准不可删除。")


class HistoryInventoryBaselineReversal(models.Model):
    baseline = models.OneToOneField(HistoryInventoryBaseline, on_delete=models.PROTECT, related_name="reversal")
    group = models.ForeignKey(HistoryTakeoverGroup, on_delete=models.PROTECT, related_name="inventory_baseline_reversals")
    reason = models.TextField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    objects = _InventoryBaselineQuerySet.as_manager()

    def save(self, *args, **kwargs):
        if self.pk and not self._state.adding:
            raise ValidationError("库存基准撤销记录只允许追加。")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("库存基准撤销记录不可删除。")


class HistoryOperationalContract(models.Model):
    """A traceable operational continuation of one archived contract."""

    group = models.ForeignKey(HistoryTakeoverGroup, on_delete=models.PROTECT, related_name="operational_contracts")
    source = models.OneToOneField(HistoryTakeoverSourceRecord, on_delete=models.PROTECT, related_name="operational_contract")
    archived_order = models.OneToOneField("crm.Order", null=True, blank=True, on_delete=models.PROTECT, related_name="history_operational_origin")
    archived_purchase = models.OneToOneField("crm.PurchaseOrder", null=True, blank=True, on_delete=models.PROTECT, related_name="history_operational_origin")
    continuation_order = models.OneToOneField("crm.Order", null=True, blank=True, on_delete=models.PROTECT, related_name="history_continuation")
    continuation_purchase = models.OneToOneField("crm.PurchaseOrder", null=True, blank=True, on_delete=models.PROTECT, related_name="history_continuation")
    settlement_order = models.OneToOneField("crm.Order", null=True, blank=True, on_delete=models.PROTECT, related_name="history_balance")
    settlement_purchase = models.OneToOneField("crm.PurchaseOrder", null=True, blank=True, on_delete=models.PROTECT, related_name="history_balance")
    cutover_date = models.DateField()
    balance_mode = models.CharField(max_length=16, choices=[("itemized", "逐笔未结"), ("balance_only", "余额承接")])
    opening_balance = models.DecimalField(max_digits=14, decimal_places=4)
    currency = models.CharField(max_length=10)
    evidence_reference = models.CharField(max_length=500)
    source_snapshot = models.JSONField(default=dict)
    line_links = models.JSONField(default=list)
    balance_snapshot = models.JSONField(default=dict)
    approval_snapshot = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    objects = _InventoryBaselineQuerySet.as_manager()

    class Meta:
        constraints = [
            models.CheckConstraint(condition=(models.Q(archived_order__isnull=False, archived_purchase__isnull=True, settlement_order__isnull=False, settlement_purchase__isnull=True, continuation_purchase__isnull=True) | models.Q(archived_order__isnull=True, archived_purchase__isnull=False, settlement_order__isnull=True, settlement_purchase__isnull=False, continuation_order__isnull=True)), name="history_operational_contract_type"),
            models.CheckConstraint(condition=models.Q(opening_balance__gte=0), name="history_operational_balance_nonnegative"),
            models.CheckConstraint(condition=models.Q(balance_mode__in=["itemized", "balance_only"]), name="history_operational_balance_mode"),
        ]

    def save(self, *args, **kwargs):
        if self.pk and not self._state.adding:
            raise ValidationError("历史接续记录只允许追加；请创建审计更正。")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("历史接续记录不可删除。")
