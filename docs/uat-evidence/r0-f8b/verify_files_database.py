"""Verify downloaded bytes and recorded DB transitions; never write a business DB."""
from pathlib import Path
import ast,csv,io,json,hashlib
root=Path(__file__).resolve().parent
module=ast.parse((root.parents[2]/'backend/crm/views.py').read_text(encoding='utf-8'))
fields=next(ast.literal_eval(n.value) for n in ast.walk(module) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='IMPORT_FIELDS' for t in n.targets))
files=[]
for entity,expected in fields.items():
    p=root/'downloads'/f'{entity}_template.csv';raw=p.read_bytes()
    assert raw.startswith(b'\xef\xbb\xbf')
    rows=list(csv.reader(io.StringIO(raw.decode('utf-8-sig'))))
    assert rows==[expected],(entity,rows,expected)
    files.append({'file':str(p.relative_to(root)),'encoding':'UTF-8 BOM','headers':rows[0],'sha256':hashlib.sha256(raw).hexdigest()})
p=root/'downloads/customers_import_failures.csv';raw=p.read_bytes();assert raw.startswith(b'\xef\xbb\xbf')
rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))));assert len(rows)==1 and rows[0]['row']=='3' and rows[0]['key']=='F8B-DUP' and '首次出现在第 2 行' in rows[0]['message']
files.append({'file':str(p.relative_to(root)),'encoding':'UTF-8 BOM','rows':rows,'sha256':hashlib.sha256(raw).hexdigest()})
records={r['step']:r['state'] for r in json.loads((root/'database-results.json').read_text(encoding='utf-8'))}
pairs=[('initial','customers-preview'),('initial','customers-cancel'),('customers-created','customers-update-preview'),('customers-updated','customers-invalid-files'),('customers-updated','products-preview'),('conflict-before-execute','conflict-rejected-no-write')]
for a,b in pairs:assert records[a]==records[b],(a,b)
assert records['customers-created']['crm_customer']['count']==2
assert records['products-created-update-preview']['crm_product']['count']==1
assert records['skus-created-update-preview']['crm_sku']['count']==1
assert records['transactions-created-invalid-rejected']['crm_transaction']['count']==1
c=records['customers-updated']['crm_customer']['rows'][0];assert c['name']=='中文客户 Updated' and c['notes']=='更新内容, "确认"\n第二行'
p=records['products-updated-skus-preview']['crm_product']['rows'][0];assert p['name']=='中文产品更新'
s=records['skus-updated-transactions-preview']['crm_sku']['rows'][0];assert float(s['cost_price'])==3 and float(s['default_price'])==6 and s['sku']=='F8B-S01'
t=records['transactions-created-invalid-rejected']['crm_transaction']['rows'][0];assert float(t['amount'])==12.5 and t['transaction_no']=='F8B-T01'
last=records['repeated-file-fresh-token-updated-two'];assert [last[k]['count'] for k in ['crm_customer','crm_product','crm_sku','crm_transaction']]==[2,1,1,1]
assert last['crm_customer']['rows'][0]['notes']=='含逗号, 引号"和换行\n第二行'
report={'downloaded_files':files,'unchanged_database_pairs':pairs,'final_counts':{k:v['count'] for k,v in last.items()},'result':'PASS','scope':'Synthetic isolated SQLite; formal-role audit/UAT not covered'}
(root/'file-database-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('PASS: four actual templates, failure CSV, UTF8 BOM, unchanged previews/cancel/rejected execution, counts and multiline field values')
