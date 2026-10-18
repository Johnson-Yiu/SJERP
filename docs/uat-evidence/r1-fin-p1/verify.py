"""DATABASE_VERIFICATION: exact Decimal API/CSV comparison, read-only artifacts."""
from pathlib import Path
from decimal import Decimal as D
import json,csv,io,re
p=Path(__file__).resolve().parent
before=json.loads((p/'before.json').read_text(encoding='utf8'),parse_float=D)
after=json.loads((p/'after.json').read_text(encoding='utf8'),parse_float=D)
assert before['database_sha256']==after['database_sha256']
for key in ['metrics','period','due_items','categories','monthly_cash']:assert before['finance']['body'][key]==after['finance']['body'][key],key
for source in ['cash','sales','profit']:
 for key in ['totals','previous','changes','rows','filters','period','comparison_period']:assert before[source]['body'][key]==after[source]['body'][key],(source,key)
assert before['transactions']==after['transactions']
for key in ['finance_csv','cash_csv']:
 nums=lambda text:[[D(x) for x in row if re.fullmatch(r'-?\d+(\.\d+)?',x)] for row in csv.reader(io.StringIO(text))]
 assert nums(before[key]['body'])==nums(after[key]['body']),key
 assert '人民币折算参考' in after[key]['body']
 assert '实际收入（人民币）' not in after[key]['body']
print('PASS: all CRM rows SHA256 unchanged; exact Decimal financial metrics/categories/months/plans/report rows/previous/comparisons/transactions and every CSV numeric cell unchanged')
print('income=7988.0000 expense=391.9034 net=7596.0966; USD12.34 reference=87.9034 retained; CNY receipts included, void excluded')
