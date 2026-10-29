"""Fail-closed identity checks for disposable Playwright API runtimes."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


class IsolationError(RuntimeError):
    """Raised when a browser test cannot prove it is using its own resources."""


def _resolved(value: str | os.PathLike[str], *, label: str) -> Path:
    try:
        return Path(value).expanduser().resolve(strict=False)
    except (OSError, RuntimeError, TypeError) as exc:
        raise IsolationError(f"Invalid {label} path.") from exc


def _absolute(value: str | os.PathLike[str], *, label: str) -> Path:
    try:
        return Path(os.path.abspath(Path(value).expanduser()))
    except (OSError, RuntimeError, TypeError) as exc:
        raise IsolationError(f"Invalid {label} path.") from exc


def verify_isolated_runtime(environ=None, settings=None, *, database_must_exist=False):
    """Verify process settings point only at this run's marked temp directory."""
    env = os.environ if environ is None else environ
    required = (
        "ISOLATED_TEST_ROOT",
        "ISOLATED_TEST_RUN_ID",
        "ISOLATED_TEST_TOKEN",
        "ISOLATED_TEST_DATABASE",
        "ISOLATED_TEST_MEDIA_ROOT",
    )
    missing = [key for key in required if not str(env.get(key, "")).strip()]
    if missing:
        raise IsolationError(f"Missing isolation identity: {', '.join(missing)}")
    if str(env.get("APP_STAGE", "")).strip().lower() != "development":
        raise IsolationError("Isolated browser tests require APP_STAGE=development.")
    rbac_test_mode = str(env.get("ISOLATED_TEST_RBAC_MODE", "")).strip()
    if rbac_test_mode not in {"", "iss055"}:
        raise IsolationError("Only the allowlisted ISS-055 isolated RBAC test mode is supported.")

    temp_root = _resolved(tempfile.gettempdir(), label="system temp")
    declared_root = _absolute(env["ISOLATED_TEST_ROOT"], label="isolation root")
    if declared_root.is_symlink():
        raise IsolationError("Isolation root must not be a symlink.")
    root = _resolved(declared_root, label="isolation root")
    try:
        root.relative_to(temp_root)
    except ValueError as exc:
        raise IsolationError("Isolation root is outside the system temp directory.") from exc
    if root == temp_root:
        raise IsolationError("Isolation root cannot be the system temp directory itself.")

    marker_path = declared_root / ".sunjack-playwright-isolation.json"
    if marker_path.is_symlink() or not marker_path.is_file():
        raise IsolationError("Isolation marker is missing or is not a regular file.")
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IsolationError("Isolation marker cannot be read.") from exc
    if (
        marker.get("runId") != env["ISOLATED_TEST_RUN_ID"]
        or marker.get("token") != env["ISOLATED_TEST_TOKEN"]
        or _resolved(marker.get("root", ""), label="marker root") != root
    ):
        raise IsolationError("Isolation marker does not match this process.")

    expected_database_path = declared_root / "db.sqlite3"
    configured_database_path = _absolute(env["ISOLATED_TEST_DATABASE"], label="declared database")
    expected_media_path = declared_root / "media"
    configured_media_path = _absolute(env["ISOLATED_TEST_MEDIA_ROOT"], label="declared media root")
    if configured_database_path != expected_database_path:
        raise IsolationError("Declared database is not this run's isolated SQLite file.")
    if configured_media_path != expected_media_path:
        raise IsolationError("Declared MEDIA_ROOT is not this run's isolated media directory.")
    if expected_database_path.is_symlink() or expected_media_path.is_symlink():
        raise IsolationError("Database and MEDIA_ROOT must not be symlinks.")
    expected_database = _resolved(expected_database_path, label="expected database")
    expected_media = _resolved(expected_media_path, label="expected media root")
    if expected_database.parent != root or expected_media.parent != root:
        raise IsolationError("Database and MEDIA_ROOT must resolve directly inside this run's isolation root.")

    if settings is not None:
        if getattr(settings, "APP_STAGE", "") != "development":
            raise IsolationError("Isolated browser tests require Django APP_STAGE=development.")
        enforcement = bool(getattr(settings, "RBAC_ENFORCEMENT", False))
        development_superadmin = str(env.get("DEVELOPMENT_SUPERADMIN", "0")).strip().lower() in {"1", "true", "yes", "on"}
        if rbac_test_mode == "iss055":
            if not enforcement:
                raise IsolationError("ISS-055 test mode requires controlled RBAC enforcement.")
            if development_superadmin:
                raise IsolationError("ISS-055 test mode must disable the development superadmin identity.")
        elif enforcement:
            raise IsolationError("Formal RBAC must remain disabled in this development test runtime.")
        if set(settings.DATABASES) != {"default"}:
            raise IsolationError("Isolated browser tests must not configure additional database connections.")
        if getattr(settings, "MEDIA_STORAGE_BACKEND", "") != "django.core.files.storage.FileSystemStorage":
            raise IsolationError("Isolated browser tests require local filesystem media storage.")
        database = settings.DATABASES.get("default", {})
        engine = database.get("ENGINE", "")
        if engine != "django.db.backends.sqlite3":
            raise IsolationError("Write-capable browser tests require the isolated SQLite backend.")
        configured_name = database.get("NAME", "")
        configured_name_path = _absolute(configured_name, label="configured database")
        if configured_name_path.is_symlink():
            raise IsolationError("Django database path must not be a symlink.")
        actual_database = _resolved(configured_name_path, label="configured database")
        if actual_database != expected_database:
            raise IsolationError(
                "Django is configured for a database outside this run's isolation root "
                f"(Django NAME={configured_name!r}, actual={actual_database}, expected={expected_database})."
            )
        configured_media_setting = _absolute(settings.MEDIA_ROOT, label="configured MEDIA_ROOT")
        if configured_media_setting.is_symlink():
            raise IsolationError("Django MEDIA_ROOT must not be a symlink.")
        actual_media = _resolved(configured_media_setting, label="configured MEDIA_ROOT")
        if actual_media != expected_media:
            raise IsolationError("Django is configured for a MEDIA_ROOT outside this run's isolation root.")

    if database_must_exist and (not expected_database.is_file() or expected_database.is_symlink()):
        raise IsolationError("Isolated SQLite database was not created as a regular file.")
    if not database_must_exist and expected_database.exists():
        raise IsolationError("Isolated SQLite database already exists before this run's migrations.")
    if expected_media.exists() and (not expected_media.is_dir() or expected_media.is_symlink()):
        raise IsolationError("Isolated MEDIA_ROOT is not a regular directory.")
    return {
        "runId": env["ISOLATED_TEST_RUN_ID"],
        "token": env["ISOLATED_TEST_TOKEN"],
        "database": str(expected_database),
        "mediaRoot": str(expected_media),
        "rbacEnforcement": bool(getattr(settings, "RBAC_ENFORCEMENT", False)) if settings is not None else False,
    }
