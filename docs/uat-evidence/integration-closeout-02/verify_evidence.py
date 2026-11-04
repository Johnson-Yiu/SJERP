"""Check closeout evidence integrity without connecting to any business DB."""
from collections import Counter
from contextlib import ExitStack
import hashlib
import io
import os
import json
from pathlib import Path
import re
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = '8087f2c68b19a302a25e814ec8ce6113d91d4750'


def native_path(path):
    # Same authorized local file; avoid Win32 MAX_PATH false missing evidence.
    value = os.path.abspath(os.fspath(path))
    if os.name == 'nt' and not value.startswith('\\\\?\\'):
        if value.startswith('\\\\'):
            return '\\\\?\\UNC\\' + value[2:]
        return '\\\\?\\' + value
    return value


def file_bytes(path):
    with open(native_path(path), 'rb') as stream:
        return stream.read()


def load(path):
    return json.loads(file_bytes(path).decode('utf-8-sig'))


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
        expected = {r['id'] for r in previous['rows'] if r['status'] == status}
        if status == 'FIXED_PENDING_REVIEW':
            supplement = load(HERE / 'ISS121-REVIEW-SUPPLEMENT.json')
            assert supplement['current_status'] == status
            assert supplement['status_calibration']['previous'] == 'OPEN'
            assert supplement['candidate']['sha'] == '02140bf46df27ba1abf5b9018507c07aae825769'
            assert supplement['in_prior_86_fixed_pending_review_set'] is False
            expected.add('ISS-121')
        assert {r['id'] for r in rows if r['status'] == status} == {
            issue_id for issue_id in expected
        }, f'unexpected {status} set change outside documented calibration'
    checks.append('unique current IDs; original 86 pending and 10 closed sets unchanged; ISS-121 separately added pending review with implementation/evidence supplement')

    histories = load(HERE / 'history-manifest.json')
    for item in histories:
        raw = file_bytes(ROOT / item['historical_copy'])
        assert len(raw) == item['bytes']
        assert hashlib.sha256(raw).hexdigest() == item['sha256']
        original = subprocess.check_output(['git', 'show', item['source_sha'] + ':' + item['original']], cwd=ROOT)
        assert raw.replace(b'\r\n', b'\n') == original.replace(b'\r\n', b'\n'), item['original']
    checks.append(f'{len(histories)} historical reports match source Git text and original byte hashes')

    checkpoints = load(HERE / 'checkpoint-history' / 'manifest.json')
    for item in checkpoints['files']:
        raw = file_bytes(ROOT / item['snapshot'])
        assert len(raw) == item['bytes'], item['snapshot']
        assert hashlib.sha256(raw).hexdigest() == item['sha256'], item['snapshot']
    checks.append(f"{len(checkpoints['files'])} later working-document checkpoints retain original bytes")

    for result_name, archive_name, digest_key in (
        ('frontend-f928-result.json', 'frontend-f928-full-logs.zip', 'sha256'),
        ('attachment-regression-result.json', 'attachment-regression-logs.zip', 'published_sha256'),
    ):
        result = load(HERE / result_name)
        with zipfile.ZipFile(HERE / archive_name) as archive:
            assert archive.testzip() is None, archive_name
            for item in result['logs']:
                raw = archive.read(item['path'])
                assert hashlib.sha256(raw).hexdigest() == item[digest_key], item['path']
    checks.append('closed frontend/attachment logs retain declared published hashes and ZIP CRC')

    receipt = load(HERE / 'baseline-8087-ci-receipt.json')
    assert receipt['final_sha'] == BASE and receipt['ci_run'] == 41839476121
    assert receipt['ci_status'] == 'SUCCESS'
    assert {j['name'] for j in receipt['ci_jobs']} == {'backend', 'backend-postgres', 'frontend'}
    assert all(j['status'] == 'SUCCESS' for j in receipt['ci_jobs'])
    checks.append('baseline CI receipt binds exact SHA and all three successful jobs')

    logs = load(HERE / 'baseline-ci-log-manifest.json')
    archive = HERE / 'baseline-ci-41839476121-logs.zip'
    assert hashlib.sha256(file_bytes(archive)).hexdigest() == logs['logs_zip_sha256']
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for item in logs['entries']:
            raw = z.read(item['path'])
            assert hashlib.sha256(raw).hexdigest() == item['published_sha256']
            assert len(raw) == item['bytes']
    compact = HERE / 'final-ci-41839476121-evidence.zip'
    assert hashlib.sha256(file_bytes(compact)).hexdigest() == logs['compact_evidence_sha256']
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
            return file_bytes(ROOT / path)

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
        assert {r['id'] for r in backlog['rows']} == {
            r['id'] for r in rows if r['status'] == 'FIXED_PENDING_REVIEW' and r['id'] != 'ISS-121'
        }
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

    pg_base = HERE / 'final-pg-447d'
    pg_manifest = load(pg_base / 'final-pg-447d-log-manifest.json')
    pg_archive = pg_base / pg_manifest['rawlogs_zip']
    assert hashlib.sha256(file_bytes(pg_archive)).hexdigest() == pg_manifest['rawlogs_zip_sha256']
    with zipfile.ZipFile(pg_archive) as archive:
        assert archive.testzip() is None
        for item in pg_manifest['members']:
            assert hashlib.sha256(archive.read(item['archive_member'])).hexdigest() == item['published_sha256']
    for item in pg_manifest['frozen_pg_artifacts']:
        raw = file_bytes(pg_base / item['path'])
        assert len(raw) == item['bytes'] and hashlib.sha256(raw).hexdigest() == item['sha256'], item['path']
    for result_name, archive_name in (
        ('backend-full-447d-python312-result.json', 'backend-full-447d-python312-logs.zip'),
        ('final-backup-command-447d-result.json', 'final-backup-command-447d-logs.zip'),
    ):
        result = load(HERE / result_name)
        with zipfile.ZipFile(HERE / archive_name) as archive:
            assert archive.testzip() is None
            for item in result['logs']:
                raw = archive.read(item['path'])
                assert hashlib.sha256(raw).hexdigest() == item.get('published_sha256', item.get('sha256')), item['path']
    checks.append('final447d SQLite/PG/backup-command closed logs and restored artifacts retain hashes/ZIP CRC; failures preserved')

    final_pg = HERE / 'final-pg-02140bf'
    final_pg_manifest = load(final_pg / 'PUBLISHED-EVIDENCE-MANIFEST.json')
    for item in final_pg_manifest['payload_files']:
        raw = file_bytes(final_pg / item['path'])
        assert len(raw) == item['size'] and hashlib.sha256(raw).hexdigest() == item['sha256'], item['path']
    for name in ('final-02140bf-history-chrome-published-logs-manifest.json',
                 'legacy-r01-r03-history-chrome-published-logs-manifest.json'):
        manifest = load(HERE / name)
        archive_path = HERE / manifest['archive']
        assert hashlib.sha256(file_bytes(archive_path)).hexdigest() == manifest['archive_sha256']
        with zipfile.ZipFile(archive_path) as archive:
            assert archive.testzip() is None
            for item in manifest['entries']:
                assert hashlib.sha256(archive.read(item['zip_member'])).hexdigest() == item['published_sha256']
    for result_name, archive_name in (
        ('backend-full-02140bf-python312-result.json', 'backend-full-02140bf-python312-logs.zip'),
        ('quote-boundary-controls-02140bf-result.json', 'quote-boundary-controls-02140bf-logs.zip'),
    ):
        result = load(HERE / result_name)
        with zipfile.ZipFile(HERE / archive_name) as archive:
            assert archive.testzip() is None
            for item in result['logs']:
                assert hashlib.sha256(archive.read(item['path'])).hexdigest() == item['published_sha256']
    invariant = load(HERE / 'source-invariance-02140bf-result.json')
    invariant_archive = HERE / 'source-invariance-02140bf-evidence.zip'
    assert hashlib.sha256(file_bytes(invariant_archive)).hexdigest() == invariant['archive_sha256']
    with zipfile.ZipFile(invariant_archive) as archive:
        assert archive.testzip() is None
        for item in invariant['files']:
            assert hashlib.sha256(archive.read(item['path'])).hexdigest() == item['sha256']
    final_history_root = HERE / 'final-02140bf-history-chrome'
    history_result = load(final_history_root / 'result.json')
    for item in history_result['screenshots']:
        raw = file_bytes(final_history_root / item['path'])
        assert hashlib.sha256(raw).hexdigest() == item['sha256']
    db_bytes = file_bytes(final_history_root / 'artifacts/isolated-sanitized.sqlite3')
    assert hashlib.sha256(db_bytes).hexdigest() == history_result['database_copy']['published_sha256']
    checks.append('02140 final backend/PG/history and supplemental invariant/control archives retain actual hashes/CRC; original failures are not overwritten')

    for folder in ('final-02140bf-frontend', 'final-447d-frontend'):
        package = HERE / folder
        manifest = load(package / 'PUBLISHED-EVIDENCE-MANIFEST-v2.json')
        v1 = manifest['v1_manifest_snapshot']
        assert hashlib.sha256(file_bytes(package / v1['path'])).hexdigest() == v1['sha256']
        recovery = manifest['recovery_audit']
        assert hashlib.sha256(file_bytes(package / recovery['path'])).hexdigest() == recovery['sha256']
        for item in manifest['published_inventory']['files']:
            raw = file_bytes(package / item['path'])
            assert len(raw) == item['size'], item['path']
            assert hashlib.sha256(raw).hexdigest() == item['sha256'], item['path']
    checks.append('both frontend v2 inventories retain v1 manifests and recovered long-path byte hashes; original failed suite results unchanged')

    publication = load(HERE / 'legacy-local-business-evidence-publication.json')
    archive_path = HERE / 'legacy-local-business-evidence-published.zip'
    assert hashlib.sha256(file_bytes(archive_path)).hexdigest() == publication['archive_sha256']
    prior_index = file_bytes(HERE / 'visual-evidence-before-publication-reconciliation.json')
    assert hashlib.sha256(prior_index).hexdigest() == publication['prior_visual_index_sha256']
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None
        for item in publication['files']:
            assert hashlib.sha256(archive.read(item['archive_member'])).hexdigest() == item['published_sha256']
            if item['session_rows_removed']:
                assert item['all_non_session_tables_unchanged'] is True
    for folder in ('quote-download-diagnostic-02140bf', 'quote-download-interrupt-capture-02140bf'):
        diagnostic = HERE / folder
        manifest = load(diagnostic / 'artifact-manifest.json')
        for item in manifest['artifacts']:
            local = item['path'].replace('\\', '/').split(folder + '/', 1)[-1]
            raw = file_bytes(diagnostic / local)
            assert len(raw) == item['bytes'], local
            assert hashlib.sha256(raw).hexdigest() == item['sha256'], local
    checks.append('12 historical operation artifacts published with explicit original/public hashes and session-only copy sanitation; bounded diagnostic artifacts retain hashes without overriding full-suite failure')

    integrated_pages = load(HERE / 'integrated-page-evidence-447d.json')
    assert integrated_pages['source_sha'] == '447d7816ead2e971e249cb2e762b1a6f7009b9c0'
    for item in integrated_pages['images']:
        page = ROOT / item['path']
        raw = file_bytes(page)
        assert len(raw) == item['bytes'] and hashlib.sha256(raw).hexdigest() == item['sha256'], item['path']
        from PIL import Image
        with Image.open(io.BytesIO(raw)) as im:
            im.load()
            assert im.size == (item['actual_width'], item['actual_height']), item['path']
    assert len(integrated_pages['images']) == integrated_pages['actual_page_capture_count']
    checks.append(f"{len(integrated_pages['images'])} supplemental integrated page images retain source/dimensions/hashes; not independent acceptance")

    output = {'checked_worktree_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'baseline_ci_sha': BASE, 'status': 'PASS', 'checks': checks,
              'unique_ids': len(rows), 'counts': dict(Counter(r['status'] for r in rows)),
              'rows': rows, 'scope': 'Evidence integrity and ledger consistency; not product regression or independent review.'}
    (HERE / 'ledger-current.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in output.items() if k != 'rows'}, ensure_ascii=False))


if __name__ == '__main__':
    verify()
