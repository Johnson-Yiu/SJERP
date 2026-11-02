# R1-CSV-AUDIT-TRUNCATE-TEST-FIX-01

## 范围

- 基线：`e2e7e017a5a2675af44b47fc93650b3837971755`
- 分支：`codex/r1-csv-audit-truncate-test-20261102`
- 测试代码提交：`1aba37600cadbdf88aebe787d742310bac1a333f`
- 目标：让 PostgreSQL 原始 SQL 测试执行时由迁移 0094 的 append-only 触发器拒绝 TRUNCATE，而不是先被外键约束拦截。

## 改动

仅修改 `backend/crm/tests/test_csv_import_audit_postgres.py`，未修改迁移 0094 或任何生产业务代码。

- 分别对 `CSVImportBatch`、`CSVImportRowAudit`、`CSVImportPreviewAudit` 发起 `TRUNCATE TABLE <table> CASCADE`，让 PostgreSQL 满足审计表之间的外键约束条件后进入 TRUNCATE 触发器执行路径。
- 每个目标执行前查询 `pg_trigger`，精确断言对应的 0094 命名触发器安装在该关系上。
- 每次预期拒绝后，核对三张表各自的合成原始记录均仍存在。
- 保留原始 UPDATE/DELETE 拒绝测试。

## 验收状态

`BLOCKED — REAL POSTGRESQL NOT AVAILABLE`。本机未找到 `psql`、`pg_isready`、Docker 或 Podman；没有已安装 PostgreSQL 服务或 WSL 发行版；对 `127.0.0.1:5432` 的连接探测失败。没有连接或触碰任何业务数据库。

锁定依赖下的 SQLite 测试只确认 Django 加载、全部迁移和测试收集正常；PostgreSQL 专项按 vendor 条件跳过，不能证明 0094 触发器在 PostgreSQL 上运行，也不构成本任务验收通过。应在隔离 PostgreSQL 测试库可用后运行测试日志中的命令，确认三表触发器拒绝及原始记录保留，再解除阻断。

ISS-052 保持 `FIXED_PENDING_REVIEW`。未触发 CI、未创建 PR、未合并 master、未关闭 Issue。

## 测试与原始结果

详见[测试日志](logs/test-results.md)。
