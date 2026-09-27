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
- 完整 backend：`320 tests`，`316 PASS`，`4 skipped`（PostgreSQL-only concurrency tests，新增 through-table sanity test）。
- settings isolation tests：8/8 PASS。
- 前端：unit `61/61`、node-only `1/1`、Vitest `31/31`、build PASS。

## 4. First PostgreSQL CI failure

第一次 PostgreSQL CI：`36322185884`。

结果：SQLite `319/319 PASS`（3 个 PostgreSQL-only skipped）；`backend-postgres` 运行 316 tests，`1 failure / 75 errors`。失败分类为：POSTGRESQL COMPATIBILITY BUG（FOR UPDATE 与 nullable outer join、DISTINCT 与 FOR UPDATE）、TEST ASSUMPTION（Supplier.code 超过 max_length=2）、TEST ENVIRONMENT/HARNESS（development-only export test 环境未声明完整、reset_sequences 导致 sequence reset 问题）。本轮不放宽业务断言。

第二次 PostgreSQL CI：`36325725537`。结果为 `1 error / 1 failure`。失败根因已确认是 `HSMigrationTests` 的测试隔离问题：测试将 schema 降级到 0053 后，`finally` 只恢复到固定的 0053，污染了后续 PostgreSQL `TransactionTestCase`；这不是 migration 本身失败，也不是业务逻辑失败。主流程 `migrate --noinput` 已成功迁移至 0066。修复方式是在降级前保存当前 `crm` migration graph 的 `leaf_nodes("crm")`，测试结束时恢复该最新 leaf。

修复后的验证 CI：`36326712291`。`backend` 与 `frontend` PASS；`backend-postgres` 的 migration、schema check 均 PASS，测试仅剩 1 个 harness fixture error：并发成本测试直接调用 service 时传入字符串数量，触发 `Decimal + str`，与 API serializer 的正常输入契约不一致。已将 fixture 改为 `Decimal("100")`，等待下一次 CI 验证。

## 5. PostgreSQL CI job

`.github/workflows/ci.yml` 新增独立 `backend-postgres` job：

- PostgreSQL service：`postgres:17`。
- database：`sunjack_ci`；user/password：`postgres/postgres`。
- `pg_isready` health check。
- `APP_STAGE=staging` 与 PostgreSQL `DATABASE_URL`。
- 顺序执行 `check`、`makemigrations --check --dry-run`、`migrate --noinput`、完整 `manage.py test`。
- 原有 `backend` SQLite job 和 `frontend` job 保留不变。

本机没有 Docker 或 `psql`，因此不能在本地启动 PostgreSQL service；PostgreSQL 完整结果必须以 GitHub Actions `backend-postgres` job 为准。当前记录不把 SQLite 结果冒充 PostgreSQL 结果。

## 6. PostgreSQL-specific concurrency tests

新增 `backend/crm/tests/test_postgres_concurrency.py`，使用 `TransactionTestCase`、独立线程数据库连接，并在 SQLite 上明确 skip：

1. `allocate_root_quote_no()`：5 个并发 worker，验证初次 sequence row 创建、编号唯一且连续。
2. `allocate_revision_quote_no()`：5 个并发 worker，验证 revision counter 与 child suffix 唯一且连续。
3. `save_costs()`：两个独立 transaction 使用同一 version，预期一个成功、一个 stale version 拒绝，最终 version 为 1。

新增 supplier M2M through-table sanity assertion，使用 Django introspection 获取 through model 的实际表名；同时确认 `crm_product` 存在 `Product.combination_rules` 对应列；不写死 SQL 表名。

本地 SQLite 运行结果为 4 skipped；PostgreSQL-only 四个测试在 SQLite 上不执行，最终 PostgreSQL 执行结果以修复后的 CI 为准。

## 7. Lock-query compatibility audit

| 位置 | 原因 | 修复方式 |
|---|---|---|
| `finance.py:record_transaction` | PaymentPlan 的 order/purchase_order nullable，select_related 会生成 outer join | 先锁 PaymentPlan，再按非空 FK 单独锁 Order/PurchaseOrder，并锁 customer/supplier |
| `finance.py:allocate_advance` | 同上 | 同样的两阶段锁 |
| `finance.py:approve_contract_change` | ContractChangeRequest 的 order/purchase_order nullable | 先锁变更单，再单独锁实际 contract |
| `fulfillment.py:reverse_receipt` | GoodsReceipt.inventory_movement、PurchaseOrderItem.supplier_sku nullable | 先锁 receipt、purchase item、SKU；存在时单独锁原 movement |
| `fulfillment.py:reverse_shipment` | ShipmentItem.inventory_movement nullable | 锁 Shipment → Order → ShipmentItem；收集 movement IDs 后单独锁 InventoryMovement；再锁 SKU |
| `sku_plans.py:apply_category_attribute_reorder` | DISTINCT + FOR UPDATE | 先 distinct 得到 Product IDs，再锁 Product base rows |
| `supplier_allocation.py:allocate_order_item_supplier` | OrderItem.supplier_sku nullable | 锁 OrderItem 时只 join 非 nullable order/sku |

锁没有被删除，且在验证到创建 reversal/更新成本前仍覆盖主体与实际关联行。

## 8. Compatibility and migration status

- 本轮没有新增业务 schema migration。
- 本轮没有执行 SQLite → PostgreSQL 数据迁移。
- 没有连接当前开发库以外的数据库，也没有导出或修改 UAT 数据。
- 静态审计未发现需立即重写的历史 migration；第一次 PostgreSQL CI 已确认 `migrate --noinput` 成功至 0066，第二次失败属于测试 harness 隔离，修复后的最终 CI 结果待确认。
- `UniqueConstraint`、JSONField、DecimalField、timezone、bulk 操作的完整 PostgreSQL 验证等待同一 CI suite。
- `DATA-MIGRATION-RISK-01`：SQLite 不严格执行 varchar 长度；Phase 4B-2 前必须扫描真实开发库 `Supplier.code` 长度是否超过 2。若存在，必须人工映射为合法二字代码，禁止静默截断；本轮不修改开发数据库。

## 9. Findings

- `REAL BUSINESS BUG-PG`：0（本轮只修复已确认的 PostgreSQL query compatibility，不改变业务规则）。
- `POSTGRESQL COMPATIBILITY BUG`：第一次 CI 确认的 2 类 query compatibility 问题已完成代码修复，最终 CI 结果待确认。
- `TEST HARNESS / MIGRATION TEST ISOLATION`：已完成修复（恢复到测试开始前保存的最新 migration leaf），最终 CI 结果待确认。
- `DATA/MIGRATION ISSUE`：0（未执行 data migration）。
- `CONCURRENCY BUG`：0（本地只运行 skip；未把未运行当作通过）。
- 当前不具备进入 data-migration rehearsal 的条件，必须先取得 PostgreSQL job 全绿并完成 staging restore/row-count/金额/库存校验。

## 10. Scope boundary

本轮不开始 Authentication、RBAC、production security、data migration rehearsal 或任何 Phase 4B-2 工作。

