# 测试日志 — R1-CSV-AUDIT-TRUNCATE-TEST-FIX-01

日期：2026-11-02。代码提交：`1aba37600cadbdf88aebe787d742310bac1a333f`。运行环境：Windows、Python 3.14.5、项目锁定依赖的临时虚拟环境。

## SQLite 本地结构检查（非 PostgreSQL 验收）

命令（工作目录 `backend/`）：

```powershell
$env:DATABASE_URL='sqlite:///:memory:'
$env:AUDIT_LOG_ENABLED='1'
& "$env:TEMP/sunjack-r1-postgres-supplier-fixtures-20261101-venv/Scripts/python.exe" manage.py test crm.tests.test_csv_import_audit_postgres -v 2
```

结果：Django system check 无问题；SQLite 内存测试库从全新状态成功迁移至 `crm.0095_merge_fulfillment_idempotency`。测试收集 2 项：

- `test_raw_update_and_delete_are_rejected_for_all_audit_tables` — SKIPPED（requires an isolated PostgreSQL test database）
- `test_truncate_is_rejected_for_each_audit_table_and_preserves_all_rows` — SKIPPED（requires an isolated PostgreSQL test database）

最终输出：`Ran 2 tests in 0.000s`，`OK (skipped=2)`，进程退出码 0。该结果不是 PostgreSQL 通过。

## PostgreSQL 可用性检查

- `psql`：未找到。
- `pg_isready`：未找到。
- `docker` / `podman`：未找到。
- Windows PostgreSQL 服务及常见安装目录：未发现。
- WSL 命令存在，但没有可用 Linux 发行版。
- `Test-NetConnection 127.0.0.1 -Port 5432`：失败，返回 `False`。

结论：真实 PostgreSQL 测试无法启动，标记 `BLOCKED`。不得用 SQLite 跳过结果替代。

## 差异检查与待运行命令

`git diff --check`：通过（在代码提交前执行）。

PostgreSQL 恢复后，在隔离 PostgreSQL 数据库及锁定 Python 环境中运行：

```powershell
$env:DATABASE_URL='<isolated PostgreSQL test database URL>'
$env:AUDIT_LOG_ENABLED='1'
python manage.py test crm.tests.test_csv_import_audit_postgres -v 2
```

预期须由真实 PostgreSQL 日志证明：三张表各自对应的 0094 触发器存在；逐表的 `TRUNCATE ... CASCADE` 因 append-only 规则失败而非外键错误；每次失败后 Batch、RowAudit、PreviewAudit 原始行均仍存在。未取得该证据前，本任务不视为完成。
