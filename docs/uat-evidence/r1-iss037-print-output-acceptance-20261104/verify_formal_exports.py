"""Read-only reconciliation of the generated synthetic API/XLSX evidence."""
from decimal import Decimal
import json
from pathlib import Path
from openpyxl import load_workbook

root = Path(__file__).resolve().parent / 'formal-matrix'
results = []
for sample in json.loads((root / 'samples.json').read_text(encoding='utf-8')):
    label = sample['label']
    data = json.loads((root / f'{label}.json').read_text(encoding='utf-8'))
    book = load_workbook(root / f'{label}.xlsx', data_only=True)
    sheet = book['PI']
    assert sheet['B3'].value == data['buyer']['company_name']
    assert (sheet['B4'].value or '') == data['buyer']['name']
    assert sheet['B5'].value == data['buyer']['address']
    assert sheet['B7'].value == data['buyer']['email']
    assert sheet['B8'].value == data['buyer']['phone']
    assert sheet['I3'].value == data['seller']['name']
    values = [cell.value for row in sheet for cell in row]
    for bank_label, bank_value in data['bank']:
        assert bank_label in values
        assert bank_value in values
    assert data['bank_notice'] in values
    total = Decimal('0')
    for index, product in enumerate(data['products']):
        row = 11 + index
        assert Decimal(str(sheet[f'J{row}'].value)) == Decimal(str(product['quantity']))
        assert Decimal(str(sheet[f'M{row}'].value)) == Decimal(str(product['amount']))
        total += Decimal(str(product['amount']))
    assert total == Decimal(data['totals']['subtotal'])
    assert len(sheet._images) == sample['rows']
    after = load_workbook(root / f'{label}-after-current-template-change.xlsx', data_only=True)['PI']
    assert [(cell.coordinate, cell.value) for row in sheet for cell in row] == [(cell.coordinate, cell.value) for row in after for cell in row]
    results.append(dict(label=label, rows=sample['rows'], subtotal=str(total), embedded_images=len(sheet._images), frozen_cells_equal=True))
print(json.dumps(results, indent=2))
