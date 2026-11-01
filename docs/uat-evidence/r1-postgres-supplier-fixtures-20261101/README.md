# R1-POSTGRES-SUPPLIER-FIXTURES-01 验收报告

## 范围

- 分支：`codex/r1-postgres-supplier-fixtures-20261101`
- 共同基线：`cd479ea5ad7cd923f5b1798c0f296f960ae46dae`（`codex/fix-unified-ci-env-20261101`）
- 测试代码提交：`e8e5d1199067a339d9cf6719310c9b32294b44f1`
- 目标字段：`Supplier.code` 为 `max_length=2, unique=True`
- 实施：仅更正六个目标测试文件中的 9 个超长供应商代码；保留已合法的 `HS`。新代码均为两字符，且本轮十个供应商夹具代码互不重复。

代码映射：

| 测试文件 | 原代码 | 新代码 |
|---|---|---|
| `test_finance_drill.py` | `FIN-DRILL-S` | `FD` |
| `test_historical_orders.py` | `HIST-P-S` | `HP` |
| `test_integration_039_037_040.py` | `INT-039-037-040-S` | `I4` |
| `test_iss039_shared_purchase_costs.py` | `ISS039-S` | `C9` |
| `test_order_quantity_adjustments.py` | `SUP-QTY-ADJUST` | `Q1` |
| `test_order_quantity_adjustments.py` | `SUP-QTY-GROUP` | `Q2` |
| `test_order_quantity_adjustments.py` | `QTY-INTEGRATION-S` | `Q3` |
| `test_order_quantity_adjustments.py` | `SUP-QTY-RBAC` | `Q4` |
| `test_purchase_moq.py` | `ISS022-S` | `M2` |

没有扩大字段长度、修改生产逻辑、修改数据库迁移或更改测试业务断言。`test_iss006_idempotency.py`、`test_iss006_pre_uat.py`、`test_fulfillment_audit_atomicity.py`、`test_postgres_concurrency.py` 均未改动。

## 验证

依赖使用 `backend/requirements.lock` 安装至独立 Python 3.14.5 临时虚拟环境；Django 6.0.9、DRF 3.18.3、psycopg 3.3.6，`pip check` 通过。测试运行使用 `APP_STAGE=development`、内存 SQLite 测试数据库和一次性临时 `MEDIA_ROOT`，没有连接业务数据库。

SQLite 定向命令：

```powershell
python manage.py test crm.tests.test_finance_drill crm.tests.test_historical_orders crm.tests.test_integration_039_037_040 crm.tests.test_iss039_shared_purchase_costs crm.tests.test_order_quantity_adjustments crm.tests.test_purchase_moq --verbosity 2
```

结果：57 项运行、57 通过、0 失败；迁移在隔离内存数据库中应用成功。原始日志：[sqlite-targeted.log](logs/sqlite-targeted.log)。`git diff --check` 通过。

PostgreSQL 定向命令以 `postgresql://...@127.0.0.1:5432/sunjack_test?connect_timeout=3` 指向本地隔离测试库执行，但本机 5432 端口未开放，连接在创建测试数据库前超时。因此本地 PostgreSQL 结果为 **BLOCKED**，不是通过或跳过。原始失败日志：[postgres-targeted-local.log](logs/postgres-targeted-local.log)。

GitHub Actions 的 [PostgreSQL 17 job](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41316120587/job/124876424265) 使用隔离服务数据库，测试代码 SHA 为 `ddc0ef0ac19aa273d16af68d6dbbdbfc209a9db2`。PostgreSQL 初始化、system check、迁移检查及迁移通过；全量 Django 测试 1066 项，15 failures、62 errors、1 skipped，因此该 job 为失败，不能报告全量 PostgreSQL 通过。

六个目标模块中没有因本轮九个修正值产生 `varchar(2)` 插入错误；`test_finance_drill.py`、`test_integration_039_037_040.py`、`test_iss039_shared_purchase_costs.py`、`test_purchase_moq.py` 无失败/错误。另三条非夹具失败为：`test_historical_orders.py` 一条权限断言收到 401、预期 403；`test_order_quantity_adjustments.py` 一条权限断言同为 401/403 差异，以及一条测试清理受到 ISS-052 PostgreSQL 审计表 TRUNCATE 保护拒绝。完整 job 日志见上述 GitHub 链接。全套日志还显示明确排除的 ISS-006 测试文件仍包含超长 Supplier 夹具并报字段长度错误；本轮按用户边界未修改这些文件。其他 PostgreSQL errors/failures 不属于本轮夹具修改范围。

同一 CI run 的普通 `backend` job 全量测试通过。`frontend` job 在本报告更新时仍处于 isolated Playwright 阶段；它与本轮后端夹具验收无关。SQLite 结果不替代 PostgreSQL 验收。

## 边界结论

本轮仅纠正测试供应商夹具，使其符合现有两字符且唯一的字段约束；没有改变供应商业务代码格式或任何业务规则。后续 PostgreSQL 验收应使用隔离 CI 测试数据库，并检查这六个测试模块在 PostgreSQL 17 下的结果。
