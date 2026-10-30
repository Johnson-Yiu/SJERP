# E — ISS-052 PostgreSQL TRUNCATE 防护

- 统一基线：`bd324a8c3fb64af245c3afcabbd4301c84f7711c`
- 新分支：`codex/r1-iss052-pg-truncate-bd324-20261030`
- 来源工作树：`codex/r1-iss052-pg-audit-appendonly-20261029`，原 HEAD `315d50cb2a80c882ea901181da1d5910bc6a80f3`；仅迁移新的 0093 迁移、测试运行器兼容和 PostgreSQL 专项测试，没有重写 0088/0089。

## 验收

使用 `backend/requirements.lock` 锁定依赖、一次性 SQLite 测试库和隔离 MEDIA_ROOT。

- `crm.tests.test_postgres_csv_import_audit crm.tests.test_safe_csv_import crm.tests.test_audit`：34 项，27 项通过、7 项 PostgreSQL 专项跳过、0 失败。
- SQLite 验证 0093 迁移正反向往返保留既有审计行；测试运行器对已安装防护的 PostgreSQL FLUSH SQL mock 验证通过。
- Django system check：通过；`makemigrations --check --dry-run`：无未生成迁移。
- PostgreSQL 的 UPDATE、DELETE、TRUNCATE 触发器保护测试保留在测试集中，未以 SQLite 结果代替。

## PostgreSQL 状态：BLOCKED

当前环境无可用 PostgreSQL 服务/客户端；7 项仅 PostgreSQL 测试被跳过，真实 UPDATE/DELETE/TRUNCATE 拒绝行为及数据库迁移部署验证仍待 PostgreSQL 环境完成。

日志位于 `logs/`：`locked-dependencies.log`、`system-check.log`、`makemigrations-check.log`、`truncate-and-audit-tests.log`、`postgres-tools.txt`。

未连接生产服务；未运行 GitHub Actions。
