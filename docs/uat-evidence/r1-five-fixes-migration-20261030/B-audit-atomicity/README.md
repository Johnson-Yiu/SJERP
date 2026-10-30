# B — ISS-006 收货、发货及冲销审计原子性

- 统一基线：`bd324a8c3fb64af245c3afcabbd4301c84f7711c`
- 新分支：`codex/r1-iss006-audit-atomicity-bd324-20261030`
- 来源工作树：`codex/r1-iss006-audit-atomicity-20261029`，原 HEAD `dfa36058206fe7021ff6e6192fbbd247fb471947`；未提交的源码和测试分别保存在本任务原始补丁备份中。
- 迁移适配：新基线已包含 ISS-006 幂等履约实现；保留该实现，只移植并适配收货/发货状态快照及冲销审计事务，不覆盖基线代码。

## 验收

使用 `backend/requirements.lock` 锁定依赖、一次性 SQLite 测试库和隔离 MEDIA_ROOT。

- `crm.tests.test_fulfillment_audit_atomicity`、`crm.tests.test_fulfillment`、`crm.tests.test_inventory_movement_reversal`：52 项通过，0 失败。
- 验证收货部分/完成状态、最终发货状态的 before/after 快照；对收货、发货、冲销分别注入审计写入异常，确认库存流水、业务记录/状态及幂等键均随事务回滚。
- Django system check：通过。

日志位于 `logs/`：`locked-dependencies.log`、`system-check.log`、`backend-targeted.log`。预期注入的数据库异常会出现在测试日志中，对应测试断言通过。

此处 SQLite 测试验证事务行为，不构成 PostgreSQL 并发证明。未连接生产服务；未运行 GitHub Actions。
