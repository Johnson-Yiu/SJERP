from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("crm", "0012_quote_saved_pi_snapshots"),
    ]

    operations = [
        migrations.CreateModel(
            name="QuoteImportantNote",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("content", models.TextField()),
                ("is_active", models.BooleanField(default=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("root_quote", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="important_notes", to="crm.quote")),
                ("source_quote", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="sourced_important_notes", to="crm.quote")),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.AddIndex(
            model_name="quoteimportantnote",
            index=models.Index(fields=["root_quote", "-created_at"], name="crm_quoteim_root_qu_549bb5_idx"),
        ),
    ]
