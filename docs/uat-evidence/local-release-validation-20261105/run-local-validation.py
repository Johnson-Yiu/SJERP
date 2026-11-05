"""Run local release checks against one clean, immutable application checkout.

The PostgreSQL and browser runners retain their own isolation and safety checks.
A PASS for one stage is never a substitute for all stages or independent UAT.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
APP = ("backend", "frontend", "templates", ".github/workflows", ":(exclude)frontend/docs/**")
REPORT = Path(__file__).resolve().parent


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def identity(expected):
    actual = git("rev-parse", "HEAD")
    if actual != expected:
        raise RuntimeError(f"HEAD changed: expected {expected}, actual {actual}")
    dirty = git("status", "--porcelain", "--untracked-files=all", "--", *APP)
    if dirty:
        raise RuntimeError("Application checkout is not clean:\n" + dirty)
    return {name: git("rev-parse", f"{expected}:{name}") for name in ("backend", "frontend", "templates", ".github/workflows")}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sha", required=True, help="Full committed candidate HEAD SHA")
    parser.add_argument("--python", required=True, help="Absolute path to the locked Python 3.12+ interpreter")
    parser.add_argument("--postgres-bin", required=True, help="Absolute directory containing PostgreSQL 17 tools")
    parser.add_argument("--openssl", help="Absolute OpenSSL executable for applicable signature tests")
    parser.add_argument("--run-name", required=True, help="New evidence directory name; never overwrites")
    parser.add_argument("--preflight-only", action="store_true", help="Run prerequisites and SQLite migration checks only; not a release validation")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.sha):
        parser.error("--sha must be a full lowercase 40-character SHA")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,49}", args.run_name):
        parser.error("--run-name must contain lowercase letters, numbers or hyphens")
    python = Path(args.python)
    pg_bin = Path(args.postgres_bin)
    if not python.is_absolute() or not python.is_file() or not pg_bin.is_absolute() or not pg_bin.is_dir():
        parser.error("--python and --postgres-bin must be existing absolute paths")
    if args.openssl and (not Path(args.openssl).is_absolute() or not Path(args.openssl).is_file()):
        parser.error("--openssl must be an existing absolute executable")
    objects = identity(args.sha)
    helper_paths = [Path(__file__).resolve(), REPORT / "browser-suite.mjs",
                    ROOT / "docs/uat-evidence/review-integration-batch-20261104/run-postgres-regression.py",
                    ROOT / "docs/uat-evidence/review-integration-batch-20261104/finance-backup-seed/seed_finance_backup.py",
                    ROOT / "docs/uat-evidence/review-integration-batch-20261104/seed_history_backup.py",
                    ROOT / "docs/uat-evidence/integration-closeout-02/seed_history_operational_backup.py",
                    ROOT / "docs/uat-evidence/integration-closeout-02/run-final-history-chrome.mjs",
                    ROOT / "docs/uat-evidence/integration-closeout-02/seed_integrated_history_uat.py",
                    ROOT / "docs/uat-evidence/integration-closeout-02/verify_integrated_history_uat.py"]
    helper_hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in helper_paths}
    def attest():
        identity(args.sha)
        for path in helper_paths:
            if hashlib.sha256(path.read_bytes()).hexdigest() != helper_hashes[str(path.relative_to(ROOT))]:
                raise RuntimeError(f"Validation helper changed: {path.relative_to(ROOT)}")
    out = REPORT / args.run_name
    out.mkdir(exist_ok=False)
    (out / "logs").mkdir()
    media = Path(tempfile.mkdtemp(prefix="sunjack-local-release-media-"))
    env = os.environ.copy()
    for name in list(env):
        if name.startswith("PG") or name.startswith("ISS018_DRILL_"):
            env.pop(name, None)
    env.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8", APP_STAGE="development",
               DATABASE_URL="sqlite:///:memory:", MEDIA_ROOT=str(media), AUDIT_LOG_ENABLED="1",
               DJANGO_SECRET_KEY=secrets.token_urlsafe(48),
               DEVELOPMENT_SUPERADMIN="1", RBAC_ENFORCEMENT="0",
               ISOLATED_TEST_PYTHON=str(python), RELEASE_CANDIDATE_SHA=args.sha,
               RELEASE_EVIDENCE_ROOT=str(out / "browser"), R1_PLAYWRIGHT_EVIDENCE_ROOT=str(out / "browser"),
               REVIEW_EVIDENCE_ROOT=str(out / "postgres"), REVIEW_FINANCE_SEED="1",
               REVIEW_HISTORY_SEED="1", REVIEW_HISTORY_OPERATIONAL_SEED="1", REVIEW_TEST_LABELS="")
    env["PATH"] = str(python.parent) + os.pathsep + env.get("PATH", "")
    env["PYTHON"] = str(python)
    # Windows CreateProcess may resolve an executable using the parent PATH,
    # not only the supplied child environment. Restrict the runner process too.
    os.environ["PATH"] = env["PATH"]
    if args.openssl:
        env["OPS_TEST_OPENSSL"] = args.openssl
    npm = [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", "npm.cmd"] if os.name == "nt" else ["npm"]
    npx = [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", "npx.cmd"] if os.name == "nt" else ["npx"]
    upgrade_db = out / "isolated-upgrade.sqlite3"
    exe = lambda *command: [str(x) for x in command]
    lock_check = "import importlib.metadata as m,re,pathlib,sys; lines=pathlib.Path('backend/requirements.lock').read_text().splitlines(); pins=[x.strip().split('==') for x in lines if re.match(r'^[A-Za-z0-9_.-]+==',x.strip())]; bad=[(n,v,m.version(n)) for n,v in pins if m.version(n)!=v]; print('locked pins:',len(pins),'mismatches:',bad); sys.exit(bool(bad))"
    phases = [
      ("python-version", exe(python, "-c", "import sys; print(sys.version); sys.exit(sys.version_info < (3,12))"), ROOT),
      ("postgres-version", exe(pg_bin / ("pg_config.exe" if os.name == "nt" else "pg_config"), "--version"), ROOT),
      ("python-path-identity", exe("node", "-e", "const r=require(\"node:child_process\").spawnSync(\"python\", [\"-c\", \"import sys,django; print(sys.executable); print(django.get_version()); assert django.get_version() == \\\"6.0.9\\\"\"], {stdio: \"inherit\"}); process.exit(r.status === null ? 1 : r.status)"), ROOT),
      ("locked-dependencies", exe(python, "-c", lock_check), ROOT),
      ("pip-check", exe(python, "-m", "pip", "check"), ROOT),
      ("django-check", exe(python, "manage.py", "check"), ROOT / "backend"),
      ("migrations-check", exe(python, "manage.py", "makemigrations", "--check", "--dry-run"), ROOT / "backend"),
      ("migration-graph", exe(python, "manage.py", "showmigrations", "--plan"), ROOT / "backend"),
      ("sqlite-upgrade-0103", exe(python, "manage.py", "migrate", "crm", "0103", "--noinput"), ROOT / "backend"),
      ("sqlite-upgrade-seed", exe(python, "manage.py", "shell", "-c", "from crm.models import Customer; Customer.objects.create(code=\"UAT-UPGRADE\", name=\"Synthetic migration customer\"); print(\"SYNTHETIC_SEED_OK\")"), ROOT / "backend"),
      ("sqlite-upgrade-latest", exe(python, "manage.py", "migrate", "--noinput"), ROOT / "backend"),
      ("sqlite-upgrade-verify", exe(python, "manage.py", "shell", "-c", "from crm.models import Customer; assert Customer.objects.filter(code=\"UAT-UPGRADE\", name=\"Synthetic migration customer\").count() == 1; print(\"SYNTHETIC_UPGRADE_OK\")"), ROOT / "backend"),
      ("sqlite-full", exe(python, "manage.py", "test", "--verbosity", "2"), ROOT / "backend"),
      ("postgres17-full-backup-restore", exe(python, "docs/uat-evidence/review-integration-batch-20261104/run-postgres-regression.py", "--postgres-bin", pg_bin), ROOT),
      ("backup-command-faults", exe(python, "manage.py", "test", "crm.tests.test_iss018_drill_command", "--verbosity", "2"), ROOT / "backend"),
      ("npm-ci", exe(*npm, "ci"), ROOT / "frontend"),
      # Serialize test files to avoid unrelated load while the isolation test
      # still launches its two worktrees concurrently and retains all assertions.
      ("node", exe(*npm, "run", "test:unit", "--", "--test-concurrency=1"), ROOT / "frontend"),
      ("font", exe("node", "--test", "tests/detail-drawer-typography.spec.js"), ROOT / "frontend"),
      ("vitest", exe(*npx, "--no-install", "vitest", "run", "tests", "--environment", "jsdom", "--exclude", "tests/detail-drawer-typography.spec.js"), ROOT / "frontend"),
      ("browser-applicable", exe("node", REPORT / "browser-suite.mjs"), ROOT / "frontend"),
      ("build", exe(*npm, "run", "build"), ROOT / "frontend"),
      ("history-chrome", exe("node", "docs/uat-evidence/integration-closeout-02/run-final-history-chrome.mjs", "--checkout", ROOT, "--sha", args.sha, "--evidence-dir", ROOT / "docs/uat-evidence/integration-closeout-02" / ("local-release-" + args.run_name)), ROOT),
    ]
    if args.preflight_only:
        phases = phases[:12]
    results = []
    receipt = out / "result.json"
    for name, command, cwd in phases:
        try:
            attest()
            start = datetime.datetime.now(datetime.timezone.utc).isoformat()
            log = out / "logs" / (name + ".log")
            stage_env = env.copy()
            if name == "backup-command-faults":
                stage_env["ISS018_COMMAND_PG_BIN"] = str(pg_bin)
            if name.startswith("sqlite-upgrade-"):
                stage_env["DATABASE_URL"] = "sqlite:///" + upgrade_db.as_posix()
            with log.open("xb") as stream:
                proc = subprocess.Popen(command, cwd=cwd, env=stage_env, stdout=stream, stderr=subprocess.STDOUT, shell=False)
                while True:
                    try:
                        proc.wait(timeout=5)
                        break
                    except subprocess.TimeoutExpired:
                        try:
                            attest()
                        except Exception:
                            proc.terminate()
                            proc.wait(timeout=30)
                            raise RuntimeError("Application source changed while the stage was running; results are invalid")
            attest()
            raw = log.read_bytes()
            tail = raw.decode("utf-8", errors="replace")
            if name == "postgres-version" and (proc.returncode or not re.search(r"PostgreSQL 17(?:\.|\b)", tail)):
                raise RuntimeError("PostgreSQL tools are not version 17")
            summary = re.findall(r"(?:Ran \d+ tests?[^\n]*|OK(?: \([^\n]*\))?|FAILED \([^\n]*\)|\d+ passed[^\n]*)", tail)
            results.append({"stage": name, "command": command, "cwd": str(cwd.relative_to(ROOT)), "started_utc": start,
                            "exit_code": proc.returncode, "log": str(log.relative_to(ROOT)),
                            "sha256": hashlib.sha256(raw).hexdigest(), "summary_candidates": summary[-5:]})
        except Exception as exc:
            results.append({"stage": name, "status": "BLOCKED", "error": str(exc)})
            receipt.write_text(json.dumps({"sha": args.sha, "application_objects": objects, "helper_sha256": helper_hashes, "results": results}, indent=2), encoding="utf-8")
            raise
        receipt.write_text(json.dumps({"sha": args.sha, "application_objects": objects, "helper_sha256": helper_hashes, "results": results,
            "excluded": [{"spec": "iss037-print-output-acceptance.spec.js", "reason": "USER_DEFERRED"}],
            "github_actions": "NOT_RUN", "selection": "preflight-only, full suite NOT_RUN" if args.preflight_only else "full", "scope": "isolated synthetic local verification; not production UAT"}, indent=2), encoding="utf-8")
        print(f"{name}: exit={proc.returncode}", flush=True)
        if proc.returncode and name in {"python-version", "postgres-version", "python-path-identity", "locked-dependencies", "pip-check", "django-check", "migrations-check", "sqlite-upgrade-0103", "sqlite-upgrade-seed", "sqlite-upgrade-latest", "sqlite-upgrade-verify", "npm-ci"}:
            print("Prerequisite failed; remaining stages NOT_RUN", flush=True)
            break
    return 0 if len(results) == len(phases) and all(x.get("exit_code") == 0 for x in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
