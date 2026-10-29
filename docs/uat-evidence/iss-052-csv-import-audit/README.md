# ISS-052 CSV 导入批次与行级审计

## 本轮范围

- 基线：`54e715bdc568b80ba624186fecd866550676cf38`
- 分支：`codex/fix-iss052-csv-import-audit-20261029`
- 本轮迁移：`backend/crm/migrations/0091_csv_import_audit.py`
- 迁移依赖：`crm.0089_operationlog_operator_protect`
- 约束：未修改共享 `PROJECT_ISSUES.md` / `PROJECT_PHASES.md`，未连接真实业务库，未触发 CI，未合并 master，未创建 PR。

## 历史缺口核实

ISS-052 原验收报告 `docs/uat-evidence/iss-052-csv-import-verification/README.md` 已确认客户、产品、SKU、财务流水四类 CSV 的预览、文件哈希、预览令牌、状态冲突、重复主键和原子导入行为；同时明确记录：开发身份 `authenticated=false`、`AUDIT_LOG_ENABLED=false`、`OperationLog=0`，原导入路径没有调用 `record_operation`，因此没有持久化批次及行级 before/after 审计。

ISS-043 的现有审计保护继续保留：`OperationLog` ORM 追加保护、操作人 `PROTECT`，以及 0088 在 PostgreSQL 的更新/删除触发器。本轮没有改写这些历史迁移。

## 实施内容

1. 新增不可变 `CSVImportBatch` 和 `CSVImportRowAudit`：批次记录数据类型、UUID 批次标识、文件 SHA256、真实认证用户、操作时间、成功/失败状态、计数和失败原因；行记录 CSV 行号、业务主键、创建/更新/失败结果、业务对象 ID、必要的 before/after 字段快照和错误信息。
2. 0091 为批次、行审计增加 PostgreSQL `BEFORE UPDATE OR DELETE` 触发器；应用层 queryset、实例 `save()`/`delete()` 也拒绝修改或删除。批次与行使用 `PROTECT`，不提供普通业务删除路径。
3. 正式执行入口现在要求真实认证操作人且 `AUDIT_LOG_ENABLED=true`。开发匿名身份会明确返回“不能作为审计操作人”，不会写入伪造操作人；审计关闭时返回 503，未写入业务数据。
4. 成功路径在同一个 `transaction.atomic()` 中完成业务写入、批次、行审计和对应 `OperationLog`；任何业务或审计写入异常都会回滚业务数据。
5. 预览状态改变、凭证/文件不匹配、运行时失败和重复执行均保留失败批次及错误行；失败批次在业务事务回滚后单独落库。未解析的空文件/缺表头仍在读取阶段拒绝，不凭空生成无数据审计批次。
6. 未改变现有预览字段、文件 SHA256、签名预览令牌、状态校验、重复主键拒绝、订单导入禁用和四类导入业务字段。成功响应只增加 `import_batch_id`，旧字段保持不变。
7. `crm.csvimportbatch` 纳入既有 OperationLog 只读查询的 `imports` 权限映射；行审计通过批次外键和业务 OperationLog metadata 关联。

## 隔离身份与数据

自动化测试在 Django 隔离测试数据库中创建真实认证用户 `csv-audit-operator`（测试 superuser，仅用于测试权限，不是开发匿名身份），通过 `APIClient.force_authenticate()` 执行正式导入。覆盖客户、产品、SKU、财务流水的创建；客户更新的 before/after；无效预览、重复提交、状态冲突、运行时异常回滚、文件 SHA256、操作人、行号、批次关联、OperationLog 查询和追加保护。测试数据在测试事务结束后销毁。

## 测试矩阵

| 检查 | 命令/环境 | 结果 |
|---|---|---|
| Django system check | `python manage.py check` | PASS，无问题 |
| 模型迁移一致性 | `python manage.py makemigrations crm --check --dry-run` | PASS，No changes detected |
| 迁移 SQL 生成 | `python manage.py sqlmigrate crm 0091` | PASS；SQLite 下 Python PostgreSQL trigger 操作按设计不输出 SQL |
| 全新 SQLite | 独立临时库 `fresh-correct.sqlite3`，`python manage.py migrate --noinput` | PASS，全部迁移至 0091 |
| 已有库升级 | 独立临时库先 `python manage.py migrate crm 0089`，再 `python manage.py migrate --noinput` | PASS，0089 → 0091 |
| CSV/审计定向回归 | `python manage.py test crm.tests.test_safe_csv_import crm.tests.test_audit --verbosity 1` | PASS，26 tests；1 项 PostgreSQL 原生触发器测试按 SQLite 环境跳过 |
| 相关旧导入回归 | `python manage.py test crm.tests.BusinessFlowTests.test_customer_csv_import_updates_by_code crm.tests.test_dashboard_import crm.tests.test_sales_data_scope.SalesDataScopeTests.test_customer_import_rejects_out_of_scope_code_and_defaults_new_owner --verbosity 1` | PASS，16 tests |
| 后端全量 | `python manage.py test --verbosity 1` | PASS，1012 tests，18 skipped；对应产品代码修改的全量复测通过 |

全量首次复测曾出现 6 个失败，均为旧测试在开发匿名身份下直接执行正式导入，收到本轮新增的 403/503 审计门禁；没有业务数据、迁移或原子性失败。相关测试已仅补入真实认证测试用户，并在导入场景显式启用审计后重跑通过，未删除用例、未放宽断言。最终定向结果为 26 项通过，最终全量产品代码回归为 1012 项通过。

本地第一次迁移命令的 PowerShell 临时路径替换表达式写错，曾回退到工作树默认 SQLite 配置；该次不作为隔离证据，后续已用明确的临时绝对路径重新完成 fresh 与 0089→0091 升级。期间未连接外部业务数据库，也未执行业务数据写入。

## 证据结论与剩余风险

- 已修复：ISS-052 原报告中的持久化导入批次、真实操作人关联、行级结果、before/after、失败批次/错误行、成功事务一致性和应用层/数据库层追加保护缺口。
- 已保留：预览与冲突检测、文件哈希和令牌、状态校验、重复主键拒绝、订单导入限制、四类既有业务导入规则。
- 尚未在本地执行：PostgreSQL 实例上的 0091 真实触发器和生产数据库角色权限验证；SQLite 只能证明应用层保护及迁移可执行，不能替代 ISS-043 的 PostgreSQL 独立验收。
- 尚未执行：真实 Chrome/UI 回归。本轮没有修改前端代码或页面布局；正式导入在开发匿名身份下现在会明确拒绝，真实 UI 需在具备认证会话且审计开启的隔离环境验证成功提示和批次 ID展示。
- 不关闭 ISS-043/ISS-052，不把本报告视为 master 合并或生产部署许可；交付后等待独立审查。
