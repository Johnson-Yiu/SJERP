"""Verify saved authoritative outcomes and complete native Chrome viewport coverage."""
import json
from decimal import Decimal
from pathlib import Path
root = Path(__file__).resolve().parent
chrome = root / 'browser' / 'chrome'
read = lambda name: json.loads((chrome / name).read_text(encoding='utf-8'))
run = read('run.json')
assert run['browser'].startswith('Chrome/')
assert len(run['captures']) == 78
states = {row['name'] for row in run['captures']}
assert len(states) == 13
expected = {(1366, 1), (1366, 1.25), (1920, 1), (1920, 1.25), (390, 1), (390, 1.25)}
for state in states:
    captures = [row for row in run['captures'] if row['name'] == state]
    assert {(row['width'], row['zoom']) for row in captures} == expected
    assert all((chrome / row['file']).is_file() for row in captures)
paid = read('refunded-order-and-source.json')
assert Decimal(paid['source']['amount']) == 1000 and paid['source']['status'] == 'confirmed'
assert sorted(Decimal(row['amount']) for row in paid['source']['receipt_refunds']) == [100, 400, 500]
for name, expected_status, contract, cash in [
    ('final-workbench.json', 'completed', 400, 400),
    ('cancelled-void-workbench.json', 'cancelled', 0, 0),
    ('cancelled-correction-workbench.json', 'cancelled', 0, 999),
]:
    value = read(name)
    assert value['order']['status'] == expected_status
    assert Decimal(value['order']['total_amount']) == contract
    assert Decimal(value['payment_summary']['paid_amount']) == cash
    assert Decimal(value['payment_summary']['balance_amount']) == 0
value = read('final-workbench.json')
assert sorted(Decimal(row['quantity']) for row in value['items']) == [0, 40]
assert Decimal(value['fulfillment_summary']['shipped_quantity']) == 40
assert Decimal(value['fulfillment_summary']['remaining_quantity']) == 0
assert all(Decimal(paid['order']['payment_summary'][field]) == 0 for field in ('paid_amount', 'balance_amount'))
assert any(row['url'].endswith('/cancel/') and row['status'] == 400 for row in run['events'])
assert '1 passed' in (root / 'browser-final.log').read_text(encoding='utf-8-sig')
print('PASS: 78 screenshots, 13 states, 6 native viewport/zoom combinations; original cash, cancellation corrections and partial termination outcomes verified.')
