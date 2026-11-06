import hashlib, json, os, secrets, shutil, socket, subprocess, sys, tempfile, uuid
from pathlib import Path
from urllib.parse import quote
import psycopg
from psycopg import sql

report = Path(__file__).resolve().parent
repo = report.parents[4]
pg = Path(r'C:\Users\Johnson\AppData\Local\Temp\sunjack-history-pg17-isolated-20261105\minimal\pgsql\bin')
root = Path(tempfile.mkdtemp(prefix='sunjack-party-version-pg17-')).resolve()
marker = uuid.uuid4().hex
(root / 'owner.json').write_text(json.dumps({'marker': marker}), encoding='utf8')
secret = secrets.token_urlsafe(32)
user = 'party_' + uuid.uuid4().hex[:12]
db = 'party_src_' + uuid.uuid4().hex[:12]
(root / 'password').write_text(secret, encoding='ascii')
(root / 'media').mkdir()
env = {k:v for k,v in os.environ.items() if not k.upper().startswith('PG')}
env.update(APP_STAGE='development', PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1', MEDIA_ROOT=str(root / 'media'))
for key in ('ISS018_COMMAND_PG_BIN', 'ISS018_DRILL_ROOT', 'ISS018_DRILL_PASSWORD_FILE'):
    env.pop(key, None)
results = {'head':subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip(), 'root':str(root), 'stages':{}, 'cleanup':'not-started'}
started = False
def source_hashes(name):
    tracked = subprocess.check_output(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=repo)
    entries = sorted(set(part.decode('utf-8') for part in tracked.split(b'\0') if part))
    hashes = {}
    for path in entries:
        if not (path.startswith('backend/') or path.startswith('frontend/src/') or path.startswith('frontend/tests/') or path.startswith('frontend/browser-tests/')):
            continue
        file = repo / path
        if file.is_file():
            hashes[path] = hashlib.sha256(file.read_bytes()).hexdigest()
    (report / (name + '.json')).write_text(json.dumps(hashes, ensure_ascii=False, indent=2), encoding='utf8')
    return hashes

before = source_hashes('source-hashes-before')
def cmd(name, args, timeout=300):
    with (report / (name + '.log')).open('wb') as log:
        result = subprocess.run(args, cwd=repo / 'backend', env=env, stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
    results['stages'][name] = result.returncode
    print(name, result.returncode, flush=True)
    return result.returncode
def tool(name, args):
    return cmd(name, [str(pg / (name.split('-')[0] + '.exe')), *args])
try:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    if port == 5432: raise RuntimeError('unsafe port')
    results['port'] = port
    if tool('initdb', ['-D', str(root / 'data'), '-U', user, '--pwfile', str(root / 'password'), '--auth=scram-sha-256', '-E', 'UTF8', '--locale=C']): raise RuntimeError('initdb failed')
    if tool('pg_ctl-start', ['-D', str(root / 'data'), '-l', str(root / 'postgres.log'), '-o', f'-h 127.0.0.1 -p {port}', '-w', 'start']): raise RuntimeError('start failed')
    started = True
    with psycopg.connect(host='127.0.0.1', port=port, user=user, password=secret, dbname='postgres', autocommit=True) as conn:
        actual = Path(conn.execute('SHOW data_directory').fetchone()[0]).resolve()
        if actual != (root / 'data').resolve(): raise RuntimeError('cluster identity mismatch')
        results['server_version'] = conn.execute('SHOW server_version').fetchone()[0]
        results['identity_verified'] = True
        conn.execute(sql.SQL('CREATE DATABASE {} TEMPLATE template0').format(sql.Identifier(db)))
    env['DATABASE_URL'] = f'postgresql://{user}:{quote(secret,safe="")}@127.0.0.1:{port}/{db}'
    commands = [('migrate-0108', ['migrate', 'crm', '0108', '--noinput', '--verbosity', '2']), ('migrate-new', ['migrate', '--noinput', '--verbosity', '2']), ('migration-check', ['migrate', '--check']), ('models-check', ['makemigrations', '--check', '--dry-run']), ('party-tests', ['test', 'crm.tests.test_party_request_lifecycle', 'crm.tests.test_party_request_lifecycle_migration', 'crm.tests.test_party_pg_cleanup', 'crm.tests.test_postgres_test_isolation', 'crm.tests.test_party_document_version', 'crm.tests.test_party_quote_application', 'crm.tests.test_party_version_service', 'crm.tests.test_party_version_concurrency', 'crm.tests.test_quote_party_approval_guard', '--verbosity', '2'])]
    for name, args in commands:
        if cmd(name, [sys.executable, 'manage.py', *args], 1200): results['failed'] = True
    seed = "from crm.models import Customer,Quote; from datetime import date; c=Customer.objects.create(code='PG-REV',name='Synthetic'); q=Quote.objects.create(quote_no='PG-REV',customer=c,quote_date=date(2026,11,5),buyer_country_snapshot='Germany'); print('seeded',q.pk,q.buyer_country_snapshot)"
    if cmd('rollback-seed', [sys.executable, 'manage.py', 'shell', '-c', seed]): results['failed'] = True
    reverse = cmd('rollback-rejection', [sys.executable, 'manage.py', 'migrate', 'crm', '0108', '--noinput'])
    log = (report / 'rollback-rejection.log').read_text(encoding='utf8', errors='replace')
    if reverse == 0 or '拒绝回退' not in log: results['failed'] = True
    verify = "from crm.models import Quote; from django.db.migrations.recorder import MigrationRecorder; q=Quote.objects.get(quote_no='PG-REV'); assert q.buyer_country_snapshot=='Germany'; assert MigrationRecorder.Migration.objects.filter(app='crm',name='0109_quote_buyer_country_snapshot').exists(); print('PASS snapshot preserved and 0109 remains applied')"
    if cmd('rollback-verify', [sys.executable, 'manage.py', 'shell', '-c', verify]): results['failed'] = True
    with psycopg.connect(host='127.0.0.1', port=port, user=user, password=secret, dbname='postgres') as conn:
        results['remaining_test_databases'] = [x[0] for x in conn.execute("SELECT datname FROM pg_database WHERE datname LIKE 'test_sunjack_%'").fetchall()]
        if results['remaining_test_databases']: results['failed'] = True
except Exception as exc:
    results['error'] = str(exc).replace(secret, '[REDACTED]')
    results['failed'] = True
finally:
    try:
        after = source_hashes('source-hashes-after')
        results['source_hashes_match'] = before == after
        if before != after: results['failed'] = True
    except Exception as exc:
        results['source_hash_error'] = str(exc)
        results['failed'] = True
    if started:
        try:
            stop = tool('pg_ctl-stop', ['-D', str(root / 'data'), '-m', 'fast', '-w', 'stop'])
            if stop: raise RuntimeError('pg_ctl stop failed')
            started = False
        except Exception as exc:
            results['cleanup_error'] = str(exc)
            results['failed'] = True
    if not started:
        try:
            if root.parent != Path(tempfile.gettempdir()).resolve() or not root.name.startswith('sunjack-party-version-pg17-') or json.loads((root / 'owner.json').read_text())['marker'] != marker: raise RuntimeError('ownership mismatch')
            shutil.rmtree(root)
            results['cleanup'] = 'complete'
        except Exception as exc:
            results['cleanup_error'] = str(exc)
            results['failed'] = True
    (report / 'result.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps(results, ensure_ascii=False), flush=True)
sys.exit(1 if results.get('failed') else 0)


