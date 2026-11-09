import django.db.models.deletion
from django.db import migrations, models


def preserve_bank_matches(apps, schema_editor):
    if apps.get_model("crm", "FinanceBankFactMatch").objects.using(schema_editor.connection.alias).exists():
        raise RuntimeError("已有跨模块银行核实记录，禁止回退丢失核实历史。")


class Migration(migrations.Migration):
    dependencies = [("crm", "0123_merge_finance_receipt_histories")]
    operations = [
        migrations.CreateModel(
            name="FinanceBankFactMatch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reason", models.TextField()),
                ("actor", models.JSONField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("event", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="account_fact_match", to="crm.rmbcashevent")),
                ("fact", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="bank_event_match", to="crm.financefact")),
            ],
        ),
        migrations.RunPython(migrations.RunPython.noop, preserve_bank_matches),
    ]
