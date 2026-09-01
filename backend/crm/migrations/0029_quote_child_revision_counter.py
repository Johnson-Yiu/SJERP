from django.core.validators import MaxValueValidator
from django.db import migrations, models
import django.db.models.deletion


def populate_child_revision_counters(apps, schema_editor):
    Quote = apps.get_model("crm", "Quote")
    Counter = apps.get_model("crm", "QuoteChildRevisionCounter")
    for parent in Quote.objects.all().iterator():
        prefix = f"{parent.quote_no}-"
        maximum = 0
        for child_no in Quote.objects.filter(parent_quote=parent).values_list("quote_no", flat=True):
            suffix = child_no.removeprefix(prefix)
            if suffix.isdigit():
                maximum = max(maximum, int(suffix))
        if maximum:
            Counter.objects.update_or_create(parent_quote=parent, defaults={"last_value": maximum})


class Migration(migrations.Migration):
    dependencies = [("crm", "0028_remove_legacy_dimensions_from_sku_product_details")]

    operations = [
        migrations.AlterField(
            model_name="quote",
            name="quote_no",
            field=models.CharField(max_length=120, unique=True, verbose_name="报价单号"),
        ),
        migrations.CreateModel(
            name="QuoteChildRevisionCounter",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("last_value", models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(99)])),
                ("parent_quote", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="child_revision_counter", to="crm.quote")),
            ],
        ),
        migrations.RunPython(populate_child_revision_counters, migrations.RunPython.noop),
    ]
