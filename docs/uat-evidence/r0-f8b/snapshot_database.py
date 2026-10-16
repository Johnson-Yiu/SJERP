"""Read-only evidence from the dedicated R0-F8B SQLite database."""
import sqlite3,json,sys,hashlib
from pathlib import Path
root=Path(__file__).resolve().parent
path=root.parents[2]/'backend'/'r0f8b-ux.sqlite3'
assert path.name=='r0f8b-ux.sqlite3' and path.exists()
conn=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True);conn.row_factory=sqlite3.Row
state={}
for table in ['crm_customer','crm_product','crm_sku','crm_transaction']:
    rows=[dict(row) for row in conn.execute('SELECT * FROM '+table+' ORDER BY id')]
    state[table]={'count':len(rows),'sha256':hashlib.sha256(json.dumps(rows,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),'rows':rows}
log=root/'database-results.json'
records=json.loads(log.read_text(encoding='utf-8')) if log.exists() else []
records.append({'step':sys.argv[1],'database':'backend/r0f8b-ux.sqlite3','state':state})
log.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
print(sys.argv[1],{k:v['count'] for k,v in state.items()})
