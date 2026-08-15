from django.db import migrations, models


def migrate_customer_stages(apps, schema_editor):
    Customer = apps.get_model("crm", "Customer")
    for customer in Customer.objects.all():
        orders = customer.orders.exclude(status="cancelled").count()
        if orders > 1:
            stage = "company"
        elif orders == 1:
            stage = "customer"
        elif customer.quotes.exists():
            stage = "opportunity"
        elif customer.follow_ups.exclude(result="").exists() or customer.status == "active":
            stage = "contact"
        else:
            stage = "lead"
        Customer.objects.filter(pk=customer.pk).update(status=stage)


class Migration(migrations.Migration):
    dependencies = [("crm", "0002_inventorymovement_productcertificate_and_more")]

    operations = [
        migrations.AlterField(
            model_name="customer",
            name="status",
            field=models.CharField(
                choices=[
                    ("lead", "线索"),
                    ("contact", "联系人"),
                    ("opportunity", "商机"),
                    ("customer", "正式客户"),
                    ("company", "公司客户"),
                ],
                default="lead",
                max_length=20,
                verbose_name="状态",
            ),
        ),
        migrations.AlterField(
            model_name="followup",
            name="content",
            field=models.TextField(blank=True, verbose_name="跟进记录/解决方案"),
        ),
        migrations.AlterField(
            model_name="followup",
            name="result",
            field=models.CharField(blank=True, max_length=500, verbose_name="客户回复/客户疑问"),
        ),
        migrations.RunPython(migrate_customer_stages, migrations.RunPython.noop),
    ]
