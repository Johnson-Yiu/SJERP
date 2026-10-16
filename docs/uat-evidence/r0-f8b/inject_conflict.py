"""Create a state conflict only in the explicitly disposable R0-F8B database."""
from pathlib import Path
import sqlite3
p=Path(__file__).resolve().parents[3]/'backend'/'r0f8b-ux.sqlite3'
assert p.name=='r0f8b-ux.sqlite3' and p.exists()
with sqlite3.connect(p) as c:
    row=c.execute('SELECT name FROM crm_customer WHERE code=?',('F8B-C01',)).fetchone()
    assert row and row[0]=='中文客户 Updated'
    c.execute('UPDATE crm_customer SET notes=? WHERE code=?',('R0F8B controlled concurrent change','F8B-C01'))
print('Injected one controlled concurrent update in dedicated R0-F8B database')
