"""Run preflight-only acceptance using the existing isolated recovery drill."""
import argparse
import json
import os
import runpy
import secrets
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--postgres-bin", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if os.environ.get("APP_STAGE", "development") != "development" or (
        os.environ.get("DATABASE_URL") and not os.environ["DATABASE_URL"].startswith("sqlite://")
    ):
        parser.error("Parent requires development and an isolated SQLite URL")
    evidence = Path(__file__).resolve().parent
    backend = evidence.parents[2] / "backend"
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    os.environ.update(DATABASE_URL="sqlite:///:memory:", DJANGO_SETTINGS_MODULE="config.settings",
                      PYTHONPATH=str(evidence), PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1",
                      HISTORY_PROBE_PASSWORD=secrets.token_urlsafe(28), HISTORY_PROBE_OUTPUT=str(output))
    sys.path.insert(0, str(backend))
    import django
    django.setup()
    from crm.services.postgres_drill_backup import IsolatedPostgresDrill
    original_manage = IsolatedPostgresDrill._manage
    original_restore = IsolatedPostgresDrill.restore

    def manage(drill, *command):
        if command != ("shell", "--no-imports", "-c", "from crm.tests.iss018_drill_fixture import seed; seed()"):
            return original_manage(drill, *command)
        fixture = json.loads(original_manage(drill, "shell", "--no-imports", "-c",
            "import os; from probe import seed; seed(os.environ['HISTORY_PROBE_PASSWORD'], os.environ['HISTORY_PROBE_OUTPUT'])"))
        os.environ["HISTORY_PROBE_SESSIONS"] = json.dumps(fixture.pop("sessions"))
        print(json.dumps(fixture.pop("checks"), ensure_ascii=False), flush=True)
        return json.dumps(fixture)

    def restore(drill, **kwargs):
        restored = original_restore(drill, **kwargs)
        result = drill._manage_database(restored["database"], restored["media"], "shell", "--no-imports", "-c",
            "import json, os; from probe import verify_restore; verify_restore(json.loads(os.environ['HISTORY_PROBE_SESSIONS']))")
        print(result.strip(), flush=True)
        return restored

    IsolatedPostgresDrill._manage = manage
    IsolatedPostgresDrill.restore = restore
    script = backend / "isolated_postgres_drill.py"
    sys.argv = [str(script), "--postgres-bin", str(args.postgres_bin.resolve(strict=True))]
    runpy.run_path(str(script), run_name="__main__")


if __name__ == "__main__":
    main()
