"""Verify real UI output against its associated API; render every page for review."""
import json
from pathlib import Path
import re
import subprocess
import sys
from pypdf import PdfReader

root = Path(sys.argv[1]).resolve()
results = []
for metadata in sorted(root.glob('ui-formal-*.json')):
    record = json.loads(metadata.read_text(encoding='utf-8'))
    pdf = metadata.with_suffix('.pdf')
    reader = PdfReader(pdf)
    normalize = lambda value: re.sub(r'\s+', '', str(value)).casefold()
    text = normalize(' '.join(page.extract_text() or '' for page in reader.pages))
    data = record['api']
    required = [data['buyer']['company_name'], data['buyer']['name'], data['seller']['name'], data['totals']['total_amount']]
    required += [value for _, value in data['bank']]
    for value in required:
        if value:
            assert normalize(value) in text, (pdf.name, 'missing content', value)
    for product in data['products']:
        assert normalize(product['description']) in text, (pdf.name, 'missing product description')
    image_count = sum(len(page.images) for page in reader.pages)
    assert image_count > 0, (pdf.name, 'no product image in PDF')
    for page in reader.pages:
        assert abs(float(page.mediabox.width) - 595.3) < 3
        assert abs(float(page.mediabox.height) - 841.9) < 3
    subprocess.run(['pdftoppm', '-png', '-r', '90', str(pdf), str(pdf.with_suffix('')) + '-page'], check=True)
    results.append(dict(file=pdf.name, pages=len(reader.pages), image_objects=image_count, paper='A4 portrait', api_content_verified=True))
assert results, 'No UI PDF/API pairs found; not a passing result'
print(json.dumps(results, indent=2))
