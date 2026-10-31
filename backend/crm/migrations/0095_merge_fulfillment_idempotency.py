from django.db import migrations


class Migration(migrations.Migration):
    """Join the pre-pilot per-document key migration with the canonical ledger.

    0090_fulfillment_request_idempotency was published on the pre-pilot
    branch. The later request-ledger implementation adds its own 0090
    migration. Preserve both histories and converge the graph without
    dropping the legacy columns or rewriting either migration.
    """

    dependencies = [
        ("crm", "0090_fulfillment_request_idempotency"),
        ("crm", "0094_csv_import_audit_truncate_guard"),
    ]

    operations = []
