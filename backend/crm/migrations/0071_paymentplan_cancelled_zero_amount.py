# Generated manually for the retained, zero-value cancelled adjustment-plan history.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("crm", "0070_shipmentitem_overage_reversal_links")]

    operations = [
        migrations.RemoveConstraint(model_name="paymentplan", name="payment_plan_amount_positive"),
        migrations.AddConstraint(
            model_name="paymentplan",
            constraint=models.CheckConstraint(
                condition=models.Q(("planned_amount__gt", 0)) | models.Q(("planned_amount", 0), ("settled_amount", 0), ("status", "cancelled")),
                name="payment_plan_amount_positive",
            ),
        ),
    ]
