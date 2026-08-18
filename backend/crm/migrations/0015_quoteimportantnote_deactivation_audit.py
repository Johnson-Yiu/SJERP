from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("crm", "0014_quote_parent_and_revision_summary")]

    operations = [
        migrations.AddField(
            model_name="quoteimportantnote",
            name="deactivated_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="失效时间"),
        ),
        migrations.AddField(
            model_name="quoteimportantnote",
            name="deactivated_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="deactivated_quote_important_notes",
                to=settings.AUTH_USER_MODEL,
                verbose_name="失效操作人",
            ),
        ),
    ]
