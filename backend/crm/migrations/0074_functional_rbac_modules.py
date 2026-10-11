from django.db import migrations, models


MODULES = [
    ("dashboard", "经营概览"), ("reports", "报表中心"),
    ("customers", "客户管理"), ("contacts", "联系人"), ("followups", "跟进记录"),
    ("quotes", "报价管理"), ("orders", "订单管理"),
    ("suppliers", "供应商管理"), ("purchases", "采购管理"), ("inventory", "库存"),
    ("products", "产品管理"), ("skus", "SKU 管理"), ("categories", "产品分类"),
    ("parameters", "产品参数"), ("packaging", "包装管理"), ("trade_units", "交易单位"),
    ("certificates", "产品证书"), ("hs_codes", "HS 编码"),
    ("finance", "财务计划"), ("transactions", "财务流水"), ("imports", "数据导入"),
    ("organization", "组织架构"), ("employees", "成员管理"), ("permissions", "权限配置"),
]


def add_missing_modules(apps, schema_editor):
    Role = apps.get_model("crm", "AccessRole")
    Permission = apps.get_model("crm", "RolePermission")
    for role in Role.objects.all().iterator():
        existing = set(Permission.objects.filter(role_id=role.pk).values_list("module", flat=True))
        for module, _label in MODULES:
            if module not in existing:
                Permission.objects.create(
                    role_id=role.pk,
                    module=module,
                    can_view=False,
                    can_create=False,
                    can_update=False,
                    can_delete=False,
                    can_export=False,
                    can_import=False,
                )


class Migration(migrations.Migration):
    dependencies = [("crm", "0073_followup_next_follow_up_mode")]

    operations = [
        migrations.AlterField(
            model_name="rolepermission",
            name="module",
            field=models.CharField(
                choices=MODULES,
                max_length=30,
                verbose_name="功能模块",
            ),
        ),
        migrations.RunPython(add_missing_modules, migrations.RunPython.noop),
    ]
