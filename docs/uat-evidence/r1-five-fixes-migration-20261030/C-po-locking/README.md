# C — ISS-006 采购单并发收货锁定

- 统一基线：`bd324a8c3fb64af245c3afcabbd4301c84f7711c`
- 新分支：`codex/r1-iss006-po-locking-bd324-20261030`
- 来源工作树：`codex/r1-iss006-po-locking-20261029`，原 HEAD `083b99d1f3be5ed6796b71f7dfd5108b2fc12b3a`；只迁移履约服务和并发专项测试。

## 验收

使用 `backend/requirements.lock` 锁定依赖。服务调整为在变更收货前先锁定采购单，再锁定采购明细、关联销售单（按主键顺序）和 SKU；冲销采用一致的父单优先顺序。状态计算读取新的有效收货聚合，不在 SKU 锁之后追加父单锁。

- `crm.tests.test_fulfillment crm.tests.test_postgres_concurrency`：49 项运行通过，12 项 PostgreSQL 专项跳过。
- `crm.tests.test_inventory_movement_reversal crm.tests.test_iss006_idempotency`：16 项运行通过，1 项 PostgreSQL 专项跳过。
- 两个新增 `TransactionTestCase` 并发场景（同一采购单不同 SKU 收货；收货与冲销交叉）在 SQLite 上被明确跳过。
- Django system check：通过。

## PostgreSQL 状态：BLOCKED

当前环境没有可用的 PostgreSQL 服务/客户端，因此未验证真实行锁、死锁行为及并发最终状态。SQLite 结果仅验证兼容性，不作为 PostgreSQL 并发通过证据。恢复 PostgreSQL/CI 后必须运行两个专项场景，并核对采购单状态、库存、收货记录、库存流水和预留。

命令输出位于 `logs/`：`locked-dependencies.log`、`system-check.log`、`fulfillment-and-concurrency.log`、`reversal-and-idempotency.log`、`postgres-specific-two-tests.sqlite-skip-corrected.log`、`postgres-tools.txt`。另保留一次测试方法名拼写错误的早期尝试日志 `postgres-specific-two-tests.sqlite-skip.log`；更正后的运行结果以 `...-corrected.log` 为准。

未连接生产服务；未运行 GitHub Actions。
