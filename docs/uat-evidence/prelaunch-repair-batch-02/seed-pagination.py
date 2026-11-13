from django.conf import settings
import django
django.setup()
from test_support.isolated_runtime import verify_isolated_runtime
verify_isolated_runtime(settings=settings,database_must_exist=True)
from crm.models import Customer
Customer.objects.bulk_create([Customer(code=f'UI-PAGE-{i:03}',name=f'合成分页客户{i:03}',country='CN') for i in range(55)])
