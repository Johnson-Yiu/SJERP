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

    temp_root = _resolved(tempfile.gettempdir(), label="system temp")
    root = _resolved(env["ISOLATED_TEST_ROOT"], label="isolation root")
    try:
        root.relative_to(temp_root)
    except ValueError as exc:
        raise IsolationError("Isolation root is outside the system temp directory.") from exc
    if root == temp_root:
        raise IsolationError("Isolation root cannot be the system temp directory itself.")

    marker_path = root / ".sunjack-playwright-isolation.json"
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

    expected_database = _resolved(root / "db.sqlite3", label="expected database")
    configured_database = _resolved(env["ISOLATED_TEST_DATABASE"], label="declared database")
    expected_media = _resolved(root / "media", label="expected media root")
    configured_media = _resolved(env["ISOLATED_TEST_MEDIA_ROOT"], label="declared media root")
    if configured_database != expected_database:
        raise IsolationError("Declared database is not this run's isolated SQLite file.")
    if configured_media != expected_media:
        raise IsolationError("Declared MEDIA_ROOT is not this run's isolated media directory.")
    if configured_database.is_symlink() or configured_media.is_symlink():
        raise IsolationError("Database and MEDIA_ROOT must not be symlinks.")

    if settings is not None:
        if getattr(settings, "APP_STAGE", "") != "development":
            raise IsolationError("Isolated browser tests require Django APP_STAGE=development.")
        if getattr(settings, "RBAC_ENFORCEMENT", False):
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
        actual_database = _resolved(configured_name, label="configured database")
        if actual_database != expected_database:
            raise IsolationError(
                "Django is configured for a database outside this run's isolation root "
                f"(Django NAME={configured_name!r}, actual={actual_database}, expected={expected_database})."
            )
        actual_media = _resolved(settings.MEDIA_ROOT, label="configured MEDIA_ROOT")
        if actual_media != expected_media:
            raise IsolationError("Django is configured for a MEDIA_ROOT outside this run's isolation root.")

    if database_must_exist and (not expected_database.is_file() or expected_database.is_symlink()):
        raise IsolationError("Isolated SQLite database was not created as a regular file.")
    if expected_media.exists() and (not expected_media.is_dir() or expected_media.is_symlink()):
        raise IsolationError("Isolated MEDIA_ROOT is not a regular directory.")
    return {
        "runId": env["ISOLATED_TEST_RUN_ID"],
        "token": env["ISOLATED_TEST_TOKEN"],
        "database": str(expected_database),
        "mediaRoot": str(expected_media),
    }
