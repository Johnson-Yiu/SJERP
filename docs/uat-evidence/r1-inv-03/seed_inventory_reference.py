"""Create the disposable R1-INV-03 browser fixture only."""

from datetime import date
from decimal import Decimal

from django.conf import settings

from crm.models import (
    Customer,
    InventoryMovement,
    InventoryReservation,
    Order,
    Product,
    PurchaseOrder,
    SKU,
    SKUVersion,
    Supplier,
    SupplierSKU,
)


assert str(settings.DATABASES["default"]["NAME"]).endswith("r1-inv-03-ux.sqlite3")
assert not SKU.objects.exists(), "Run this fixture only against the empty disposable database."

day = date(2026, 10, 20)
product = Product.objects.create(code="INV3-P", name="库存参考验收灯具")

stocked = SKU.objects.create(
    product=product,
    sku="INV3-STOCKED-001",
    display_name_cn="库存参考灯具（有库存）",
    sales_model="INV3-SM-001",
    specification="24W / 4000K / 可定制线长",
    description_cn="采购页面库存参考测试 SKU。",
    parameter_values={"色温": "4000K", "功率": "24W"},
    product_details=[{"custom": "线长可定制", "note": "仅供资料查看"}],
    unit="pcs",
)
empty = SKU.objects.create(
    product=product,
    sku="INV3-EMPTY-002",
    display_name_cn="库存参考灯具（无库存）",
    sales_model="INV3-SM-002",
    specification="12W / 暖白",
    unit="box",
)
negative = SKU.objects.create(
    product=product,
    sku="INV3-NEGATIVE-003",
    display_name_cn="库存参考灯具（可用库存为负）",
    sales_model="INV3-SM-003",
    unit="roll",
)

InventoryMovement.objects.create(
    movement_no="INV3-IN-001",
    movement_date=day,
    type="adjust_in",
    sku=stocked,
    quantity=Decimal("120"),
    warehouse="验收仓",
    source_type="manual",
)
InventoryMovement.objects.create(
    movement_no="INV3-OUT-001",
    movement_date=day,
    type="sample_out",
    sku=stocked,
    quantity=Decimal("20"),
    warehouse="验收仓",
    source_type="manual",
)
InventoryMovement.objects.create(
    movement_no="INV3-NEG-OUT-001",
    movement_date=day,
    type="adjust_out",
    sku=negative,
    quantity=Decimal("8"),
    warehouse="验收仓",
    source_type="manual",
)

customer = Customer.objects.create(code="IV3-C", name="库存参考验收客户")
order = Order.objects.create(
    order_no="INV3-RESERVE-001",
    customer=customer,
    order_date=day,
    status="confirmed",
    currency="CNY",
)
order_item = order.items.create(sku=stocked, quantity=Decimal("30"), unit_price=Decimal("50"))
InventoryReservation.objects.create(order_item=order_item, sku=stocked, quantity=Decimal("30"))

supplier = Supplier.objects.create(code="IV", name="库存参考验收供应商")
source = SupplierSKU.objects.create(
    supplier=supplier,
    sku=stocked,
    supplier_sku_code="IV3-SUP-001",
    supplier_model="IV3-MODEL-001",
    purchase_price=Decimal("18.50"),
    currency="CNY",
    moq=Decimal("10"),
    is_preferred=True,
)
purchase = PurchaseOrder.objects.create(
    purchase_no="INV3-DRAFT-001",
    supplier=supplier,
    order_date=day,
    status="draft",
    currency="CNY",
)
purchase.items.create(
    sku=stocked,
    supplier_sku=source,
    quantity=Decimal("12"),
    unit_price=Decimal("18.50"),
)
in_transit = PurchaseOrder.objects.create(
    purchase_no="INV3-TRANSIT-001",
    supplier=supplier,
    order_date=day,
    status="ordered",
    currency="CNY",
)
in_transit.items.create(
    sku=stocked,
    supplier_sku=source,
    quantity=Decimal("40"),
    unit_price=Decimal("18.50"),
)

SKUVersion.objects.create(
    sku=stocked,
    version_no=1,
    sku_code_snapshot=stocked.sku,
    sales_model_snapshot=stocked.sales_model,
    display_name_cn_snapshot=stocked.display_name_cn,
    description_cn_snapshot=stocked.description_cn,
    description_en_snapshot="Inventory reference fixture.",
    parameter_values_snapshot=stocked.parameter_values,
    product_details_snapshot=stocked.product_details,
    specification_snapshot=stocked.specification,
    changed_fields=["specification"],
    change_reason="浏览器验收历史版本",
)

print(
    {
        "database": settings.DATABASES["default"]["NAME"],
        "stocked_sku": stocked.pk,
        "empty_sku": empty.pk,
        "negative_sku": negative.pk,
        "draft_purchase": purchase.pk,
        "stocked_metrics_expected": {"actual": "100", "reserved": "30", "available": "70", "in_transit": "40"},
    }
)
