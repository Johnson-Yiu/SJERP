# PostgreSQL snapshots — not captured

Status: BLOCKED. No isolated PostgreSQL instance was available, so the UAT did
not create a test database or execute business requests. There are no truthful
before/after database snapshots to attach. No SQLite snapshot is substituted.

Capture a clean pre-test snapshot and a post-test snapshot after PostgreSQL is
provisioned, using synthetic fixtures only. The post-test evidence should
include purchase/receipt/reversal rows, inventory movements, reservation and
in-transit quantities, purchase status, idempotency records, and audit rows.
