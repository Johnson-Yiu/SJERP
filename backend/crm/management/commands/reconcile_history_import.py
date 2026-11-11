"""Read-only reconciliation of a single historical takeover application."""
from collections import Counter
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.core.serializers.json import DjangoJSONEncoder
import json
import subprocess
import hashlib
from pathlib import Path
from crm.history_takeover import _record_source_id
from crm.history_products import document_product_rows
from crm.history_operational_finance import SOURCE_SYSTEM, _source_key
from crm.models import (HistoryTakeoverApplication, Order, PurchaseOrder, FinanceFact,
                        InventoryMovement, InventoryReservation, Shipment, GoodsReceipt, Transaction)


def reconcile(application, source_sha):
    result = {'application_id': application.pk, 'file': application.source_file_name,
              'file_sha256': application.source_sha256, 'source_sha': source_sha,
              'application_status': application.status, 'groups': [],
              'global_fact_counts': {m.__name__: m.objects.count() for m in
                  (FinanceFact, Transaction, InventoryMovement, InventoryReservation, Shipment, GoodsReceipt)},
              'scope_note': 'global_fact_counts are database-wide; compare isolated snapshots only',
              'unverified': []}
    for group in application.groups.all():
        records = {(r.record_type, r.source_record_id): r for r in group.source_records.all()}
        mappings = []
        for sheet, items in group.source_rows.items():
            for item in items:
                identity = _record_source_id(sheet, item['data'])
                source = records.get((sheet, identity))
                mappings.append({'sheet': sheet, 'row': item['row'], 'source_id': identity,
                                 'record_id': source.pk if source else None,
                                 'target_model': source.target_model if source else '',
                                 'target_id': source.target_id if source else None})
        doc_ids = {model: [r.target_id for r in records.values() if r.target_model == label and r.target_id]
                   for model, label in ((Order, 'crm.Order'), (PurchaseOrder, 'crm.PurchaseOrder'))}
        documents, products, currency = [], [], {}
        customers = set()
        for model in (Order, PurchaseOrder):
            for doc in model.objects.filter(pk__in=doc_ids[model]):
                is_sale = isinstance(doc, Order)
                lines = document_product_rows(doc)
                products.extend(lines)
                if is_sale and doc.customer_id:
                    customers.add(doc.customer_id)
                row = {'id': doc.pk, 'kind': 'sales' if is_sale else 'purchase',
                       'number': doc.order_no if is_sale else doc.purchase_no,
                       'currency': doc.currency, 'status': doc.status,
                       'products': lines, 'shipping': str(doc.shipping_fee) if is_sale else '0',
                       'discount': str(doc.discount) if is_sale else '0', 'total': str(doc.total_amount),
                       'paid_formal': str(doc.paid_amount),
                       'open_formal': str(doc.outstanding_amount if is_sale else doc.unpaid_amount)}
                documents.append(row)
                bucket = currency.setdefault(doc.currency, {'sales_total': Decimal(0), 'purchase_total': Decimal(0),
                    'sales_products': Decimal(0), 'purchase_products': Decimal(0), 'shipping': Decimal(0),
                    'discount': Decimal(0), 'sales_paid_formal': Decimal(0), 'purchase_paid_formal': Decimal(0),
                    'receivable_formal': Decimal(0), 'payable_formal': Decimal(0)})
                side = 'sales' if is_sale else 'purchase'
                bucket[side + '_total'] += doc.total_amount
                bucket[side + '_products'] += sum((Decimal(line['amount']) for line in lines), Decimal(0))
                bucket[side + '_paid_formal'] += doc.paid_amount
                bucket['receivable_formal' if is_sale else 'payable_formal'] += doc.outstanding_amount if is_sale else doc.unpaid_amount
                if is_sale:
                    bucket['shipping'] += doc.shipping_fee
                    bucket['discount'] += doc.discount
        statuses = Counter(row['status'] for row in products)
        cash_sources = [r for r in records.values() if r.record_type == '收付款流水']
        facts = list(FinanceFact.objects.filter(source_system=SOURCE_SYSTEM,
                         source_key__in=[_source_key(r) for r in cash_sources]).values(
                             'id', 'source_key', 'amount', 'direction', 'actual_date'))
        checks = group.preflight_result.get('results', [])
        result['groups'].append({'id': group.pk, 'source_group': group.source_group_id,
            'status': group.status, 'truth': group.truth_status, 'coverage': group.coverage_status,
            'preflight_status_counts': dict(Counter(x.get('status', '') for x in checks)),
            'preflight_results': checks,
            'handoffs': {'finance': group.finance_handoff_status, 'inventory': group.inventory_handoff_status,
                         'fulfillment': group.fulfillment_handoff_status},
            'remainder_snapshot': group.remainder_snapshot, 'source_rows': mappings, 'source_record_count': len(records), 'customer_count': len(customers),
            'order_count': len(documents), 'product_count': len(products), 'product_states': dict(statuses),
            'documents': documents, 'currency_totals': currency,
            'source_cash': [{'source_id': r.source_record_id, 'snapshot': r.source_snapshot.get('source', {}),
                             'finance_key': _source_key(r)} for r in cash_sources],
            'cny_finance_facts': facts})
        if group.status != 'executed':
            result['unverified'].append(f'group {group.source_group_id}: not executed; no target mapping assumed')
        result['unverified'].append(f'group {group.source_group_id}: source completeness, conflicts and unposted amounts require review')
    return result


class Command(BaseCommand):
    help = 'Output a read-only historical application reconciliation as JSON.'
    def add_arguments(self, parser):
        parser.add_argument('application_id', type=int)
        parser.add_argument('--source-sha', required=True, help='verified full source commit SHA')
        parser.add_argument('--source-file', required=True, help='original source workbook path')
    def handle(self, *args, **options):
        sha = options['source_sha']
        if len(sha) != 40 or any(c not in '0123456789abcdef' for c in sha):
            raise ValueError('source SHA must be a full lowercase 40-character commit SHA')
        actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
        dirty = subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=all', '--', 'backend', 'templates'], text=True).strip()
        if actual != sha or dirty:
            raise ValueError('source SHA mismatch or tracked working tree is dirty')
        app = HistoryTakeoverApplication.objects.get(pk=options['application_id'])
        digest = hashlib.sha256(Path(options['source_file']).read_bytes()).hexdigest()
        if digest != app.source_sha256:
            raise ValueError('source workbook SHA-256 does not match application')
        self.stdout.write(json.dumps(reconcile(app, sha), cls=DjangoJSONEncoder, ensure_ascii=False, indent=2))
