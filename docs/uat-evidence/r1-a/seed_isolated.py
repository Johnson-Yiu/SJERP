"""FIXTURE_SETUP only: disposable master data, never a UI acceptance result."""
from pathlib import Path
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from crm.models import Customer, Order, InventoryMovement

assert Path(settings.DATABASES['default']['NAME']).resolve() == (settings.BASE_DIR/'r1a-isolated.sqlite3').resolve()
with transaction.atomic():
    source = settings.BASE_DIR.parent/'docs/uat-evidence/r0-f7b/seed_isolated.py'
    exec(source.read_text(encoding='utf-8').replace('r0f7b-ux.sqlite3', 'r1a-isolated.sqlite3').replace('R0F7B', 'R1A'))
    customer = Customer.objects.create(code='R1A-C', name='R1A 合成客户', country='Germany')
    order = Order.objects.create(order_no='R1A-USD500',customer=customer,order_date=timezone.localdate(),expected_ship_date=timezone.localdate(),currency='USD',exchange_rate=Decimal('7.1'),status='draft')
    order.items.create(sku=pcs,quantity=Decimal('10'),unit_price=Decimal('50'))
    InventoryMovement.objects.create(movement_no='R1A-OPENING',movement_date=timezone.localdate(),type='adjust_in',sku=pcs,quantity=Decimal('10'),unit_cost=Decimal('20'),source_type='manual',notes='FIXTURE_SETUP opening stock')
print('FIXTURE_SETUP complete: no real account; order draft requires real UI confirmation')
