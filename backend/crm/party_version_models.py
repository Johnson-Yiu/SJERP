from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class ImmutableQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError('主体版本记录不可修改。')

    def delete(self):
        raise ValidationError('主体版本记录不可删除。')


class ImmutableRecord(models.Model):
    objects = ImmutableQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError('主体版本记录不可修改。')
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('主体版本记录不可删除。')


class PartyVersionRequest(ImmutableRecord):
    quote = models.ForeignKey('crm.Quote', null=True, blank=True, on_delete=models.PROTECT)
    order = models.ForeignKey('crm.Order', null=True, blank=True, on_delete=models.PROTECT)
    purchase_order = models.ForeignKey('crm.PurchaseOrder', null=True, blank=True, on_delete=models.PROTECT)
    quote_customer = models.ForeignKey('crm.Customer', null=True, blank=True, on_delete=models.PROTECT, related_name='party_version_quote_requests')
    initiator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='party_version_requests')
    base_snapshot = models.JSONField()
    proposed_snapshot = models.JSONField()
    base_fingerprint = models.CharField(max_length=64)
    source_document_fingerprint = models.CharField(max_length=64, null=True, blank=True)
    content_fingerprint = models.CharField(max_length=64)
    change_type = models.CharField(max_length=24, choices=[('correction', '同主体更正'), ('replacement', '法律主体替换')])
    reason = models.TextField()
    evidence = models.TextField()
    source_trust = models.CharField(max_length=24, choices=[('unknown', '未知'), ('unverified', '未核验')])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=(models.Q(quote__isnull=False, order__isnull=True, purchase_order__isnull=True) | models.Q(quote__isnull=True, order__isnull=False, purchase_order__isnull=True) | models.Q(quote__isnull=True, order__isnull=True, purchase_order__isnull=False)), name='party_request_one_target'),
            models.UniqueConstraint(fields=['quote', 'base_fingerprint'], condition=models.Q(quote__isnull=False), name='party_quote_base_unique'),
            models.UniqueConstraint(fields=['order', 'base_fingerprint'], condition=models.Q(order__isnull=False), name='party_order_base_unique'),
            models.UniqueConstraint(fields=['purchase_order', 'base_fingerprint'], condition=models.Q(purchase_order__isnull=False), name='party_purchase_base_unique'),
        ]


class PartyVersionApproval(ImmutableRecord):
    request = models.OneToOneField(PartyVersionRequest, on_delete=models.PROTECT, related_name='approval')
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='party_version_approvals')
    approved_fingerprint = models.CharField(max_length=64)
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class PartyQuoteApplication(ImmutableRecord):
    """One approval applied once to one existing quote revision tree."""
    approval = models.OneToOneField(PartyVersionApproval, on_delete=models.PROTECT, related_name='application')
    source_quote = models.ForeignKey('crm.Quote', on_delete=models.PROTECT, related_name='party_applications')
    result_quote = models.OneToOneField('crm.Quote', on_delete=models.PROTECT, related_name='party_application')
    applied_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='party_quote_applications')
    approved_fingerprint = models.CharField(max_length=64)
    approval_attestation_fingerprint = models.CharField(max_length=64)
    source_fingerprint = models.CharField(max_length=64)
    revision_fingerprint = models.CharField(max_length=64)
    application_fingerprint = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
