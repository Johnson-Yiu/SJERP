import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from crm.tests.test_packing_list_export import PackingListExportTests
t = PackingListExportTests()
t.setUp()
t.full_mixed_packing()
print('order', t.order.pk, 'shipment', t.shipment.pk)
