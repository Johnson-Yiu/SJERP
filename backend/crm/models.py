from decimal import Decimal
import uuid
from django.utils import timezone

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.db import models, transaction

from .money import (
    CURRENT_AMOUNT_CALCULATION_VERSION,
    LEGACY_AMOUNT_CALCULATION_VERSION,
    document_total,
    legacy_document_total,
    money,
)


# Inventory movement types which reduce available stock.  Keep this list in
# one place so model properties and reporting code can stay in sync.
INVENTORY_OUTBOUND_TYPES = {
    "sale_out",
    "adjust_out",
    "sample_out",
    "transfer_out",
    "production_out",
    "other_out",
}


TAIL_GOODS_POLICY_CHOICES = [
    ("SAME_CARTON", "使用标准箱"),
    ("REPACK", "尾箱待确认"),
    ("MANUAL", "人工装箱"),
]


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class OperationLogQuerySet(models.QuerySet):
    """Prevent application-level updates/deletes of historical audit rows."""

    def update(self, **kwargs):
        raise ValidationError("操作日志只允许追加，历史审计不可修改。")

    def delete(self):
        raise ValidationError("操作日志只允许追加，历史审计不可删除。")

    def bulk_update(self, objs, fields, batch_size=None):
        raise ValidationError("操作日志只允许追加，历史审计不可批量修改。")


class OperationLog(models.Model):
    """Generic, append-only audit record for business data changes."""

    ACTION_CHOICES = [
        ("create", "创建"),
        ("update", "修改"),
        ("delete", "删除"),
        ("custom", "业务操作"),
    ]
    content_type = models.ForeignKey("contenttypes.ContentType", on_delete=models.PROTECT, related_name="operation_logs")
    object_id = models.CharField("对象 ID", max_length=100)
    entity = models.CharField("对象类型", max_length=100, db_index=True)
    entity_label = models.CharField("对象类型名称", max_length=100, blank=True)
    object_label = models.CharField("对象名称", max_length=300, blank=True)
    action = models.CharField("操作类型", max_length=30, choices=ACTION_CHOICES, default="custom")
    action_label = models.CharField("操作说明", max_length=100, blank=True)
    # Deleting an operator must not cause the database to rewrite this row
    # through ON DELETE SET NULL; historical identity is part of the audit.
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="operation_logs")
    changed_fields = models.JSONField("变更字段", default=list, blank=True)
    before_data = models.JSONField("变更前数据", default=dict, blank=True)
    after_data = models.JSONField("变更后数据", default=dict, blank=True)
    metadata = models.JSONField("操作元数据", default=dict, blank=True)
    request_method = models.CharField("请求方法", max_length=10, blank=True)
    request_path = models.CharField("请求路径", max_length=500, blank=True)
    created_at = models.DateTimeField("操作时间", auto_now_add=True)

    objects = OperationLogQuerySet.as_manager()

    def save(self, *args, **kwargs):
        if self.pk and not self._state.adding:
            raise ValidationError("操作日志只允许追加，历史审计不可修改。")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("操作日志只允许追加，历史审计不可删除。")

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["entity", "object_id", "created_at"]),
            models.Index(fields=["operator", "created_at"]),
        ]


class FulfillmentIdempotency(TimestampedModel):
    """Persist the request identity for receiving and shipment commands.

    The row is created in the same transaction as the fulfillment side
    effects.  A unique key therefore serializes concurrent retries without
    relying on a browser button state, while the request hash prevents a key
    from being silently reused for different business content.
    """

    STATUS_CHOICES = [("processing", "处理中"), ("succeeded", "已完成")]
    key = models.CharField("请求标识", max_length=128, unique=True)
    operation = models.CharField("业务操作", max_length=20)
    target_id = models.PositiveBigIntegerField("目标对象 ID")
    request_hash = models.CharField("请求内容摘要", max_length=64)
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="fulfillment_idempotency_records",
    )
    status = models.CharField("处理状态", max_length=20, choices=STATUS_CHOICES, default="processing")
    response_status = models.PositiveSmallIntegerField("响应状态码", default=201)
    response_payload = models.JSONField("原始业务响应", default=dict)

    class Meta:
        indexes = [
            models.Index(fields=["operation", "target_id"], name="crm_fi_op_target_idx"),
            models.Index(fields=["operator", "created_at"], name="crm_fi_operator_created_idx"),
        ]

class CSVImportAuditQuerySet(models.QuerySet):
    """Keep CSV import history append-only at the application boundary."""

    def update(self, **kwargs):
        raise ValidationError("CSV 导入审计只允许追加，历史记录不可修改。")

    def delete(self):
        raise ValidationError("CSV 导入审计只允许追加，历史记录不可删除。")

    def bulk_update(self, objs, fields, batch_size=None):
        raise ValidationError("CSV 导入审计只允许追加，历史记录不可批量修改。")


class CSVImportBatch(models.Model):
    """One immutable, authenticated CSV import attempt."""

    STATUS_CHOICES = [
        ("succeeded", "成功"),
        ("failed", "失败"),
    ]

    batch_id = models.UUIDField("批次标识", default=uuid.uuid4, unique=True, editable=False)
    entity = models.CharField("数据类型", max_length=30)
    file_sha256 = models.CharField("文件 SHA256", max_length=64)
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="csv_import_batches",
    )
    preview = models.ForeignKey(
        "CSVImportPreviewAudit",
        on_delete=models.PROTECT,
        related_name="batches",
        null=True,
        blank=True,
    )
    status = models.CharField("批次状态", max_length=20, choices=STATUS_CHOICES)
    total_rows = models.PositiveIntegerField("总行数", default=0)
    created_rows = models.PositiveIntegerField("创建行数", default=0)
    updated_rows = models.PositiveIntegerField("更新行数", default=0)
    failed_rows = models.PositiveIntegerField("失败行数", default=0)
    failure_reason = models.TextField("失败原因", blank=True)
    created_at = models.DateTimeField("操作时间", auto_now_add=True)

    objects = CSVImportAuditQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["entity", "created_at"]),
            models.Index(fields=["operator", "created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def save(self, *args, **kwargs):
        if self.pk and not self._state.adding:
            raise ValidationError("CSV 导入审计只允许追加，历史记录不可修改。")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("CSV 导入审计只允许追加，历史记录不可删除。")

    def __str__(self):
        return str(self.batch_id)


class CSVImportRowAudit(models.Model):
    """Immutable row-level result linked to its CSVImportBatch."""

    RESULT_CHOICES = [
        ("created", "创建"),
        ("updated", "更新"),
        ("failed", "失败"),
    ]

    batch = models.ForeignKey(
        CSVImportBatch,
        on_delete=models.PROTECT,
        related_name="rows",
    )
    row_number = models.PositiveIntegerField("CSV 行号")
    business_key = models.CharField("业务主键", max_length=255)
    object_id = models.CharField("业务对象 ID", max_length=100, blank=True)
    result = models.CharField("处理结果", max_length=20, choices=RESULT_CHOICES)
    before_data = models.JSONField("更新前快照", default=dict, blank=True)
    after_data = models.JSONField("更新后快照", default=dict, blank=True)
    error_message = models.TextField("错误信息", blank=True)
    created_at = models.DateTimeField("记录时间", auto_now_add=True)

    objects = CSVImportAuditQuerySet.as_manager()

    class Meta:
        ordering = ["row_number", "id"]
        constraints = [
            models.UniqueConstraint(fields=["batch", "row_number"], name="crm_csv_import_batch_row_unique"),
        ]
        indexes = [
            models.Index(fields=["batch", "result"]),
            models.Index(fields=["business_key"]),
        ]

    def save(self, *args, **kwargs):
        if self.pk and not self._state.adding:
            raise ValidationError("CSV 导入审计只允许追加，历史记录不可修改。")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("CSV 导入审计只允许追加，历史记录不可删除。")


class CSVImportPreviewAudit(models.Model):
    """Immutable preview event; it never represents a formal business import."""

    STATUS_CHOICES = [
        ("ready", "可执行"),
        ("invalid", "校验未通过"),
        ("failed", "解析失败"),
    ]

    preview_id = models.UUIDField("预览标识", default=uuid.uuid4, unique=True, editable=False)
    entity = models.CharField("数据类型", max_length=30)
    file_sha256 = models.CharField("文件 SHA256", max_length=64, blank=True)
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="csv_import_previews",
        null=True,
        blank=True,
    )
    retry_of_batch = models.ForeignKey(
        CSVImportBatch,
        on_delete=models.PROTECT,
        related_name="retry_previews",
        null=True,
        blank=True,
    )
    endpoint = models.CharField("预览入口", max_length=120, blank=True)
    status = models.CharField("预览结果", max_length=20, choices=STATUS_CHOICES)
    total_rows = models.PositiveIntegerField("解析行数", default=0)
    validation_errors = models.JSONField("预览校验错误", default=list, blank=True)
    failure_reason = models.TextField("失败原因", blank=True)
    created_at = models.DateTimeField("操作时间", auto_now_add=True)

    objects = CSVImportAuditQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["entity", "created_at"], name="crm_csvimpo_entity_37832f_idx"),
            models.Index(fields=["operator", "created_at"], name="crm_csvimpo_operato_7cba16_idx"),
            models.Index(fields=["status", "created_at"], name="crm_csvimpo_status_6ee3f2_idx"),
        ]

    def save(self, *args, **kwargs):
        if self.pk and not self._state.adding:
            raise ValidationError("CSV 导入审计只允许追加，历史记录不可修改。")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("CSV 导入审计只允许追加，历史记录不可删除。")


class SharedReportTemplate(TimestampedModel):
    """A validated report query definition shared with the reporting team."""

    name = models.CharField("模板名称", max_length=80)
    description = models.CharField("模板说明", max_length=300, blank=True)
    config = models.JSONField("报表配置", default=dict)
    published = models.BooleanField("已发布", default=False, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_shared_report_templates",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_shared_report_templates",
    )
    published_at = models.DateTimeField("发布时间", null=True, blank=True)
    config_version = models.PositiveIntegerField("配置版本", default=1)

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [
            models.Index(fields=["published", "updated_at"]),
            models.Index(fields=["created_by", "updated_at"]),
        ]

    def __str__(self):
        return self.name


class OrganizationUnit(TimestampedModel):
    TYPE_CHOICES = [("company", "公司"), ("department", "部门"), ("team", "小组")]
    name = models.CharField("组织名称", max_length=100)
    code = models.CharField("组织编码", max_length=50, unique=True)
    type = models.CharField("组织类型", max_length=20, choices=TYPE_CHOICES, default="department")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children")
    sort_order = models.PositiveIntegerField("排序", default=0)
    active = models.BooleanField("启用", default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [models.UniqueConstraint(fields=["parent", "name"], name="unique_org_name_under_parent")]

    def __str__(self):
        return self.name


class Position(TimestampedModel):
    LEVEL_CHOICES = [("manager", "管理员"), ("supervisor", "主管"), ("staff", "员工")]
    unit = models.ForeignKey(OrganizationUnit, on_delete=models.CASCADE, related_name="positions")
    name = models.CharField("岗位名称", max_length=100)
    code = models.CharField("岗位编码", max_length=50, unique=True)
    level = models.CharField("岗位级别", max_length=20, choices=LEVEL_CHOICES, default="staff")
    sort_order = models.PositiveIntegerField("排序", default=0)
    active = models.BooleanField("启用", default=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.unit.name} · {self.name}"


class AccessRole(TimestampedModel):
    DATA_SCOPE_CHOICES = [
        ("all", "全部数据"),
        ("department_tree", "本部门及下级"),
        ("department", "本部门"),
        ("self", "仅本人负责"),
    ]
    name = models.CharField("角色名称", max_length=100)
    code = models.CharField("角色编码", max_length=50, unique=True)
    description = models.CharField("角色说明", max_length=300, blank=True)
    default_data_scope = models.CharField("默认数据范围", max_length=30, choices=DATA_SCOPE_CHOICES, default="self")
    priority = models.PositiveIntegerField("优先级", default=100)
    is_system = models.BooleanField("系统预置", default=False)
    active = models.BooleanField("启用", default=True)

    class Meta:
        ordering = ["priority", "id"]

    def __str__(self):
        return self.name


class RolePermission(models.Model):
    MODULE_CHOICES = [
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
    role = models.ForeignKey(AccessRole, on_delete=models.CASCADE, related_name="permissions")
    module = models.CharField("功能模块", max_length=30, choices=MODULE_CHOICES)
    can_view = models.BooleanField("查看", default=False)
    can_create = models.BooleanField("新建", default=False)
    can_update = models.BooleanField("修改", default=False)
    can_delete = models.BooleanField("删除", default=False)
    can_export = models.BooleanField("导出", default=False)
    can_import = models.BooleanField("导入", default=False)

    class Meta:
        ordering = ["module"]
        constraints = [models.UniqueConstraint(fields=["role", "module"], name="unique_role_module_permission")]


class EmployeeProfile(TimestampedModel):
    DATA_SCOPE_CHOICES = [("inherit", "跟随角色")] + AccessRole.DATA_SCOPE_CHOICES
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="employee_profile")
    display_name = models.CharField("姓名", max_length=100)
    unit = models.ForeignKey(OrganizationUnit, on_delete=models.PROTECT, related_name="employees")
    position = models.ForeignKey(Position, on_delete=models.PROTECT, related_name="employees")
    roles = models.ManyToManyField(AccessRole, related_name="employees", blank=True)
    data_scope_override = models.CharField("数据范围覆盖", max_length=30, choices=DATA_SCOPE_CHOICES, default="inherit")
    phone = models.CharField("电话", max_length=50, blank=True)
    active = models.BooleanField("在职", default=True)

    class Meta:
        ordering = ["unit__sort_order", "display_name"]

    def __str__(self):
        return self.display_name


class Customer(TimestampedModel):
    STATUS_CHOICES = [
        ("lead", "线索"),
        ("contact", "联系人"),
        ("opportunity", "商机"),
        ("customer", "正式客户"),
        ("company", "公司客户"),
    ]
    name = models.CharField("客户名称", max_length=200, unique=True)
    code = models.CharField("客户编号", max_length=30, unique=True)
    country = models.CharField("国家/地区", max_length=100, blank=True)
    region = models.CharField("业务区域", max_length=100, blank=True)
    source = models.CharField("客户来源", max_length=100, blank=True)
    status = models.CharField("状态", max_length=20, choices=STATUS_CHOICES, default="lead")
    owner = models.CharField("负责人", max_length=100, blank=True)
    owner_profile = models.ForeignKey(
        "EmployeeProfile", verbose_name="负责人账号", null=True, blank=True,
        on_delete=models.PROTECT, related_name="owned_customers", db_index=True,
    )
    website = models.URLField("网站", blank=True)
    address = models.TextField("地址", blank=True)
    notes = models.TextField("备注", blank=True)
    next_follow_up = models.DateField("下次跟进", null=True, blank=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.name


class CustomerCodeSequence(models.Model):
    """全公司共用的客户编号流水，不随日期重置。"""
    last_value = models.IntegerField(default=-1)


class Contact(TimestampedModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="contacts")
    name = models.CharField("姓名", max_length=100)
    title = models.CharField("职位", max_length=100, blank=True)
    email = models.EmailField("邮箱", blank=True)
    phone = models.CharField("电话", max_length=50, blank=True)
    whatsapp = models.CharField("WhatsApp", max_length=50, blank=True)
    is_primary = models.BooleanField("主联系人", default=False)
    notes = models.TextField("备注", blank=True)

    class Meta:
        ordering = ["-is_primary", "name"]

    def __str__(self):
        return f"{self.customer.name} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.pk and not Contact.objects.filter(customer_id=self.customer_id).exists():
            self.is_primary = True
        super().save(*args, **kwargs)
        if self.is_primary:
            Contact.objects.filter(customer_id=self.customer_id).exclude(pk=self.pk).update(is_primary=False)


class FollowUp(TimestampedModel):
    TYPE_CHOICES = [("email", "邮件"), ("call", "电话"), ("message", "即时通讯"), ("meeting", "会议"), ("visit", "拜访"), ("other", "其他")]
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="follow_ups")
    contact = models.ForeignKey(Contact, on_delete=models.SET_NULL, null=True, blank=True, related_name="follow_ups")
    followed_at = models.DateTimeField("跟进时间")
    type = models.CharField("方式", max_length=20, choices=TYPE_CHOICES, default="email")
    subject = models.CharField("主题", max_length=200, blank=True, default="")
    content = models.TextField("跟进记录/解决方案", blank=True)
    result = models.CharField("客户回复/客户疑问", max_length=500, blank=True)
    next_action = models.CharField("下一步", max_length=200, blank=True)
    NEXT_FOLLOW_UP_MODE_CHOICES = [("keep", "保留当前计划"), ("set", "设置新的跟进日期"), ("clear", "暂不安排后续跟进")]
    next_follow_up_mode = models.CharField("下次跟进安排", max_length=5, choices=NEXT_FOLLOW_UP_MODE_CHOICES, default="keep")
    next_follow_up = models.DateField("下次跟进", null=True, blank=True)
    owner = models.CharField("跟进人", max_length=100, blank=True)

    class Meta:
        ordering = ["-followed_at"]


class FollowUpAttachment(TimestampedModel):
    follow_up = models.ForeignKey(FollowUp, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField("附件文件", upload_to="follow-up-attachments/%Y/%m/")
    name = models.CharField("文件名", max_length=255)
    content_type = models.CharField("文件类型", max_length=150, blank=True)
    size = models.PositiveBigIntegerField("文件大小", default=0)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return self.name


class ProductCategory(TimestampedModel):
    name = models.CharField("分类名称", max_length=100, unique=True)
    description = models.TextField("说明", blank=True)
    parent = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="children", verbose_name="上级分类")
    sort_order = models.PositiveIntegerField("同级排序", default=0)

    class Meta:
        verbose_name_plural = "产品分类"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.name


class CategoryAttribute(TimestampedModel):
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, related_name="attributes")
    name = models.CharField("属性名称", max_length=100)
    key = models.CharField("属性编码", max_length=50)
    default_value = models.CharField("默认值", max_length=200, blank=True)
    unit = models.CharField("单位", max_length=30, blank=True)
    include_in_sku = models.BooleanField("参与 SKU 命名", default=False)
    include_in_sales_model = models.BooleanField("参与生成型号", default=False)
    uppercase = models.BooleanField("SKU 中转为大写", default=False)
    required = models.BooleanField("创建 SKU 时必填", default=False)
    sort_order = models.PositiveIntegerField("排序", default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [models.UniqueConstraint(fields=["category", "key"], name="unique_category_attribute_key")]

    def __str__(self):
        return f"{self.category.name} · {self.name}"


class ProductCodeSequence(models.Model):
    code_date = models.DateField(unique=True)
    last_value = models.PositiveIntegerField(default=0)


class HSCode(TimestampedModel):
    """Controlled customs-code catalog assigned to products by administrators."""
    code = models.CharField("HS 编码", max_length=30, unique=True)
    description = models.CharField("商品描述", max_length=300, blank=True)
    notes = models.TextField("备注", blank=True)
    active = models.BooleanField("启用", default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return self.code


class SKUCodeSequence(models.Model):
    last_value = models.PositiveIntegerField(default=0)


class Product(TimestampedModel):
    STATUS_CHOICES = [("active", "在售"), ("development", "开发中"), ("discontinued", "停产")]
    name = models.CharField("产品名称", max_length=200)
    name_en = models.CharField("产品英文名称", max_length=200, blank=True)
    hs_code = models.ForeignKey(HSCode, on_delete=models.PROTECT, null=True, blank=True, related_name="products", verbose_name="HS 编码")
    code = models.CharField("产品编号", max_length=50, unique=True)
    combination_rules = models.JSONField("SKU 组合规则", default=list, blank=True)
    sales_model_prefix = models.CharField("销售型号前缀", max_length=30, unique=True, null=True, blank=True)
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")
    additional_categories = models.ManyToManyField(ProductCategory, blank=True, related_name="secondary_products", verbose_name="附加分类")
    suppliers = models.ManyToManyField("Supplier", blank=True, related_name="products", verbose_name="供应商")
    description = models.TextField("描述", blank=True)
    status = models.CharField("状态", max_length=20, choices=STATUS_CHOICES, default="active")

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} {self.name}"


class SKU(TimestampedModel):
    schema_version = models.PositiveIntegerField(default=0, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="skus")
    sku = models.CharField("SKU", max_length=80, unique=True)
    specification = models.CharField("规格", max_length=200, blank=True)
    display_name_cn = models.CharField("内部中文显示名称", max_length=300, blank=True)
    display_name_key = models.CharField("内部名称规范化键", max_length=300, blank=True, null=True, editable=False, db_index=True)
    sales_model = models.CharField("对外商业型号", max_length=80, unique=True, null=True, blank=True)
    sales_model_abbreviations = models.JSONField("销售型号参数缩写", default=dict, blank=True)
    description_cn = models.TextField("中文描述", blank=True)
    description_en = models.TextField("英文描述", blank=True)
    unit = models.CharField("单位", max_length=30, default="pcs")
    cost_price = models.DecimalField("成本价", max_digits=14, decimal_places=4, default=0)
    default_price = models.DecimalField("默认售价", max_digits=14, decimal_places=4, default=0)
    currency = models.CharField("币种", max_length=10, default="USD")
    active = models.BooleanField("启用", default=True)
    parameter_values = models.JSONField("参数快照", default=dict, blank=True)
    identity_signature = models.CharField("身份参数签名", max_length=500, blank=True, db_index=True)
    product_details = models.JSONField("产品明细", default=list, blank=True)
    image = models.ImageField("SKU 图片", upload_to="sku-images/%Y/%m/", blank=True)

    class Meta:
        ordering = ["sku"]
        constraints = [
            models.UniqueConstraint(fields=["display_name_key"], name="sku_display_name_key_unique"),
        ]

    def save(self, *args, **kwargs):
        if not self.sku:
            from .sku_numbers import allocate_sku_code

            self.sku = allocate_sku_code()
        if self.pk:
            original_sku = SKU.objects.filter(pk=self.pk).values_list("sku", flat=True).first()
            if original_sku is not None and self.sku != original_sku:
                raise ValidationError({"sku": "SKU Code 创建后不可修改。"})
        display_name_was_blank = not self.display_name_cn
        if self.product_id and (not self.display_name_cn or not self.description_cn or not self.description_en):
            from .sku_identity import build_sku_identity

            generated = build_sku_identity(
                self.product,
                self.specification,
                self.parameter_values,
                self.product_details,
            )
            self.display_name_cn = self.display_name_cn or generated["display_name_cn"]
            self.description_cn = self.description_cn or generated["description_cn"]
            self.description_en = self.description_en or generated["description_en"]
        from .sku_identity import normalize_display_name

        normalized_name = normalize_display_name(self.display_name_cn)
        if normalized_name:
            duplicate_name = SKU.objects.filter(display_name_key=normalized_name).exclude(pk=self.pk).exists()
            if duplicate_name:
                if not display_name_was_blank:
                    raise ValidationError({"display_name_cn": "内部识别名称已存在（不区分大小写）。"})
                suffix = f" · {self.sku}"
                base = str(self.display_name_cn or "SKU").strip()
                candidate = f"{base[: max(1, 300 - len(suffix))]}{suffix}"
                candidate_key = normalize_display_name(candidate)
                sequence = 2
                while SKU.objects.filter(display_name_key=candidate_key).exclude(pk=self.pk).exists():
                    suffix = f" · {self.sku}-{sequence}"
                    candidate = f"{base[: max(1, 300 - len(suffix))]}{suffix}"
                    candidate_key = normalize_display_name(candidate)
                    sequence += 1
                self.display_name_cn = candidate
                normalized_name = candidate_key
            self.display_name_key = normalized_name
        else:
            self.display_name_key = None
        super().save(*args, **kwargs)

    def __str__(self):
        return self.display_name_cn or self.sku


class SKUVersion(models.Model):
    """An immutable copy of the SKU state immediately before a material change."""
    sku = models.ForeignKey(SKU, on_delete=models.CASCADE, related_name="versions")
    version_no = models.PositiveIntegerField("版本号")
    sku_code_snapshot = models.CharField("SKU 编码快照", max_length=80)
    sales_model_snapshot = models.CharField("销售型号快照", max_length=80, blank=True)
    display_name_cn_snapshot = models.CharField("内部名称快照", max_length=300, blank=True)
    description_cn_snapshot = models.TextField("中文描述快照", blank=True)
    description_en_snapshot = models.TextField("英文描述快照", blank=True)
    parameter_values_snapshot = models.JSONField("参数快照", default=dict)
    product_details_snapshot = models.JSONField("产品明细快照", default=list)
    specification_snapshot = models.CharField("规格快照", max_length=200, blank=True)
    changed_fields = models.JSONField("变更字段", default=list)
    changed_at = models.DateTimeField("变更时间", default=timezone.now)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="sku_versions")
    change_reason = models.CharField("变更说明", max_length=300, blank=True)

    class Meta:
        ordering = ["-version_no"]
        constraints = [models.UniqueConstraint(fields=["sku", "version_no"], name="unique_sku_version_no")]


class SKUParameterPlan(TimestampedModel):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="sku_parameter_plans")
    version = models.PositiveIntegerField()
    status = models.CharField(max_length=12, default="draft", choices=[("draft", "草稿"), ("published", "已发布")])
    definitions = models.JSONField(default=list)
    assignments = models.JSONField(default=dict, blank=True)
    baseline = models.CharField(max_length=64)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["product", "version"], name="product_sku_plan_version_unique")]


class SKURelationship(TimestampedModel):
    source = models.ForeignKey(SKU, on_delete=models.PROTECT, related_name="successors")
    target = models.ForeignKey(SKU, on_delete=models.PROTECT, related_name="predecessors")
    plan = models.ForeignKey(SKUParameterPlan, on_delete=models.PROTECT, related_name="relationships")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["source", "target"], name="sku_relationship_unique")]


class SupplierCapability(TimestampedModel):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="supplier_capabilities")
    supplier = models.ForeignKey("Supplier", on_delete=models.PROTECT, related_name="capabilities")
    name = models.CharField(max_length=120)
    filters = models.JSONField(default=dict, blank=True)
    characteristics = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)


class SupplierCandidateOverride(TimestampedModel):
    sku = models.ForeignKey(SKU, on_delete=models.PROTECT, related_name="candidate_overrides")
    supplier = models.ForeignKey("Supplier", on_delete=models.PROTECT)
    is_allowed = models.BooleanField(default=True)
    characteristics = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["sku", "supplier"], name="sku_supplier_override_unique")]


class PackagingTemplate(TimestampedModel):
    """Reusable physical carton specification. Dimensions are stored in cm."""
    PARTIAL_POLICIES = TAIL_GOODS_POLICY_CHOICES
    code = models.CharField("包装模板编码", max_length=50, unique=True, blank=True)
    name = models.CharField("包装模板名称", max_length=120)
    supplier = models.ForeignKey("Supplier", on_delete=models.SET_NULL, null=True, blank=True, related_name="packaging_templates", verbose_name="包装供应商")
    description = models.TextField("说明", blank=True)
    carton_length = models.DecimalField("箱长(cm)", max_digits=10, decimal_places=2)
    carton_width = models.DecimalField("箱宽(cm)", max_digits=10, decimal_places=2)
    carton_height = models.DecimalField("箱高(cm)", max_digits=10, decimal_places=2)
    # 新建资料的装箱数由 SKU 包装档案维护；此字段只保留旧模板的历史兜底值。
    qty_per_carton = models.DecimalField("每箱数量（历史）", max_digits=14, decimal_places=2, null=True, blank=True)
    carton_tare_weight = models.DecimalField("纸箱皮重(kg)", max_digits=12, decimal_places=3, default=0)
    partial_carton_policy = models.CharField("尾货策略", max_length=20, choices=PARTIAL_POLICIES, default="SAME_CARTON")
    active = models.BooleanField("启用", default=True)

    class Meta:
        ordering = ["code"]
        constraints = [
            models.CheckConstraint(condition=models.Q(carton_length__gt=0), name="pack_template_length_positive"),
            models.CheckConstraint(condition=models.Q(carton_width__gt=0), name="pack_template_width_positive"),
            models.CheckConstraint(condition=models.Q(carton_height__gt=0), name="pack_template_height_positive"),
            models.CheckConstraint(condition=models.Q(carton_tare_weight__gte=0), name="pack_template_tare_non_negative"),
        ]

    def save(self, *args, **kwargs):
        if not self.code:
            prefix = f"PKG-{timezone.localdate():%Y%m%d}-"
            latest = self.__class__.objects.filter(code__startswith=prefix).order_by("-code").values_list("code", flat=True).first()
            try:
                sequence = int(latest.rsplit("-", 1)[-1]) + 1 if latest else 1
            except (ValueError, IndexError):
                sequence = 1
            self.code = f"{prefix}{sequence:04d}"
        super().save(*args, **kwargs)

    @property
    def cbm(self):
        return (Decimal(str(self.carton_length)) * Decimal(str(self.carton_width)) * Decimal(str(self.carton_height)) / Decimal("1000000")).quantize(Decimal("0.000001"))


class SKUPackagingProfile(TimestampedModel):
    """SKU defaults: only values which differ from its shared template are saved here."""
    sku = models.OneToOneField(SKU, on_delete=models.CASCADE, related_name="packaging_profile")
    packaging_template = models.ForeignKey(PackagingTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name="sku_profiles")
    unit_net_weight = models.DecimalField("单件净重(kg)", max_digits=12, decimal_places=3, null=True, blank=True)
    qty_per_carton_override = models.DecimalField("每箱数量覆盖", max_digits=14, decimal_places=2, null=True, blank=True)
    carton_length_override = models.DecimalField("箱长覆盖(cm)", max_digits=10, decimal_places=2, null=True, blank=True)
    carton_width_override = models.DecimalField("箱宽覆盖(cm)", max_digits=10, decimal_places=2, null=True, blank=True)
    carton_height_override = models.DecimalField("箱高覆盖(cm)", max_digits=10, decimal_places=2, null=True, blank=True)
    carton_tare_weight_override = models.DecimalField("纸箱皮重覆盖(kg)", max_digits=12, decimal_places=3, null=True, blank=True)
    gross_weight_override = models.DecimalField("整箱预计毛重覆盖(kg)", max_digits=12, decimal_places=3, null=True, blank=True)
    verified_at = models.DateTimeField("验证时间", null=True, blank=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="verified_sku_packaging_profiles")

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(unit_net_weight__gte=0) | models.Q(unit_net_weight__isnull=True), name="sku_pack_unit_weight_non_negative"),
            models.CheckConstraint(condition=models.Q(qty_per_carton_override__gt=0) | models.Q(qty_per_carton_override__isnull=True), name="sku_pack_qty_positive"),
            models.CheckConstraint(condition=models.Q(carton_tare_weight_override__gte=0) | models.Q(carton_tare_weight_override__isnull=True), name="sku_pack_tare_non_negative"),
        ]


class QuoteNumberSequence(models.Model):
    quote_date = models.DateField()
    country_code = models.CharField(max_length=2)
    last_value = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["quote_date", "country_code"], name="unique_quote_number_sequence")]


class DocumentNumberSequence(models.Model):
    DOCUMENT_TYPE_CHOICES = [("SO", "销售订单"), ("PO", "采购订单")]

    document_type = models.CharField(max_length=2, choices=DOCUMENT_TYPE_CHOICES)
    year = models.PositiveSmallIntegerField()
    last_value = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["document_type", "year"],
                name="unique_document_number_sequence",
            ),
        ]


class ProductParameter(TimestampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="parameters")
    group = models.CharField("参数分组", max_length=100, blank=True, default="基础参数")
    name = models.CharField("参数名称", max_length=100)
    value = models.CharField("参数值", max_length=300)
    unit = models.CharField("单位", max_length=30, blank=True)
    sort_order = models.PositiveIntegerField("排序", default=0)

    class Meta:
        ordering = ["group", "sort_order", "id"]
        constraints = [models.UniqueConstraint(fields=["product", "group", "name"], name="unique_product_parameter")]

    def __str__(self):
        return f"{self.product.code} · {self.name}"


class ProductCertificate(TimestampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="certificates")
    name = models.CharField("证书名称", max_length=150)
    certificate_no = models.CharField("证书编号", max_length=100, blank=True)
    issuer = models.CharField("签发机构", max_length=150, blank=True)
    issued_date = models.DateField("签发日期", null=True, blank=True)
    expires_on = models.DateField("有效期至", null=True, blank=True)
    file = models.FileField("私有证书文件", upload_to="product-certificates/%Y/%m/", blank=True)
    # Kept only as a legacy migration field. New API responses never expose or
    # accept this external URL because it cannot inherit ERP permissions.
    file_url = models.URLField("文件链接", blank=True)
    notes = models.TextField("备注", blank=True)

    class Meta:
        ordering = ["-expires_on", "name"]

    def __str__(self):
        return f"{self.product.code} · {self.name}"


class QuoteTemplateAssetQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("已保存的报价模板资源不可修改。")

    def delete(self):
        raise ValidationError("已保存的报价模板资源不可删除。")


class QuoteTemplateAsset(models.Model):
    digest = models.CharField(max_length=64, primary_key=True)
    snapshot = models.JSONField()
    objects = QuoteTemplateAssetQuerySet.as_manager()

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("已保存的报价模板资源不可修改。")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("已保存的报价模板资源不可删除。")


class Quote(TimestampedModel):
    STATUS_CHOICES = [("draft", "草稿"), ("sent", "已发送"), ("accepted", "已接受"), ("rejected", "已拒绝"), ("expired", "已过期")]
    quote_no = models.CharField("报价单号", max_length=120, unique=True)
    root_quote = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="revisions",
        verbose_name="原始报价",
    )
    parent_quote = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="child_revisions",
        verbose_name="直接来源报价",
    )
    revision_no = models.PositiveSmallIntegerField("修订号", default=0, validators=[MaxValueValidator(99)])
    revision_summary = models.CharField("修订说明", max_length=500, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="quotes")
    buyer_company_name = models.CharField("买方公司快照", max_length=200, blank=True)
    pi_template_snapshots = models.JSONField(default=dict, editable=False)
    quote_date = models.DateField("报价日期")
    valid_until = models.DateField("有效期至", null=True, blank=True)
    status = models.CharField("状态", max_length=20, choices=STATUS_CHOICES, default="draft")
    currency = models.CharField("币种", max_length=10, default="USD")
    exchange_rate = models.DecimalField("对人民币汇率", max_digits=12, decimal_places=6, default=1)
    shipping_fee = models.DecimalField("运费", max_digits=14, decimal_places=4, default=0)
    discount = models.DecimalField("折扣金额", max_digits=14, decimal_places=4, default=0)
    notes = models.TextField("条款/备注", blank=True)
    recipient_name = models.CharField("收件人", max_length=200, blank=True)
    buyer_address = models.TextField("买方地址", blank=True)
    buyer_email = models.EmailField("买方邮箱", blank=True)
    buyer_phone = models.CharField("买方电话", max_length=100, blank=True)
    lead_time_days = models.PositiveIntegerField("交期（天）", null=True, blank=True)
    deposit_ratio = models.DecimalField("定金比例", max_digits=6, decimal_places=4, default=0)
    trading_terms = models.TextField("贸易条款", blank=True)
    shipping_details = models.TextField("运输信息", blank=True)
    amount_calculation_version = models.PositiveSmallIntegerField(default=CURRENT_AMOUNT_CALCULATION_VERSION, editable=False)

    class Meta:
        ordering = ["-quote_date", "-id"]

    def __init__(self, *args, **kwargs):
        # Keep an explicitly unknown buyer distinct from an omitted new-quote
        # default. Positional fields are supplied too (including ORM loading).
        buyer_index = next(
            index for index, field in enumerate(self._meta.concrete_fields)
            if field.attname == "buyer_company_name"
        )
        self._buyer_company_name_supplied = (
            "buyer_company_name" in kwargs or len(args) > buyer_index
        )
        template_index = next(
            index for index, field in enumerate(self._meta.concrete_fields)
            if field.attname == "pi_template_snapshots"
        )
        self._pi_template_supplied = "pi_template_snapshots" in kwargs or len(args) > template_index
        super().__init__(*args, **kwargs)

    @transaction.atomic
    def save(self, *args, **kwargs):
        if self._state.adding and not self._pi_template_supplied:
            if self.parent_quote_id:
                self.pi_template_snapshots = self.parent_quote.pi_template_snapshots
            else:
                from .quote_template_snapshot import capture_template
                snapshots = {key: capture_template(key) for key in (
                    "standard_en_no_discount", "standard_en_with_discount"
                )}
                self.pi_template_snapshots = {}
                for key, snapshot in snapshots.items():
                    digest = snapshot["metadata_sha256"]
                    asset, _ = QuoteTemplateAsset.objects.get_or_create(digest=digest, defaults={"snapshot": snapshot})
                    if asset.snapshot != snapshot:
                        raise ValidationError("报价模板资源摘要冲突。")
                    self.pi_template_snapshots[key] = digest
        elif not self._state.adding:
            update_fields = kwargs.get("update_fields")
            if update_fields is None or "pi_template_snapshots" in update_fields:
                saved = type(self).objects.filter(pk=self.pk).values_list("pi_template_snapshots", flat=True).first()
                if saved != self.pi_template_snapshots:
                    raise ValidationError({"pi_template_snapshots": "保存的报价模板不能修改。"})
        if (
            self._state.adding
            and not self.parent_quote_id
            and not self.root_quote_id
            and not self._buyer_company_name_supplied
            and not self.buyer_company_name
            and self.customer_id
        ):
            self.buyer_company_name = self.customer.name
        super().save(*args, **kwargs)

    def clean(self):
        if not self.parent_quote_id:
            return
        parent_root = self.parent_quote.root_quote or self.parent_quote
        own_root = self.root_quote or self
        if parent_root.pk != own_root.pk:
            raise ValidationError({"parent_quote": "直接来源报价必须属于同一原始报价链。"})

    @property
    def total_amount(self):
        if self.amount_calculation_version == LEGACY_AMOUNT_CALCULATION_VERSION:
            return legacy_document_total(self.items.all(), shipping_fee=self.shipping_fee, discount=self.discount)
        return document_total(self.items.all(), shipping_fee=self.shipping_fee, discount=self.discount)


class QuoteRevisionCounter(models.Model):
    root_quote = models.OneToOneField(Quote, on_delete=models.CASCADE, related_name="revision_counter")
    last_value = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(99)])


class QuoteChildRevisionCounter(models.Model):
    parent_quote = models.OneToOneField(Quote, on_delete=models.CASCADE, related_name="child_revision_counter")
    last_value = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(99)])


class SKUTradeUnit(TimestampedModel):
    sku = models.ForeignKey(SKU, on_delete=models.PROTECT, related_name="trade_units")
    supplier = models.ForeignKey("Supplier", on_delete=models.PROTECT, null=True, blank=True)
    name = models.CharField("规格名称", max_length=120)
    unit = models.CharField("交易单位", max_length=30)
    factor = models.DecimalField("每交易单位的基础数量", max_digits=14, decimal_places=2)
    allow_fraction = models.BooleanField("允许非整包装", default=False)
    is_default = models.BooleanField("默认规格", default=False)
    active = models.BooleanField("启用", default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['sku_id', '-is_default', 'id']
        constraints = [
            models.CheckConstraint(condition=models.Q(factor__gt=0), name='trade_unit_factor_positive'),
            models.UniqueConstraint(fields=['sku'], condition=models.Q(is_default=True), name='trade_unit_one_default'),
            models.CheckConstraint(condition=models.Q(is_default=False) | models.Q(active=True), name='trade_unit_default_active'),
        ]


class TradeUnitLine(models.Model):
    trade_unit = models.ForeignKey(SKUTradeUnit, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    trade_quantity = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    trade_unit_price = models.DecimalField(max_digits=16, decimal_places=4, null=True, blank=True)
    trade_snapshot = models.JSONField(default=dict, blank=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.trade_snapshot and not self.trade_unit_id:
            sku = getattr(self, 'sku', None)
            if sku is None and hasattr(self, 'purchase_item'):
                sku = self.purchase_item.sku
            if sku is not None:
                unit = getattr(self, 'unit_snapshot', '') or sku.unit
                self.trade_snapshot = {'unit': unit, 'base_unit': unit, 'factor': '1', 'name': ''}
        super().save(*args, **kwargs)

    @property
    def amount(self):
        if self.trade_quantity is not None and self.trade_unit_price is not None:
            return self.trade_quantity * self.trade_unit_price
        return self.quantity * self.unit_price


class QuoteItem(TradeUnitLine):
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="items")
    sku = models.ForeignKey(SKU, on_delete=models.PROTECT, related_name="quote_items")
    sku_code_snapshot = models.CharField("SKU 编码快照", max_length=80, blank=True)
    sales_model_snapshot = models.CharField("销售型号快照", max_length=80, blank=True)
    product_name_snapshot = models.CharField("产品名称快照", max_length=200, blank=True)
    unit_snapshot = models.CharField("单位快照", max_length=30, blank=True)
    sales_rules_snapshot = models.JSONField(default=list, blank=True)
    image_snapshot = models.ImageField("产品图片快照", upload_to="quote-item-images/%Y/%m/", blank=True)
    quantity = models.DecimalField("数量", max_digits=14, decimal_places=2)
    unit_price = models.DecimalField("单价", max_digits=24, decimal_places=12)
    description = models.TextField("产品描述", blank=True)
    notes = models.CharField("备注", max_length=200, blank=True)

    def save(self, *args, **kwargs):
        if self._state.adding and self.sku_id:
            sku = self.sku
            self.sku_code_snapshot = self.sku_code_snapshot or sku.sku
            self.sales_model_snapshot = self.sales_model_snapshot or sku.sales_model or ""
            self.product_name_snapshot = self.product_name_snapshot or sku.display_name_cn or sku.product.name
            self.unit_snapshot = self.unit_snapshot or sku.unit
            self.description = self.description or sku.description_en or sku.description_cn or self.product_name_snapshot
        super().save(*args, **kwargs)

    @property
    def amount(self):
        return super().amount


class QuoteImportantNote(TimestampedModel):
    root_quote = models.ForeignKey(Quote, on_delete=models.PROTECT, related_name="important_notes")
    source_quote = models.ForeignKey(Quote, on_delete=models.PROTECT, related_name="sourced_important_notes")
    content = models.TextField()
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    deactivated_at = models.DateTimeField("失效时间", null=True, blank=True)
    deactivated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deactivated_quote_important_notes",
        verbose_name="失效操作人",
    )

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["root_quote", "-created_at"])]

    def clean(self):
        source_root = self.source_quote.root_quote or self.source_quote
        if self.root_quote_id != source_root.id:
            raise ValidationError({"source_quote": "来源报价必须属于原始报价链。"})


class Order(TimestampedModel):
    STATUS_CHOICES = [("draft", "草稿"), ("confirmed", "已确认"), ("production", "生产中"), ("shipped", "已发货"), ("completed", "已完成"), ("cancelled", "已取消"), ("historical", "历史订单 · 仅用于经营分析")]
    order_no = models.CharField("订单号", max_length=40, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="orders")
    customer_name_snapshot = models.CharField("客户名称快照", max_length=200, blank=True)
    customer_country_snapshot = models.CharField("客户国家/地区快照", max_length=100, blank=True)
    customer_address_snapshot = models.TextField("客户地址快照", blank=True)
    customer_contact_name_snapshot = models.CharField("交易联系人快照", max_length=200, blank=True)
    customer_phone_snapshot = models.CharField("联系人电话快照", max_length=100, blank=True)
    customer_email_snapshot = models.CharField("联系人邮箱快照", max_length=254, blank=True)
    quote = models.ForeignKey(Quote, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    order_date = models.DateField("订单日期")
    expected_ship_date = models.DateField("预计交期", null=True, blank=True)
    tail_goods_policy = models.CharField("尾货策略", max_length=20, choices=TAIL_GOODS_POLICY_CHOICES, default="SAME_CARTON")
    status = models.CharField("状态", max_length=20, choices=STATUS_CHOICES, default="draft")
    historical_only = models.BooleanField("仅用于历史分析", default=False, editable=False, db_index=True)
    currency = models.CharField("币种", max_length=10, default="USD")
    exchange_rate = models.DecimalField("对人民币汇率", max_digits=12, decimal_places=6, default=1)
    shipping_fee = models.DecimalField("运费", max_digits=14, decimal_places=4, default=0)
    discount = models.DecimalField("折扣金额", max_digits=14, decimal_places=4, default=0)
    notes = models.TextField("备注", blank=True)
    cancelled_at = models.DateTimeField("取消时间", null=True, blank=True)
    cancellation_reason = models.TextField("取消原因", blank=True)
    quantity_change_version = models.PositiveIntegerField("数量变更版本", default=0)
    amount_calculation_version = models.PositiveSmallIntegerField(default=CURRENT_AMOUNT_CALCULATION_VERSION, editable=False)

    class Meta:
        ordering = ["-order_date", "-id"]

    @property
    def base_amount(self):
        if self.amount_calculation_version == LEGACY_AMOUNT_CALCULATION_VERSION:
            return legacy_document_total(self.items.all(), shipping_fee=self.shipping_fee, discount=self.discount)
        return document_total(self.items.all(), shipping_fee=self.shipping_fee, discount=self.discount)

    @property
    def approved_change_amount(self):
        return sum(self.contract_changes.filter(status="approved").values_list("amount_delta", flat=True), Decimal("0"))

    @property
    def total_amount(self):
        total = self.base_amount + self.approved_change_amount
        return total if self.amount_calculation_version == LEGACY_AMOUNT_CALCULATION_VERSION else money(total)

    @property
    def paid_amount(self):
        # A draft has no formal receivable yet.  Keep it out of payment
        # projections even if historical/imported rows happen to be linked.
        if self.status == "draft" or ((self.status == "historical" or self.historical_only) and not hasattr(self, "history_balance")):
            return Decimal("0")
        receipts = sum(self.transactions.filter(status="confirmed", kind="customer_receipt").values_list("amount", flat=True), Decimal("0"))
        refunds = sum((t.amount for t in self.transactions.filter(direction="expense", status="confirmed", kind="refund")), Decimal("0"))
        allocations = sum(AdvanceAllocation.objects.filter(plan__order=self, is_active=True, advance__status="confirmed").values_list("amount", flat=True), Decimal("0"))
        return receipts + allocations - refunds

    @property
    def outstanding_amount(self):
        """Current receivable, derived solely from effective payment plans.

        Contract amount remains historical/commercial information.  A draft or
        cancelled order has no current receivable, while a formal order's
        receivable is the sum of its still-open receivable-plan balances.
        """
        if self.status in {"draft", "cancelled"} or ((self.status == "historical" or self.historical_only) and not hasattr(self, "history_balance")):
            return Decimal("0")
        return self.payment_plans.filter(
            direction="receivable", status="open",
        ).aggregate(total=models.Sum(models.F("planned_amount") - models.F("settled_amount")))["total"] or Decimal("0")


class OrderItem(TradeUnitLine):
    SUPPLIER_ALLOCATION_SCOPE_CHOICES = [
        ("order_only", "仅本次订单"),
        ("customer_preferred", "设为该客户此 SKU 今后优先来源"),
        ("recommended", "历史兼容值"),
    ]
    SUPPLIER_ALLOCATION_SOURCE_CHOICES = [
        ("rule_match", "规则匹配"),
        ("historical_purchase", "历史采购"),
        ("manual", "人工补充"),
        ("supplier_sku", "供货档案"),
        ("customer_preference", "客户优先来源"),
    ]
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    sku = models.ForeignKey(SKU, on_delete=models.PROTECT, related_name="order_items")
    sku_code_snapshot = models.CharField("SKU 编码快照", max_length=80, blank=True)
    sales_model_snapshot = models.CharField("销售型号快照", max_length=80, blank=True)
    display_name_snapshot = models.CharField("显示名称快照", max_length=300, blank=True)
    description_snapshot = models.TextField("描述快照", blank=True)
    unit_snapshot = models.CharField("单位快照", max_length=30, blank=True)
    quantity = models.DecimalField("数量", max_digits=14, decimal_places=2)
    unit_price = models.DecimalField("单价", max_digits=24, decimal_places=12)
    cost_price = models.DecimalField("成交时成本", max_digits=14, decimal_places=4, default=0)
    notes = models.CharField("备注", max_length=200, blank=True)
    supplier_sku = models.ForeignKey(
        "SupplierSKU",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="sales_order_items",
        verbose_name="本次采购供应来源",
    )
    supplier_name_snapshot = models.CharField("供应商名称快照", max_length=200, blank=True)
    supplier_model_snapshot = models.CharField("供应商型号快照", max_length=120, blank=True)
    supplier_sku_code_snapshot = models.CharField("供应商 SKU 编码快照", max_length=100, blank=True)
    supplier_barcode_snapshot = models.CharField("供应商条码快照", max_length=100, blank=True)
    supplier_characteristics_snapshot = models.JSONField("供货特点快照", default=dict, blank=True)
    supplier_price_snapshot = models.DecimalField("供应商参考价快照", max_digits=14, decimal_places=4, null=True, blank=True)
    supplier_currency_snapshot = models.CharField("供应商报价币种快照", max_length=10, blank=True)
    supplier_moq_snapshot = models.DecimalField("MOQ 快照", max_digits=14, decimal_places=2, null=True, blank=True)
    supplier_lead_time_days_snapshot = models.PositiveIntegerField("交期快照（天）", null=True, blank=True)
    supplier_allocation_source = models.CharField("供应商候选来源", max_length=30, choices=SUPPLIER_ALLOCATION_SOURCE_CHOICES, blank=True)
    supplier_allocation_sources_snapshot = models.JSONField("候选来源快照", default=list, blank=True)
    supplier_allocation_scope = models.CharField("供应商分配范围", max_length=30, choices=SUPPLIER_ALLOCATION_SCOPE_CHOICES, blank=True)
    supplier_allocation_note = models.CharField("供应商分配说明", max_length=300, blank=True)
    supplier_allocated_at = models.DateTimeField("供应商分配时间", null=True, blank=True)

    def save(self, *args, **kwargs):
        if self._state.adding and self.sku_id:
            sku = self.sku
            self.sku_code_snapshot = self.sku_code_snapshot or sku.sku
            self.sales_model_snapshot = self.sales_model_snapshot or sku.sales_model or ""
            self.display_name_snapshot = self.display_name_snapshot or sku.display_name_cn or sku.product.name
            self.description_snapshot = self.description_snapshot or sku.description_en or sku.description_cn or self.display_name_snapshot
            self.unit_snapshot = self.unit_snapshot or sku.unit
        if self._state.adding and self.supplier_sku_id:
            source = self.supplier_sku
            self.supplier_name_snapshot = self.supplier_name_snapshot or source.supplier.name
            self.supplier_model_snapshot = self.supplier_model_snapshot or source.supplier_model
            self.supplier_sku_code_snapshot = self.supplier_sku_code_snapshot or source.supplier_sku_code
            self.supplier_barcode_snapshot = self.supplier_barcode_snapshot or source.supplier_barcode
            self.supplier_characteristics_snapshot = self.supplier_characteristics_snapshot or source.characteristics
            if self.supplier_price_snapshot is None:
                self.supplier_price_snapshot = source.purchase_price
            self.supplier_currency_snapshot = self.supplier_currency_snapshot or source.currency
            if self.supplier_moq_snapshot is None:
                self.supplier_moq_snapshot = source.moq
            if self.supplier_lead_time_days_snapshot is None:
                self.supplier_lead_time_days_snapshot = source.lead_time_days
        super().save(*args, **kwargs)

    @property
    def amount(self):
        return super().amount


class OrderQuantityAdjustment(TimestampedModel):
    """Immutable business record for a confirmed sales-order quantity change.

    The line and impact snapshots intentionally live on the adjustment record.
    They preserve the commercial meaning of the operation even if later
    fulfillment or procurement facts change.  No public generic CRUD endpoint
    is exposed for this model; the order action below is append-only.
    """

    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="quantity_adjustments")
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_quantity_adjustments",
    )
    request_key = models.CharField("请求幂等键", max_length=100, unique=True, default=uuid.uuid4)
    request_fingerprint = models.CharField("请求指纹", max_length=64)
    reason = models.TextField("变更原因")
    before_total_amount = models.DecimalField("变更前订单金额", max_digits=24, decimal_places=12)
    after_total_amount = models.DecimalField("变更后订单金额", max_digits=24, decimal_places=12)
    amount_delta = models.DecimalField("金额差额", max_digits=24, decimal_places=12)
    lines = models.JSONField("数量变更明细", default=list)
    impact = models.JSONField("影响快照", default=dict)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["order", "created_at"]),
            models.Index(fields=["operator", "created_at"]),
        ]


OVERAGE_REASON_CHOICES = [
    ("overprocurement", "超采"),
    ("gift", "赠品"),
    ("carton_variance", "尾差"),
    ("customer_addon", "客户追加"),
    ("gift_or_sample", "赠品或样品"),
    ("packing_variance", "包装尾差"),
]


class Supplier(TimestampedModel):
    supply_categories = models.ManyToManyField("ProductCategory", blank=True, related_name="suppliers", verbose_name="可供产品分类")
    country = models.CharField("国家/地区", max_length=100, blank=True, default="中国")
    address = models.TextField("地址", blank=True, default="")
    main_products = models.CharField("主要产品", max_length=300, blank=True)
    name = models.CharField("供应商名称", max_length=200, unique=True)
    code = models.CharField("供应商二字代码", max_length=2, unique=True)
    contact_name = models.CharField("联系人", max_length=100, blank=True)
    phone = models.CharField("电话", max_length=50, blank=True)
    email = models.EmailField("邮箱", blank=True)
    store_url = models.URLField("店铺链接", max_length=500, blank=True)
    payment_terms = models.CharField("付款条款", max_length=200, blank=True, default="30%预付款，70%尾款发货前结清")
    payment_terms_config = models.JSONField("系统执行付款规则", default=list, blank=True)
    notes = models.TextField("备注", blank=True)
    is_active = models.BooleanField("启用", default=True, db_index=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class SupplierSKU(TimestampedModel):
    """A supplier's purchasing identity for one internal SKU.

    The internal SKU remains the inventory and sales identity.  This entity
    only records how a supplier identifies and quotes that SKU.
    """

    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="supplier_skus")
    sku = models.ForeignKey(SKU, on_delete=models.PROTECT, related_name="supplier_skus")
    supplier_model = models.CharField("供应商型号", max_length=120, blank=True)
    supplier_product_name = models.CharField("供应商产品名称", max_length=200, blank=True)
    supplier_sku_code = models.CharField("供应商 SKU 编码", max_length=100)
    supplier_barcode = models.CharField("供应商条码", max_length=100, blank=True)
    purchase_price = models.DecimalField("参考采购价", max_digits=14, decimal_places=4, default=0)
    currency = models.CharField("采购币种", max_length=10, default="USD")
    moq = models.DecimalField("最小起订量", max_digits=14, decimal_places=2, default=0)
    lead_time_days = models.PositiveIntegerField("交期（天）", default=0)
    is_active = models.BooleanField("启用", default=True)
    is_preferred = models.BooleanField("首选供应来源", default=False)
    remarks = models.TextField("备注", blank=True)
    characteristics = models.JSONField("供货特点", default=dict, blank=True)

    class Meta:
        ordering = ["supplier__name", "supplier_sku_code", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["supplier", "supplier_sku_code"],
                name="supplier_supplier_sku_code_unique",
            ),
            models.UniqueConstraint(
                fields=["sku"],
                condition=models.Q(is_active=True, is_preferred=True),
                name="active_preferred_supplier_sku_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(purchase_price__gte=0),
                name="supplier_sku_purchase_price_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(moq__gte=0),
                name="supplier_sku_moq_non_negative",
            ),
        ]

    def __str__(self):
        return f"{self.supplier.name} / {self.supplier_sku_code}"


class CustomerSupplierPreference(TimestampedModel):
    """Explicit purchasing preference for one customer and internal SKU.

    This is deliberately separate from SupplierSKU.is_preferred.  The latter
    remains a weak, global SKU fallback; this row records an intentional
    customer-specific choice without changing the SKU master.
    """

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="supplier_preferences")
    sku = models.ForeignKey(SKU, on_delete=models.PROTECT, related_name="customer_supplier_preferences")
    supplier_sku = models.ForeignKey(SupplierSKU, on_delete=models.PROTECT, related_name="customer_preferences")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_customer_supplier_preferences",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_customer_supplier_preferences",
    )

    class Meta:
        ordering = ["customer__name", "sku__sku", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "sku"],
                name="customer_supplier_preference_unique",
            ),
        ]

    def __str__(self):
        return f"{self.customer.name} / {self.sku.sku} / {self.supplier_sku.supplier.name}"


class PurchaseOrder(TimestampedModel):
    payment_terms_snapshot = models.JSONField("本次付款计划", default=list, blank=True)
    cost_allocation_version = models.PositiveIntegerField(default=0, editable=False)
    additional_costs = models.JSONField(default=list, blank=True, editable=False)
    STATUS_CHOICES = [
        ("draft", "草稿"),
        ("ordered", "已下单"),
        ("partial", "部分到货"),
        ("completed", "已完成"),
        ("cancelled", "已取消"),
        ("historical", "历史订单 · 仅用于经营分析"),
    ]
    purchase_no = models.CharField("采购单号", max_length=40, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="purchase_orders")
    supplier_name_snapshot = models.CharField("供应商名称快照", max_length=200, blank=True)
    supplier_address_snapshot = models.TextField("供应商地址快照", blank=True)
    supplier_contact_name_snapshot = models.CharField("供应商联系人快照", max_length=100, blank=True)
    supplier_phone_snapshot = models.CharField("供应商电话快照", max_length=50, blank=True)
    supplier_email_snapshot = models.CharField("供应商邮箱快照", max_length=254, blank=True)
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="purchase_orders", null=True, blank=True)
    order_date = models.DateField("下单日期")
    expected_arrival_date = models.DateField("预计到货日", null=True, blank=True)
    status = models.CharField("状态", max_length=20, choices=STATUS_CHOICES, default="draft")
    historical_only = models.BooleanField("仅用于历史分析", default=False, editable=False, db_index=True)
    history_finance_mode = models.BooleanField("历史接续财务口径", default=False, editable=False)
    currency = models.CharField("币种", max_length=10, default="USD")
    exchange_rate = models.DecimalField("对人民币汇率", max_digits=12, decimal_places=6, default=1)
    notes = models.TextField("备注", blank=True)
    cancelled_at = models.DateTimeField("取消时间", null=True, blank=True)
    cancellation_reason = models.TextField("取消原因", blank=True)

    class Meta:
        ordering = ["-order_date", "-id"]

    @property
    def base_amount(self):
        return sum((item.amount for item in self.items.all()), Decimal("0"))

    @property
    def approved_change_amount(self):
        return sum(self.contract_changes.filter(status="approved").values_list("amount_delta", flat=True), Decimal("0"))

    @property
    def total_amount(self):
        return self.base_amount + self.approved_change_amount

    @property
    def paid_amount(self):
        if (self.status == "historical" or self.historical_only) and not hasattr(self, "history_balance"):
            return Decimal("0")
        paid = sum(self.transactions.filter(status="confirmed", kind="supplier_payment").values_list("amount", flat=True), Decimal("0"))
        allocations = sum(AdvanceAllocation.objects.filter(plan__purchase_order=self, is_active=True, advance__status="confirmed").values_list("amount", flat=True), Decimal("0"))
        refunds = sum(self.transactions.filter(direction="income", status="confirmed", kind="supplier_refund").values_list("amount", flat=True), Decimal("0"))
        return paid + allocations - refunds

    @property
    def unpaid_amount(self):
        if (self.status == "historical" or self.historical_only) and not hasattr(self, "history_balance"):
            return Decimal("0")
        if self.history_finance_mode or self.status == "historical" or self.historical_only:
            return self.payment_plans.filter(direction="payable", status="open").aggregate(total=models.Sum(models.F("planned_amount") - models.F("settled_amount")))["total"] or Decimal("0")
        return self.total_amount - self.paid_amount

    def __str__(self):
        return self.purchase_no


class PurchaseCostAllocation(models.Model):
    target_name = models.CharField("自定义成本归属", max_length=100, blank=True, default="")
    purchase_item = models.ForeignKey("PurchaseOrderItem", on_delete=models.CASCADE, related_name="cost_allocations")
    target_type = models.CharField(max_length=20, choices=[("order", "销售订单"), ("inventory", "库存"), ("sample", "样品"), ("loss", "损耗"), ("gift", "赠品"), ("after_sales", "售后补发"), ("research", "研发试制"), ("internal", "内部领用"), ("marketing", "展会推广"), ("other", "其他")])
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.PROTECT, related_name="purchase_cost_allocations")
    quantity = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="cost_allocation_quantity_positive"),
            models.CheckConstraint(condition=(models.Q(target_type="order", order__isnull=False) | models.Q(target_type__in=["inventory", "sample", "loss", "gift", "after_sales", "research", "internal", "marketing", "other"], order__isnull=True)), name="cost_allocation_target_valid"),
        ]


class PurchaseOrderItem(TradeUnitLine):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="items")
    sku = models.ForeignKey(SKU, on_delete=models.PROTECT, related_name="purchase_order_items")
    supplier_sku = models.ForeignKey(
        "SupplierSKU",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="purchase_items",
    )
    sku_code_snapshot = models.CharField("SKU 编码快照", max_length=80, blank=True)
    sales_model_snapshot = models.CharField("销售型号快照", max_length=80, blank=True)
    display_name_snapshot = models.CharField("显示名称快照", max_length=300, blank=True)
    description_snapshot = models.TextField("描述快照", blank=True)
    supplier_name_snapshot = models.CharField("供应商名称快照", max_length=200, blank=True)
    supplier_model_snapshot = models.CharField("供应商型号快照", max_length=120, blank=True)
    supplier_sku_code_snapshot = models.CharField("供应商 SKU 编码快照", max_length=100, blank=True)
    supplier_barcode_snapshot = models.CharField("供应商条码快照", max_length=100, blank=True)
    supplier_characteristics_snapshot = models.JSONField("供货特点快照", default=dict, blank=True)
    quantity = models.DecimalField("采购数量", max_digits=14, decimal_places=2)
    unit_price = models.DecimalField("采购单价", max_digits=24, decimal_places=12)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="purchase_item_quantity_positive"),
            models.CheckConstraint(condition=models.Q(unit_price__gte=0), name="purchase_item_price_non_negative"),
        ]

    @property
    def received_quantity(self):
        return sum((receipt.quantity for receipt in self.receipts.filter(reversal_inventory_movement__isnull=True)), Decimal("0"))

    @property
    def remaining_quantity(self):
        return max(Decimal("0"), self.quantity - self.received_quantity)

    @property
    def overage_quantity(self):
        return max(Decimal("0"), self.received_quantity - self.quantity)

    def save(self, *args, **kwargs):
        creating = self._state.adding
        if self._state.adding and self.sku_id:
            sku = self.sku
            self.sku_code_snapshot = self.sku_code_snapshot or sku.sku
            self.sales_model_snapshot = self.sales_model_snapshot or sku.sales_model or ""
            self.display_name_snapshot = self.display_name_snapshot or sku.display_name_cn or sku.product.name
            self.description_snapshot = self.description_snapshot or sku.description_en or sku.description_cn or self.display_name_snapshot
        if self._state.adding and self.supplier_sku_id:
            supplier_sku = self.supplier_sku
            self.supplier_name_snapshot = self.supplier_name_snapshot or supplier_sku.supplier.name
            self.supplier_model_snapshot = self.supplier_model_snapshot or supplier_sku.supplier_model
            self.supplier_sku_code_snapshot = self.supplier_sku_code_snapshot or supplier_sku.supplier_sku_code
            self.supplier_barcode_snapshot = self.supplier_barcode_snapshot or supplier_sku.supplier_barcode
            self.supplier_characteristics_snapshot = self.supplier_characteristics_snapshot or supplier_sku.characteristics
        elif self._state.adding and self.purchase_order_id:
            # A manual purchase may deliberately have no maintained SupplierSKU.
            # Its supplier is still a historical business fact and must not change
            # with a later supplier rename.
            self.supplier_name_snapshot = self.supplier_name_snapshot or self.purchase_order.supplier.name
        super().save(*args, **kwargs)
        if creating and self.purchase_order.cost_allocation_version == 0 and not self.cost_allocations.exists():
            PurchaseCostAllocation.objects.create(
                purchase_item=self,
                target_type="order" if self.purchase_order.order_id else "inventory",
                order=self.purchase_order.order if self.purchase_order.order_id else None,
                quantity=self.quantity,
            )


class PurchaseMOQException(TimestampedModel):
    """Immutable evidence for a formal PO placed below a maintained MOQ."""

    purchase_order = models.OneToOneField(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="moq_exception",
    )
    reason = models.TextField("例外原因")
    details = models.JSONField("MOQ 明细快照", default=list)
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchase_moq_exceptions",
    )

    class Meta:
        ordering = ["-created_at", "-id"]


class PaymentPlan(TimestampedModel):
    DIRECTION_CHOICES = [("receivable", "应收"), ("payable", "应付")]
    STATUS_CHOICES = [("open", "待结清"), ("settled", "已结清"), ("cancelled", "已取消")]

    order = models.ForeignKey(Order, on_delete=models.PROTECT, null=True, blank=True, related_name="payment_plans")
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, null=True, blank=True, related_name="payment_plans")
    direction = models.CharField("收付款方向", max_length=12, choices=DIRECTION_CHOICES)
    due_date = models.DateField("预计日期", null=True, blank=True)
    planned_amount = models.DecimalField("计划原币金额", max_digits=14, decimal_places=4)
    settled_amount = models.DecimalField("已核销原币金额", max_digits=14, decimal_places=4, default=0)
    currency = models.CharField("币种", max_length=10)
    status = models.CharField("状态", max_length=12, choices=STATUS_CHOICES, default="open")
    notes = models.TextField("备注", blank=True)

    class Meta:
        ordering = ["due_date", "id"]
        constraints = [
            models.CheckConstraint(
                condition=(models.Q(order__isnull=False, purchase_order__isnull=True) | models.Q(order__isnull=True, purchase_order__isnull=False)),
                name="payment_plan_one_contract",
            ),
            models.CheckConstraint(
                condition=models.Q(planned_amount__gt=0) | models.Q(status="cancelled", planned_amount=0, settled_amount=0),
                name="payment_plan_amount_positive",
            ),
            models.CheckConstraint(condition=models.Q(settled_amount__gte=0), name="payment_plan_settled_non_negative"),
        ]

    @property
    def remaining_amount(self):
        return self.planned_amount - self.settled_amount

    def clean(self):
        super().clean()
        if bool(self.order_id) == bool(self.purchase_order_id):
            raise ValidationError("收付款计划必须且只能关联一个订单或采购单。")
        expected_direction = "receivable" if self.order_id else "payable"
        if self.direction != expected_direction:
            raise ValidationError("销售订单只能建立应收计划，采购单只能建立应付计划。")
        if self.settled_amount > self.planned_amount:
            raise ValidationError("已核销金额不能超过计划金额。")


class ContractChangeRequest(TimestampedModel):
    STATUS_CHOICES = [("pending", "待确认"), ("approved", "已确认"), ("rejected", "已拒绝")]
    order = models.ForeignKey(Order, on_delete=models.PROTECT, null=True, blank=True, related_name="contract_changes")
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, null=True, blank=True, related_name="contract_changes")
    amount_delta = models.DecimalField("合同原币变更金额", max_digits=14, decimal_places=4)
    due_date = models.DateField("新增计划日期", null=True, blank=True)
    status = models.CharField("状态", max_length=12, choices=STATUS_CHOICES, default="pending")
    notes = models.TextField("变更说明")

    def clean(self):
        if bool(self.order_id) == bool(self.purchase_order_id):
            raise ValidationError("变更单必须且只能关联一个订单或采购单。")
        if self.amount_delta == 0:
            raise ValidationError("合同变更金额不能为零。")


class Shipment(TimestampedModel):
    STATUS_CHOICES = [("draft", "草稿"), ("confirmed", "已确认"), ("cancelled", "已取消")]
    shipment_no = models.CharField("发货单号", max_length=40, unique=True)
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="shipments")
    shipment_date = models.DateField("发货日期")
    logistics_provider = models.CharField("物流商", max_length=100, blank=True)
    waybill_no = models.CharField("物流单号", max_length=100, blank=True)
    status = models.CharField("状态", max_length=20, choices=STATUS_CHOICES, default="draft")
    notes = models.TextField("备注", blank=True)
    order_status_before_confirm = models.CharField("确认发货前订单状态", max_length=20, blank=True)
    reversed_at = models.DateTimeField(null=True, blank=True)
    reversal_reason = models.TextField(blank=True)
    request_key = models.CharField("请求幂等键", max_length=100, unique=True, null=True, blank=True)
    request_fingerprint = models.CharField("请求指纹", max_length=64, blank=True)

    class Meta:
        ordering = ["-shipment_date", "-id"]

    def __str__(self):
        return self.shipment_no


class PackingPlan(TimestampedModel):
    """Estimated packing snapshot for exactly one quote or sales order."""
    STATUS_CHOICES = [("generated", "已生成"), ("needs_attention", "待处理")]
    quote = models.OneToOneField(Quote, on_delete=models.CASCADE, null=True, blank=True, related_name="packing_plan")
    order = models.OneToOneField(Order, on_delete=models.CASCADE, null=True, blank=True, related_name="packing_plan")
    status = models.CharField("状态", max_length=20, choices=STATUS_CHOICES, default="generated")
    total_cartons = models.PositiveIntegerField("预计箱数", default=0)
    total_net_weight = models.DecimalField("预计净重(kg)", max_digits=16, decimal_places=3, default=0)
    total_gross_weight = models.DecimalField("预计毛重(kg)", max_digits=16, decimal_places=3, default=0)
    total_cbm = models.DecimalField("预计CBM", max_digits=16, decimal_places=6, default=0)
    warnings = models.JSONField("警告", default=list, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=(models.Q(quote__isnull=False, order__isnull=True) | models.Q(quote__isnull=True, order__isnull=False)), name="packing_plan_one_source")]


class PackingPlanCarton(models.Model):
    packing_plan = models.ForeignKey(PackingPlan, on_delete=models.CASCADE, related_name="cartons")
    carton_no = models.PositiveIntegerField("箱号")
    packaging_template_snapshot = models.JSONField("包装模板快照", default=dict)
    qty_per_carton_snapshot = models.DecimalField("每箱数量快照", max_digits=14, decimal_places=2, null=True, blank=True)
    partial_carton_policy_snapshot = models.CharField("尾货策略快照", max_length=20, blank=True)
    length = models.DecimalField("箱长(cm)", max_digits=10, decimal_places=2, null=True, blank=True)
    width = models.DecimalField("箱宽(cm)", max_digits=10, decimal_places=2, null=True, blank=True)
    height = models.DecimalField("箱高(cm)", max_digits=10, decimal_places=2, null=True, blank=True)
    carton_tare_weight = models.DecimalField("纸箱皮重(kg)", max_digits=12, decimal_places=3, default=0)
    estimated_net_weight = models.DecimalField("预计净重(kg)", max_digits=16, decimal_places=3, default=0)
    estimated_gross_weight = models.DecimalField("预计毛重(kg)", max_digits=16, decimal_places=3, default=0)
    estimated_cbm = models.DecimalField("预计CBM", max_digits=16, decimal_places=6, default=0)
    is_partial = models.BooleanField("尾箱", default=False)
    requires_confirmation = models.BooleanField("待确认", default=False)

    class Meta:
        ordering = ["carton_no"]
        constraints = [models.UniqueConstraint(fields=["packing_plan", "carton_no"], name="packing_plan_carton_no_unique")]


class PackingPlanCartonItem(models.Model):
    carton = models.ForeignKey(PackingPlanCarton, on_delete=models.CASCADE, related_name="items")
    sku = models.ForeignKey(SKU, on_delete=models.PROTECT, related_name="packing_plan_items")
    sku_code_snapshot = models.CharField("SKU编码快照", max_length=80)
    sku_name_snapshot = models.CharField("SKU名称快照", max_length=200)
    unit_net_weight_snapshot = models.DecimalField("单件净重快照(kg)", max_digits=12, decimal_places=3, null=True, blank=True)
    quantity = models.DecimalField("数量", max_digits=14, decimal_places=2)


class ShipmentPackage(models.Model):
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name="packages")
    carton_no = models.PositiveIntegerField("箱号")
    packaging_template = models.ForeignKey(PackagingTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    length = models.DecimalField("实际箱长(cm)", max_digits=10, decimal_places=2, null=True, blank=True)
    width = models.DecimalField("实际箱宽(cm)", max_digits=10, decimal_places=2, null=True, blank=True)
    height = models.DecimalField("实际箱高(cm)", max_digits=10, decimal_places=2, null=True, blank=True)
    actual_net_weight = models.DecimalField("实际净重(kg)", max_digits=16, decimal_places=3, default=0)
    actual_gross_weight = models.DecimalField("实际毛重(kg)", max_digits=16, decimal_places=3, default=0)
    notes = models.TextField("备注", blank=True)

    @property
    def actual_cbm(self):
        if not all([self.length, self.width, self.height]): return Decimal("0")
        return (self.length * self.width * self.height / Decimal("1000000")).quantize(Decimal("0.000001"))

    class Meta:
        ordering = ["carton_no"]
        constraints = [models.UniqueConstraint(fields=["shipment", "carton_no"], name="shipment_package_carton_no_unique")]


class ShipmentPackageItem(models.Model):
    shipment_package = models.ForeignKey(ShipmentPackage, on_delete=models.CASCADE, related_name="items")
    sku = models.ForeignKey(SKU, on_delete=models.PROTECT, related_name="shipment_package_items")
    quantity = models.DecimalField("实际装箱数量", max_digits=14, decimal_places=2)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(quantity__gt=0), name="shipment_package_item_quantity_positive")]


class InventoryReservation(models.Model):
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name="reservations")
    sku = models.ForeignKey(SKU, on_delete=models.PROTECT, related_name="inventory_reservations")
    quantity = models.DecimalField("预留数量", max_digits=14, decimal_places=2)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="inventory_reservation_quantity_positive"),
        ]


class InventoryMovement(TradeUnitLine, TimestampedModel):
    TYPE_CHOICES = [
        ("purchase_in", "采购入库"),
        ("return_in", "客户退回"),
        ("adjust_in", "盘盈入库"),
        ("transfer_in", "调拨入库"),
        ("production_in", "生产入库"),
        ("other_in", "其他入库"),
        ("sale_out", "销售出库"),
        ("sample_out", "样品出库"),
        ("adjust_out", "盘亏出库"),
        ("transfer_out", "调拨出库"),
        ("production_out", "生产领料"),
        ("other_out", "其他出库"),
    ]
    movement_no = models.CharField("流水号", max_length=50, unique=True)
    movement_date = models.DateField("发生日期")
    type = models.CharField("类型", max_length=20, choices=TYPE_CHOICES)
    sku = models.ForeignKey(SKU, on_delete=models.PROTECT, related_name="inventory_movements")
    supplier_sku = models.ForeignKey(
        "SupplierSKU",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_movements",
    )
    sku_code_snapshot = models.CharField("SKU 编码快照", max_length=80, blank=True)
    sales_model_snapshot = models.CharField("销售型号快照", max_length=80, blank=True)
    display_name_snapshot = models.CharField("显示名称快照", max_length=300, blank=True)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name="inventory_movements")
    related_orders = models.ManyToManyField(Order, blank=True, related_name="related_inventory_movements", verbose_name="关联订单")
    quantity = models.DecimalField("数量", max_digits=14, decimal_places=2)
    warehouse = models.CharField("仓库", max_length=100, default="默认仓")
    warehouse_type = models.CharField("仓库类型", max_length=10, choices=[("自有仓", "自有仓"), ("第三方仓", "第三方仓")], default="自有仓")
    lot_reference = models.CharField("批次或货位", max_length=160, blank=True)
    unit_cost = models.DecimalField("单位成本", max_digits=24, decimal_places=12, default=0)
    reference = models.CharField("参考号", max_length=100, blank=True)
    notes = models.TextField("备注", blank=True)
    source_type = models.CharField(
        "来源类型",
        max_length=20,
        choices=[("manual", "手工"), ("receipt", "到货"), ("shipment", "发货"), ("return", "退货"), ("reversal", "冲销")],
        default="manual",
    )
    source_no = models.CharField("来源单号", max_length=50, blank=True)
    is_automatic = models.BooleanField("系统自动生成", default=False)
    is_overage = models.BooleanField("超额记录", default=False)
    overage_reason = models.CharField("超额原因", max_length=30, choices=OVERAGE_REASON_CHOICES, blank=True)

    class Meta:
        ordering = ["-movement_date", "-id"]

    @property
    def signed_quantity(self):
        return -self.quantity if self.type in INVENTORY_OUTBOUND_TYPES else self.quantity

    @property
    def overage_quantity(self):
        """Return the recorded receipt's contract-overage portion when available."""
        if not self.is_overage:
            return Decimal("0")
        try:
            return self.goods_receipt.overage_quantity
        except GoodsReceipt.DoesNotExist:
            # Historical imports may flag an overage without a linked receipt.
            return self.quantity

    def save(self, *args, **kwargs):
        if self._state.adding and self.sku_id:
            sku = self.sku
            self.sku_code_snapshot = self.sku_code_snapshot or sku.sku
            self.sales_model_snapshot = self.sales_model_snapshot or sku.sales_model or ""
            self.display_name_snapshot = self.display_name_snapshot or sku.display_name_cn or sku.product.name
        super().save(*args, **kwargs)

    def __str__(self):
        return self.movement_no


class GoodsReceipt(TradeUnitLine, TimestampedModel):
    purchase_item = models.ForeignKey(PurchaseOrderItem, on_delete=models.PROTECT, related_name="receipts")
    receipt_date = models.DateField("到货日期")
    quantity = models.DecimalField("到货数量", max_digits=14, decimal_places=2)
    unit_cost = models.DecimalField("实际单价", max_digits=24, decimal_places=12, default=0)
    is_overage = models.BooleanField("超到", default=False)
    overage_reason = models.CharField("超到原因", max_length=30, choices=OVERAGE_REASON_CHOICES, blank=True)
    notes = models.TextField("备注", blank=True)
    inventory_movement = models.OneToOneField(
        InventoryMovement,
        on_delete=models.PROTECT,
        related_name="goods_receipt",
        null=True,
        blank=True,
    )
    reversal_inventory_movement = models.OneToOneField(
        InventoryMovement,
        on_delete=models.PROTECT,
        related_name="reversed_goods_receipt",
        null=True,
        blank=True,
    )
    reversed_at = models.DateTimeField(null=True, blank=True)
    reversal_reason = models.TextField(blank=True)
    request_key = models.CharField("请求幂等键", max_length=100, unique=True, null=True, blank=True)
    request_fingerprint = models.CharField("请求指纹", max_length=64, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="goods_receipt_quantity_positive"),
            models.CheckConstraint(condition=models.Q(unit_cost__gte=0), name="goods_receipt_cost_non_negative"),
        ]

    @property
    def overage_quantity(self):
        """The part of this receipt that was beyond its line's contract quantity.

        This is derived from the receipt sequence instead of treating an entire
        mixed receipt as overage (for example, receiving 10 against 5 remaining).
        It deliberately keeps the original event's classification visible after a
        later reversal, which is important for the audit history.
        """
        if not self.is_overage:
            return Decimal("0")
        received_before = Decimal("0")
        for receipt in self.purchase_item.receipts.order_by("created_at", "pk"):
            if receipt.pk == self.pk:
                break
            # Reconstruct this receipt's creation-time projection. A receipt
            # reversed before this event no longer consumed contract quantity;
            # a later reversal must not rewrite this event's audit history.
            if receipt.reversed_at is None or receipt.reversed_at > self.created_at:
                received_before += receipt.quantity
        return min(self.quantity, max(Decimal("0"), received_before + self.quantity - self.purchase_item.quantity))


class ShipmentItem(TradeUnitLine):
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name="items")
    order_item = models.ForeignKey(OrderItem, on_delete=models.PROTECT, related_name="shipment_items")
    source_order_item = models.ForeignKey(
        OrderItem, on_delete=models.PROTECT, null=True, blank=True, related_name="sourced_shipment_items"
    )
    generated_payment_plan = models.ForeignKey(
        PaymentPlan, on_delete=models.PROTECT, null=True, blank=True, related_name="generated_shipment_items"
    )
    sku = models.ForeignKey(SKU, on_delete=models.PROTECT, related_name="shipment_items")
    quantity = models.DecimalField("发货数量", max_digits=14, decimal_places=2)
    is_overage = models.BooleanField("超发", default=False)
    overage_reason = models.CharField("超发原因", max_length=30, choices=OVERAGE_REASON_CHOICES, blank=True)
    creates_supplement = models.BooleanField("创建订单增补", default=False)
    inventory_movement = models.OneToOneField(
        InventoryMovement,
        on_delete=models.PROTECT,
        related_name="shipment_item",
        null=True,
        blank=True,
    )
    reversal_inventory_movement = models.OneToOneField(
        InventoryMovement,
        on_delete=models.PROTECT,
        related_name="reversed_shipment_item",
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="shipment_item_quantity_positive"),
        ]


class Transaction(TimestampedModel):
    split_from = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="split_rows")
    DIRECTION_CHOICES = [("income", "收入"), ("expense", "支出")]
    STATUS_CHOICES = [("pending", "待确认"), ("confirmed", "已确认"), ("cancelled", "已作废")]
    KIND_CHOICES = [
        ("other", "其他收支"), ("customer_receipt", "客户收款"), ("supplier_payment", "供应商付款"),
        ("order_expense", "订单费用"), ("period_expense", "期间费用"), ("unallocated_advance", "未分配预收预付"),
        ("supplier_refund", "供应商退款返利"), ("other_income", "其他收入"),
        ("sample_expense", "样品费用"), ("freight_expense", "运费物流费"), ("bank_fee", "银行手续费"),
        ("tax_fee", "税费"), ("salary_expense", "工资福利"), ("office_expense", "办公费用"),
        ("travel_expense", "差旅招待"), ("marketing_expense", "营销推广"), ("warehouse_expense", "仓储费用"),
        ("asset_expense", "设备固定资产"), ("unallocated_payment", "未分配预付款"), ("other_expense", "其他支出"),
        ("refund", "退款或折让"), ("exchange_difference", "汇兑差额"),
    ]
    transaction_no = models.CharField("流水号", max_length=50, unique=True)
    transaction_date = models.DateField("发生日期")
    direction = models.CharField("收支方向", max_length=10, choices=DIRECTION_CHOICES)
    category = models.CharField("收支分类", max_length=100)
    amount = models.DecimalField("金额", max_digits=14, decimal_places=4)
    currency = models.CharField("币种", max_length=10, default="USD")
    exchange_rate = models.DecimalField("对人民币汇率", max_digits=12, decimal_places=6, default=1)
    rmb_amount = models.DecimalField("账面人民币折算参考", max_digits=14, decimal_places=4, default=0)
    allocated_amount = models.DecimalField("已分配原币金额", max_digits=14, decimal_places=4, default=0)
    kind = models.CharField("业务类型", max_length=30, choices=KIND_CHOICES, default="other")
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions")
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions")
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions")
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    plan = models.ForeignKey(PaymentPlan, on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions")
    replaces = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="replacements")
    status = models.CharField("状态", max_length=20, choices=STATUS_CHOICES, default="confirmed")
    voided_at = models.DateTimeField(null=True, blank=True)
    void_reason = models.TextField(blank=True)
    payment_method = models.CharField("支付方式", max_length=100, blank=True)
    reference = models.CharField("外部参考号", max_length=100, blank=True)
    notes = models.TextField("备注", blank=True)

    class Meta:
        ordering = ["-transaction_date", "-id"]


class FinanceAccount(TimestampedModel):
    """Explicit account identity; legacy labels never establish ownership."""
    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=200)
    account_type = models.CharField(max_length=12, choices=[("bank", "银行"), ("cash", "现金")])
    ownership = models.CharField(max_length=12, choices=[("unverified", "待核实"), ("own", "自有"), ("external", "外部")], default="unverified")
    currency = models.CharField(max_length=3, default="CNY")
    is_active = models.BooleanField(default=True)
    ownership_reason = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(account_type__in=["bank", "cash"]), name="finance_account_type_valid"),
            models.CheckConstraint(condition=models.Q(ownership__in=["unverified", "own", "external"]), name="finance_account_owner_valid"),
            models.CheckConstraint(condition=models.Q(ownership="unverified") | ~models.Q(ownership_reason=""), name="finance_account_owner_reason"),
        ]


class FinanceAppendOnly(models.Model):
    objects = OperationLogQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.pk and not self._state.adding:
            raise ValidationError("资金历史只允许追加。")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("资金历史不可删除。")


class FinanceVoucher(FinanceAppendOnly):
    file = models.FileField(upload_to="finance-vouchers/%Y/%m/")
    original_name = models.CharField(max_length=200)
    sha256 = models.CharField(max_length=64)
    size = models.PositiveIntegerField()
    actor = models.JSONField()
    scope = models.CharField(max_length=12, default="account")
    bank_sources = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("凭证只允许追加。")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("凭证不可删除。")


class FinanceBankVoucherBinding(FinanceAppendOnly):
    event = models.OneToOneField("RmbCashEvent", on_delete=models.PROTECT, related_name="private_voucher_binding")
    voucher = models.ForeignKey(FinanceVoucher, on_delete=models.PROTECT)
    actor = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)


class FinanceInstruction(TimestampedModel):
    request_key = models.CharField(max_length=128, unique=True)
    request_hash = models.CharField(max_length=64)
    payload = models.JSONField()
    kind = models.CharField(max_length=30)
    status = models.CharField(max_length=16, default="pending")
    created_actor = models.JSONField()
    approved_actor = models.JSONField(default=dict)
    approved_at = models.DateTimeField(null=True)
    reason = models.TextField()
    replaces = models.ForeignKey("self", null=True, on_delete=models.PROTECT)

    def save(self, *args, **kwargs):
        if self.pk and not self._state.adding:
            previous = type(self).objects.get(pk=self.pk)
            for field in ("request_key", "request_hash", "payload", "kind", "created_actor", "reason", "replaces_id"):
                if getattr(previous, field) != getattr(self, field):
                    raise ValidationError("指令内容不可覆盖；取消后创建修订并重新复核。")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("资金指令必须保留历史。")


class FinanceFact(models.Model):
    """Actual CNY movement or independent opening snapshot; never overwrite."""
    instruction = models.OneToOneField(FinanceInstruction, on_delete=models.PROTECT)
    account = models.ForeignKey(FinanceAccount, on_delete=models.PROTECT)
    voucher = models.ForeignKey(FinanceVoucher, on_delete=models.PROTECT)
    actual_date = models.DateField()
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    direction = models.CharField(max_length=10)
    kind = models.CharField(max_length=30)
    excess_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    nature = models.CharField(max_length=30, default="unclassified")
    truth = models.CharField(max_length=20, default="verified")
    source_system = models.CharField(max_length=80)
    source_key = models.CharField(max_length=128)
    parent = models.ForeignKey("self", null=True, on_delete=models.PROTECT)
    legacy_parent = models.ForeignKey("RmbCashEvent", null=True, on_delete=models.PROTECT)
    actor = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    objects = OperationLogQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["source_system", "source_key"], name="finance_fact_source_unique"),
            models.CheckConstraint(condition=models.Q(amount__gt=0) | models.Q(kind__in=["opening", "correction"], amount=0), name="finance_fact_positive"),
            models.CheckConstraint(condition=models.Q(direction__in=["income", "expense"]), name="finance_fact_direction_valid"),
            models.CheckConstraint(condition=models.Q(parent__isnull=True) | models.Q(legacy_parent__isnull=True), name="finance_fact_one_parent"),
            models.UniqueConstraint(fields=["account"], condition=models.Q(kind="opening"), name="finance_opening_account_unique"),
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("资金事实只允许追加；请发起更正。")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("资金事实不可删除。")


class FinanceAccountMapping(FinanceAppendOnly):
    legacy_code = models.CharField(max_length=40, unique=True)
    account = models.ForeignKey(FinanceAccount, on_delete=models.PROTECT)
    reason = models.TextField()
    actor = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    objects = OperationLogQuerySet.as_manager()


class FinanceReview(FinanceAppendOnly):
    account = models.ForeignKey(FinanceAccount, on_delete=models.PROTECT)
    date_from = models.DateField()
    date_to = models.DateField()
    voucher = models.ForeignKey(FinanceVoucher, on_delete=models.PROTECT)
    statement_balance = models.DecimalField(max_digits=18, decimal_places=2)
    calculated_balance = models.DecimalField(max_digits=18, decimal_places=2)
    difference = models.DecimalField(max_digits=18, decimal_places=2)
    fingerprint = models.CharField(max_length=64)
    completed = models.BooleanField(default=False)
    reason = models.TextField()
    actor = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    objects = OperationLogQuerySet.as_manager()


class FinanceTransferMatch(FinanceAppendOnly):
    outgoing = models.OneToOneField(FinanceFact, on_delete=models.PROTECT, related_name="outgoing_match")
    incoming = models.OneToOneField(FinanceFact, on_delete=models.PROTECT, related_name="incoming_match")
    reason = models.TextField()
    actor = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    objects = OperationLogQuerySet.as_manager()


class FinanceHistoricalTransfer(FinanceAppendOnly):
    outgoing_fact = models.OneToOneField(FinanceFact, null=True, on_delete=models.PROTECT, related_name="historical_outgoing_match")
    incoming_fact = models.OneToOneField(FinanceFact, null=True, on_delete=models.PROTECT, related_name="historical_incoming_match")
    outgoing_legacy = models.OneToOneField("RmbCashEvent", null=True, on_delete=models.PROTECT, related_name="historical_outgoing_match")
    incoming_legacy = models.OneToOneField("RmbCashEvent", null=True, on_delete=models.PROTECT, related_name="historical_incoming_match")
    outgoing_voucher = models.ForeignKey(FinanceVoucher, on_delete=models.PROTECT, related_name="historical_transfer_outgoing")
    incoming_voucher = models.ForeignKey(FinanceVoucher, on_delete=models.PROTECT, related_name="historical_transfer_incoming")
    reason = models.TextField()
    actor = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(outgoing_fact__isnull=False, outgoing_legacy__isnull=True) | models.Q(outgoing_fact__isnull=True, outgoing_legacy__isnull=False), name="finance_transfer_out_one_ref"),
            models.CheckConstraint(condition=models.Q(incoming_fact__isnull=False, incoming_legacy__isnull=True) | models.Q(incoming_fact__isnull=True, incoming_legacy__isnull=False), name="finance_transfer_in_one_ref"),
        ]


class FinanceClassification(FinanceAppendOnly):
    fact = models.ForeignKey(FinanceFact, on_delete=models.PROTECT, related_name="classifications")
    nature = models.CharField(max_length=30)
    reason = models.TextField()
    actor = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    objects = OperationLogQuerySet.as_manager()


class RmbCashEvent(TimestampedModel):
    """Additive bank facts. Never a second business receipt or a bank balance."""
    event_no = models.CharField(max_length=64, unique=True)
    request_key = models.CharField(max_length=128, unique=True)
    request_hash = models.CharField(max_length=64)
    request_payload = models.JSONField()
    kind = models.CharField(max_length=24, choices=[("fx_settlement", "结汇到账"), ("cny_direct", "人民币直接收付"), ("bank_fee", "独立银行扣费")])
    currency = models.CharField(max_length=3)
    amount = models.DecimalField(max_digits=18, decimal_places=4)
    direction = models.CharField(max_length=10, choices=Transaction.DIRECTION_CHOICES)
    bank_date = models.DateField()
    bank_net_amount = models.DecimalField(max_digits=18, decimal_places=2)
    fee_mode = models.CharField(max_length=10, choices=[("none", "无"), ("included", "净额已含扣")], default="none")
    fee_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    source_account = models.CharField(max_length=40)
    rmb_account = models.CharField(max_length=40)
    bank_reference = models.CharField(max_length=120)
    bank_counterparty = models.CharField(max_length=200, blank=True)
    bank_summary = models.CharField(max_length=500, blank=True)
    bank_transaction_id = models.CharField(max_length=120, blank=True)
    evidence_reference = models.CharField(max_length=200, blank=True)
    evidence_sha256 = models.CharField(max_length=64, blank=True)
    evidence_note = models.CharField(max_length=500, blank=True)
    quoted_rate = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    status = models.CharField(max_length=12, choices=[("pending", "待人工确认"), ("confirmed", "已确认银行事实"), ("cancelled", "草稿已放弃")], default="pending")
    created_actor = models.JSONField()
    confirmed_actor = models.JSONField(default=dict)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_reason = models.CharField(max_length=500, blank=True)
    correction_of = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="corrections")
    fee_for = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="separate_fees")

    class Meta:
        ordering = ["-bank_date", "-pk"]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="cash_event_source_positive"),
            models.CheckConstraint(condition=models.Q(bank_net_amount__gt=0), name="cash_event_net_positive"),
            models.CheckConstraint(condition=models.Q(fee_amount__gte=0), name="cash_event_fee_nonnegative"),
            models.CheckConstraint(condition=models.Q(status="confirmed", confirmed_at__isnull=False) | models.Q(status__in=["pending", "cancelled"], confirmed_at__isnull=True), name="cash_event_confirmation_state"),
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            old = type(self).objects.get(pk=self.pk)
            allowed = {"status", "confirmed_at", "confirmed_actor", "cancelled_reason", "updated_at"}
            if old.status != "pending" or any(getattr(old, f.attname) != getattr(self, f.attname) for f in self._meta.concrete_fields if f.name not in allowed):
                from django.core.exceptions import ValidationError
                raise ValidationError("资金事实及凭证快照不可覆盖；请使用留痕更正指令保留原始记录。")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        from django.core.exceptions import ValidationError
        raise ValidationError("资金事件必须留痕，不可删除。")


class CashDuplicateReview(models.Model):
    """Immutable evidence of a reviewed possible duplicate."""
    event = models.OneToOneField(RmbCashEvent, on_delete=models.PROTECT, related_name="duplicate_review")
    candidate_ids = models.JSONField()
    reason = models.CharField(max_length=500)
    actor = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    objects = OperationLogQuerySet.as_manager()

    def save(self, *args, **kwargs):
        if self.pk and not self._state.adding:
            raise ValidationError("核实记录只允许追加。")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("核实记录不可删除。")


class CashSourceAllocation(TimestampedModel):
    event = models.ForeignKey(RmbCashEvent, on_delete=models.PROTECT, related_name="sources")
    source = models.ForeignKey(Transaction, on_delete=models.PROTECT, related_name="cash_source_allocations")
    amount = models.DecimalField(max_digits=18, decimal_places=4)
    currency = models.CharField(max_length=3)
    source_snapshot = models.JSONField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["event", "source"], name="cash_event_source_unique"),
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="cash_allocation_positive"),
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            from django.core.exceptions import ValidationError
            raise ValidationError("资金来源快照不可覆盖。")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        from django.core.exceptions import ValidationError
        raise ValidationError("资金来源分配必须保留。")


# Keep the historical takeover workflow in its own module while registering its
# models in the existing CRM app.
from .history_takeover_models import (  # noqa: E402,F401
    HistoryInventoryBaseline,
    HistoryInventoryBaselineReversal,
    HistoryOperationalContract,
    HistoryTakeoverApplication,
    HistoryTakeoverEvent,
    HistoryTakeoverGroup,
    HistoryTakeoverHandoff,
    HistoryTakeoverSourceRecord,
)


class AdvanceAllocation(TimestampedModel):
    """Non-cash allocation: keeps cash totals unchanged and preserves reversal history."""
    advance = models.ForeignKey(Transaction, on_delete=models.PROTECT, related_name="allocations")
    plan = models.ForeignKey(PaymentPlan, on_delete=models.PROTECT, related_name="advance_allocations")
    amount = models.DecimalField(max_digits=14, decimal_places=4)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(amount__gt=0), name="advance_allocation_positive")]


class SalesRule(TimestampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="sales_rules")
    sku = models.ForeignKey(SKU, null=True, blank=True, on_delete=models.PROTECT, related_name="sales_rules")
    name = models.CharField("规则名称", max_length=120)
    rule_type = models.CharField(max_length=20, choices=[("moq", "最低报价数量")], default="moq")
    filters = models.JSONField("参数条件", default=dict, blank=True)
    minimum_quantity = models.DecimalField(max_digits=14, decimal_places=2)
    unit = models.CharField(max_length=30, default="pcs")
    effective_from = models.DateField(null=True, blank=True)
    effective_until = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(minimum_quantity__gt=0), name="sales_moq_positive")]


class ReminderQuerySet(models.QuerySet):
    def delete(self):
        raise ValidationError("新品提醒不可删除，请使用作废。")


class NewProductReminder(TimestampedModel):
    """One independent customer requirement; never inferred from legacy notes."""
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="new_product_reminders")
    follow_up = models.ForeignKey(FollowUp, on_delete=models.PROTECT, null=True, blank=True, related_name="new_product_reminders")
    contact = models.ForeignKey(Contact, on_delete=models.PROTECT, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, null=True, blank=True)
    objects = ReminderQuerySet.as_manager()
    requirement = models.TextField("所找产品")
    specification = models.TextField("规格", blank=True)
    other_requirements = models.TextField("其他要求", blank=True)
    request_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    version = models.PositiveIntegerField(default=1)
    created_by = models.CharField(max_length=180)
    voided_at = models.DateTimeField(null=True, blank=True)
    voided_by = models.CharField(max_length=180, blank=True)
    void_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [models.CheckConstraint(condition=(models.Q(voided_at__isnull=True, voided_by="", void_reason="") | (models.Q(voided_at__isnull=False) & ~models.Q(voided_by="") & ~models.Q(void_reason=""))), name="reminder_void_complete")]

    def delete(self, *args, **kwargs):
        raise ValidationError("新品提醒不可删除，请使用作废。")
