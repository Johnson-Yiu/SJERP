"""Initial structured party facts; formal changes use the approval chain."""
from django.db import models


class PartyDocumentDetailsStorage(models.Model):
    quote = models.OneToOneField('crm.Quote', null=True, blank=True, on_delete=models.PROTECT)
    order = models.OneToOneField('crm.Order', null=True, blank=True, on_delete=models.PROTECT)
    purchase_order = models.OneToOneField('crm.PurchaseOrder', null=True, blank=True, on_delete=models.PROTECT)
    details = models.JSONField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=(
                models.Q(quote__isnull=False, order__isnull=True, purchase_order__isnull=True)
                | models.Q(quote__isnull=True, order__isnull=False, purchase_order__isnull=True)
                | models.Q(quote__isnull=True, order__isnull=True, purchase_order__isnull=False)
            ), name='party_details_one_target'),
        ]
