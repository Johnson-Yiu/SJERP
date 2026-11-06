import hashlib, json, os, secrets, shutil, socket, subprocess, sys, tempfile, uuid
from pathlib import Path
from urllib.parse import quote
import psycopg
from psycopg import sql

report = Path(__file__).resolve().parent
repo = Path('D:\\Codex项目\\森爵照明管理系统\\.worktrees\\r1-prelaunch-consolidation-20261104\\.tmp\\party-int-01')
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
        if not (path.startswith('backend/') or path.startswith('frontend/')):
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
        if not results['server_version'].startswith('17.'): raise RuntimeError('PostgreSQL 17 required')
        results['identity_verified'] = True
        conn.execute(sql.SQL('CREATE DATABASE {} TEMPLATE template0').format(sql.Identifier(db)))
    env['DATABASE_URL'] = f'postgresql://{user}:{quote(secret,safe="")}@127.0.0.1:{port}/{db}'
    commands = [('migrate-reminder-baseline', ['migrate', 'crm', '0109_new_product_reminders', '--noinput']), ('seed-old', ['shell', '-c', "from django.db import connection; from django.db.migrations.executor import MigrationExecutor; from datetime import date; a=MigrationExecutor(connection).loader.project_state([('crm','0109_new_product_reminders')]).apps; C=a.get_model('crm','Customer'); Q=a.get_model('crm','Quote'); R=a.get_model('crm','NewProductReminder'); c=C.objects.create(code='UAT-OLD',name='Synthetic legacy'); Q.objects.create(quote_no='UAT-OLD',customer=c,quote_date=date(2020,1,2)); R.objects.create(customer=c,requirement='Synthetic reminder'); print('OLD_DATABASE_SEEDED')"]), ('migrate-new', ['migrate', '--noinput']), ('verify-old', ['shell', '-c', "from crm.models import Quote,NewProductReminder; from django.db.migrations.recorder import MigrationRecorder as M; q=Quote.objects.get(quote_no='UAT-OLD'); assert q.customer.name=='Synthetic legacy'; assert q.buyer_tax_id is None; assert NewProductReminder.objects.filter(requirement='Synthetic reminder').count()==1; assert M.Migration.objects.filter(app='crm',name__in=['0109_new_product_reminders','0118_merge_party_reminders']).count()==2; print('OLD_QUOTE_UNKNOWN_AND_REMINDER_PRESERVED')"]), ('migration-check', ['migrate', '--check']), ('models-check', ['makemigrations', '--check', '--dry-run'])]
    for name, args in commands:
        if cmd(name, [sys.executable, 'manage.py', *args], 1200): results['failed'] = True
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
        results['backend_hashes_match'] = {k:v for k,v in before.items() if k.startswith('backend/')} == {k:v for k,v in after.items() if k.startswith('backend/')}
        results['changed_source_paths'] = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
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
