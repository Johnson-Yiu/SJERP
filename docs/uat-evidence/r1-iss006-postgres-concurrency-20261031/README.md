# R1-ISS006-POSTGRES-CONCURRENCY-UAT

固定基线：`bd324a8c3fb64af245c3afcabbd4301c84f7711c`

分支：`codex/r1-iss006-postgres-concurrency-20261031`
本轮代码测试 HEAD：固定基线（未修改业务代码）

## 结论

**PostgreSQL 并发 UAT：BLOCKED。** 本机未发现 PostgreSQL 服务、`psql`/`pg_ctl`/`createdb`、Docker 可执行程序或 `127.0.0.1:5432` 监听；PostgreSQL 连接环境变量也未配置。未安装软件、未连接共享或远端数据库。按任务边界，没有把 SQLite 结果当作 PostgreSQL 并发证据。

本轮没有确认新的业务代码缺陷，因此未修改产品代码或测试断言。ISS-006 继续为 `NEEDS_VERIFICATION`；本报告中被阻塞的 PostgreSQL 专项不代表已验收。

## 环境与隔离

- Python 3.14.5、Django 6.0.6。
- 两组测试均明确设置 `APP_STAGE=development`、临时目录下的 SQLite `DATABASE_URL` 和独立临时 `MEDIA_ROOT`。Django 测试运行器创建隔离的 `file:memorydb_default?mode=memory&cache=shared` 测试库，未读写工作区或共享业务数据库。
- PostgreSQL 可用性只通过本机服务/命令存在性和 loopback TCP 端口探测确认；没有尝试连接任何非本机主机。
- 全新 SQLite 测试库成功应用到现有迁移叶节点 `0092_merge_fulfillment_and_csv_audit`。迁移结果只证明 SQLite 启动成功，不证明 PostgreSQL 迁移或锁语义。

## 测试矩阵

| 命令/范围 | 结果 | 解释 |
|---|---:|---|
| `python manage.py test crm.tests.test_postgres_concurrency --verbosity 2` | 10 skipped，0 executed | PostgreSQL 专项类按 `connection.vendor == "postgresql"` 跳过。包含同 SKU 并发收货/发货用例，但未执行。 |
| `python manage.py test crm.tests.test_iss006_idempotency crm.tests.test_fulfillment crm.tests.test_trade_finance_upgrade --verbosity 2` | 101 项：100 passed、1 skipped、0 failed | 验证 SQLite 下的顺序业务回归；唯一跳过项是 PostgreSQL 并发重复请求用例。不是 PostgreSQL 并发通过。 |
| 两次 Django 测试运行自动执行的 system check / 全新 SQLite 迁移 | PASS | 无 system check 错误；测试数据库迁移至 `0092`。 |

原始完整输出：[PostgreSQL 专项在 SQLite 上的跳过日志](logs/postgres-specific-on-sqlite.log)、[隔离 SQLite 履约回归首次日志](logs/sqlite-fulfillment-regression.log)、[UTF-8 环境重复运行日志](logs/sqlite-fulfillment-regression-utf8.log)。首次履约日志中的一条中文跳过原因受 Windows 默认输出编码影响显示为替换字符；相同命令启用 `PYTHONIOENCODING=utf-8`、`PYTHONUTF8=1` 后重复运行，UTF-8 日志中的原因文本可读且结果一致。两份日志均保留。

本机可用性检查摘要见[环境探测记录](logs/environment-probe.log)。

首次启动专项测试时，测试命令从仓库根目录调用了仅位于 `backend/` 的 `manage.py`，同时 Windows PowerShell 的反斜杠替换表达式无效；该次没有进入 Django，也没有产生测试结果。修正工作目录和路径转换后执行的完整结果记录在上述日志中，不将启动错误计作测试失败。

定向回归中的非并发数据库断言包括：相同幂等键顺序重放不重复创建收货/发货及库存流水；失败收货不留下幂等记录或库存副作用；收货冲销恢复库存、已收数量及采购状态；第二次冲销无重复副作用；发货失败的多行写入回滚并保留预留一致性。它们均不是并发执行证据。

## PostgreSQL 场景核对

| 场景 | 当前证据 / 状态 |
|---|---|
| 同一采购单并发收货 | **BLOCKED**；现有 `test_postgres_concurrency.py` 未发现该用例，未执行 PostgreSQL 验证。 |
| 同一收货记录并发重复冲销 | **BLOCKED**；现有 PostgreSQL 专项未发现该用例，顺序二次冲销测试通过不能替代并发验证。 |
| 同一 SKU 并发收货与发货 | **BLOCKED**；已有 `test_receipt_and_shipment_concurrently_rebalance_one_sku_without_deadlock`，但在本机因 SQLite 后端跳过。 |
| 相同幂等请求并发重复提交 | **BLOCKED**；已有 `test_postgresql_concurrent_duplicate_requests_are_serialized` 覆盖并发发货重试，但在 SQLite 上跳过。顺序重放回归通过。 |
| 并发失败后的库存、预留、采购状态和流水对账 | **BLOCKED**；本轮只有顺序失败/回滚回归，没有并发失败注入及 PostgreSQL 前后状态核对。 |
| 死锁、重复流水、负库存 | **BLOCKED**；没有执行 PostgreSQL 并发事务，不能声称未发生。 |
| 失败请求无部分业务写入 | SQLite 顺序失败回滚测试通过；**并发 PostgreSQL 路径 BLOCKED**。 |

静态检查确认履约服务存在针对采购明细、收货记录、订单、SKU 与关联流水的 `select_for_update()` 路径；现有 PostgreSQL 测试也有两个并发覆盖点。但代码锁声明和 SQLite 顺序测试不能证明 PostgreSQL 下的锁竞争、死锁顺序或并发回滚原子性，本轮没有据此作通过结论。

## 后续解除条件

在获准的本机/隔离环境提供可用 PostgreSQL 后，为本任务创建独立临时数据库，至少实际运行现有两个 PostgreSQL 并发用例，并补验同 PO 并发收货、同收货记录并发冲销、失败请求并发竞争。每个场景需保存原始命令日志和数据库前后快照，对账库存数量、预留、PO/订单状态、收货/冲销记录及库存流水，明确检查唯一流水、非负库存和死锁/超时。未完成前 ISS-006 保持 `NEEDS_VERIFICATION`。

本轮未触发 CI、未创建 PR、未合并、未部署、未关闭 Issue。证据提交 SHA 以分支最终 HEAD 为准。
