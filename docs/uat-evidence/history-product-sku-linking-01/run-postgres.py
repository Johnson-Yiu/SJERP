"""Run H1 against a new loopback PostgreSQL cluster owned by this invocation."""
import argparse
import os
import secrets
import socket
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--postgres-bin", type=Path, required=True)
    parser.add_argument('--full', action='store_true')
    parser.add_argument('--test-label', action='append', default=[])
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[3]
    root = Path(tempfile.mkdtemp(prefix="sunjack-h1-pg-"))
    cluster = root / "cluster"
    secret = root / "password"
    password = secrets.token_urlsafe(32)
    secret.write_text(password + "\n", encoding="ascii")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    env = {
        **os.environ, "DATABASE_URL": f"postgresql://h1_test:{password}@127.0.0.1:{port}/postgres",
        "MEDIA_ROOT": str(root / "media"), "APP_STAGE": "development",
        "PYTHONUTF8": "1",
    }

    def pg(name, *options, check=True):
        return subprocess.run([str(args.postgres_bin / (name + (".exe" if os.name == "nt" else ""))), *map(str, options)],
                              check=check, env=os.environ)

    def django(*options):
        subprocess.run([sys.executable, "manage.py", *options], cwd=repo / "backend", env=env, check=True)

    verify = Path(__file__).with_name("verify-migration.py")
    migration_check = f"exec(compile(open({str(verify)!r}, 'rb').read(), {str(verify)!r}, 'exec'))"
    try:
        print("H1 source:", subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(), flush=True)
        pg("initdb", "-D", cluster, "-U", "h1_test", "--auth=scram-sha-256", "--pwfile=" + str(secret),
           "--encoding=UTF8", "--no-locale")
        secret.unlink()
        pg("pg_ctl", "-D", cluster, "-l", root / "server.log", "-o", f"-h 127.0.0.1 -p {port}", "-w", "start")
        if args.test_label:
            django('test', *args.test_label, '--noinput', '-v', '2')
            return
        print("H1 forward migration from D2", flush=True)
        django("migrate", "crm", "0128", "--noinput", "--verbosity", "0")
        env["H1_MIGRATION_PHASE"] = "seed"
        django("shell", "--no-imports", "-c", migration_check)
        django("migrate", "--noinput", "--verbosity", "1")
        env["H1_MIGRATION_PHASE"] = "verify"
        django("shell", "--no-imports", "-c", migration_check)
        print("H1 new test database, transactional and concurrency checks", flush=True)
        if args.full:
            django('makemigrations', '--check', '--dry-run')
            django('test', '--noinput', '-v', '2')
            return
        django("test", "crm.tests.test_history_products", "crm.tests.test_history_takeover",
               "crm.tests.test_history_operational_contracts", "--noinput")
    finally:
        secret.unlink(missing_ok=True)
        if (cluster / "postmaster.pid").exists():
            pg("pg_ctl", "-D", cluster, "-m", "fast", "-w", "stop", check=False)


if __name__ == "__main__":
    main()
