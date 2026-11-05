from django.db import migrations, models


def reject_loss_of_snapshots(apps, schema_editor):
    Quote = apps.get_model("crm", "Quote")
    if Quote.objects.using(schema_editor.connection.alias).filter(buyer_country_snapshot__isnull=False).exists():
        raise RuntimeError("报价买方国家快照已存在，拒绝回退以避免丢失历史事实。")


class Migration(migrations.Migration):
    dependencies = [("crm", "0108_history_append_only_truncate")]

    operations = [
        migrations.AddField(
            model_name="quote",
            name="buyer_country_snapshot",
            field=models.CharField(blank=True, editable=False, max_length=100, null=True, verbose_name="买方国家/地区快照"),
        ),
        migrations.RunPython(migrations.RunPython.noop, reject_loss_of_snapshots),
    ]
