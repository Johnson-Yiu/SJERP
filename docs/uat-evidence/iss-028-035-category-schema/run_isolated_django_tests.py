"""Run focused category/SKU regression tests against an owned temporary SQLite DB."""

import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from urllib.parse import quote


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
TEST_LABELS = (
    "crm.tests.test_product_category_sku_identity_safety",
    "crm.tests.test_sku_commercial_identity",
    "crm.tests.test_sku_plans_candidates",
)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    temp_parent = Path(tempfile.gettempdir()).resolve(strict=True)
    run_root = Path(tempfile.mkdtemp(prefix="sunjack-iss028-035-", dir=temp_parent)).resolve(strict=True)
    if run_root == Path(run_root.anchor) or run_root.parent != temp_parent or not run_root.name.startswith("sunjack-iss028-035-"):
        raise SystemExit("refusing: generated test directory is outside the owned temp namespace")
    database = run_root / "db.sqlite3"
    media = run_root / "media"
    media.mkdir()
    run_id = str(uuid.uuid4())
    token = uuid.uuid4().hex + uuid.uuid4().hex[:16]
    normalized = database.as_posix()
    database_url = "sqlite:///" + quote(normalized, safe="/:\\")
    env = {
        **os.environ,
        "APP_STAGE": "development",
        "DJANGO_DEBUG": "1",
        "DEVELOPMENT_SUPERADMIN": "1",
        "RBAC_ENFORCEMENT": "0",
        "AUDIT_LOG_ENABLED": "0",
        "MEDIA_STORAGE_BACKEND": "django.core.files.storage.FileSystemStorage",
        "DJANGO_SETTINGS_MODULE": "test_support.isolated_settings",
        "DATABASE_URL": database_url,
        "MEDIA_ROOT": str(media),
        "ISOLATED_TEST_ROOT": str(run_root),
        "ISOLATED_TEST_RUN_ID": run_id,
        "ISOLATED_TEST_TOKEN": token,
        "ISOLATED_TEST_DATABASE": str(database),
        "ISOLATED_TEST_MEDIA_ROOT": str(media),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
    }
    command = [sys.executable, "manage.py", "test", *TEST_LABELS, "--verbosity=2"]
    print(f"Owned isolated SQLite: {database}")
    print(f"Owned isolated MEDIA_ROOT: {media}")
    print(f"Environment run ID: {run_id}")
    try:
        result = subprocess.run(command, cwd=BACKEND_ROOT, env=env, check=False)
        return result.returncode
    finally:
        resolved = run_root.resolve(strict=True)
        if resolved.parent != temp_parent or not resolved.name.startswith("sunjack-iss028-035-"):
            raise RuntimeError("refusing cleanup: isolated test root identity changed")
        shutil.rmtree(resolved)
        print("Removed only this script's owned temporary SQLite and MEDIA_ROOT.")


if __name__ == "__main__":
    raise SystemExit(main())
