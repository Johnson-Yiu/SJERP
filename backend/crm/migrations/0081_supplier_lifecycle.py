from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0080_formal_party_snapshots"),
    ]

    operations = [
        migrations.AddField(
            model_name="supplier",
            name="is_active",
            field=models.BooleanField(db_index=True, default=True, verbose_name="启用"),
        ),
    ]
