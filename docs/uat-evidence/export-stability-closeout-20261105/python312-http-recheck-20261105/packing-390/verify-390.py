import hashlib
import json
from pathlib import Path
from zipfile import ZipFile
from openpyxl import load_workbook

folder = Path(__file__).resolve().parent
file = folder / 'download-390.xlsx'
with ZipFile(file) as archive:
    assert archive.testzip() is None
    assert {'[Content_Types].xml', 'xl/workbook.xml'} <= set(archive.namelist())
sheet = load_workbook(file, data_only=False).active
assert sheet.max_column == 16
assert sheet['C1'].value == 'SH-PL-01' and sheet['F3'].value == 'SO-PL-01'
assert [sheet[f'E{i}'].value for i in (6, 7, 8)] == [3, 2, 4]
assert [sheet[f'H{i}'].value for i in (6, 7, 8)] == [1, 1, None]
assert sheet['H15'].value == '=SUM(H6:H14)'
result = {'file': file.name, 'bytes': file.stat().st_size, 'sha256': hashlib.sha256(file.read_bytes()).hexdigest(), 'zip_crc': 'pass', 'sheet': sheet.title, 'columns': sheet.max_column, 'shipment': sheet['C1'].value, 'order': sheet['F3'].value, 'quantities': [3, 2, 4], 'cartons': [1, 1, None], 'subtotal': sheet['H15'].value, 'print_area': str(sheet.print_area)}
print(json.dumps(result, ensure_ascii=False, indent=2))
(folder / 'xlsx-verification-390.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
