from decimal import Decimal

from django.db import migrations


def reconcile(apps, schema_editor):
    Allocation = apps.get_model('crm', 'AdvanceAllocation')
    Transaction = apps.get_model('crm', 'Transaction')
    alias = schema_editor.connection.alias
    for advance in Transaction.objects.using(alias).filter(kind='unallocated_advance').iterator():
        rows = list(Allocation.objects.using(alias).filter(advance_id=advance.pk, is_active=True).order_by('id'))
        cash = sum((row.cash_amount or Decimal('0') for row in rows), Decimal('0'))
        if cash <= advance.amount:
            continue
        total = sum((row.amount for row in rows), Decimal('0'))
        if advance.fee_responsibility != 'company' or total > advance.amount + advance.bank_fee_amount:
            raise RuntimeError(f'Legacy allocation requires review: advance {advance.pk}')
        remaining = advance.amount
        for row in rows:
            actual = min(row.amount, remaining)
            Allocation.objects.using(alias).filter(pk=row.pk).update(cash_amount=actual, fee_credit_amount=row.amount - actual)
            remaining -= actual


class Migration(migrations.Migration):
    dependencies = [('crm', '0120_finance_actual_receipt_and_writeoff_correction')]
    operations = [migrations.RunPython(reconcile, migrations.RunPython.noop)]
