# ISS-018 PostgreSQL 17 isolated joint backup/restore — 2026-11-03

## Scope and status

The real PostgreSQL synthetic drill passed on code commit `98d5dfebcd84b1eccf222c18c76d2b6e8d3d72a6`; the later evidence-only commit is the delivery HEAD. This does **not** close ISS-018 or establish production readiness. The new adapter is deliberately restricted to a fresh local task-owned cluster and is not a production backup command. The original SQLite implementation and its PostgreSQL fail-closed check remain unchanged.

This delivery remains **BLOCKED for full operational acceptance**: the media gate controls only cooperating writers in the drill process, not arbitrary external OS writers; production-wide quiescence and independent storage/ACL controls have not been proven. The injected failures were checked as Python exceptions in the test runner; individual command-line nonzero exit codes and a standalone operator-facing PostgreSQL command were not demonstrated. Do not use this drill adapter as a production procedure.

## Isolation and tested versions

- Local, newly initialized synthetic cluster: `C:\Users\Johnson\AppData\Local\Temp\sunjack-iss018-pg17-d26bfa744cf54322af03ea964e90089f\cluster-host`, loopback `127.0.0.1:55483`; no shared or production database or media was used.
- PostgreSQL server, `pg_dump` and `pg_restore`: 17.11; Django 6.0.6. EDB portable binary archive SHA256 `80379b2c04d51c30225532e0ae04509899141e9957ed096fe749d7fd9df8f82f` was compared with EDB's published checksum.
- Source `iss018_src_4d7f6ae495764c3e`, independently created target `iss018_dst_80e288f003244b2e`, distinct task-owned media directories. Archive SHA256 `2e67cef368938605ca08263153e06caef0425c4ff49f27840d5986e472f2d675`; SHA is independently passed to restore. 118 applied migrations compared. Credentials were kept out of archive, command arguments and logs.
- No GitHub Actions workflow or run was needed: a real local PG17 was available. Consequently there is no workflow run URL or CI result for this drill.

## Real drill results

Raw log: `logs-02/business-drill-02.log` (one integration test, passed in 48.991 s). Database snapshot comparison includes every selected business row, sequence values, foreign-key definitions and enabled triggers; it compares source against restored target, including actual amounts, quantities and historical snapshot fields rather than recalculating them. The synthetic set includes 2 users, 2 customers, 1 supplier, SKU, product, quote and line, order and line, purchase order and line, payment plan, transaction, receipt, inventory movement, reservation, cost allocation, follow-up and attachment, 4 operation logs and one each CSV preview, batch and row audit.

Three synthetic files totaling 95 bytes matched their size and SHA256 manifests; manifest hash `368b406b403b813afb9ef8fa8b0d2493092ebdecd4d09417dd198740e7dc6fdb`. The application running against the restored database and media returned authorized attachment 200, historical image 200, anonymous 403, unauthorized 404, and old public path 404. This is not an assessment of production proxies, CDNs, object storage or NTFS ACLs.

The drill holds PostgreSQL table locks and an exported snapshot while copying media. A competing database update timed out on its lock, and the controlled media writer could not pass the in-process gate until the backup finished. Before/after media manifests were compared. These observations establish the controlled synthetic scenario only; they do not prove that unrelated filesystem processes are stopped.

Restored operation/CSV audit records rejected raw SQL UPDATE and DELETE; CSV audit tables also rejected TRUNCATE. Audit protections were not disabled. Source and target migration lists were compared, and restored private-media HTTP access was exercised with distinct authenticated synthetic sessions.

Failure injections asserted rejection of an incorrect archive hash, modified manifest, version mismatch, missing media member, unowned database target, failed `pg_restore`, and interrupted `pg_dump`. The restore-created database was removed on restore failure, no final archive was added on injected backup failure, and source fixture data remained unchanged. These are exception-level checks within the passing runner, not individually executed CLI failure tests. Backup took 4.245 s and restore 3.123 s for this tiny synthetic set; these timings are not production RTO claims.

## Reproduction and logs

Prepare a new isolated PostgreSQL 17 cluster under a fresh temporary directory named `sunjack-iss018-pg17-*`, with its cluster at `cluster-host`, binaries at `pgsql/bin`, and a dedicated non-default loopback port. Provision a synthetic cluster-only user/password, place the password in a restricted temporary file, and never expose it in command arguments or logs. Do not reuse a business cluster. From the clean checkout of the code commit, in PowerShell and from `backend`, set `ISS018_DRILL_ROOT`, `ISS018_DRILL_PASSWORD_FILE`, `ISS018_DRILL_PORT`, `ISS018_DRILL_APP_SHA=(git rev-parse HEAD).Trim()`, `MEDIA_ROOT` to an isolated directory, and `DATABASE_URL=sqlite:///:memory:`; then run `python manage.py test crm.tests.test_postgres_drill_backup --verbosity 2`. The default Django test database is unused; the actual source and restore operations use the dedicated PostgreSQL cluster. Stop the temporary cluster after use. This test harness is not a production operator runbook.

- `logs-02/business-drill-01.log`: earlier successful real business drill at `8f6f09990b37d9ad1b278e4945182551af212d0d`.
- `logs-02/business-drill-02.log`: final code test, above.
- `logs-02/sqlite-regression.log`: 22 tests, 19 passed and 3 skipped on Windows (POSIX permissions/symlink limitations); skips are not passes. Includes the existing PostgreSQL fail-closed boundary test.
- `logs-02/check.log`: Django system check passed.
- `logs-02/migrations-check.log`: `makemigrations crm --check --dry-run`, no changes.

The first early PG attempt exposed an address-format comparison error (`127.0.0.1/32` versus `127.0.0.1`); it was corrected in `a9f80b68953116d75f339cd1210d452517f71bdc` and the real drill rerun. Its initial console output was not archived as a raw log.

## Remaining acceptance

An independently enforced multi-process write pause covering every application, worker and filesystem writer; operator-facing failure exit-code tests; production configuration/secret custody, permissions and external digest handling; backup scheduling, retention, offsite copies, recovery tests against approved production-like infrastructure, and proxy/CDN/storage ACL checks remain outstanding. Do not change shared issue status or infer a production readiness decision from this synthetic drill.
