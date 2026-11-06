"""Immutable records for an independently approved legal-party replacement."""
from django.conf import settings
from django.db import models

from .party_version_models import ImmutableRecord


class PartyReplacementTarget(ImmutableRecord):
    request = models.OneToOneField('crm.PartyVersionRequest', on_delete=models.PROTECT, related_name='replacement_target')
    customer = models.ForeignKey('crm.Customer', null=True, blank=True, on_delete=models.PROTECT)
    supplier = models.ForeignKey('crm.Supplier', null=True, blank=True, on_delete=models.PROTECT)
    target_name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=(
            models.Q(customer__isnull=False, supplier__isnull=True) |
            models.Q(customer__isnull=True, supplier__isnull=False)), name='party_replacement_one_target')]


class PartyReplacementLink(ImmutableRecord):
    target = models.OneToOneField(PartyReplacementTarget, on_delete=models.PROTECT, related_name='link')
    approval = models.OneToOneField('crm.PartyVersionApproval', on_delete=models.PROTECT, related_name='replacement_link')
    result_quote = models.OneToOneField('crm.Quote', null=True, blank=True, on_delete=models.PROTECT, related_name='replacement_link')
    result_order = models.OneToOneField('crm.Order', null=True, blank=True, on_delete=models.PROTECT, related_name='replacement_link')
    result_purchase_order = models.OneToOneField('crm.PurchaseOrder', null=True, blank=True, on_delete=models.PROTECT, related_name='replacement_link')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='party_replacement_links')
    approved_fingerprint = models.CharField(max_length=64)
    approval_fingerprint = models.CharField(max_length=64)
    payload_fingerprint = models.CharField(max_length=64)
    link_fingerprint = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=(
            models.Q(result_quote__isnull=False, result_order__isnull=True, result_purchase_order__isnull=True) |
            models.Q(result_quote__isnull=True, result_order__isnull=False, result_purchase_order__isnull=True) |
            models.Q(result_quote__isnull=True, result_order__isnull=True, result_purchase_order__isnull=False)), name='party_replacement_one_result')]
