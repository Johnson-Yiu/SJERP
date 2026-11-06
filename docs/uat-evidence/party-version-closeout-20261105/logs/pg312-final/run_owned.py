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
    env['DATABASE_URL'] = f'postgresql://{user}:{quote(secret,safe="")}@127.0.0.1:{port}/{fresh}'
    if cmd('fresh-migrate-all', [sys.executable, 'manage.py', 'migrate', '--noinput', '--verbosity', '2'], 1200): results['failed'] = True
    if cmd('fresh-migration-check', [sys.executable, 'manage.py', 'migrate', '--check'], 1200): results['failed'] = True
    env['DATABASE_URL'] = f'postgresql://{user}:{quote(secret,safe="")}@127.0.0.1:{port}/{db}'
    commands = [('migrate-0108', ['migrate', 'crm', '0108', '--noinput', '--verbosity', '2']), ('migrate-0109', ['migrate', 'crm', '0109', '--noinput', '--verbosity', '2']), ('migration-plan', ['migrate', '--plan']), ('migrate-new', ['migrate', '--noinput', '--verbosity', '2']), ('migration-check', ['migrate', '--check']), ('models-check', ['makemigrations', '--check', '--dry-run']), ('party-tests', ['test', 'crm.tests.test_formal_party_snapshots', 'crm.tests.test_party_version_current_baseline', 'crm.tests.test_quote_buyer_country_snapshot', 'crm.tests.test_party_version_service', 'crm.tests.test_party_version_concurrency', 'crm.tests.test_quote_buyer_tax_id', 'crm.tests.test_party_version_migrations', '--verbosity', '2'])]
    for name, args in commands:
        if cmd(name, [sys.executable, 'manage.py', *args], 1200): results['failed'] = True
    env['DATABASE_URL'] = f'postgresql://{user}:{quote(secret,safe="")}@127.0.0.1:{port}/{guard}'
    if cmd('0110-only-migrate', [sys.executable,'manage.py','migrate','crm','0110','--noinput'],1200): results['failed'] = True
    seed_request = "from django.db import connection; from django.db.migrations.executor import MigrationExecutor; from django.contrib.auth import get_user_model; from datetime import date; a=MigrationExecutor(connection).loader.project_state([('crm','0110_party_version')]).apps; C=a.get_model('crm','Customer'); Q=a.get_model('crm','Quote'); R=a.get_model('crm','PartyVersionRequest'); u=get_user_model().objects.create_user(username='pg-guard'); c=C.objects.create(code='PG-GUARD',name='Synthetic'); q=Q.objects.create(quote_no='PG-GUARD',customer_id=c.pk,quote_date=date(2026,11,5),buyer_country_snapshot=None); r=R.objects.create(quote_id=q.pk,initiator_id=u.pk,base_snapshot={},proposed_snapshot={},base_fingerprint='a'*64,content_fingerprint='b'*64,change_type='correction',reason='synthetic',evidence='synthetic',source_trust='unknown'); print('request',r.pk)"
    if cmd('0110-request-seed', [sys.executable,'manage.py','shell','-c',seed_request]): results['failed'] = True
    reverse_request = cmd('0110-request-rejection', [sys.executable,'manage.py','migrate','crm','0109','--noinput'])
    reqlog = (report/'0110-request-rejection.log').read_text(encoding='utf8', errors='replace')
    if reverse_request == 0 or 'reject_history_loss' not in reqlog: results['failed'] = True
    verify_request = "from django.db import connection; from django.db.migrations.executor import MigrationExecutor; from django.db.migrations.recorder import MigrationRecorder; a=MigrationExecutor(connection).loader.project_state([('crm','0110_party_version')]).apps; assert a.get_model('crm','PartyVersionRequest').objects.filter(initiator__username='pg-guard').exists(); assert MigrationRecorder.Migration.objects.filter(app='crm',name='0110_party_version').exists(); assert not MigrationRecorder.Migration.objects.filter(app='crm',name='0111_quote_buyer_tax_id').exists(); print('PASS request preserved and 0110 remains applied')"
    if cmd('0110-request-verify', [sys.executable,'manage.py','shell','-c',verify_request]): results['failed'] = True
    env['DATABASE_URL'] = f'postgresql://{user}:{quote(secret,safe="")}@127.0.0.1:{port}/{fresh}'
    seed = "from crm.models import Customer,Quote; from datetime import date; c=Customer.objects.create(code='PG-REV',name='Synthetic'); q=Quote.objects.create(quote_no='PG-REV',customer=c,quote_date=date(2026,11,5),buyer_country_snapshot='Germany',buyer_tax_id=None); print('seeded',q.pk,q.buyer_country_snapshot)"
    if cmd('rollback-seed', [sys.executable, 'manage.py', 'shell', '-c', seed]): results['failed'] = True
    reverse = cmd('rollback-rejection', [sys.executable, 'manage.py', 'migrate', 'crm', '0108', '--noinput'])
    log = (report / 'rollback-rejection.log').read_text(encoding='utf8', errors='replace')
    if reverse == 0 or '拒绝回退' not in log: results['failed'] = True
    verify = "from crm.models import Quote; from django.db.migrations.recorder import MigrationRecorder; q=Quote.objects.get(quote_no='PG-REV'); assert q.buyer_country_snapshot=='Germany'; assert all(MigrationRecorder.Migration.objects.filter(app='crm',name=n).exists() for n in ['0109_quote_buyer_country_snapshot','0110_party_version','0111_quote_buyer_tax_id']); assert Quote.objects.get(quote_no='PG-REV').buyer_country_snapshot=='Germany'; print('PASS 0109 0110 0111 retained and ORM readable')"
    if cmd('rollback-verify', [sys.executable, 'manage.py', 'shell', '-c', verify]): results['failed'] = True
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


