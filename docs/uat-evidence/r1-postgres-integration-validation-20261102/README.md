# R1-POSTGRES-INTEGRATION-VALIDATION-01

日期：2026-11-02
分支：`codex/r1-postgres-integration-validation-20261102`
基线：`9f0e59ea4e31778e0944bdac8cff858d0cfd9fa2`

## 范围与来源

| 项目 | 指定来源 SHA | 集成方式 |
|---|---|---|
| Supplier 夹具 | `644f6a908a755f9d2293dba74c609471f86fcd5d` | 完整保留该审查提交的测试夹具、seeder、前端 fixture 和验收记录修改 |
| ISS-018 PostgreSQL 测试边界 | `0c326ba7e7bfb3c4022f57e9f5680ce1cffbfc93` | 仅应用该提交补丁；SQLite 专属测试与 PostgreSQL fail-closed 测试分离 |
| CSV 审计 TRUNCATE | `1aba37600cadbdf88aebe787d742310bac1a333f` | 仅应用该提交补丁；三个 append-only 审计表逐表测试拒绝 TRUNCATE 并保留行 |
| RBAC 认证契约 | `3a79e1a68988aa2099159d9f393f22766280f68f` | 完整保留指定代码修改；匿名预期为 401，已认证无业务权限仍为 403，测试显式设置操作员名 |

B、C 未合并其历史分支或父提交。对 A 与 D 的 `test_order_quantity_adjustments.py` 重叠变更逐项复核，两类夹具/断言都保留。集成差异不修改生产业务代码、数据库模型/迁移、认证逻辑或审计保护。

以下基线文件保持原样：

- `backend/crm/test_runner.py`
- `backend/crm/postgres_test_cleanup.py`
- `.github/workflows/ci.yml`

本轮向历史阶段文档追加集成记录；更新 Issue 台账最新轮次说明但不改变任何 Issue 状态。规范状态统计：124 项，OPEN 1、BLOCKED 18、NEEDS_VERIFICATION 16、FIXED_PENDING_REVIEW 79、CLOSED 10。

## 本地环境与命令

本地使用 CPython 3.14.5、Django 6.0.6、DRF 3.17.2。依赖是本机现有 Python 环境；未以 Python 3.14 结果冒充 CI 的 Python 3.12。Django 使用 `DATABASE_URL=sqlite:///:memory:` 和每次运行新建的临时 `MEDIA_ROOT`。本机没有可用 PostgreSQL 服务，因此 PostgreSQL SQL/触发器用例必须由 GitHub PostgreSQL 17 job 验证。

在 `backend/` 执行：

```powershell
$env:APP_STAGE='development'
$env:DATABASE_URL='sqlite:///:memory:'
$env:MEDIA_ROOT='<本次新建的临时目录>'
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test --verbosity 1 --noinput
python manage.py test crm.tests.test_finance_drill crm.tests.test_historical_orders crm.tests.test_integration_039_037_040 crm.tests.test_iss039_shared_purchase_costs crm.tests.test_order_quantity_adjustments crm.tests.test_purchase_moq crm.tests.test_fulfillment_audit_atomicity crm.tests.test_iss006_pre_uat --verbosity 1 --noinput
python manage.py test crm.tests.test_iss018_backup_recovery --verbosity 1 --noinput
python manage.py test crm.tests.test_csv_import_audit_postgres --verbosity 1 --noinput
python manage.py test crm.tests.test_functional_rbac crm.tests.test_order_quantity_adjustments crm.tests.test_quotes --verbosity 1 --noinput
```

在 `frontend/` 执行：

```powershell
npm ci --no-audit --no-fund
npm run test:unit
npx --no-install vitest run tests/sku-management.spec.js --environment jsdom
npm run build
```

最终集成差异执行 `git diff --check`。本地完整命令通过；日志摘要如下：

| 检查 | 结果 |
|---|---|
| Django `check` | 通过，无问题 |
| `makemigrations --check --dry-run` | 通过，无迁移差异 |
| Backend 全量 SQLite | 1098 项运行，33 项跳过，0 失败；总耗时约 621 秒 |
| Supplier 相关后端组 | 67/67 通过 |
| ISS-018 备份恢复 | 22 项运行，19 通过、3 项 Windows 平台条件跳过，0 失败 |
| CSV 审计 PostgreSQL 专项 | 2 项在 SQLite 后端按设计跳过；未声称本地验证 PostgreSQL 触发器 |
| RBAC/认证相关后端组 | 130/130 通过 |
| `npm ci` | 按锁文件安装 227 个包成功；提示 `lucide-vue-next@1.0.0` 已弃用，为基线既有依赖 |
| Node 单元测试 | 171/171 通过 |
| Supplier SKU Vitest | 9/9 通过 |
| `npm run build` | 成功；Vite 报现有主 JS chunk 大于 500 kB 警告 |

全量测试过程出现的 Bad Request、Forbidden 和被注入异常日志是相应负向/原子性测试的预期输出；最终 Django 退出码为 0。CI 原始日志会在运行完成后按下方索引归档。

## PostgreSQL 17 验收重点

本机未运行 PostgreSQL。CI 的 `backend-postgres` job 必须使用 PostgreSQL 17 通过并给出日志证据，以确认：

1. Supplier 测试创建的 `Supplier.code` 均符合 `varchar(2)`。
2. ISS-018 SQLite 专属归档/恢复测试明确跳过，PostgreSQL 无一致性快照备份 fail-closed 测试执行并通过；生产保护代码未改。
3. 三张 CSV 审计表分别拒绝 `TRUNCATE`，拒绝后原有审计记录仍保留。
4. 匿名请求为 401；已认证但无业务权限仍为 403。
5. PostgreSQL 测试数据库隔离、清理机制与基线 `test_runner.py` / `postgres_test_cleanup.py` 一致，无集成差异。

## GitHub Actions 与原始日志

集成提交 push 后填写精确 SHA、运行链接、三个 job 的最终状态。需保存完整原始 job 日志：

- `logs/backend.log`
- `logs/backend-postgres.log`
- `logs/frontend.log`

若任一 job 失败，逐条列出错误并区分环境、测试数据和产品问题；不删测试、不降低断言、不弱化安全机制。出现失败即暂停后续集成，等待独立审查。

## 状态与未覆盖事项

- ISS-006 仍为 `NEEDS_VERIFICATION`；生产/专用 PostgreSQL 并发及数据库清理场景待真实环境复核。
- ISS-018 仍为 `BLOCKED`；本轮测试边界不替代生产 PostgreSQL 与数据库/媒体联合备份恢复、ACL、异地副本、告警及 RPO/RTO 验收。
- ISS-052 仍为 `FIXED_PENDING_REVIEW`；PostgreSQL 三表 TRUNCATE 触发器与迁移回退安全仍需本轮 PostgreSQL 17 job 及独立审查证据。
- 开发身份/RBAC、业务规则及财务/采购历史数据未修改；没有连接业务数据库。
- 不创建 PR、不合并 master、不部署、不关闭 Issue。
