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

### 2026-10-31 并发测试夹具补修

来源：本分支后续修复提交 `61d857c213d832101a19ca5ed13a16f9d7832107`（本轮起始 HEAD `94402f951e4d4243276f018cc3a6051f0f6f2c57`）。`PurchaseOrderItem.save()` 在 `cost_allocation_version=0` 时已自动创建默认成本分配；两个 PostgreSQL 并发场景不再重复手动插入。每个场景现断言成本分配恰有一条，且 `target_type=order`、销售订单归属正确、数量与采购明细一致。生产代码未修改。

使用 `backend/requirements.lock` 对应的 Python 3.14.5 环境，在一次性内存 SQLite 数据库运行：

```powershell
python manage.py test crm.tests.test_postgres_concurrency crm.tests.test_fulfillment crm.tests.test_inventory_movement_reversal crm.tests.test_iss006_idempotency crm.tests.test_purchase_costs --verbosity 2
```

结果：74 项发现，61 项通过，13 项跳过，0 项失败。跳过项包括 `test_same_purchase_order_different_sku_receipts_serialize_status_and_reservations`、`test_receipt_and_reversal_race_keeps_purchase_stock_and_reservations_consistent` 及其余 PostgreSQL 专项；**不得把跳过计为 PostgreSQL 并发通过**。收货/冲销、库存流水、实际库存、预留和成本分配相关 SQLite 回归通过。原始日志：[fixture-repair-20261031.log](logs/fixture-repair-20261031.log)。

本机没有 `psql`、`pg_isready`、`postgres` 或 Docker 命令，也没有 PostgreSQL Windows 服务；`127.0.0.1:5432` 未监听。真实 PostgreSQL 两个并发场景仍为 **BLOCKED**。PostgreSQL 可用后须执行两个目标用例，并核对采购单状态、库存、收货记录、库存流水和预留数据。

未连接生产服务；未运行 GitHub Actions。
