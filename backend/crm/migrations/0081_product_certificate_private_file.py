from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0080_formal_party_snapshots"),
    ]

    operations = [
        migrations.AddField(
            model_name="productcertificate",
            name="file",
            field=models.FileField(blank=True, upload_to="product-certificates/%Y/%m/", verbose_name="私有证书文件"),
        ),
    ]
