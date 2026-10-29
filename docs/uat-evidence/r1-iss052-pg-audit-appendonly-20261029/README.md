# R1-ISS052 PostgreSQL CSV 审计追加保护

## 验收状态

- SQLite 代码与迁移回归：**PASS**。
- PostgreSQL 原始 SQL 触发器验收：**BLOCKED**。本地没有 PostgreSQL 客户端/服务；未运行、未连接 PostgreSQL，因此不声称触发器已通过 PostgreSQL 验证。待 CI 恢复后执行。
- 生产数据库：未连接。

## 基线与范围

- 目标分支：`codex/r1-iss052-pg-audit-appendonly-20261029`
- 起点：`codex/r1-review-iss052-csv-audit-20261029`，SHA `27734334833395196ae9951c5409f87c3574655d`（该审查分支基于集成 SHA `bd324a8c3fb64af245c3afcabbd4301c84f7711c`）。
- 本轮检查：`0091_csv_import_audit.py`、CSV 审计模型及现有 ORM 防修改测试。
- 未改写 `0091`；未修改批次/行审计模型及历史数据；未触发 GitHub Actions、未合并 master、未部署。

## 发现与修复

`0091` 现有 PostgreSQL 触发器为 `BEFORE UPDATE OR DELETE ... FOR EACH ROW`。`TRUNCATE` 是语句级事件，不会逐行触发这些保护，因此原有保护可被原始 `TRUNCATE` 绕过。

新增 `backend/crm/migrations/0093_csv_import_audit_truncate_guard.py`，依赖现有合并迁移 `0092_merge_fulfillment_and_csv_audit`。它仅为 `CSVImportBatch` 和 `CSVImportRowAudit` 各安装 `BEFORE TRUNCATE ... FOR EACH STATEMENT` 触发器；触发器以 SQLSTATE `42501` 拒绝操作。前向迁移没有 INSERT/UPDATE/DELETE，也不重写 `0091`。反向迁移仅移除这两个 TRUNCATE 触发器及其函数，不删除或改写审计记录。

新增 `backend/crm/tests/test_postgres_csv_import_audit.py`：

- 六项 PostgreSQL 专项测试分别验证两张表的原始 SQL `UPDATE`、`DELETE` 和 `TRUNCATE` 被触发器拒绝，并校验 SQLSTATE 为 `42501`，避免将外键等其他拒绝原因误判为触发器通过。
- 批次删除测试使用没有行子记录的批次，避免外键约束造成假阳性；批次 `TRUNCATE ... CASCADE` 测试会在隔离测试事务内暂时禁用行表触发器，以证明批次表自身的保护生效。
- 迁移往返测试在迁移前创建批次和行审计，向后迁移到 `0092`、再前向迁移至 `0093`，逐字段比较两条既有记录。该测试在本地 SQLite 上通过，只证明该后端上的迁移往返未改写数据，不证明 PostgreSQL DDL 或触发器有效。
- 新增测试运行器 SQL 生成单测，验证 PostgreSQL 测试库 flush 只在已安装的审计 TRUNCATE 触发器周围生成临时 DISABLE/ENABLE 语句。该 mock 单测通过，不替代真实 PostgreSQL 清理验证。

保留 `test_safe_csv_import.py` 中现有 SQLite ORM 级追加保护测试，没有删除或降低断言。由于 Django 的 PostgreSQL `TransactionTestCase` 清理使用 `TRUNCATE`，测试运行器在隔离 PostgreSQL 测试库执行 flush 时会在单个可回滚 flush 事务内暂时停用这两个触发器，并在清理后重新启用；该逻辑只在 PostgreSQL 测试运行器中启用，不作用于应用请求或生产数据库。此 PostgreSQL 清理路径同样等待恢复 CI 后验证。

## 本地验证

环境明确设置为 `APP_STAGE=development`，`DATABASE_URL` 指向 `%TEMP%` 下本轮专用 SQLite 测试数据库，`MEDIA_ROOT` 指向本轮专用临时目录；没有读取默认业务数据库连接，也没有连接生产数据库。

| 命令/检查 | 结果 |
|---|---|
| `python -B manage.py test crm.tests.test_postgres_csv_import_audit crm.tests.test_safe_csv_import crm.tests.test_audit --verbosity 1` | 34 项，27 通过，7 跳过，0 失败；退出码 0。跳过项为本文件 6 项 PostgreSQL 专项测试和既有 1 项 OperationLog PostgreSQL 触发器测试。 |
| SQLite 全新测试库迁移 | 成功应用至 `crm.0093_csv_import_audit_truncate_guard`；迁移往返数据保留测试通过。SQLite 的 PostgreSQL 分支按设计不创建触发器。 |
| `python -B manage.py check` | 通过，无系统检查问题。 |
| `python -B manage.py makemigrations --check --dry-run crm` | 通过，`No changes detected in app 'crm'`。 |
| `MigrationLoader(None).graph.leaf_nodes('crm')` | 唯一 CRM 迁移叶节点为 `0093_csv_import_audit_truncate_guard`。 |
| PostgreSQL 本地环境探测 | `psql`、`pg_isready`、`postgres`、`docker` 命令均不可用，未发现本地 PostgreSQL 服务。 |

## BLOCKED 后续验收

恢复 CI 后，在隔离 PostgreSQL 测试数据库运行：

```powershell
python -B manage.py test crm.tests.test_postgres_csv_import_audit crm.tests.test_audit --verbosity 2
```

确认 6 项 CSV PostgreSQL 原始 SQL 用例全部实际运行并通过；确认向前/反向迁移保留记录；确认 Django 测试库 flush 清理后触发器仍安装。CI 运行结果出来前，`0093` PostgreSQL DDL、SQLSTATE 行为和测试清理路径均为 **BLOCKED / 未验证**。
