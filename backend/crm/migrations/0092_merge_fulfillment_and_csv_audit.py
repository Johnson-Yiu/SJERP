from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0090_fulfillment_idempotency"),
        ("crm", "0091_csv_import_audit"),
    ]

    operations = []
