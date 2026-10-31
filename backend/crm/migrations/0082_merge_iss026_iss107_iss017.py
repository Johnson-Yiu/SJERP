from django.db import migrations


class Migration(migrations.Migration):
    """Join the three independent 0081 feature leaves without rewriting history."""

    dependencies = [
        ("crm", "0081_supplier_lifecycle"),
        ("crm", "0081_transaction_rmb_reference_label"),
        ("crm", "0081_product_certificate_private_file"),
    ]

    operations = []
