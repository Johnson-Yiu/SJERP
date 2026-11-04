# ISS-018 isolated PostgreSQL command acceptance — 2026-11-04

This is an **isolated synthetic exercise tool**, not a production backup or restore entry point. It creates and destroys a task-owned temporary PostgreSQL 17 cluster, a random source database and restore database, and task-owned media. It verifies the cluster identity before using the existing drill adapter. Never point it at a business server or use it as a production runbook. The existing `POSTGRES-02.md` and its Django 6.0.6 results remain historical evidence.

## Operation

In a clean backend checkout, install `backend/requirements.lock` into an isolated Python environment. From the repository root:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONUTF8 = '1'
python backend/isolated_postgres_drill.py --postgres-bin '<PostgreSQL 17 bin directory>'
```

The command copies those binaries to a fresh temporary root, generates a fresh credential without putting it on a command line, migrates a random synthetic source, seeds synthetic data, takes and checks a joint archive, restores into a random target, reconciles all public-table rows and media associations, then stops and deletes its own temporary cluster. JSON is emitted only after cleanup; exit 0 denotes completion. Failure emits nonzero and does not assert a successful target. Cleanup errors include the original error and the leftover task-owned path. No archive or secret is intended to persist after cleanup.

`--test-fault checksum|missing-media|corrupt|version|tool|environment` is for synthetic negative tests only; it intentionally returns nonzero. These switches do not simulate production backup or production recovery.

The previous business-level PostgreSQL regression can be repeated under a new command-owned cluster without changing the original test:

```powershell
$env:APP_STAGE = 'development'
$env:DATABASE_URL = 'sqlite:///:memory:'
python docs/uat-evidence/r1-iss018-backup-restore-drill-20261103/run-existing-drill.py --postgres-bin '<PostgreSQL 17 bin directory>'
```

This harness invokes the repository's existing `crm.tests.test_postgres_drill_backup` inside the temporary cluster; the original test's process-local media gate remains limited to cooperating writers. The command starts with a clean committed backend checkout and removes the entire owned cluster afterwards.

## Evidence and limitations

The locked environment is CPython 3.14.5, Django 6.0.9, PostgreSQL/pg_dump/pg_restore 17.11. Exact packages and checks are recorded in `logs-03/environment.log` and `logs-03/checks.log`. The first command success on implementation commit `d4859c5` returned exit 0, compared 82 public tables / 908 rows / 118 migrations and two media hashes, and reported cleanup complete (`logs-03/command-success.log`). The later commit preserving original errors during cleanup is subject to the full command suite recorded separately.

SQLite regression: `logs-03/sqlite-regression.log`, 22 tests, 19 passed and 3 skipped on Windows; the existing PostgreSQL fail-closed test passed. A first sandboxed attempt failed to start `pg_ctl`; a subsequent initial external attempt exposed inherited Windows output pipes, and its task-owned cluster was explicitly stopped and cleaned before the pipe fix. Neither failure is counted as a passing drill.

The first full command suite (`logs-03/command-all.log`) ran seven tests: six passed and the version case errored because cleanup did not complete and the test failed to print the returned cleanup details. The retained task-owned cluster had shut down and was partially removed; its remaining directory and synthetic credential were manually removed after checking that no associated PostgreSQL process remained. The precise cleanup cause was not preserved by that test and is **unknown**. A subsequent change records the whole returned result, verifies source media, and retries transient Windows permission failures within the same validated owned root. The subsequent suite and its actual outcome are recorded separately; the initial failure remains part of the evidence.

At code commit `c805cbed7140c50f0066acf8b2a84f3356ea7178`, the prior business-level regression was actually rerun under PostgreSQL 17.11 and locked Django 6.0.9: `logs-03/existing-pg-drill-locked.log`, one test, exit 0. The original test compared business data, migrations, foreign keys, sequences and audit triggers; checked controlled database and in-process media lock behavior; verified three media SHA256s and authenticated/anonymous HTTP results; and exercised its existing exception-level negative cases. The outer command then restored and compared 82 public tables and 908 rows, checked the source media remained unchanged and reported `cleanup=complete`. These results are synthetic and do not establish a production write pause.

`logs-03/cleanup-injection.log` records a separate synthetic unit injection: a missing binary followed by an intentionally failing directory removal retained the original error and exact task-owned path; the empty test directory was then removed by the test. It does not prove Windows ACLs or arbitrary operating-system failures.

The complete retry on code commit `c805cbed7140c50f0066acf8b2a84f3356ea7178` is in `logs-03/command-retry.log`: eight tests, exit 0, no skips. The command success case returned exit 0. Wrong SHA256, missing media, corrupt ZIP, incompatible PostgreSQL version, real `pg_restore` failure, and an unowned database environment each returned exit 1, with source database rows and media unchanged and task-owned cleanup complete. A production-stage environment returned exit 1 before creating a cluster. Each case ran as a separate subprocess; the seven PostgreSQL cases used newly created task-owned clusters.

Reproducible local commands, using the locked environment and a task-private `MEDIA_ROOT`:

```powershell
$env:DATABASE_URL = 'sqlite:///:memory:'
$env:APP_STAGE = 'development'
$env:ISS018_COMMAND_PG_BIN = '<PostgreSQL 17 bin directory>'
python backend/manage.py test crm.tests.test_iss018_drill_command --verbosity 2
python backend/manage.py test crm.tests.test_iss018_backup_recovery --verbosity 2
python docs/uat-evidence/r1-iss018-backup-restore-drill-20261103/test-cleanup-failure.py
python backend/manage.py check
python backend/manage.py makemigrations --check --dry-run
```

The SQLite rerun on the current code is `logs-03/sqlite-regression-final.log`: 22 tests, exit 0, three Windows-only skips. The results do not turn skipped cases into passes. Dependency recheck is `logs-03/lock-install.log`; `pip check`, Django check, and migration consistency succeeded in the captured logs.

The media gate only controls cooperating writers in the drill process. Arbitrary external writers are not paused. Production-wide quiescence, credential custody, production database/media permissions, independent encrypted offsite copies, scheduling/alerts, restore on approved production-like infrastructure and RPO/RTO remain **DEPLOYMENT_VERIFICATION_PENDING**. ISS-018 remains **BLOCKED**, with no production connection, deployment, formal RBAC activation or issue closure.
