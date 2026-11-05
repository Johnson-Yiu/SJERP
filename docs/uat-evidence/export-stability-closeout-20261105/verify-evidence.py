"""Read-only integrity check for the export stability evidence package."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CODE = '56ce3588f544fcfeb98d431fb71d7e2d937f67db'


def raw(path):
    value = os.path.abspath(os.fspath(path))
    if os.name == 'nt' and not value.startswith('\\\\?\\'):
        value = '\\\\?\\' + value
    with open(value, 'rb') as stream:
        return stream.read()


def load(path):
    return json.loads(raw(path).decode('utf-8-sig'))


def verify():
    manifest = load(HERE / 'evidence-manifest.json')
    assert manifest['code_sha'] == CODE
    for item in manifest['files']:
        data = raw(HERE / item['path'])
        assert len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256'], item['path']
    assert all(item['session_rows'] == 0 and item['auth_users'] == 0 for item in manifest['database_identity_checks'])

    result = load(HERE / 'RESULTS.json')
    assert result['tested_code_sha'] == CODE
    suite = load(HERE / 'full-suite/test-counts.json')
    assert suite['code_sha'] == CODE and suite['suite_exit_code'] == 0
    assert suite['counts'] == {'passed': 266, 'failed': 0, 'skipped': 0}
    assert len(suite['profiles']) == 9 and suite['deferred_print_cases_not_run'] == 7
    assert result['earlier_failure']['failed'] == 1 and result['earlier_failure']['root_cause'] == 'UNKNOWN'

    for section, count in (('dashboard', 16), ('ledger', 8)):
        directory = HERE / 'finance/django609-rerun' / section
        rows = load(directory / 'results.json')
        assert len(rows) == count
        for row in rows:
            month = row['period'][0][5:7]
            filename = (f"{row['width']}-{month}-{row['kind']}-{row['iteration']}.csv"
                        if section == 'dashboard' else row['file'])
            data = raw(directory / filename)
            assert data.startswith(b'\xef\xbb\xbf')
            assert hashlib.sha256(data).hexdigest() == row['sha256']
            text = data.decode('utf-8-sig')
            assert row['amount'] in text
            marker = 'synthetic' if section == 'dashboard' else 'SYNTH'
            assert all("'" + prefix + marker in text for prefix in ('=', '+', '-', '@'))
            assert row.get('rawHttpEqualsDownload', row.get('independentHttpEqualsDownload')) is True

    for name in ('quote-chrome/browser/quote-editor-mobile-actions.spec/downloaded-quote.xlsx',
                 'python312-http-recheck-20261105/quote/browser-download.xlsx',
                 'python312-http-recheck-20261105/packing-390/download-390.xlsx'):
        import io
        with zipfile.ZipFile(io.BytesIO(raw(HERE / name))) as archive:
            assert archive.testzip() is None, name

    history = load(HERE / 'full-suite/history-path-overwrites/manifest.json')
    for item in history['files']:
        assert hashlib.sha256(raw(ROOT / item['generated_copy'])).hexdigest() == item['generated_sha256']
        if item.get('restored_exact'):
            assert hashlib.sha256(raw(ROOT / item['source_path'])).hexdigest() == item['restored_head_sha256']

    subprocess.run(['git', 'diff', '--quiet', CODE, 'HEAD', '--', 'frontend', 'backend', '.github/workflows'], cwd=ROOT, check=True)
    print(f"PASS: {len(manifest['files'])} evidence hashes, 266 Playwright, 24 real CSV files, historical screenshots restored; quote root cause remains UNKNOWN")


if __name__ == '__main__':
    verify()
