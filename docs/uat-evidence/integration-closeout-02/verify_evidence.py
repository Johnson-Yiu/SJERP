"""Check closeout evidence integrity without connecting to any business DB."""
from collections import Counter
from contextlib import ExitStack
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = '8087f2c68b19a302a25e814ec8ce6113d91d4750'


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def ledger_rows():
    rows = []
    for line in (ROOT / 'docs/PROJECT_ISSUES.md').read_text(encoding='utf-8').splitlines():
        if not re.match(r'^\| ISS-\d', line):
            continue
        cells = [cell.strip() for cell in line.split('|')[1:-1]]
        status = re.search(r'\b(OPEN|BLOCKED|NEEDS_VERIFICATION|FIXED_PENDING_REVIEW|CLOSED)\b', cells[1])
        assert status, cells[0]
        rows.append({'id': cells[0], 'status': status.group(1), 'cells': cells[2:]})
    assert len(rows) == len({row['id'] for row in rows}), 'duplicate primary Issue ID'
    return rows


def verify():
    checks = []
    previous = load(ROOT / 'docs/uat-evidence/review-integration-batch-20261104/ledger-verification.json')
    rows = ledger_rows()
    for status in ('CLOSED', 'FIXED_PENDING_REVIEW'):
        assert {r['id'] for r in rows if r['status'] == status} == {
            r['id'] for r in previous['rows'] if r['status'] == status
        }, f'{status} set changed without independent acceptance'
    checks.append('unique current IDs; original 86 pending and 10 closed sets unchanged')

    histories = load(HERE / 'history-manifest.json')
    for item in histories:
        raw = (ROOT / item['historical_copy']).read_bytes()
        assert len(raw) == item['bytes']
        assert hashlib.sha256(raw).hexdigest() == item['sha256']
        original = subprocess.check_output(['git', 'show', item['source_sha'] + ':' + item['original']], cwd=ROOT)
        assert raw.replace(b'\r\n', b'\n') == original.replace(b'\r\n', b'\n'), item['original']
    checks.append(f'{len(histories)} historical reports match source Git text and original byte hashes')

    receipt = load(HERE / 'baseline-8087-ci-receipt.json')
    assert receipt['final_sha'] == BASE and receipt['ci_run'] == 41839476121
    assert receipt['ci_status'] == 'SUCCESS'
    assert {j['name'] for j in receipt['ci_jobs']} == {'backend', 'backend-postgres', 'frontend'}
    assert all(j['status'] == 'SUCCESS' for j in receipt['ci_jobs'])
    checks.append('baseline CI receipt binds exact SHA and all three successful jobs')

    logs = load(HERE / 'baseline-ci-log-manifest.json')
    archive = HERE / 'baseline-ci-41839476121-logs.zip'
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == logs['logs_zip_sha256']
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for item in logs['entries']:
            raw = z.read(item['path'])
            assert hashlib.sha256(raw).hexdigest() == item['published_sha256']
            assert len(raw) == item['bytes']
    compact = HERE / 'final-ci-41839476121-evidence.zip'
    assert hashlib.sha256(compact.read_bytes()).hexdigest() == logs['compact_evidence_sha256']
    with zipfile.ZipFile(compact) as z:
        assert z.testzip() is None
    checks.append('published baseline log and real-file archives pass byte hashes and ZIP CRC')

    sources = load(HERE / 'starting-source-verification.json')
    for source in sources['source_complete_ancestors']:
        subprocess.run(['git', 'merge-base', '--is-ancestor', source['full_source_sha'], BASE], cwd=ROOT, check=True)
    checks.append('all six original complete source SHAs remain ancestors of baseline')

    visual = load(HERE / 'visual-evidence.json')
    from PIL import Image
    with ExitStack() as stack:
        archives = {}

        def evidence_bytes(path):
            separator = '::' if '::' in path else '!' if '!' in path else None
            if separator:
                archive_path, member = path.split(separator, 1)
                if archive_path not in archives:
                    archives[archive_path] = stack.enter_context(zipfile.ZipFile(ROOT / archive_path))
                return archives[archive_path].read(member)
            return (ROOT / path).read_bytes()

        for item in visual['images']:
            raw = evidence_bytes(item['path'])
            assert len(raw) == item['bytes'], item['path']
            assert hashlib.sha256(raw).hexdigest() == item['sha256'], item['path']
            with Image.open(io.BytesIO(raw)) as image:
                assert image.size == (item['actual_image']['width'], item['actual_image']['height']), item['path']
                image.verify()
        operation_count = 0
        for item in visual['operation_artifacts']:
            if not item.get('exists', True):
                continue
            raw = evidence_bytes(item['path'])
            assert len(raw) == item['bytes'], item['path']
            assert hashlib.sha256(raw).hexdigest() == item['sha256'], item['path']
            operation_count += 1
        backlog = load(HERE / 'review-backlog.json')
        assert len(backlog['rows']) == 86
        assert {r['id'] for r in backlog['rows']} == {r['id'] for r in rows if r['status'] == 'FIXED_PENDING_REVIEW'}
        checked_code_sha = backlog['checked_worktree_head']
        assert re.fullmatch(r'[0-9a-f]{40}', checked_code_sha)
        code_paths = set(subprocess.check_output(
            ['git', 'ls-tree', '-r', '--name-only', checked_code_sha],
            cwd=ROOT, text=True, encoding='utf-8').splitlines())
        entry_count = 0
        for row in backlog['rows']:
            assert row['review_risk'] in {'R1', 'R2', 'R3'} and row['module']
            assert row['closing_gaps'] and all(g['statement'] for g in row['closing_gaps'])
            for entry in row['code_entries']:
                assert entry['path'] in code_paths and (ROOT / entry['path']).is_file(), entry['path']
                entry_count += 1
            for source in row['evidence']['item_sources']:
                for artifact in source.get('artifact_refs', []):
                    if artifact['status'] in {'PRESENT', 'PRESENT_IN_ARCHIVE'}:
                        target = ROOT / artifact['resolved_path']
                        if target.is_dir():
                            # A cited evidence directory is a navigation index,
                            # not a byte-verifiable file or proof of test PASS.
                            assert target.exists()
                        else:
                            evidence_bytes(artifact['resolved_path'])
        checks.append(f'86 exact pending IDs; {entry_count} code entries exist in {checked_code_sha[:12]} Git tree; all cited local artifacts resolve')
    checks.append(f"{len(visual['images'])} actual images decoded/dimensions/byte hashes; {operation_count} operation files byte hashes verified")

    output = {'checked_worktree_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'baseline_ci_sha': BASE, 'status': 'PASS', 'checks': checks,
              'unique_ids': len(rows), 'counts': dict(Counter(r['status'] for r in rows)),
              'rows': rows, 'scope': 'Evidence integrity and ledger consistency; not product regression or independent review.'}
    (HERE / 'ledger-current.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in output.items() if k != 'rows'}, ensure_ascii=False))


if __name__ == '__main__':
    verify()
