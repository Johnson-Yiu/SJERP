import json, os, secrets, shutil, socket, subprocess, sys, tempfile, uuid
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
guard = 'party_guard_' + uuid.uuid4().hex[:12]
fresh = 'party_fresh_' + uuid.uuid4().hex[:12]
(root / 'password').write_text(secret, encoding='ascii')
(root / 'media').mkdir()
env = {k:v for k,v in os.environ.items() if not k.upper().startswith('PG')}
env.update(APP_STAGE='development', PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1', MEDIA_ROOT=str(root / 'media'))
for key in ('ISS018_COMMAND_PG_BIN', 'ISS018_DRILL_ROOT', 'ISS018_DRILL_PASSWORD_FILE'):
    env.pop(key, None)
results = {'head':'bcdcb57545f121b8a4102f352c74008b47372035', 'root':str(root), 'stages':{}, 'cleanup':'not-started'}
started = False
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
        conn.execute(sql.SQL('CREATE DATABASE {} TEMPLATE template0').format(sql.Identifier(fresh)))
        conn.execute(sql.SQL('CREATE DATABASE {} TEMPLATE template0').format(sql.Identifier(guard)))
    env['DATABASE_URL'] = f'postgresql://{user}:{quote(secret,safe="")}@127.0.0.1:{port}/{db}'
    args = [sys.executable, 'manage.py', 'test', 'crm.tests.test_quote_party_fingerprint_versions', 'crm.tests.test_party_quote_application', 'crm.tests.test_quotes.QuoteApiTests.test_order_with_commercial_changes_creates_and_links_quote_revision', 'crm.tests.test_quotes.QuoteApiTests.test_editing_order_draft_defers_quote_revision_until_confirmation', '--verbosity', '2']
    if cmd('party-service-concurrency', args, 1200): results['failed'] = True
    with psycopg.connect(host='127.0.0.1', port=port, user=user, password=secret, dbname='postgres') as conn:
        results['remaining_test_databases'] = [x[0] for x in conn.execute("SELECT datname FROM pg_database WHERE datname LIKE 'test_sunjack_%'").fetchall()]
        if results['remaining_test_databases']: results['failed'] = True
except Exception as exc:
    results['error'] = str(exc).replace(secret, '[REDACTED]')
    results['failed'] = True
finally:
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









