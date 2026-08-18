from django.db import migrations, models
import django.db.models.deletion


def attach_existing_revisions_to_roots(apps, schema_editor):
    Quote = apps.get_model("crm", "Quote")
    Quote.objects.filter(root_quote__isnull=False, parent_quote__isnull=True).update(parent_quote=models.F("root_quote"))


class Migration(migrations.Migration):
    dependencies = [("crm", "0013_quoteimportantnote")]

    operations = [
        migrations.AddField(
            model_name="quote",
            name="parent_quote",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="child_revisions", to="crm.quote", verbose_name="直接来源报价"),
        ),
        migrations.AddField(
            model_name="quote",
            name="revision_summary",
            field=models.CharField(blank=True, max_length=500, verbose_name="修订说明"),
        ),
        migrations.RunPython(attach_existing_revisions_to_roots, migrations.RunPython.noop),
    ]
