"""Evidence-only launcher for the frozen 447d disposable PG17 regression.

Not a production tool or a general ERP acceptance command. The existing drill
retains every database, application-cleanliness and cleanup guard unchanged.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]
SHA = "447d7816ead2e971e249cb2e762b1a6f7009b9c0"
FROZEN = ROOT / ".tmp/final-integrated-447d"
REPORT = ROOT / "docs/uat-evidence/integration-closeout-02"
PG_BIN = Path("C:/Users/Johnson/AppData/Local/Temp/sunjack-iss018-pg17-d26bfa744cf54322af03ea964e90089f/pgsql/bin")


def main():
    if len(sys.argv) != 2 or not re.fullmatch(r"postgres-final-447d-[a-z0-9-]+\.log", sys.argv[1]):
        raise SystemExit("Supply one new, explicitly named 447d evidence log")
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=FROZEN, text=True).strip() != SHA:
        raise SystemExit("Frozen application SHA differs")
    if subprocess.check_output(["git", "status", "--porcelain", "--", "backend", "templates"], cwd=FROZEN):
        raise SystemExit("Frozen backend/templates must remain clean")
    log = REPORT / sys.argv[1]
    metadata = log.with_suffix(".launcher.json")
    if log.exists() or metadata.exists():
        raise FileExistsError("Refusing to overwrite a previous attempt")
    paths = ["docs/uat-evidence/review-integration-batch-20261104/run-postgres-regression.py",
             "docs/uat-evidence/review-integration-batch-20261104/seed_history_backup.py",
             "docs/uat-evidence/integration-closeout-02/seed_history_operational_backup.py"]
    helpers = {}
    for name in paths:
        raw = (FROZEN / name).read_bytes()
        if raw != (ROOT / name).read_bytes():
            raise SystemExit("Frozen evidence helper differs from reviewed coordinator copy")
        helpers[name] = hashlib.sha256(raw).hexdigest()
    env = {**os.environ, "APP_STAGE": "development", "DATABASE_URL": "sqlite:///:memory:",
           "AUDIT_LOG_ENABLED": "1", "DEVELOPMENT_SUPERADMIN": "1", "RBAC_ENFORCEMENT": "0",
           "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8",
           "OPS_TEST_OPENSSL": "D:/Program Files/Git/usr/bin/openssl.exe",
           "REVIEW_TEST_LABELS": "", "REVIEW_FINANCE_SEED": "1", "REVIEW_HISTORY_SEED": "1",
           "REVIEW_HISTORY_OPERATIONAL_SEED": "1",
           "REVIEW_EVIDENCE_ROOT": str(FROZEN / "docs/uat-evidence/integration-closeout-02/final-pg-447d")}
    command = [sys.executable, str(FROZEN / paths[0]), "--postgres-bin", str(PG_BIN)]
    with log.open("xb") as stream:
        result = subprocess.run(command, cwd=FROZEN, env=env, stdout=stream, stderr=subprocess.STDOUT)
    receipt = {"product_sha": SHA, "helper_sha256": helpers, "exit_code": result.returncode,
               "raw_log": log.name, "raw_log_sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
               "scope": "Actual owned-cluster attempt; exit code alone does not assert tests passed"}
    metadata.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"exit_code": result.returncode, "log": log.name}))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
