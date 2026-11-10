"""Create only disposable synthetic reminder rows for long-list UI evidence."""
import django
django.setup()
from django.conf import settings
from test_support.isolated_runtime import verify_isolated_runtime
from crm.models import Customer, NewProductReminder

verify_isolated_runtime(settings=settings, database_must_exist=True)
if Customer.objects.exists() or NewProductReminder.objects.exists():
    raise SystemExit('Refusing nonempty reminder fixture')
customer = Customer.objects.create(code='UIREM-C001', name='合成需求客户')
for i in range(1, 13):
    NewProductReminder.objects.create(customer=customer, requirement=f'合成产品需求 {i:02d}', specification='合成规格，仅用于界面验收', created_by='synthetic fixture')
print('Created 12 synthetic reminder rows in isolated database')
