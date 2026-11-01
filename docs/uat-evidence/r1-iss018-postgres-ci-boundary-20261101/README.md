# R1-ISS018-POSTGRES-CI-BOUNDARY

## 结论

基线：`cd479ea5ad7cd923f5b1798c0f296f960ae46dae`（`codex/fix-unified-ci-env-20261101`）

分支：`codex/r1-iss018-postgres-ci-boundary-20261101`
测试代码提交：`0ea0115d56a73bade82dd4575e44027ec733ace9`（独立提交；最终报告 SHA 以交付为准）

将依赖本机 SQLite 文件语义的备份/恢复测试限定为 SQLite 后端；PostgreSQL fail-closed 测试现在独立运行，不会被 SQLite 类级跳过吞掉。未改 `.github/workflows/ci.yml`、数据库迁移或 `backend/crm/services/backup_recovery.py`，也未降低任何安全断言。

## 审查与改动

`test_iss018_backup_recovery.py` 中 `_make_fixture()` 直接用 Python `sqlite3` 创建 SQLite 文件，并断言归档内 `database.sqlite3`、SQLite 数据行及媒体关系；这些验证是 SQLite 文件备份/恢复契约，PostgreSQL CI 不应执行。

- `ISS018BackupRecoveryTests` 类使用 `skipUnless(connection.vendor == "sqlite", ...)`；在非 SQLite 后端，Django 会逐项报告明确跳过原因。
- PostgreSQL 边界检查移至 `ISS018PostgreSQLBackupBoundaryTests`。该测试设置 PostgreSQL engine，传入不存在的数据库/媒体路径并断言 fail-closed 错误和输出目录未创建，证明拒绝发生在数据库路径、媒体路径和备份输出访问之前。
- 生产保护保持原样：`backend/crm/services/backup_recovery.py` 的 `_assert_sqlite()` 对未绑定一致性快照的 PostgreSQL 备份继续拒绝。

## 本地验证

本机环境：CPython 3.14.5、Django 6.0.6；没有本地 PostgreSQL、Docker、`psql` 或 `pg_isready`。这与 CI 锁定的 Python 3.12 / Django 6.0.9 不同，因此本地结果是定向逻辑验证，精确 CI 依赖与真实 PostgreSQL 服务的结果以 GitHub Actions 为准。

### 隔离 SQLite 配置

命令：

```text
python manage.py test crm.tests.test_iss018_backup_recovery --verbosity 2
```

使用 `DATABASE_URL=sqlite:///:memory:` 和本次新建的临时 `MEDIA_ROOT`。结果：22 项运行，19 通过、3 跳过、0 失败。3 项跳过均为平台限制：POSIX mode 检查在 Windows 跳过；两项符号链接测试因当前 Windows 用户没有创建符号链接的权限而按既有条件跳过。PostgreSQL fail-closed 用例也在此配置中通过。原始输出：[`sqlite-backup-recovery-test.log`](logs/sqlite-backup-recovery-test.log)，退出码：[`sqlite-backup-recovery-test.exit-code.txt`](logs/sqlite-backup-recovery-test.exit-code.txt)。

### PostgreSQL 设置下的跳过/边界逻辑验证（非真实 PostgreSQL）

同一测试命令在 staging 配置、PostgreSQL `DATABASE_URL` 下运行；Django 测试输出明确为 unused database，未连接端口或创建测试库。结果：22 项运行，21 项 SQLite 专属测试明确跳过，PostgreSQL fail-closed 边界测试 1 项通过，0 失败。该项验证的是 PostgreSQL 设置识别、跳过分类和拒绝保护；**不是**真实 PostgreSQL 服务验收。原始输出：[`postgres-config-boundary-test.log`](logs/postgres-config-boundary-test.log)，退出码：[`postgres-config-boundary-test.exit-code.txt`](logs/postgres-config-boundary-test.exit-code.txt)。

在隔离 SQLite 设置下，`python manage.py check` 通过，`python manage.py makemigrations --check --dry-run` 返回 `No changes detected`；没有模型或迁移差异。两项原始输出和退出码均在 `logs/`。

### GitHub Actions

本分支最终证据提交推送后，将由仓库现有工作流执行 `backend`、`backend-postgres`、`frontend`。在报告初次提交时结果待运行；稍后以精确 SHA 和 run/job 状态补记。SQLite 配置下的本地测试不冒充 PostgreSQL CI 通过。

## 变更和限制

- 本次仅改 `backend/crm/tests/test_iss018_backup_recovery.py` 以及验收报告/日志和共享项目记录。
- 无业务代码、备份策略、迁移、依赖或 CI workflow 变更。
- ISS-018 保持 `BLOCKED`：生产 PostgreSQL 与私有媒体同一恢复点、真实媒体卷、异地加密副本、生产文件 ACL、调度/告警和 RPO/RTO 仍需部署环境演练；本任务不声称这些通过。
- 本轮未连接真实业务数据库或真实 PostgreSQL，不修改既有记录；未合并 master、未关闭 Issue、未部署。

## 日志索引

- [`runtime-and-versions.txt`](logs/runtime-and-versions.txt)：本机 Python、Django 版本和测试代码 SHA。
- [`django-check.log`](logs/django-check.log)、[`django-check.exit-code.txt`](logs/django-check.exit-code.txt)：Django system check。
- [`makemigrations-check.log`](logs/makemigrations-check.log)、[`makemigrations-check.exit-code.txt`](logs/makemigrations-check.exit-code.txt)：迁移差异检查。
- [`sqlite-backup-recovery-test.log`](logs/sqlite-backup-recovery-test.log)：SQLite 配置完整原始测试输出。
- [`sqlite-backup-recovery-test.exit-code.txt`](logs/sqlite-backup-recovery-test.exit-code.txt)：SQLite 测试退出码。
- [`postgres-config-boundary-test.log`](logs/postgres-config-boundary-test.log)：PostgreSQL 设置下的 SQLite skips 与安全边界测试原始输出。
- [`postgres-config-boundary-test.exit-code.txt`](logs/postgres-config-boundary-test.exit-code.txt)：PostgreSQL 设置测试退出码。
