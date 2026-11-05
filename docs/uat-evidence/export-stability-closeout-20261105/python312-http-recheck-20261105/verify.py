import hashlib, json, sys, zipfile
from pathlib import Path
import django, openpyxl
root = Path(__file__).resolve().parent
q = root / 'quote'
a = (q / 'http-response.xlsx').read_bytes()
b = (q / 'browser-download.xlsx').read_bytes()
assert a == b
for p in [q / 'http-response.xlsx', q / 'browser-download.xlsx']:
    with zipfile.ZipFile(p) as z: assert z.testzip() is None
    s = openpyxl.load_workbook(p, data_only=False)['PI']
    assert {k:s[k].value for k in ('L9','C11','J11','L11','M11','M14')} == {'L9':'QHTTP-20261105-001','C11':'QHTTP-MODEL','J11':2,'L11':12.5,'M11':25,'M14':25}
pack = root / 'packing'
result = json.loads((pack/'chrome-results.json').read_text(encoding='utf-8'))
assert len(result['results']) == 10
checked=[]
for item in result['results']:
    assert item.get('status')==200 and item.get('matchesResponse') is True and item.get('failure') is None and item.get('filename')=='PackingList-SH-PL-01.xlsx', item
    p=pack/f"download-{item['attempt']}.xlsx"
    data=p.read_bytes()
    assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256']
    with zipfile.ZipFile(p) as z: assert z.testzip() is None
    s=openpyxl.load_workbook(p,data_only=False).active
    assert s.max_column==16 and s['C1'].value=='SH-PL-01' and s['F3'].value=='SO-PL-01'
    assert [s[f'E{i}'].value for i in (6,7,8)]==[3,2,4]
    assert [s[f'H{i}'].value for i in (6,7,8)]==[1,1,None] and s['H15'].value=='=SUM(H6:H14)'
    checked.append({'file':p.name,'sha256':item['sha256'],'bytes':len(data),'zip_crc':'pass'})
output={'python':sys.version,'executable':sys.executable,'django':django.get_version(),'openpyxl':openpyxl.__version__,'quote':{'byte_equal':True,'bytes':len(a),'sha256':hashlib.sha256(a).hexdigest(),'cells':'pass','zip_crc':'pass'},'packing':checked}
print(json.dumps(output,indent=2,ensure_ascii=True))
(root/'verification.json').write_text(json.dumps(output,indent=2,ensure_ascii=True)+'\n',encoding='utf-8')
