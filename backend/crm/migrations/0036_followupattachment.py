from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0035_sku_display_name_key_sku_sku_display_name_key_unique"),
    ]

    operations = [
        migrations.CreateModel(
            name="FollowUpAttachment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("file", models.FileField(upload_to="follow-up-attachments/%Y/%m/", verbose_name="附件文件")),
                ("name", models.CharField(max_length=255, verbose_name="文件名")),
                ("content_type", models.CharField(blank=True, max_length=150, verbose_name="文件类型")),
                ("size", models.PositiveBigIntegerField(default=0, verbose_name="文件大小")),
                ("follow_up", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attachments", to="crm.followup")),
            ],
            options={"ordering": ["created_at", "id"]},
        ),
    ]
