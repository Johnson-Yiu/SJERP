from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("crm", "0047_remove_purchasecostallocation_cost_allocation_target_valid_and_more")]
    operations = [
        migrations.AddField(model_name=model, name=name, field=models.CharField(label, max_length=100, blank=True))
        for model, name, label in [("customer", "region", "业务区域"), ("supplier", "region", "业务区域"), ("supplier", "country", "国家/地区")]
    ]
