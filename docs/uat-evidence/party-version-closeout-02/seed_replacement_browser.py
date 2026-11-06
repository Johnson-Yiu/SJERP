"""Extend the isolated document seed with a synthetic replacement target."""
import contextlib
import io
import json
import runpy
from pathlib import Path
from uuid import uuid4

buffer = io.StringIO()
with contextlib.redirect_stdout(buffer):
    runpy.run_path(str(Path(__file__).with_name('seed_document_party.py')), run_name='__main__')
seed = json.loads(buffer.getvalue().strip().splitlines()[-1])
from crm.models import Customer, Order, Supplier

suffix = uuid4().hex[:8].upper()
target = Customer.objects.create(code=f'RP{suffix}', name=f'Synthetic Replacement {suffix}', country='France')
seed['replacement_customer'] = target.pk
seed['replacement_name'] = target.name
supplier = Supplier.objects.create(code='RZ', name=f'Synthetic Replacement Supplier {suffix}')
seed['replacement_supplier'] = supplier.pk
seed['sku'] = Order.objects.get(pk=seed['order']).items.first().sku_id
print(json.dumps(seed))
