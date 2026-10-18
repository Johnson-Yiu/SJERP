"""FIXTURE_SETUP: one synthetic quote only, no financial mutation."""
exec(compile(__import__('pathlib').Path(__file__).with_name('db_snapshot.py').read_text(encoding='utf8'), 'snapshot_setup', 'exec'))
from crm.models import Quote,Customer
from django.utils import timezone
quote,created=Quote.objects.get_or_create(quote_no='FIX01-QUOTE',defaults={'customer':Customer.objects.get(code='FUP02-C'),'quote_date':timezone.localdate(),'currency':'USD'})
print('FIXTURE_SETUP quote',quote.pk,created)
