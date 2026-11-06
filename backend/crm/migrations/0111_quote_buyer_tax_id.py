from django.db import migrations, models


def reject_tax_loss(apps, schema_editor):
    alias = schema_editor.connection.alias
    quote = apps.get_model("crm", "Quote")
    if quote.objects.using(alias).filter(buyer_tax_id__isnull=False).exists():
        raise RuntimeError("已有买方税号快照，拒绝回退以避免丢失数据。")
    if quote.objects.using(alias).filter(buyer_country_snapshot__isnull=False).exists():
        raise RuntimeError("报价买方国家快照已存在，拒绝回退以避免丢失历史事实。")
    request = apps.get_model("crm", "PartyVersionRequest")
    approval = apps.get_model("crm", "PartyVersionApproval")
    if request.objects.using(alias).exists() or approval.objects.using(alias).exists():
        raise RuntimeError("主体更正申请或审批记录已存在，拒绝回退以避免丢失历史。")


class Migration(migrations.Migration):
    dependencies = [("crm", "0110_party_version")]

    operations = [
        migrations.AddField(
            model_name="quote",
            name="buyer_tax_id",
            field=models.CharField("买方税号快照", max_length=200, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name="quote",
            name="buyer_tax_id",
            field=models.CharField("买方税号快照", max_length=200, null=True, blank=True, default=""),
        ),
        migrations.RunPython(migrations.RunPython.noop, reject_tax_loss),
    ]
