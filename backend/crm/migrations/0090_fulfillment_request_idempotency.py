from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0089_operationlog_operator_protect"),
    ]

    operations = [
        migrations.AddField(
            model_name="goodsreceipt",
            name="request_fingerprint",
            field=models.CharField(blank=True, max_length=64, verbose_name="请求指纹"),
        ),
        migrations.AddField(
            model_name="goodsreceipt",
            name="request_key",
            field=models.CharField(blank=True, max_length=100, null=True, unique=True, verbose_name="请求幂等键"),
        ),
        migrations.AddField(
            model_name="shipment",
            name="request_fingerprint",
            field=models.CharField(blank=True, max_length=64, verbose_name="请求指纹"),
        ),
        migrations.AddField(
            model_name="shipment",
            name="request_key",
            field=models.CharField(blank=True, max_length=100, null=True, unique=True, verbose_name="请求幂等键"),
        ),
    ]
