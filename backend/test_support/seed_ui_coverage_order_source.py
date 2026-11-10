import runpy
from pathlib import Path

# Reuse the established isolated workspace fixture, including its runtime guard.
runpy.run_path(str(Path(__file__).with_name('seed_workspace_tabs.py')))
from crm.models import SKU, Supplier, SupplierSKU

SupplierSKU.objects.create(
    sku=SKU.objects.get(sku='WS-SKU001'),
    supplier=Supplier.objects.get(code='WS-S001'),
    supplier_sku_code='SYNTH-SOURCE-01',
    supplier_model='Synthetic supplier model',
    purchase_price='12.50', currency='USD', moq=10, lead_time_days=7,
)
