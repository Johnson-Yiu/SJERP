"""Append-only effective-party versions for sales and purchase documents."""
from django.conf import settings
from django.db import models
from .party_version_models import ImmutableRecord


class PartyDocumentVersion(ImmutableRecord):
    order = models.ForeignKey('crm.Order', null=True, blank=True, on_delete=models.PROTECT, related_name='party_versions')
    purchase_order = models.ForeignKey('crm.PurchaseOrder', null=True, blank=True, on_delete=models.PROTECT, related_name='party_versions')
    previous = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='next_versions')
    approval = models.OneToOneField('crm.PartyVersionApproval', on_delete=models.PROTECT, related_name='document_version')
    applied_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='applied_document_party_versions')
    version_no = models.PositiveIntegerField()
    base_snapshot = models.JSONField()
    snapshot = models.JSONField()
    identity_fingerprint = models.CharField(max_length=64)
    base_fingerprint = models.CharField(max_length=64)
    snapshot_fingerprint = models.CharField(max_length=64)
    approved_fingerprint = models.CharField(max_length=64)
    approval_attestation_fingerprint = models.CharField(max_length=64)
    source_trust = models.CharField(max_length=24, choices=[('unknown', '未知'), ('unverified', '未核验')])
    version_fingerprint = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=(models.Q(order__isnull=False, purchase_order__isnull=True) | models.Q(order__isnull=True, purchase_order__isnull=False)), name='party_doc_one_target'),
            models.CheckConstraint(condition=models.Q(version_no__gte=1), name='party_doc_version_positive'),
            models.UniqueConstraint(fields=['order', 'version_no'], condition=models.Q(order__isnull=False), name='party_doc_order_version_unique'),
            models.UniqueConstraint(fields=['purchase_order', 'version_no'], condition=models.Q(purchase_order__isnull=False), name='party_doc_purchase_version_unique'),
        ]
