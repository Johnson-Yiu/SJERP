from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.db import models


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


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
        ("dashboard", "经营概览"), ("customers", "客户管理"), ("contacts", "联系人"),
        ("followups", "跟进记录"), ("quotes", "报价管理"), ("orders", "订单管理"),
        ("products", "产品管理"), ("skus", "SKU 管理"), ("inventory", "库存流水"),
        ("parameters", "产品参数"), ("certificates", "产品证书"), ("categories", "产品分类"),
        ("transactions", "财务流水"), ("imports", "数据导入"), ("organization", "组织架构"),
        ("employees", "成员管理"), ("permissions", "权限配置"),
    ]
    role = models.ForeignKey(AccessRole, on_delete=models.CASCADE, related_name="permissions")
    module = models.CharField("功能模块", max_length=30, choices=MODULE_CHOICES)
    can_view = models.BooleanField("查看", default=True)
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
    source = models.CharField("客户来源", max_length=100, blank=True)
    status = models.CharField("状态", max_length=20, choices=STATUS_CHOICES, default="lead")
    owner = models.CharField("负责人", max_length=100, blank=True)
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
    next_follow_up = models.DateField("下次跟进", null=True, blank=True)
    owner = models.CharField("跟进人", max_length=100, blank=True)

    class Meta:
        ordering = ["-followed_at"]


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
    uppercase = models.BooleanField("SKU 中转为大写", default=False)
    sort_order = models.PositiveIntegerField("排序", default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [models.UniqueConstraint(fields=["category", "key"], name="unique_category_attribute_key")]

    def __str__(self):
        return f"{self.category.name} · {self.name}"


class ProductCodeSequence(models.Model):
    code_date = models.DateField(unique=True)
    last_value = models.PositiveIntegerField(default=0)


class Product(TimestampedModel):
    STATUS_CHOICES = [("active", "在售"), ("development", "开发中"), ("discontinued", "停产")]
    name = models.CharField("产品名称", max_length=200)
    name_en = models.CharField("产品英文名称", max_length=200, blank=True)
    hs_code = models.CharField("HS 编码", max_length=30, blank=True)
    code = models.CharField("产品编号", max_length=50, unique=True)
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")
    additional_categories = models.ManyToManyField(ProductCategory, blank=True, related_name="secondary_products", verbose_name="附加分类")
    description = models.TextField("描述", blank=True)
    status = models.CharField("状态", max_length=20, choices=STATUS_CHOICES, default="active")

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} {self.name}"


class SKU(TimestampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="skus")
    sku = models.CharField("SKU", max_length=80, unique=True)
    specification = models.CharField("规格", max_length=200, blank=True)
    unit = models.CharField("单位", max_length=30, default="pcs")
    cost_price = models.DecimalField("成本价", max_digits=14, decimal_places=4, default=0)
    default_price = models.DecimalField("默认售价", max_digits=14, decimal_places=4, default=0)
    currency = models.CharField("币种", max_length=10, default="USD")
    active = models.BooleanField("启用", default=True)
    parameter_values = models.JSONField("参数快照", default=dict, blank=True)
    product_details = models.JSONField("产品明细", default=list, blank=True)
    image = models.ImageField("SKU 图片", upload_to="sku-images/%Y/%m/", blank=True)

    class Meta:
        ordering = ["sku"]

    def __str__(self):
        return self.sku


class QuoteNumberSequence(models.Model):
    quote_date = models.DateField()
    country_code = models.CharField(max_length=2)
    last_value = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["quote_date", "country_code"], name="unique_quote_number_sequence")]


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
    file_url = models.URLField("文件链接", blank=True)
    notes = models.TextField("备注", blank=True)

    class Meta:
        ordering = ["-expires_on", "name"]

    def __str__(self):
        return f"{self.product.code} · {self.name}"


class Quote(TimestampedModel):
    STATUS_CHOICES = [("draft", "草稿"), ("sent", "已发送"), ("accepted", "已接受"), ("rejected", "已拒绝"), ("expired", "已过期")]
    quote_no = models.CharField("报价单号", max_length=40, unique=True)
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
    quote_date = models.DateField("报价日期")
    valid_until = models.DateField("有效期至", null=True, blank=True)
    status = models.CharField("状态", max_length=20, choices=STATUS_CHOICES, default="draft")
    currency = models.CharField("币种", max_length=10, default="USD")
    exchange_rate = models.DecimalField("对人民币汇率", max_digits=12, decimal_places=6, default=1)
    shipping_fee = models.DecimalField("运费", max_digits=14, decimal_places=2, default=0)
    discount = models.DecimalField("折扣金额", max_digits=14, decimal_places=2, default=0)
    notes = models.TextField("条款/备注", blank=True)
    recipient_name = models.CharField("收件人", max_length=200, blank=True)
    buyer_address = models.TextField("买方地址", blank=True)
    buyer_email = models.EmailField("买方邮箱", blank=True)
    buyer_phone = models.CharField("买方电话", max_length=100, blank=True)
    lead_time_days = models.PositiveIntegerField("交期（天）", null=True, blank=True)
    deposit_ratio = models.DecimalField("定金比例", max_digits=6, decimal_places=4, default=0)
    trading_terms = models.TextField("贸易条款", blank=True)
    shipping_details = models.TextField("运输信息", blank=True)

    class Meta:
        ordering = ["-quote_date", "-id"]

    def save(self, *args, **kwargs):
        if not self.buyer_company_name and self.customer_id:
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
        return sum((item.amount for item in self.items.all()), Decimal("0")) + self.shipping_fee - self.discount


class QuoteRevisionCounter(models.Model):
    root_quote = models.OneToOneField(Quote, on_delete=models.CASCADE, related_name="revision_counter")
    last_value = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(99)])


class QuoteItem(models.Model):
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="items")
    sku = models.ForeignKey(SKU, on_delete=models.PROTECT, related_name="quote_items")
    sku_code_snapshot = models.CharField("SKU 编码快照", max_length=80, blank=True)
    product_name_snapshot = models.CharField("产品名称快照", max_length=200, blank=True)
    unit_snapshot = models.CharField("单位快照", max_length=30, blank=True)
    image_snapshot = models.ImageField("产品图片快照", upload_to="quote-item-images/%Y/%m/", blank=True)
    quantity = models.DecimalField("数量", max_digits=14, decimal_places=2)
    unit_price = models.DecimalField("单价", max_digits=14, decimal_places=4)
    description = models.TextField("产品描述", blank=True)
    notes = models.CharField("备注", max_length=200, blank=True)

    @property
    def amount(self):
        return self.quantity * self.unit_price


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
    STATUS_CHOICES = [("draft", "草稿"), ("confirmed", "已确认"), ("production", "生产中"), ("shipped", "已发货"), ("completed", "已完成"), ("cancelled", "已取消")]
    order_no = models.CharField("订单号", max_length=40, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="orders")
    quote = models.ForeignKey(Quote, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    order_date = models.DateField("订单日期")
    expected_ship_date = models.DateField("预计交期", null=True, blank=True)
    status = models.CharField("状态", max_length=20, choices=STATUS_CHOICES, default="confirmed")
    currency = models.CharField("币种", max_length=10, default="USD")
    exchange_rate = models.DecimalField("对人民币汇率", max_digits=12, decimal_places=6, default=1)
    shipping_fee = models.DecimalField("运费", max_digits=14, decimal_places=2, default=0)
    discount = models.DecimalField("折扣金额", max_digits=14, decimal_places=2, default=0)
    notes = models.TextField("备注", blank=True)

    class Meta:
        ordering = ["-order_date", "-id"]

    @property
    def total_amount(self):
        return sum((item.amount for item in self.items.all()), Decimal("0")) + self.shipping_fee - self.discount

    @property
    def paid_amount(self):
        return sum((t.amount for t in self.transactions.filter(direction="income", status="confirmed")), Decimal("0"))


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    sku = models.ForeignKey(SKU, on_delete=models.PROTECT, related_name="order_items")
    quantity = models.DecimalField("数量", max_digits=14, decimal_places=2)
    unit_price = models.DecimalField("单价", max_digits=14, decimal_places=4)
    cost_price = models.DecimalField("成交时成本", max_digits=14, decimal_places=4, default=0)
    notes = models.CharField("备注", max_length=200, blank=True)

    @property
    def amount(self):
        return self.quantity * self.unit_price


OVERAGE_REASON_CHOICES = [
    ("overprocurement", "超采"),
    ("gift", "赠品"),
    ("carton_variance", "尾差"),
    ("customer_addon", "客户追加"),
    ("gift_or_sample", "赠品或样品"),
    ("packing_variance", "包装尾差"),
]


class Supplier(TimestampedModel):
    name = models.CharField("供应商名称", max_length=200, unique=True)
    contact_name = models.CharField("联系人", max_length=100, blank=True)
    phone = models.CharField("电话", max_length=50, blank=True)
    email = models.EmailField("邮箱", blank=True)
    currency = models.CharField("默认币种", max_length=10, default="USD")
    payment_terms = models.CharField("付款条款", max_length=200, blank=True)
    notes = models.TextField("备注", blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class PurchaseOrder(TimestampedModel):
    STATUS_CHOICES = [
        ("draft", "草稿"),
        ("ordered", "已下单"),
        ("partial", "部分到货"),
        ("completed", "已完成"),
        ("cancelled", "已取消"),
    ]
    purchase_no = models.CharField("采购单号", max_length=40, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="purchase_orders")
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="purchase_orders")
    order_date = models.DateField("下单日期")
    expected_arrival_date = models.DateField("预计到货日", null=True, blank=True)
    status = models.CharField("状态", max_length=20, choices=STATUS_CHOICES, default="draft")
    currency = models.CharField("币种", max_length=10, default="USD")
    exchange_rate = models.DecimalField("对人民币汇率", max_digits=12, decimal_places=6, default=1)
    notes = models.TextField("备注", blank=True)

    class Meta:
        ordering = ["-order_date", "-id"]

    @property
    def total_amount(self):
        return sum((item.quantity * item.unit_price for item in self.items.all()), Decimal("0"))

    @property
    def paid_amount(self):
        return sum(
            (row.amount for row in self.transactions.filter(direction="expense", status="confirmed")),
            Decimal("0"),
        )

    @property
    def unpaid_amount(self):
        return self.total_amount - self.paid_amount

    def __str__(self):
        return self.purchase_no


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="items")
    sku = models.ForeignKey(SKU, on_delete=models.PROTECT, related_name="purchase_order_items")
    quantity = models.DecimalField("采购数量", max_digits=14, decimal_places=2)
    unit_price = models.DecimalField("采购单价", max_digits=14, decimal_places=4)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="purchase_item_quantity_positive"),
            models.CheckConstraint(condition=models.Q(unit_price__gte=0), name="purchase_item_price_non_negative"),
        ]

    @property
    def received_quantity(self):
        return sum((receipt.quantity for receipt in self.receipts.all()), Decimal("0"))

    @property
    def remaining_quantity(self):
        return self.quantity - self.received_quantity


class Shipment(TimestampedModel):
    STATUS_CHOICES = [("draft", "草稿"), ("confirmed", "已确认"), ("cancelled", "已取消")]
    shipment_no = models.CharField("发货单号", max_length=40, unique=True)
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="shipments")
    shipment_date = models.DateField("发货日期")
    logistics_provider = models.CharField("物流商", max_length=100, blank=True)
    waybill_no = models.CharField("物流单号", max_length=100, blank=True)
    status = models.CharField("状态", max_length=20, choices=STATUS_CHOICES, default="draft")
    notes = models.TextField("备注", blank=True)

    class Meta:
        ordering = ["-shipment_date", "-id"]

    def __str__(self):
        return self.shipment_no


class InventoryReservation(models.Model):
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name="reservations")
    sku = models.ForeignKey(SKU, on_delete=models.PROTECT, related_name="inventory_reservations")
    quantity = models.DecimalField("预留数量", max_digits=14, decimal_places=2)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="inventory_reservation_quantity_positive"),
        ]


class InventoryMovement(TimestampedModel):
    TYPE_CHOICES = [
        ("purchase_in", "采购入库"), ("sale_out", "销售出库"),
        ("adjust_in", "盘盈入库"), ("adjust_out", "盘亏出库"),
        ("sample_out", "样品出库"), ("return_in", "客户退回"),
    ]
    movement_no = models.CharField("流水号", max_length=50, unique=True)
    movement_date = models.DateField("发生日期")
    type = models.CharField("类型", max_length=20, choices=TYPE_CHOICES)
    sku = models.ForeignKey(SKU, on_delete=models.PROTECT, related_name="inventory_movements")
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name="inventory_movements")
    quantity = models.DecimalField("数量", max_digits=14, decimal_places=2)
    warehouse = models.CharField("仓库", max_length=100, default="默认仓")
    unit_cost = models.DecimalField("单位成本", max_digits=14, decimal_places=4, default=0)
    reference = models.CharField("参考号", max_length=100, blank=True)
    notes = models.TextField("备注", blank=True)
    source_type = models.CharField(
        "来源类型",
        max_length=20,
        choices=[("manual", "手工"), ("receipt", "到货"), ("shipment", "发货"), ("return", "退货")],
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
        return -self.quantity if self.type in {"sale_out", "adjust_out", "sample_out"} else self.quantity

    def __str__(self):
        return self.movement_no


class GoodsReceipt(TimestampedModel):
    purchase_item = models.ForeignKey(PurchaseOrderItem, on_delete=models.PROTECT, related_name="receipts")
    receipt_date = models.DateField("到货日期")
    quantity = models.DecimalField("到货数量", max_digits=14, decimal_places=2)
    unit_cost = models.DecimalField("实际单价", max_digits=14, decimal_places=4, default=0)
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

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="goods_receipt_quantity_positive"),
            models.CheckConstraint(condition=models.Q(unit_cost__gte=0), name="goods_receipt_cost_non_negative"),
        ]


class ShipmentItem(models.Model):
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name="items")
    order_item = models.ForeignKey(OrderItem, on_delete=models.PROTECT, related_name="shipment_items")
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

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="shipment_item_quantity_positive"),
        ]


class Transaction(TimestampedModel):
    DIRECTION_CHOICES = [("income", "收入"), ("expense", "支出")]
    STATUS_CHOICES = [("pending", "待确认"), ("confirmed", "已确认"), ("cancelled", "已作废")]
    transaction_no = models.CharField("流水号", max_length=50, unique=True)
    transaction_date = models.DateField("发生日期")
    direction = models.CharField("收支方向", max_length=10, choices=DIRECTION_CHOICES)
    category = models.CharField("收支分类", max_length=100)
    amount = models.DecimalField("金额", max_digits=14, decimal_places=2)
    currency = models.CharField("币种", max_length=10, default="USD")
    exchange_rate = models.DecimalField("对人民币汇率", max_digits=12, decimal_places=6, default=1)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions")
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions")
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    status = models.CharField("状态", max_length=20, choices=STATUS_CHOICES, default="confirmed")
    payment_method = models.CharField("支付方式", max_length=100, blank=True)
    reference = models.CharField("外部参考号", max_length=100, blank=True)
    notes = models.TextField("备注", blank=True)

    class Meta:
        ordering = ["-transaction_date", "-id"]
