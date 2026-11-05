import hashlib
import json
from pathlib import Path
from zipfile import ZipFile
from openpyxl import load_workbook

root = Path(__file__).resolve().parent
files = [root / 'http-response.xlsx', root / 'browser-download.xlsx']
data = [p.read_bytes() for p in files]
assert data[0] == data[1]
results = []
for p, payload in zip(files, data):
    with ZipFile(p) as z:
        assert z.testzip() is None
        assert {'[Content_Types].xml', 'xl/workbook.xml'} <= set(z.namelist())
    sheet = load_workbook(p, data_only=False)['PI']
    expected = {'L9': 'QHTTP-20261105-001', 'C11': 'QHTTP-MODEL', 'J11': 2, 'L11': 12.5, 'M11': 25, 'M14': 25}
    cells = {cell: sheet[cell].value for cell in expected}
    assert cells == expected, cells
    results.append({'file': p.name, 'size': len(payload), 'sha256': hashlib.sha256(payload).hexdigest(), 'zip_crc': 'pass', 'sheet': 'PI', 'cells': cells})
print(json.dumps({'byte_equal': True, 'files': results}, indent=2))
(root / 'verification.json').write_text(json.dumps({'byte_equal': True, 'files': results}, indent=2) + '\n', encoding='utf-8')
