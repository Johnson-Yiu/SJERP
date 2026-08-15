# Generated manually for product numbering and multi-category assignment.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0007_alter_productcategory_options_productcategory_parent_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductCodeSequence",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code_date", models.DateField(unique=True)),
                ("last_value", models.PositiveIntegerField(default=0)),
            ],
        ),
        migrations.AddField(
            model_name="product",
            name="additional_categories",
            field=models.ManyToManyField(blank=True, related_name="secondary_products", to="crm.productcategory", verbose_name="附加分类"),
        ),
    ]
