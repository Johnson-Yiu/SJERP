from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0082_merge_iss026_iss107_iss017"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomerSupplierPreference",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="supplier_preferences", to="crm.customer")),
                ("sku", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="customer_supplier_preferences", to="crm.sku")),
                ("supplier_sku", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="customer_preferences", to="crm.suppliersku")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_customer_supplier_preferences", to=settings.AUTH_USER_MODEL)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="updated_customer_supplier_preferences", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["customer__name", "sku__sku", "id"]},
        ),
        migrations.AddConstraint(
            model_name="customersupplierpreference",
            constraint=models.UniqueConstraint(fields=("customer", "sku"), name="customer_supplier_preference_unique"),
        ),
    ]
