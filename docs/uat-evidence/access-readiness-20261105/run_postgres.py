"""Run selected permission tests against a task-owned local PostgreSQL cluster."""
import argparse
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile

repo = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(repo / 'backend'))
from isolated_postgres_drill import run_tool, tool


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--postgres-bin', required=True)
    parser.add_argument('--session-only', action='store_true')
    parser.add_argument('--format-role-only', action='store_true')
    args = parser.parse_args()
    root = Path(tempfile.mkdtemp(prefix='sunjack-access-pg-')).resolve()
    pg = root / 'pgsql' / 'bin'
    cluster = root / 'cluster'
    started = False
    try:
        shutil.copytree(Path(args.postgres_bin).resolve(strict=True).parent, pg.parent)
        password = secrets.token_hex(32)
        secret = root / 'password'
        secret.write_text(password, encoding='ascii')
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        run_tool([tool(pg, 'initdb'), '-D', str(cluster), '-U', 'access_synthetic_admin', '--auth=scram-sha-256', '--pwfile=' + str(secret), '--encoding=UTF8', '--no-locale'])
        secret.unlink()
        started = True
        run_tool([tool(pg, 'pg_ctl'), '-D', str(cluster), '-l', str(root / 'postgres.log'), '-o', f'-h 127.0.0.1 -p {port}', '-w', 'start'])
        env = {**os.environ, 'DATABASE_URL': f'postgresql://access_synthetic_admin:{password}@127.0.0.1:{port}/postgres',
               'PYTHONPATH': str(repo / 'backend'), 'DJANGO_SETTINGS_MODULE': 'config.settings', 'MEDIA_ROOT': str(root / 'media')}
        labels = ['crm.tests.test_access_readiness_20261105', 'crm.tests.test_functional_rbac',
                   'crm.tests.test_sales_data_scope', 'crm.tests.test_procurement_data_scope',
                   'crm.tests.test_supplier_context_scope', 'crm.tests.test_finance_data_scope',
                   'crm.tests.test_finance_integration_permissions', 'crm.tests.test_audit']
        if args.session_only:
            labels = labels[:1]
        if args.format_role_only:
            labels = ['crm.tests.test_access_readiness_format_and_role']
        command = [sys.executable, str(repo / 'backend' / 'manage.py'), 'test', *labels, '--noinput', '--verbosity', '1']
        result = subprocess.run(command, cwd=repo, env=env, check=False)
        if result.returncode:
            raise RuntimeError('Selected PostgreSQL tests failed: exit ' + str(result.returncode))
        print('PASS: synthetic isolated PostgreSQL permission tests', flush=True)
    finally:
        if started:
            run_tool([tool(pg, 'pg_ctl'), '-D', str(cluster), '-m', 'fast', '-w', 'stop'])
        if root.parent != Path(tempfile.gettempdir()).resolve() or not root.name.startswith('sunjack-access-pg-') or root.is_symlink():
            raise RuntimeError('Refusing to clean unowned root')
        shutil.rmtree(root)
        print('Task-owned PostgreSQL root cleaned', flush=True)


if __name__ == '__main__':
    main()
