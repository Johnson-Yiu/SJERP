from django.db import migrations, models
import django.db.models.deletion


def forward(apps, schema_editor):
    Product = apps.get_model('crm', 'Product')
    HSCode = apps.get_model('crm', 'HSCode')
    alias = schema_editor.connection.alias
    for product in Product.objects.using(alias).exclude(legacy_hs_code='').iterator():
        code = product.legacy_hs_code.strip()
        if code:
            record, _ = HSCode.objects.using(alias).get_or_create(code=code)
            Product.objects.using(alias).filter(pk=product.pk).update(hs_code_id=record.pk)


def backward(apps, schema_editor):
    Product = apps.get_model('crm', 'Product')
    alias = schema_editor.connection.alias
    for product in Product.objects.using(alias).select_related('hs_code').iterator():
        Product.objects.using(alias).filter(pk=product.pk).update(legacy_hs_code=product.hs_code.code if product.hs_code else '')


class Migration(migrations.Migration):
    dependencies = [('crm', '0052_alter_packingplancarton_partial_carton_policy_snapshot')]
    operations = [
        migrations.CreateModel(name='HSCode', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('updated_at', models.DateTimeField(auto_now=True)),
            ('code', models.CharField('HS 编码', max_length=30, unique=True)),
            ('description', models.CharField('商品描述', max_length=300, blank=True)),
            ('notes', models.TextField('备注', blank=True)),
            ('active', models.BooleanField('启用', default=True)),
        ], options={'ordering': ['code']}),
        migrations.RenameField(model_name='product', old_name='hs_code', new_name='legacy_hs_code'),
        migrations.AddField(model_name='product', name='hs_code', field=models.ForeignKey(to='crm.hscode', on_delete=django.db.models.deletion.PROTECT, blank=True, null=True, related_name='products', verbose_name='HS 编码')),
        migrations.RunPython(forward, backward),
        migrations.RemoveField(model_name='product', name='legacy_hs_code'),
    ]
