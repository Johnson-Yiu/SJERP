from django.db import migrations, models
import django.db.models.deletion


def reject_loss(apps, schema_editor):
    Storage = apps.get_model('crm', 'PartyDocumentDetailsStorage')
    if Storage.objects.using(schema_editor.connection.alias).exists():
        raise RuntimeError('主体资料记录已存在，拒绝回退以避免丢失历史。')


class Migration(migrations.Migration):
    dependencies = [('crm', '0115_party_replacement')]
    operations = [
        migrations.CreateModel(name='PartyDocumentDetailsStorage', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('details', models.JSONField(blank=True, null=True)),
            ('quote', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='crm.quote')),
            ('order', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='crm.order')),
            ('purchase_order', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='crm.purchaseorder')),
        ], options={'constraints': [
            models.CheckConstraint(condition=(
                models.Q(quote__isnull=False, order__isnull=True, purchase_order__isnull=True)
                | models.Q(quote__isnull=True, order__isnull=False, purchase_order__isnull=True)
                | models.Q(quote__isnull=True, order__isnull=True, purchase_order__isnull=False)
            ), name='party_details_one_target'),
            models.CheckConstraint(condition=models.Q(details__isnull=True), name='party_details_not_enabled'),
        ]}),
        migrations.RunPython(migrations.RunPython.noop, reject_loss),
    ]
