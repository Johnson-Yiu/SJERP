from django.db import models


class ArchivedHistoryLine(models.Model):
    """Financial and quantity facts for a newly archived source line."""

    order = models.ForeignKey("crm.Order", null=True, on_delete=models.PROTECT, related_name="archived_lines")
    purchase_order = models.ForeignKey(
        "crm.PurchaseOrder", null=True, on_delete=models.PROTECT, related_name="archived_lines",
    )
    quantity = models.DecimalField(max_digits=14, decimal_places=2)
    unit_price = models.DecimalField(max_digits=24, decimal_places=12)
    trade_quantity = models.DecimalField(max_digits=14, decimal_places=2, null=True)
    trade_unit_price = models.DecimalField(max_digits=16, decimal_places=4, null=True)
    facts = models.JSONField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(order__isnull=False, purchase_order__isnull=True)
                    | models.Q(order__isnull=True, purchase_order__isnull=False)
                ),
                name="archived_history_line_one_parent",
            ),
        ]

    @property
    def amount(self):
        if self.trade_quantity is not None and self.trade_unit_price is not None:
            return self.trade_quantity * self.trade_unit_price
        return self.quantity * self.unit_price

    @property
    def trade_snapshot(self):
        return {
            "unit": self.facts.get("trade_unit_snapshot") or self.unit_snapshot,
            "base_unit": self.facts.get("base_unit_snapshot") or "",
            "factor": str(self.facts.get("trade_factor_snapshot") or "1"),
            "name": self.facts.get("trade_unit_snapshot") or "",
        }

    @property
    def unit_snapshot(self):
        return self.facts.get("unit_snapshot") or ""

    @property
    def display_name_snapshot(self):
        return self.facts.get("sku_name_snapshot") or ""

    @property
    def description_snapshot(self):
        return self.facts.get("description_snapshot") or ""

    @property
    def sales_model_snapshot(self):
        return self.facts.get("sales_model_snapshot") or ""


class HistoryProductLink(models.Model):
    source = models.OneToOneField(
        "crm.HistoryTakeoverSourceRecord", primary_key=True, on_delete=models.PROTECT, related_name="product_link",
    )
    sku = models.ForeignKey("crm.SKU", null=True, on_delete=models.PROTECT)
    version = models.PositiveIntegerField(default=1)
    needs_review = models.BooleanField(default=False)


class HistoryProductLinkRequest(models.Model):
    """One saved response per signed preview. Events live in the history audit ledger."""

    token_digest = models.CharField(max_length=64, primary_key=True)
    result = models.JSONField(default=dict)
class HistoryProductRule(models.Model):
    """An operator-confirmed candidate for a specific source and original code."""

    scope_key = models.CharField(max_length=64, primary_key=True)
    confirmed_source = models.ForeignKey("crm.HistoryTakeoverSourceRecord", on_delete=models.PROTECT)
    sku = models.ForeignKey("crm.SKU", on_delete=models.PROTECT)
