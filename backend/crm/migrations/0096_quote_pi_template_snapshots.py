from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("crm", "0095_merge_fulfillment_idempotency")]

    operations = [
        migrations.CreateModel(
            name="QuoteTemplateAsset",
            fields=[
                ("digest", models.CharField(max_length=64, primary_key=True, serialize=False)),
                ("snapshot", models.JSONField()),
            ],
        ),
        migrations.AddField(
            model_name="quote",
            name="pi_template_snapshots",
            field=models.JSONField(default=dict, editable=False),
        ),
    ]
