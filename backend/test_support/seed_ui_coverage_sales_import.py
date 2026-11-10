"""Generate a disposable long import preview fixture; never executes an import."""
import os
from datetime import date
from pathlib import Path
import django
django.setup()
from django.conf import settings
from openpyxl import Workbook
from test_support.isolated_runtime import verify_isolated_runtime
from crm.models import Customer, Product, SKU

verify_isolated_runtime(settings=settings, database_must_exist=True)
root = Path(os.environ['ISOLATED_TEST_ROOT']).resolve()
customer = Customer.objects.create(code='UIIMP-C001', name='合成导入客户')
product = Product.objects.create(code='UIIMP-P001', name='合成导入产品')
sku = SKU.objects.create(product=product, sku='UIIMP-SKU001', unit='个', cost_price='2')
book = Workbook()
sheet = book.active
sheet.title = '订单明细'
sheet.append(['来源订单编号', '客户编号', '订单日期', '币种', 'SKU', '交易单位', '数量', '单价', '对人民币汇率'])
for index in range(150):
    sheet.append([f'UIIMP-{index:04d}', customer.code, date(2026, 11, 6), 'CNY', sku.sku, '个', 1, '12', '1'])
book.save(root / 'ui-coverage-long-orders.xlsx')
book.close()
print('Prepared 150 synthetic order rows in isolated fixture; no import executed')
