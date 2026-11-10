"""Synthetic rows for the product operations evidence run."""
import json
import os
from datetime import date

import django

django.setup()
from django.conf import settings

from test_support.isolated_runtime import verify_isolated_runtime

verify_isolated_runtime(settings=settings, database_must_exist=True)

from crm.models import (
    CategoryAttribute, Customer, HSCode, InventoryMovement, Order, PackagingTemplate, Product,
    ProductCategory, ProductCertificate, ProductParameter, PurchaseOrder,
    PurchaseOrderItem, SKU, SKUTradeUnit, Supplier, SupplierSKU,
)

supplier = Supplier.objects.create(code="EVID-S001", name="合成供应商｜森爵照明跨区域灯具及安装配件测试样本")
root = ProductCategory.objects.create(name="合成灯具")
category = ProductCategory.objects.create(name="轨道灯与安装配件", parent=root)
for index, name in enumerate(("色温", "发光角度", "外壳颜色")):
    CategoryAttribute.objects.create(
        category=category, name=name, key=name, include_in_sku=True, include_in_sales_model=index == 0, sort_order=index
    )
product = Product.objects.create(
    code="EVID-P001", name="合成长名称｜商业展厅用低眩光可调角度模块化轨道灯及其多场景安装配件组合",
    category=category, sales_model_prefix="EVIDOLD",
)
product.suppliers.add(supplier)
if os.environ.get("PRODUCT_OPS_PREFIX") == "1":
    Product.objects.create(code="EVID-P002", name="合成前缀冲突产品", sales_model_prefix="EIVDUPE", category=category)
if os.environ.get("PRODUCT_OPS_FOLLOWUP") == "lifecycle":
    Product.objects.create(code="EVID-P002", name="合成灯具配件", category=category)
ProductParameter.objects.create(product=product, name="标称功率", value="24", unit="W")
ProductCertificate.objects.create(product=product, name="合成测试证书", certificate_no="EVID-CERT-001")
PackagingTemplate.objects.create(
    name="合成长箱规｜商业展厅轨道灯及配件混合装运",
    supplier=supplier, carton_length=80, carton_width=40, carton_height=35,
)
HSCode.objects.create(code="8539510000", description="合成测试归类")
skus = [
    SKU.objects.create(
        product=product, sku=f"EVID-TRACK-LONG-SKU-3000K-BEAM24-BLACK-{index:02}",
        unit=unit, default_price="10", cost_price="4", sales_model=f"EVIDOLD-{index:02}",
        parameter_values={f"{category.pk}:色温": str(3000 + index * 100)},
        sales_model_abbreviations={f"{category.pk}:色温:{3000 + index * 100}": f"C{index}"},
    )
    for index, unit in enumerate(("pcs", "m", "set", "pcs"), 1)
]
for index, sku in enumerate(skus, 1):
    SupplierSKU.objects.create(
        supplier=supplier, sku=sku, supplier_sku_code=f"EVID-SUPPLY-{index:02}",
        supplier_model=f"TRACK-{index:02}", purchase_price="4", currency="USD",
    )
SKUTradeUnit.objects.create(sku=skus[0], name="10 件／箱", unit="箱", factor=10, is_default=True)
SKUTradeUnit.objects.create(sku=skus[0], supplier=supplier, name="20 件／大箱", unit="箱", factor=20)
for index, (warehouse_type, warehouse) in enumerate((("自有仓", "合成一号仓"), ("第三方仓", "合成第三方仓")), 1):
    InventoryMovement.objects.create(
        movement_no=f"EVID-IM-000{index}", movement_date=date.today(),
        type="adjust_in", sku=skus[0], quantity=10, warehouse_type=warehouse_type,
        warehouse=warehouse, lot_reference=f"EVID-LOT-20261110-A-{index:02}",
    )
purchase = PurchaseOrder.objects.create(
    purchase_no="EVID-PO-0001-LONG-REFERENCE", supplier=supplier, order_date=date.today(),
    status="draft", currency="USD", exchange_rate="7.2",
)
for index, sku in enumerate(skus, 1):
    PurchaseOrderItem.objects.create(purchase_order=purchase, sku=sku, quantity=index * 10, unit_price="4")
customer = Customer.objects.create(code="EVID-C001", name="合成采购成本归属客户", country="US")
for index in (1, 2):
    Order.objects.create(
        order_no=f"EVID-SO-00{index}", customer=customer, order_date=date.today(),
        status="draft", currency="USD", exchange_rate="7.2",
    )
fixture = {"product": product.pk, "sku": skus[0].pk, "purchase": purchase.pk, "supplier": supplier.pk}
if os.environ.get("PRODUCT_OPS_FOLLOWUP") == "priority":
    cancel_purchase = PurchaseOrder.objects.create(
        purchase_no="EVID-PO-CANCEL", supplier=supplier, order_date=date.today(),
        status="draft", currency="USD", exchange_rate="7.2",
    )
    PurchaseOrderItem.objects.create(purchase_order=cancel_purchase, sku=skus[0], quantity=5, unit_price="4")
    fixture["cancel_purchase"] = cancel_purchase.pk
print(json.dumps(fixture))
