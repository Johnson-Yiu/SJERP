from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


MODULES = [
    "dashboard", "customers", "contacts", "followups", "quotes", "orders", "products", "skus",
    "inventory", "parameters", "certificates", "categories", "transactions", "imports",
    "organization", "employees", "permissions",
]


def seed_permission_templates(apps, schema_editor):
    Unit = apps.get_model("crm", "OrganizationUnit")
    Position = apps.get_model("crm", "Position")
    Role = apps.get_model("crm", "AccessRole")
    Permission = apps.get_model("crm", "RolePermission")

    company = Unit.objects.create(name="森爵照明", code="SENJU", type="company", sort_order=0)
    departments = {}
    for order, (code, name) in enumerate([
        ("SALES", "销售部"), ("OPS", "运营部"), ("WAREHOUSE", "仓管部"),
        ("FINANCE", "财务部"), ("HR_ADMIN", "人事行政部"),
    ], 1):
        departments[code] = Unit.objects.create(name=name, code=code, type="department", parent=company, sort_order=order)

    position_rows = [
        ("SALES_MANAGER", "销售主管", "SALES", "supervisor"), ("SALESPERSON", "业务员", "SALES", "staff"), ("MERCHANDISER", "跟单", "SALES", "staff"),
        ("OPS_MANAGER", "运营主管", "OPS", "supervisor"), ("WEBSITE_OPS", "网站运营", "OPS", "staff"), ("PLATFORM_OPS", "平台运营", "OPS", "staff"),
        ("WAREHOUSE_MANAGER", "仓库主管", "WAREHOUSE", "supervisor"), ("WAREHOUSE_STAFF", "仓库员工", "WAREHOUSE", "staff"),
        ("FINANCE_MANAGER", "财务主管", "FINANCE", "supervisor"), ("FINANCE_STAFF", "财务员工", "FINANCE", "staff"),
        ("HR_ADMIN_MANAGER", "人事行政主管", "HR_ADMIN", "supervisor"), ("HR_STAFF", "人事", "HR_ADMIN", "staff"), ("ADMIN_STAFF", "行政", "HR_ADMIN", "staff"),
    ]
    for order, (code, name, unit_code, level) in enumerate(position_rows, 1):
        Position.objects.create(unit=departments[unit_code], code=code, name=name, level=level, sort_order=order)

    catalog_view = ["products", "skus", "parameters", "certificates", "categories"]
    sales_core = ["dashboard", "customers", "contacts", "followups", "quotes", "orders"]

    def grants(modules, actions):
        return {module: actions for module in modules}

    role_specs = [
        ("superadmin", "超级管理员", "all", "系统最高权限，可管理所有业务、成员和权限。", 1, grants(MODULES, "vcu dei")),
        ("admin", "管理员", "all", "负责日常系统配置与跨部门业务管理。", 2, grants(MODULES, "vcu dei")),
        ("sales_manager", "销售主管", "department_tree", "管理销售团队客户、报价、订单与业绩。", 10, {**grants(sales_core, "vcude"), **grants(catalog_view, "v"), "transactions": "v"}),
        ("salesperson", "业务员", "self", "维护本人客户、跟进、报价和订单。", 20, {**grants(sales_core, "vcu"), **grants(catalog_view, "v")}),
        ("merchandiser", "跟单", "self", "跟进已分配订单、交付与客户沟通。", 21, {"dashboard": "v", "customers": "v", "contacts": "v", "followups": "vcu", "quotes": "v", "orders": "vcu", **grants(catalog_view, "v"), "inventory": "v"}),
        ("ops_manager", "运营主管", "department_tree", "管理产品资料、网站及平台运营。", 30, {"dashboard": "v", **grants(catalog_view, "vcude"), "customers": "v", "quotes": "v", "orders": "v"}),
        ("website_ops", "网站运营", "self", "维护官网产品内容、参数与证书。", 31, {**grants(catalog_view, "vcu"), "customers": "v"}),
        ("platform_ops", "平台运营", "self", "维护平台产品内容并查看相关客户线索。", 32, {**grants(catalog_view, "vcu"), "customers": "v", "contacts": "v", "followups": "v"}),
        ("warehouse_manager", "仓库主管", "department_tree", "管理库存流水并查看订单交付信息。", 40, {"dashboard": "v", "orders": "v", "products": "v", "skus": "v", "inventory": "vcude"}),
        ("warehouse_staff", "仓库员工", "department", "登记出入库并查看相关订单。", 41, {"orders": "v", "products": "v", "skus": "v", "inventory": "vcu"}),
        ("finance_manager", "财务主管", "department_tree", "管理全部财务流水、订单回款及财务导出。", 50, {"dashboard": "v", "customers": "v", "quotes": "v", "orders": "v", "transactions": "vcude", "imports": "vi"}),
        ("finance_staff", "财务员工", "department", "登记财务流水并核对订单回款。", 51, {"customers": "v", "quotes": "v", "orders": "v", "transactions": "vcu"}),
        ("hr_admin_manager", "人事行政主管", "department_tree", "管理组织、岗位、成员档案及角色分配。", 60, {"dashboard": "v", "organization": "vcude", "employees": "vcude", "permissions": "vcu"}),
        ("hr_staff", "人事", "department", "维护组织和成员档案，不配置系统权限。", 61, {"organization": "v", "employees": "vcu"}),
        ("admin_staff", "行政", "department", "查看组织通讯录并维护行政资料。", 62, {"organization": "v", "employees": "v"}),
    ]

    for code, name, scope, description, priority, role_grants in role_specs:
        role = Role.objects.create(code=code, name=name, default_data_scope=scope, description=description, priority=priority, is_system=True)
        for module, actions in role_grants.items():
            normalized = actions.replace(" ", "")
            Permission.objects.create(
                role=role, module=module,
                can_view="v" in normalized, can_create="c" in normalized, can_update="u" in normalized,
                can_delete="d" in normalized, can_export="e" in normalized, can_import="i" in normalized,
            )


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("crm", "0003_customer_sales_stages"),
    ]

    operations = [
        migrations.CreateModel(
            name="AccessRole",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=100, verbose_name="角色名称")), ("code", models.CharField(max_length=50, unique=True, verbose_name="角色编码")),
                ("description", models.CharField(blank=True, max_length=300, verbose_name="角色说明")),
                ("default_data_scope", models.CharField(choices=[("all", "全部数据"), ("department_tree", "本部门及下级"), ("department", "本部门"), ("self", "仅本人负责")], default="self", max_length=30, verbose_name="默认数据范围")),
                ("priority", models.PositiveIntegerField(default=100, verbose_name="优先级")), ("is_system", models.BooleanField(default=False, verbose_name="系统预置")), ("active", models.BooleanField(default=True, verbose_name="启用")),
            ], options={"ordering": ["priority", "id"]},
        ),
        migrations.CreateModel(
            name="OrganizationUnit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=100, verbose_name="组织名称")), ("code", models.CharField(max_length=50, unique=True, verbose_name="组织编码")),
                ("type", models.CharField(choices=[("company", "公司"), ("department", "部门"), ("team", "小组")], default="department", max_length=20, verbose_name="组织类型")),
                ("sort_order", models.PositiveIntegerField(default=0, verbose_name="排序")), ("active", models.BooleanField(default=True, verbose_name="启用")),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="children", to="crm.organizationunit")),
            ], options={"ordering": ["sort_order", "id"]},
        ),
        migrations.CreateModel(
            name="Position",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=100, verbose_name="岗位名称")), ("code", models.CharField(max_length=50, unique=True, verbose_name="岗位编码")),
                ("level", models.CharField(choices=[("manager", "管理员"), ("supervisor", "主管"), ("staff", "员工")], default="staff", max_length=20, verbose_name="岗位级别")),
                ("sort_order", models.PositiveIntegerField(default=0, verbose_name="排序")), ("active", models.BooleanField(default=True, verbose_name="启用")),
                ("unit", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="positions", to="crm.organizationunit")),
            ], options={"ordering": ["sort_order", "id"]},
        ),
        migrations.CreateModel(
            name="RolePermission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("module", models.CharField(choices=[("dashboard", "经营概览"), ("customers", "客户管理"), ("contacts", "联系人"), ("followups", "跟进记录"), ("quotes", "报价管理"), ("orders", "订单管理"), ("products", "产品管理"), ("skus", "SKU 管理"), ("inventory", "库存流水"), ("parameters", "产品参数"), ("certificates", "产品证书"), ("categories", "产品分类"), ("transactions", "财务流水"), ("imports", "数据导入"), ("organization", "组织架构"), ("employees", "成员管理"), ("permissions", "权限配置")], max_length=30, verbose_name="功能模块")),
                ("can_view", models.BooleanField(default=True, verbose_name="查看")), ("can_create", models.BooleanField(default=False, verbose_name="新建")),
                ("can_update", models.BooleanField(default=False, verbose_name="修改")), ("can_delete", models.BooleanField(default=False, verbose_name="删除")),
                ("can_export", models.BooleanField(default=False, verbose_name="导出")), ("can_import", models.BooleanField(default=False, verbose_name="导入")),
                ("role", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="permissions", to="crm.accessrole")),
            ], options={"ordering": ["module"]},
        ),
        migrations.CreateModel(
            name="EmployeeProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
                ("display_name", models.CharField(max_length=100, verbose_name="姓名")),
                ("data_scope_override", models.CharField(choices=[("inherit", "跟随角色"), ("all", "全部数据"), ("department_tree", "本部门及下级"), ("department", "本部门"), ("self", "仅本人负责")], default="inherit", max_length=30, verbose_name="数据范围覆盖")),
                ("phone", models.CharField(blank=True, max_length=50, verbose_name="电话")), ("active", models.BooleanField(default=True, verbose_name="在职")),
                ("position", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="employees", to="crm.position")),
                ("roles", models.ManyToManyField(blank=True, related_name="employees", to="crm.accessrole")),
                ("unit", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="employees", to="crm.organizationunit")),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="employee_profile", to=settings.AUTH_USER_MODEL)),
            ], options={"ordering": ["unit__sort_order", "display_name"]},
        ),
        migrations.AddConstraint(model_name="organizationunit", constraint=models.UniqueConstraint(fields=("parent", "name"), name="unique_org_name_under_parent")),
        migrations.AddConstraint(model_name="rolepermission", constraint=models.UniqueConstraint(fields=("role", "module"), name="unique_role_module_permission")),
        migrations.RunPython(seed_permission_templates, migrations.RunPython.noop),
    ]
