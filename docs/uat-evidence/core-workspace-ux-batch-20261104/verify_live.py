"""Read back only this runner's disposable DB and check a rejected real request."""
import json
import re
import sqlite3
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from uuid import uuid4

root = Path(__file__).resolve().parent
fixture_file = root / (sys.argv[2] if len(sys.argv) > 2 else 'real-api-fixture.json')
assert fixture_file.resolve().parent == root
fixture = json.loads(fixture_file.read_text(encoding='utf-8'))['fixture']
db = Path(fixture['database']).resolve()
marker = db.parent / '.sunjack-playwright-isolation.json'
assert marker.is_file() and db.parent.name.startswith('sunjack-r1-repair-06-')
assert Path(fixture['media']).resolve() == db.parent / 'media'
base = sys.argv[1]
assert re.fullmatch(r'http://127\.0\.0\.1:[0-9]{1,5}', base), 'Only a local disposable service is allowed'
identity_marker = json.loads(marker.read_text(encoding='utf-8'))
with urlopen(base + '/api/__test__/isolation/' + identity_marker['token'] + '/', timeout=30) as response:
    identity = json.load(response)
assert Path(identity['database']).resolve() == db, 'API must use the exact marked disposable database'

def request(endpoint, payload=None):
    body = None if payload is None else json.dumps(payload).encode()
    req = Request(base + '/api/' + endpoint, data=body, headers={'Content-Type': 'application/json', 'Idempotency-Key': str(uuid4())})
    try:
        with urlopen(req, timeout=30) as response:
            return {'endpoint': endpoint, 'method': req.get_method(), 'status': response.status, 'data': json.load(response)}
    except HTTPError as error:
        return {'endpoint': endpoint, 'method': req.get_method(), 'status': error.code, 'data': json.load(error)}

with sqlite3.connect(db.as_uri() + '?mode=ro', uri=True) as connection:
    connection.row_factory = sqlite3.Row
    def snapshot():
        return {table: [dict(row) for row in connection.execute('SELECT * FROM ' + table + ' ORDER BY id')] for table in ['crm_customer','crm_contact','crm_followup','crm_product','crm_purchaseorder','crm_purchaseorderitem','crm_goodsreceipt','crm_inventorymovement']}
    before = snapshot()
    rejected = request(f"purchase-orders/{fixture['purchase']}/receive/", {'purchase_item': fixture['purchase_item'], 'quantity': '0', 'unit_cost': '2', 'receipt_date': '2026-11-04'})
    assert rejected['status'] == 400, rejected
    after = snapshot()
    assert before == after, 'Rejected receive changed disposable business rows'
    assert len(after['crm_contact']) == 2, 'Exactly one contact create should persist; cancel must add no row'
    assert after['crm_customer'][0]['notes'] == '隔离浏览器办公验收备注'
    assert after['crm_customer'][0]['next_follow_up'] is None
    assert after['crm_purchaseorder'][0]['status'] == 'ordered'
    assert len(after['crm_goodsreceipt']) == 1
    assert len(after['crm_inventorymovement']) == 2
    http = [request(endpoint) for endpoint in ['customers/1/','contacts/','follow-ups/','products/1/','purchase-orders/1/','skus/inventory-list/','skus/1/inventory-detail/']]
    assert all(row['status'] == 200 for row in http)
    (root / f"real-api-after-{fixture['suffix']}.json").write_text(json.dumps({'rejected': rejected, 'rejected_db_unchanged': True, 'http': http, 'database_after': after}, ensure_ascii=False, indent=2), encoding='utf-8')
print('PASS: actual HTTP400 leaves DB unchanged; browser saves, cancel, follow-up clear, receipt/reversal and readback verified')
