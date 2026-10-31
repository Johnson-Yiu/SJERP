# R1-ISS006 PostgreSQL concurrency UAT

Date: 2026-11-01 (Asia/Shanghai)
Baseline: `bd324a8c3fb64af245c3afcabbd4301c84f7711c`
Branch: `codex/r1-iss006-postgresql-concurrency-uat-20261101`

## Result: BLOCKED — real PostgreSQL unavailable

The required UAT was not run. Local checks found no PostgreSQL service,
server/client binaries, container runtime, or reachable PostgreSQL listener on
`127.0.0.1:5432`. WSL was present, but its distro-list command returned usage
text with exit code 1; no usable WSL PostgreSQL instance was verified. See the
raw environment probe in `logs/00-postgresql-environment-check.log`.

To avoid risking an unknown or business database, no existing application
database URL was read or used, and no database connection was attempted. The
tests were not redirected to SQLite, and `connection.vendor` was not mocked.
No requested concurrency scenario has a PASS result. Since no test DB was
created, there are no database before/after snapshots; this is recorded in
[`snapshots/README.md`](snapshots/README.md). No business or audit rows were
created, and no product or test code was modified.

## Scenario disposition

| Scenario | Result | Evidence / reason |
|---|---|---|
| Concurrent receives against one purchase order | BLOCKED | Requires PostgreSQL row-lock behavior; no database available |
| Concurrent reversal of one goods receipt | BLOCKED | No PostgreSQL execution; sequential reversal tests are not a concurrency substitute |
| Receive and reversal at the same time | BLOCKED | No PostgreSQL execution |
| Duplicate request and timeout/retry behavior | BLOCKED | Existing sequential replay tests and one concurrent shipment replay test were inspected, not run; receive/reversal timeout races remain unverified |
| Final inventory, reservation, in-transit quantity and purchase status | BLOCKED | No post-run database state to inspect |
| No duplicate inventory movements | BLOCKED | No real concurrent requests executed |
| Audit/business transaction consistency | BLOCKED | No real transaction or audit rows created |

## Existing test coverage inspected (static only)

- `backend/crm/tests/test_iss006_idempotency.py` includes sequential receive
  replay, changed-payload conflict, distinct keys, failure rollback, and a
  PostgreSQL-only concurrent duplicate **shipment** request test.
- `backend/crm/tests/test_postgres_concurrency.py` includes a real PostgreSQL
  `TransactionTestCase` for receipt and shipment concurrently rebalancing one
  SKU, plus unrelated purchase-draft concurrency. It does not establish two
  receives racing on one purchase order or a receive racing its reversal.
- `backend/crm/tests/test_inventory_movement_reversal.py` and
  `backend/crm/tests/test_fulfillment.py` contain sequential reversal and
  inventory/reservation assertions; they are not PostgreSQL concurrency UAT.

This is a coverage observation, not a finding that the product code is
incorrect. The existing source references are retained in
[`logs/01-existing-test-coverage.log`](logs/01-existing-test-coverage.log).
Runtime locking, idempotency, audit atomicity, and final-state invariants all
remain **NEEDS VERIFICATION**.

## Next required step

Provision an explicitly disposable PostgreSQL instance/database, then rerun the
concurrency UAT using synthetic fixtures and independent worker connections.
Capture pre/post database snapshots and complete test/server logs. Cover the
seven scenarios above, including same-key retry after a simulated lost response
and audit counts tied to committed business operations. Do not point the run at
a developer-shared or production database.

No CI, PR, merge, deployment, or GitHub Issue closure was performed.
