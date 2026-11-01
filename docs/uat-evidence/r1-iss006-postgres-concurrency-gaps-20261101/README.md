# R1-ISS006-POSTGRES-CONCURRENCY-GAPS

- 日期：2026-11-01。
- 固定基线：`7402ad38cf40d1eea0adb076e67021c31be8ac1e`，来源 `codex/unified-github-ci-post-oct20-20261101`。
- 分支：`codex/r1-iss006-postgres-concurrency-gaps-20261101`。
- 独立 worktree：`C:\Users\Johnson\.codex\worktrees\r1-iss006-postgres-concurrency-gaps\森爵照明管理系统`。
- 结论：**BLOCKED：已补测试代码并完成静态检查，真实 PostgreSQL 并发验收尚未执行。**

推送前 `git ls-remote` 核实来源分支已推进到 `3093c22c6e0a623499a98d5a602f7b1cb5758e8e`；本任务仍按用户固定 SHA `7402ad38…` 开始，没有自动纳入随后提交。新目标分支在远端尚不存在。

## 审查与变更

已核对两组指定测试、履约服务的采购单→明细/收货记录→关联销售单→SKU 锁顺序、API 事务/幂等/审计边界及既有并发夹具补修和冲销审计原子性报告。基线已覆盖不同 SKU 的同 PO 收货、销售发货幂等竞争及服务层收货/冲销竞争；本轮补足同笔冲销、收货同键重放、同明细部分收货和 API 审计验证。

只修改测试和本轮验收/开发记录。没有改履约服务、模型、权限、迁移、库存或财务规则。无真实 PostgreSQL 运行证据，因此没有认定或修复并发业务缺陷。

| 场景 / 测试方法 | 代码中的预期验收断言 | 实际执行状态 |
|---|---|---|
| `test_two_concurrent_requests_cannot_reverse_the_same_goods_receipt_twice` | 两请求返回 200/400；拒绝原因是已冲销；收货记录和原入库事实各保留一条；仅一条冲销流水和冲销审计；PO 恢复 ordered；库存/预留为 0 | BLOCKED |
| `test_postgresql_concurrent_same_key_receipts_return_one_business_result` | 同键同内容返回两个 201、相同响应、恰一个重放标记；收货/入库流水/成功幂等记录/审计各一条；库存与预留均为 2，PO partial | BLOCKED |
| `test_concurrent_valid_partial_receipts_for_same_item_both_commit` | 同 PO/SKU/明细用不同请求键各收 3，合同 10；两请求成功、两条业务事实/审计；实际和预留均为 6，剩余 4，PO partial | BLOCKED |
| `test_concurrent_partial_receipts_for_same_purchase_item_cannot_overreceive` | 合同 10，并发各收 6；仅一个 201，另一个 400；仅一条收货/流水/成功幂等记录/审计；实际/预留 6，剩余 4 | BLOCKED |
| `test_receipt_and_reversal_race_keeps_purchase_stock_and_reservations_consistent`（增强既有用例） | 原入库 5，同时新收 5 和冲销原收货；API 201/200；两笔原始入库、一笔冲销，实际/预留 5，PO partial；两条审计的对象关联及 before/after 状态符合任一合法串行顺序 | BLOCKED |

测试均使用 `TransactionTestCase`。工作线程开启各自 Django 数据库连接，设置 20 秒 PostgreSQL statement timeout，使用 Barrier 同步开始，结束关闭连接；新增/增强场景断言两个 `pg_backend_pid()` 不同，线程异常由 Future 传播。审计通过认证合成用户的真实 API action 产生，检查操作人和收货/库存流水关联。所有 PostgreSQL 场景都有数据库 vendor 限制。

静态核查同时修正旧 `FulfillmentIdempotencyApiTests` 的供应商代码夹具：原 `ISS006-S` 超过 `Supplier.code(max_length=2)`，改为 `IS`。新增夹具也使用合法两字符供应商代码；未改变业务预期。

## 实际检查与原始日志

| 检查 | 结果 | 原始输出 |
|---|---|---|
| PostgreSQL 环境探测 | 无 psql/pg_isready/postgres/docker 命令、无相关 Windows 服务或标准安装目录；本机 5432 不可连接；未配置数据库连接环境变量 | [postgres-environment.json](logs/postgres-environment.json) |
| 两个测试模块 `py_compile` | PASS，仅语法编译 | [syntax.json](logs/syntax.json) |
| Django `manage.py check` | PASS，0 issues；配置为本机 PostgreSQL 静态检查地址，未运行测试或迁移 | [django-static-check.json](logs/django-static-check.json) |
| 模块导入/测试发现 | 24 项发现、**0 项执行**；将数据库 `ensure_connection` 替换为立即报错，导入未尝试连接数据库 | [static-test-discovery.json](logs/static-test-discovery.json) |
| `git diff --check` | PASS | [diff-check.json](logs/diff-check.json) |
| Django flush 静态检查 | 已确认框架生成 TRUNCATE 语句；未执行 SQL | [static-flush-risk.json](logs/static-flush-risk.json) |

日志以 JSON 保存完整命令、退出码和未经裁剪的合并输出；`output` 中的转义换行/空白解码后即为原始输出。最终落盘后的语法与差异检查见 [final-static-check.json](logs/final-static-check.json)。

本机静态检查使用 Python 3.14.5、Django 6.0.6、psycopg 3.3.6；本轮没有安装或验证 `requirements.lock`（其中 Django 为 6.0.9）。没有运行 SQLite、PostgreSQL 测试、前端测试或浏览器回归。未改 UI，因此没有新增截图。上述静态检查不构成并发、权限或业务验收通过。

## PostgreSQL 运行前置风险与后续动作

1. **PostgreSQL 服务缺失：BLOCKED。** 需要可创建/销毁专用测试数据库的本地 PostgreSQL 及锁定依赖环境。不得连接实际业务数据库。
2. **测试数据库清理冲突：待真实 PostgreSQL 核实。** 基线迁移 `0094_csv_import_audit_truncate_guard.py` 为三张 CSV 审计表安装无条件 `BEFORE TRUNCATE` 拒绝触发器。Django `TransactionTestCase._fixture_teardown()` 调用 flush，PostgreSQL 后端静态生成 `TRUNCATE ...`；因此存在测试 teardown 被阻断的明确静态风险，影响不只本轮新增用例。日志保留框架源代码与生成语句；本轮未删除/禁用触发器，未改生产审计保护。应先在独立 PostgreSQL 测试库验证，再制定仅作用于测试库的隔离/清理方案；任何 teardown 错误都必须计为失败。
3. 前置条件满足后，在专用 PostgreSQL 测试环境安装 `backend/requirements.lock`，确认 `connection.vendor == "postgresql"` 并检查测试数据库名称，再执行以下命令并保留完整输出：

```powershell
python backend/manage.py test crm.tests.test_postgres_concurrency crm.tests.test_iss006_idempotency --verbosity 2
```

随后运行履约、冲销、预留和审计交叉回归；核对本报告五个场景未跳过、没有 worker 异常/死锁/teardown 错误，并保留数据库前后快照。当前没有这些实际运行证据。

ISS-006 继续为 `NEEDS_VERIFICATION`，本轮并发执行状态为 `BLOCKED`，等待真实 PostgreSQL 和独立审查。未触发 GitHub Actions、未创建 PR、未合并 master、未部署。提交使用 `[skip ci]`；最终 SHA 以本分支交付记录为准。
