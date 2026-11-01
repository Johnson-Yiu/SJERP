# R1-POSTGRES-TEST-ISOLATION-01 验收记录

日期：2026-11-01
仓库：`Johnson-Yiu/SUNJACK-ERP`
基线：`codex/fix-unified-ci-env-20261101` @ `cd479ea5ad7cd923f5b1798c0f296f960ae46dae`
分支：`codex/r1-postgres-test-isolation-20261101`
代码提交：`34985cc8db0837e6257352ae39553c48e529091b`

## 调查结论

Django 6.0.6 的 `TransactionTestCase._fixture_teardown()` 会调用 Django `flush` 管理命令；该命令经数据库后端 `execute_sql_flush()` 执行清理。PostgreSQL 后端的 flush SQL 使用 `TRUNCATE ... CASCADE`，会触发 CRM 0094 中 CSV 导入批次、行审计及预览审计表的 TRUNCATE 拒绝触发器。结果是测试 teardown 被生产审计 append-only 保护阻断。

## 修复与安全边界

- 在 `backend/crm/test_runner.py` 的测试 runner 中，短暂包装 Django `BaseDatabaseOperations.execute_sql_flush()`。只有 PostgreSQL 且 Django 实际生成的测试库名严格等于 `test_{原数据库名}`、`TEST.NAME` 未显式指定、当前连接名与记录的测试库名相等时，才启用清理例外；显式配置库、SQLite、原库及其他数据库不满足条件。
- 仅在该测试库上清理三张 CSV 审计表时，于同一个数据库事务中暂时禁用对应的 TRUNCATE guard、执行原始 Django flush、随后重新启用 guard。失败时事务回滚，不能留下保护关闭的状态。
- 例外只在 Django 的 flush 清理钩子中生效。应用或安全测试直接发出的 SQL 不经过该钩子，仍由数据库触发器拒绝。
- `0094` 迁移文件未修改；没有改动 ISS-006 业务代码或其专属测试文件。
- 原始 SQL 安全回归使用 `TRUNCATE ... CASCADE`，确保在外键环境下测试确实到达审计保护触发器，而不是先被外键依赖拦截。UPDATE、DELETE、TRUNCATE 的拒绝断言均保留。

## 验收结果

| 验收项 | 结果 | 证据边界 |
|---|---|---|
| Django system check / migration check / 迁移应用 | PostgreSQL 17 Job 均通过 | GitHub Actions 运行 #41316871320 |
| CSV 审计表清理及恢复保护 | 全量 PostgreSQL 测试中无该新增回归失败；回归执行两次 flush，逐次检查三表为空、原始 TRUNCATE 仍拒绝，并复用合成用户/文件哈希/业务键且计数为 1 | 同一完整 PostgreSQL 测试 Job；不是另一个单测 Job |
| CSV 审计原始 SQL UPDATE / DELETE / TRUNCATE 拒绝 | 测试无失败；PostgreSQL 日志可见触发器拒绝信息 | 数据库日志中的拒绝语句是安全测试预期，不代表测试失败 |
| `test_csv_import_audit_migration_rollback` | 全量 PostgreSQL 测试失败清单未列出该测试 | 单独迁移回滚路径没有单独 Job |
| `test_postgres_concurrency` / `test_cash_events` | 全量 PostgreSQL 测试失败清单未列出目标测试；并发专项日志正常输出 | 仅报告此次全量 Job 中未见目标失败，不声称独立专项命令通过 |
| 后端全量测试（标准 CI 数据库） | 1068 项通过，20 项跳过 | Backend Job #124878662428 |
| 后端全量测试（PostgreSQL 17） | 1068 项，10 failures、50 errors、1 skipped；因此 Job 失败 | Backend-PostgreSQL Job #124878662673；下列剩余问题与本清理改动不在同一修复范围 |
| 前端 Node 单测 / Node-only / Vitest | 通过 | Frontend Job #124878662682 各步骤已 completed/success |
| 前端隔离 Playwright / 生产构建 | 截至报告提交时仍运行中 / 尚未开始 | Frontend Job #124878662682；GitHub 尚未给出步骤日志或最终结论，不能记为通过 |
| 本地隔离 SQLite 定向回归 | 41 项，17 项因 PostgreSQL 专属而跳过；其余通过 | 不作为 PostgreSQL 验收的替代 |
| 本地静态检查 | `manage.py check`、`makemigrations --check --dry-run`、相关 Python 编译、`git diff --check` 通过 | 使用隔离 SQLite；无迁移变更 |

PostgreSQL Job 的全量失败清单中，50 个 error 主要由多个既有测试 fixture 写入超过 `varchar(2)` 的国家/地区代码，以及 ISS-018 备份/恢复测试在 PostgreSQL 缺少绑定数据库与文件系统快照时触发的安全拒绝导致；10 个 failure 主要是 staging 匿名响应码与测试断言不一致、跟进操作人旧断言，以及 ISS-018 测试断言期待绕过该安全拒绝。不得将 PostgreSQL 全量标记为通过，也未为本任务修改这些范围外行为。

## CI 记录

- 最终代码 SHA `34985cc8db0837e6257352ae39553c48e529091b` 对应 [GitHub Actions #41316871320](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41316871320)。
- [Backend Job #124878662428](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41316871320/job/124878662428)：1068 项通过，20 项跳过。
- [Backend-PostgreSQL Job #124878662673](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41316871320/job/124878662673)：PostgreSQL 17 服务、检查及迁移通过，测试 10 failures、50 errors、1 skipped，Job failure。
- [Frontend Job #124878662682](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41316871320/job/124878662682)：Node 单测、Node-only、Vitest 和浏览器依赖安装步骤通过；截至本报告提交时，隔离 Playwright 仍 `in_progress`，生产构建 `pending`。本报告不等待/伪报未结束的步骤。
- 前一轮在改正原始 TRUNCATE 回归语句之前，PostgreSQL Job #124875573375 记录 1067 项、13 failures、50 errors、1 skipped。将安全测试改为 `TRUNCATE ... CASCADE` 后，相关安全测试不再列入失败项；其余全量失败仍须独立处理。

## 范围与后续

只修改测试 runner 和 CSV 审计 PostgreSQL 专项测试。无迁移修改、无生产审计保护放宽、无 ISS-006 文件改动。PostgreSQL 全量 CI 仍为失败，需分别跟进测试 fixture 的字段长度、staging 身份响应断言与 ISS-018 快照测试契约；在此之前不能宣称 PostgreSQL CI 完整通过。未合并 master、未创建 PR、未部署。
