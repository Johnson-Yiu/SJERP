# Phase 4B-1 — PostgreSQL Runtime & CI Compatibility 执行记录

分支：`phase-04b-postgresql-runtime-ci`  
基线：`master` / `1759c02a66353d2db6f709fd3b3ab27b46e2fc1b`  
执行范围：仅 PostgreSQL runtime dependency、数据库环境选择、CI job、settings 测试和 PostgreSQL 并发测试；未修改业务模型、serializer、view、service、frontend，未迁移或清理开发数据库。

## 1. Runtime dependency

- 新增：`psycopg[binary]>=3.2,<4`。
- 未安装 `psycopg2` 或 `psycopg2-binary`。
- `dj-database-url` 继续负责 URL 解析。

## 2. Database settings contract

| APP_STAGE | DATABASE_URL | 结果 |
|---|---|---|
| development | 缺失 | SQLite `backend/db.sqlite3` |
| development | PostgreSQL URL | PostgreSQL engine |
| staging | PostgreSQL URL | PostgreSQL engine |
| production | PostgreSQL URL | PostgreSQL engine |
| staging/production | 缺失 | `ImproperlyConfigured: DATABASE_URL is required for staging/production.` |
| staging/production | SQLite URL | `ImproperlyConfigured: DATABASE_URL must use PostgreSQL for staging/production.` |

配置只在非 development 阶段拒绝 SQLite；没有改变开发 SQLite 工作流，也没有改变当前开发数据库。

## 3. SQLite verification

- `python manage.py check`：PASS。
- `python manage.py makemigrations --check --dry-run`：PASS，No changes detected。
- 完整 backend：`319 tests`，`316 PASS`，`3 skipped`（PostgreSQL-only concurrency tests）。
- settings isolation tests：8/8 PASS。
- 前端：unit `61/61`、node-only `1/1`、Vitest `31/31`、build PASS。

## 4. PostgreSQL CI job

`.github/workflows/ci.yml` 新增独立 `backend-postgres` job：

- PostgreSQL service：`postgres:17`。
- database：`sunjack_ci`；user/password：`postgres/postgres`。
- `pg_isready` health check。
- `APP_STAGE=staging` 与 PostgreSQL `DATABASE_URL`。
- 顺序执行 `check`、`makemigrations --check --dry-run`、`migrate --noinput`、完整 `manage.py test`。
- 原有 `backend` SQLite job 和 `frontend` job 保留不变。

本机没有 Docker 或 `psql`，因此不能在本地启动 PostgreSQL service；PostgreSQL 完整结果必须以 GitHub Actions `backend-postgres` job 为准。当前记录不把 SQLite 结果冒充 PostgreSQL 结果。

## 5. PostgreSQL-specific concurrency tests

新增 `backend/crm/tests/test_postgres_concurrency.py`，使用 `TransactionTestCase`、独立线程数据库连接，并在 SQLite 上明确 skip：

1. `allocate_root_quote_no()`：5 个并发 worker，验证初次 sequence row 创建、编号唯一且连续。
2. `allocate_revision_quote_no()`：5 个并发 worker，验证 revision counter 与 child suffix 唯一且连续。
3. `save_costs()`：两个独立 transaction 使用同一 version，预期一个成功、一个 stale version 拒绝，最终 version 为 1。

本地 SQLite 运行结果为 3 skipped；尚未声称 PostgreSQL concurrency PASS。

## 6. Compatibility and migration status

- 本轮没有新增业务 schema migration。
- 本轮没有执行 SQLite → PostgreSQL 数据迁移。
- 没有连接当前开发库以外的数据库，也没有导出或修改 UAT 数据。
- 静态审计未发现需立即重写的历史 migration；PostgreSQL `migrate` 结果等待 CI。
- `UniqueConstraint`、JSONField、DecimalField、timezone、bulk 操作的完整 PostgreSQL 验证等待同一 CI suite。

## 7. Findings

- `REAL BUSINESS BUG-PG`：0（本地未发现；PostgreSQL job 尚未返回）。
- `POSTGRESQL COMPATIBILITY BUG`：0（待 CI 验证）。
- `DATA/MIGRATION ISSUE`：0（未执行 data migration）。
- `CONCURRENCY BUG`：0（本地只运行 skip；未把未运行当作通过）。
- 当前不具备进入 data-migration rehearsal 的条件，必须先取得 PostgreSQL job 全绿并完成 staging restore/row-count/金额/库存校验。

## 8. Scope boundary

本轮不开始 Authentication、RBAC、production security、data migration rehearsal 或任何 Phase 4B-2 工作。

