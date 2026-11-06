"""Conservative eligibility for correcting tax on an unformalized quote chain."""
from django.apps import apps


def can_revise_draft_tax(quote_id, *, lock=False):
    Quote = apps.get_model('crm', 'Quote')
    seen = set()
    current = quote_id
    customer_id = None
    declared_roots = set()
    terminal = None
    while current is not None:
        if current in seen or len(seen) >= 1000:
            return False
        seen.add(current)
        query = Quote.objects
        if lock:
            query = query.select_for_update()
        node = query.filter(pk=current).values('pk', 'status', 'buyer_tax_id', 'parent_quote_id', 'root_quote_id', 'customer_id').first()
        if not node or node['status'] != 'draft' or node['buyer_tax_id'] is None:
            return False
        if customer_id is None:
            customer_id = node['customer_id']
        elif node['customer_id'] != customer_id:
            return False
        if node['root_quote_id'] is not None:
            declared_roots.add(node['root_quote_id'])
        terminal = node['pk']
        current = node['parent_quote_id']
    return bool(seen) and (not declared_roots or declared_roots == {terminal})
