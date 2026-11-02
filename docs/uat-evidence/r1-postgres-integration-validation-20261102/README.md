# R1-POSTGRES-INTEGRATION-VALIDATION-01

日期：2026-11-02
分支：`codex/r1-postgres-integration-validation-20261102`
基线：`9f0e59ea4e31778e0944bdac8cff858d0cfd9fa2`
集成代码提交：`e6b40cadb04c54ef3376307daba19f78276a913d`

## 后续修复：R1-POSTGRES-AUTH-CONTRACT-FIX-02（2026-11-02）

在上述集成分支继续修复唯一 PostgreSQL CI 失败。代码提交 `7ab9913e03f1bde341158237e51aeebf77a86abc` 只改 `backend/crm/tests/test_historical_orders.py`：为 `historical_analysis` 函数视图实际包装类 `historical_analysis.cls` 临时设置 `SessionAuthenticationWithChallenge`；匿名请求断言 401，已认证但没有订单/采购查看权限仍断言 403。未改生产认证/权限逻辑、业务代码、迁移或数据库。

本地 CPython 3.14.5，Django 使用隔离内存 SQLite 与每次新建并在结束后清理的临时 `MEDIA_ROOT`。历史订单专项 `python manage.py test crm.tests.test_historical_orders --verbosity 2 --noinput`：9/9 通过；Backend 全量 `python manage.py test --verbosity 1 --noinput`：1098 项、33 跳过、0 失败（612.031 秒）。`manage.py check`、`makemigrations --check --dry-run` 和 `git diff --check` 均通过。本机没有 PostgreSQL/Docker，故未声称本地 PostgreSQL 测试。

GitHub Actions run [#41432846693](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41432846693) 的 `head_sha` 精确为代码提交 `7ab9913e03f1bde341158237e51aeebf77a86abc`，三项全部 SUCCESS：

| Job | 结果 |
|---|---|
| [Backend](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41432846693/job/125235426965) | SUCCESS；1098 项、30 跳过、0 失败；Django check 与迁移检查通过 |
| [Backend PostgreSQL 17](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41432846693/job/125235426604) | SUCCESS；1098 项、21 跳过、0 失败；目标 `test_anonymous_and_unprivileged_history_analysis_are_denied ... ok`，证明 401/403 两段均通过；PostgreSQL 专属测试正常执行 |
| [Frontend](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41432846693/job/125235427160) | SUCCESS；unit、Node-only、Vitest、隔离 Playwright 和生产构建全部通过；job 用时 17分54秒 |

原始日志索引：[FIX-02 五份本地/CI 日志原样归档](logs/r1-postgres-auth-contract-fix-02-logs.zip)，SHA-256：`5F2D1459D3269A815A09CFC0B9D407930FB821628EE9FDC9C0D3775E4B7FF311`。归档内含 `historical-orders-sqlite-auth-contract02.log`、`backend-sqlite-full-auth-contract02.log`、`backend-auth-contract02.log`、`backend-postgres-auth-contract02.log`、`frontend-auth-contract02.log`；文本文件按 GitHub/本地命令原始输出保留，避免为通过空白检查而改写日志。

上一次 run `#41424016735` 对旧代码提交 `e6b40cadb04c54ef3376307daba19f78276a913d` 的 PostgreSQL 失败仍作为历史事实保留；本次新 SHA 的三个 job 已全部通过。无 Issue 状态变更；ISS-006、ISS-018、ISS-052 等既有验收缺口不因该测试修复而改变。未创建 PR、未合并 master、未部署、未启用正式 RBAC、未连接实际业务数据库。

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

本地使用 CPython 3.14.5、Django 6.0.6、DRF 3.17.2。依赖是本机现有 Python 环境；未以 Python 3.14 结果冒充 CI 的 Python 3.12。Django 使用 `DATABASE_URL=sqlite:///:memory:` 和每次运行新建的临时 `MEDIA_ROOT`。本机没有 PostgreSQL 服务；PostgreSQL 真实 SQL/触发器证据来自下文精确 SHA 的 GitHub PostgreSQL 17 job。

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

全量本地测试过程出现的 Bad Request、Forbidden 和被注入异常日志是相应负向/原子性测试的预期输出；最终 Django 退出码为 0。

## PostgreSQL 17 验收重点

本机未运行 PostgreSQL。以下 PostgreSQL 17 job 在真实 GitHub Actions PostgreSQL 17 服务中运行，确认：

1. `Supplier.code` 未出现 `varchar(2)` 超长错误；全套测试唯一失败与该字段无关。
2. ISS-018 SQLite 专属归档/恢复测试明确跳过；PostgreSQL 无一致性快照备份 fail-closed 测试执行并通过；生产保护代码未改。
3. 三张 CSV 审计表逐表拒绝 `TRUNCATE`，原有审计记录保持存在；对应测试通过。
4. 本轮认证契约测试中的匿名请求为 401、已认证无权限仍为 403 的专用断言通过。另有一个未纳入 D 来源文件清单的历史报表测试，匿名断言仍为旧 403，见下方失败分类。
5. PostgreSQL 测试数据库隔离/清理机制回归通过，包括正常测试清理后保护触发器恢复、普通 flush 仍受保护；三个基线文件无集成差异。

## GitHub Actions 与原始日志

集成代码提交 SHA：`e6b40cadb04c54ef3376307daba19f78276a913d`。GitHub Actions run [#41424016735](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41424016735)，事件 `push`，该 run 的 `head_sha` 与集成代码提交完全一致；总体结论 `failure`。

| Job | 结果 | 详细链接 |
|---|---|---|
| Backend | SUCCESS；Python 3.12，Django check、迁移检查通过；全量 1098 项，0 失败 | [backend job](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41424016735/job/125206117732) |
| Backend PostgreSQL 17 | FAILURE；全量 1098 项，1 失败、21 跳过 | [backend-postgres job](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41424016735/job/125206117578) |
| Frontend | SUCCESS；Node 171/171、Node-only 1/1、Vitest 69 个文件通过、Playwright suites 全通过（主套件 216 项及隔离 suites 25 项）、build 成功 | [frontend job](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41424016735/job/125206117232) |

### PostgreSQL 失败分类

唯一失败：`crm.tests.test_historical_orders.HistoricalAnalysisPermissionTests.test_anonymous_and_unprivileged_history_analysis_are_denied`，位于 [test_historical_orders.py:205](../../../backend/crm/tests/test_historical_orders.py#L205)。该测试对匿名 `GET /api/reports/historical/` 仍断言 403，staging 下 `SessionAuthenticationWithChallenge` 返回 401，日志为 `AssertionError: 401 != 403`。这是旧测试断言与已确认认证契约不一致，不是数据库/runner 环境故障，也不是业务认证逻辑失败。该测试随后本应验证的已认证无权限 403 断言因首个断言失败而未执行；本轮独立权限契约测试中的 401/403 路径通过。

按用户要求，CI 失败后没有继续修改或重跑，不删除/跳过测试，不降低断言，也不改变生产认证逻辑。建议经独立审查后，仅将该历史测试的匿名预期改为 401，并继续保留其已认证无权限 403；当前分支暂不实施，等待独立审查。

### 完整原始日志

- `logs/backend.log`
- `logs/backend-postgres.log`
- `logs/frontend.log`

完整日志归档：[GitHub Actions run #41424016735 三个 job 原始日志 ZIP](logs/github-actions-41424016735.zip)。归档内含 `backend.log`、`backend-postgres.log`、`frontend.log` 三份完整 job 输出；未裁剪或改写日志内容。凭证扫描未发现未遮蔽 token（GitHub 也按其规则遮蔽 secret）。前端 build 有既有的大于 500 kB chunk 警告，不影响 job 成功。

## 状态与未覆盖事项

- ISS-006 仍为 `NEEDS_VERIFICATION`；生产/专用 PostgreSQL 并发及数据库清理场景待真实环境复核。
- ISS-018 仍为 `BLOCKED`；本轮测试边界不替代生产 PostgreSQL 与数据库/媒体联合备份恢复、ACL、异地副本、告警及 RPO/RTO 验收。
- ISS-052 仍为 `FIXED_PENDING_REVIEW`；三表 PostgreSQL TRUNCATE 拒绝/原数据保留测试现已通过，迁移回退安全及独立审查仍是后续验收项。
- 开发身份/RBAC、业务规则及财务/采购历史数据未修改；没有连接业务数据库。
- 不创建 PR、不合并 master、不部署、不关闭 Issue。
