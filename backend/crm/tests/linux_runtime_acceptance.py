"""Exercise the delivered unit on the guarded, disposable Linux operations runner."""

import getpass
import grp
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import time
import uuid

from psycopg import sql

from operations_runtime_http import ready


def exercise_runtime(root, admin, database, maint, runtime, pg_port, backend):
    """Called only after the parent verifies the runner and owns its PG17 service."""
    suffix = uuid.uuid4().hex[:12]
    name = f"sjerp-ci-{suffix}"
    sandbox = root / name
    sandbox.mkdir()
    deployment = backend.parent / "docs" / "deployment"
    venv = sandbox / "venv"
    db_b = f"{name.replace('-', '_')}_b"
    role_b = f"{db_b}_runtime"
    unit_path = Path("/run/systemd/system") / f"{name}@.service"
    instances = ("a", "b")
    units = [f"{name}@{instance}.service" for instance in instances]
    unit_installed = database_created = role_created = False

    def run(*args, **kwargs):
        return subprocess.run(list(map(str, args)), check=True, timeout=240, **kwargs)

    def ctl(*args, check=True):
        return subprocess.run(["sudo", "-n", "systemctl", *args], check=check,
                              capture_output=True, text=True, timeout=75)

    def value(unit, field):
        return ctl("show", "--value", f"--property={field}", unit).stdout.strip()

    def wait_failed(unit):
        until = time.monotonic() + 20
        while time.monotonic() < until:
            if value(unit, "ActiveState") == "failed":
                return
            time.sleep(0.2)
        raise AssertionError(f"{unit} did not reach failed state")

    def configure(instance, db, user, port, **overrides):
        home = sandbox / instance
        env = {
            "APP_STAGE": "staging", "DJANGO_ALLOWED_HOSTS": f"{instance}.erp.invalid",
            "DJANGO_SECRET_KEY": secrets.token_urlsafe(48),
            "DATABASE_URL": f"postgresql://{user}@127.0.0.1:{pg_port}/{db}?connect_timeout=4&sslmode=disable",
            "SJERP_EXPECTED_DB_HOST": "127.0.0.1", "SJERP_EXPECTED_DB_PORT": str(pg_port),
            "SJERP_EXPECTED_DB_NAME": db, "SJERP_EXPECTED_DB_USER": user,
            "MEDIA_ROOT": str(home / "media"), "SJERP_EXPECTED_MEDIA_ROOT": str(home / "media"),
            "SJERP_HTTP_HOST": f"{instance}.erp.invalid", "SJERP_HTTP_PORT": str(port),
        }
        env.update(overrides)
        path = home / "runtime.env"
        path.touch(mode=0o600, exist_ok=True)
        path.write_text("".join(f"{key}={value}\n" for key, value in env.items()), encoding="ascii")
        return env

    def probe(env, expected=None):
        proc = subprocess.run([str(venv / "bin/python"), str(backend / "manage.py"), "check_local_runtime"],
                              env={**os.environ, **env}, capture_output=True, text=True, timeout=30)
        if expected is None:
            assert proc.returncode == 0, proc.stderr
        else:
            assert proc.returncode != 0 and expected in proc.stderr, proc.stderr

    try:
        run(sys.executable, "-m", "venv", venv)
        python = venv / "bin/python"
        run(python, "-m", "pip", "install", "-r", backend / "requirements.lock",
            "-r", deployment / "sjerp-local-service-requirements.txt")
        run(python, "-m", "pip", "check")
        run(venv / "bin/gunicorn", "--version")
        for instance in instances:
            home = sandbox / instance
            (home / "media").mkdir(parents=True, mode=0o700)
            shutil.copyfile(deployment / "sjerp-local-gunicorn.conf.py.example", home / "gunicorn.conf.py")
        with socket.socket() as one, socket.socket() as two:
            one.bind(("127.0.0.1", 0))
            two.bind(("127.0.0.1", 0))
            port_a, port_b = one.getsockname()[1], two.getsockname()[1]

        admin.execute(sql.SQL("CREATE ROLE {} LOGIN NOINHERIT").format(sql.Identifier(role_b)))
        role_created = True
        admin.execute(sql.SQL("CREATE DATABASE {} OWNER {} TEMPLATE template0").format(sql.Identifier(db_b), sql.Identifier(maint)))
        database_created = True
        import psycopg
        with psycopg.connect(host="127.0.0.1", port=pg_port, dbname=database, user=maint) as conn:
            conn.execute(sql.SQL("GRANT SELECT ON django_migrations TO {}").format(sql.Identifier(runtime)))
        env_a = configure("a", database, runtime, port_a)
        env_b = configure("b", db_b, role_b, port_b)
        probe(env_a)
        probe({**env_a, "SJERP_EXPECTED_DB_NAME": db_b}, "Configured database NAME differs")
        probe(configure("a", database, maint, port_a), "violates the audit table privilege boundary")
        probe({**env_a, "MEDIA_ROOT": str(sandbox / "missing"), "SJERP_EXPECTED_MEDIA_ROOT": str(sandbox / "missing")},
              "private media directory differs")
        probe(env_b, "Database migrations are pending")
        migration_env = configure("b", db_b, maint, port_b)
        run(python, backend / "manage.py", "migrate", "--noinput", "--verbosity", "0", env={**os.environ, **migration_env})
        with psycopg.connect(host="127.0.0.1", port=pg_port, dbname=db_b, user=maint) as conn:
            conn.execute(sql.SQL("GRANT SELECT ON django_migrations TO {}").format(sql.Identifier(role_b)))
            conn.execute(sql.SQL("GRANT SELECT, INSERT ON crm_operationlog TO {}").format(sql.Identifier(role_b)))
        configure("a", database, runtime, port_a)
        configure("b", db_b, role_b, port_b)
        probe(env_b)

        # Change only host-specific paths and the Unix identity for the ephemeral runner.
        template = (deployment / "sjerp-local@.service.example").read_text()
        rendered = (template.replace("User=sjerp-%i", f"User={getpass.getuser()}")
                    .replace("Group=sjerp-%i", f"Group={grp.getgrgid(os.getgid()).gr_name}")
                    .replace("/srv/sjerp/%i/release/backend", str(backend))
                    .replace("/srv/sjerp/%i/venv", str(venv))
                    .replace("/etc/sjerp/%i", f"{sandbox}/%i"))
        local_unit = sandbox / unit_path.name
        local_unit.write_text(rendered, encoding="ascii")
        run("sudo", "-n", "install", "-m", "0644", local_unit, unit_path)
        unit_installed = True
        ctl("daemon-reload")
        a, b = units
        ctl("start", a)
        pid_a = value(a, "MainPID")
        assert pid_a != "0" and ready("a.erp.invalid", port_a)
        ctl("start", a)
        assert value(a, "MainPID") == pid_a

        configure("b", db_b, role_b, port_a)
        assert ctl("start", b, check=False).returncode != 0
        wait_failed(b)
        assert value(a, "MainPID") == pid_a and ready("a.erp.invalid", port_a)

        configure("b", db_b, role_b, port_b, SJERP_HTTP_HOST="invalid.erp.invalid")
        assert ctl("start", b, check=False).returncode != 0
        wait_failed(b)
        assert value(b, "MainPID") == "0" and not ready("b.erp.invalid", port_b)

        configure("b", db_b, role_b, port_b)
        ctl("start", b)
        pid_b = value(b, "MainPID")
        assert pid_b not in ("0", pid_a) and ready("b.erp.invalid", port_b)
        ctl("stop", a)
        ctl("stop", a)
        assert value(a, "ActiveState") == "inactive" and not ready("a.erp.invalid", port_a)
        assert value(b, "MainPID") == pid_b and ready("b.erp.invalid", port_b)
        ctl("kill", "--kill-whom=main", "--signal=KILL", b)
        wait_failed(b)
        assert value(b, "Result") == "signal"
        ctl("start", b)
        assert value(b, "ActiveState") == "active" and ready("b.erp.invalid", port_b)
        print("RUNTIME_UNIT_PASS: locked install, direct PG17 checks, independent units, collision, HTTP failure, crash and recovery", flush=True)
    finally:
        if unit_installed:
            try:
                ctl("stop", *units)
                ctl("reset-failed", *units, check=False)
            finally:
                run("sudo", "-n", "rm", "--", unit_path)
                ctl("daemon-reload")
        if database_created:
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(db_b)))
        if role_created:
            admin.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(role_b)))
