# R1-ISS018-POSTGRES-BOUNDARY-01 验收记录

日期：2026-11-02

仓库：`Johnson-Yiu/SUNJACK-ERP`

分支：`codex/r1-iss018-postgres-boundary-20261102`

基线：`codex/r1-postgres-test-isolation-20261101` @ `e280e5d140b5255bd51f5d0be428f36e87336139`

测试代码提交：`0c326ba7e7bfb3c4022f57e9f5680ce1cffbfc93`

## 来源与变更

已检查此前的 `codex/r1-iss018-postgres-ci-boundary-20261101`。所指 `ac0d5a22ebecead70cf479fdee09d2f40335600d` 是报告/台账提交；实际测试修复位于其祖先提交 `0ea0115d56a73bade82dd4575e44027ec733ace9`。本分支从上一轮 PostgreSQL 测试隔离完成提交创建，并仅 cherry-pick 该测试修复，保留来源说明。

仅改 `backend/crm/tests/test_iss018_backup_recovery.py`：

- `ISS018BackupRecoveryTests` 加 `skipUnless(connection.vendor == "sqlite", ...)`，其 SQLite 文件快照、ZIP 内容、恢复和 SQLite 数据校验只在 SQLite backend 执行。
- PostgreSQL fail-closed 用例独立为 `ISS018PostgreSQLBackupBoundaryTests`。它将设置切为 PostgreSQL engine，调用备份服务并断言因没有绑定一致性快照而拒绝；同时确认输出目录未创建。此检查不连接或读取 PostgreSQL 数据库、SQLite 文件、媒体目录。
- `backend/crm/services/backup_recovery.py` 未修改；`_assert_sqlite()` 的生产拒绝逻辑、安全检查与备份行为均保持不变。没有模型或迁移变更。

当前测试文件与来源修复提交、此前真实 PostgreSQL CI 所用测试文件的 Git blob SHA 均为 `a186710b670adfe54fc6e3dfb70362c62634f1a3`。因此本分支移植的测试代码与真实 PostgreSQL CI 执行的内容字节级一致；本分支本身按要求不触发 CI。

## 本地验证

运行环境：CPython 3.14.5、Django 6.0.6。所有数据库测试使用明确隔离的内存 SQLite，或不会连接的 PostgreSQL 配置模拟；未连接业务数据库或本地 PostgreSQL 服务。

### SQLite 备份/恢复回归

```powershell
$env:DATABASE_URL='sqlite:///:memory:'
python manage.py test crm.tests.test_iss018_backup_recovery --verbosity 2
```

结果：22 项，19 通过、3 跳过、0 失败。3 项是当前 Windows 环境的平台条件跳过：POSIX 权限模式检查 1 项；创建符号链接权限不足 2 项。没有任何失败测试被标记为通过。独立 PostgreSQL fail-closed 测试也通过。

### PostgreSQL 配置分类与安全边界

```powershell
$env:DATABASE_URL='postgresql://postgres:postgres@127.0.0.1:1/not-connected'
python manage.py test crm.tests.test_iss018_backup_recovery --verbosity 2
```

结果：22 项，21 项明确跳过，1 项 PostgreSQL fail-closed 边界测试通过，0 失败。测试运行器显示 `Skipping setup of unused database(s): default.`，因此这一步只是 PostgreSQL backend 配置下的分类/边界逻辑验证，没有连接 `127.0.0.1:1`，不能称为真实 PostgreSQL 服务测试。21 个 skip 仍按 skip 统计，没有计入通过数。

另外在隔离 SQLite 配置下，`python manage.py check` 通过，`python manage.py makemigrations --check --dry-run` 返回 `No changes detected`。首次单独执行 `py_compile` 时，默认 `__pycache__` 路径受 worktree 权限限制；改用独立临时 `PYTHONPYCACHEPREFIX` 后通过。测试运行本身已成功导入并执行全部模块用例。

## 真实 PostgreSQL 17 证据

此前来源分支的 [GitHub Actions #41315952301](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41315952301) 使用提交 `1d7a533728ca9b1f036289963d473042e37ec047`，其测试文件 blob 与本分支完全相同。该运行启动真实 PostgreSQL 17，检查和迁移步骤通过；PostgreSQL 全量测试为 1066 项、12 failures、73 errors、21 skipped，因此整个 PostgreSQL Job 失败。日志中 21 项 skip 与 SQLite 专属测试类一致，独立 `test_postgresql_backup_is_fail_closed_without_bound_snapshot` 未出现在失败/错误清单，按该 Job 记录为目标测试通过。完整 PostgreSQL 日志：[Job #124875916867](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41315952301/job/124875916867)。这仅证明该边界测试在当时的真实 PG17 CI 上通过，不等于 PostgreSQL 全套测试通过，也不是本分支 SHA 的新 CI 结果。

## 状态与限制

- ISS-018 仍为 `BLOCKED` / `DEPLOYMENT_VERIFICATION_PENDING`。生产 PostgreSQL 与私有媒体同一恢复点、持久媒体卷、独立加密副本、ACL、任务/告警及 RPO/RTO 仍待部署环境验收。
- 本轮没有修改 `backup_recovery.py`、生产安全保护、CI workflow、迁移或业务数据。
- 提交信息含 `[skip ci]`；未触发新 GitHub Actions、未创建 PR、未合并、未部署、未关闭 Issue。
