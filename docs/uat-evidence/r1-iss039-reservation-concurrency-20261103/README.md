# ISS-039 预留竞争验证：待 PostgreSQL 执行

基线 `a55469c1b07e4f13037c6644c69d8a35ef0496a0`；分支 `codex/r1-iss039-reservation-concurrency-20261103`。本工作树仅新增测试和本报告，尚未提交。没有更改产品逻辑、迁移、权限配置、共享台账或历史数据。

## 现有证据与本次补充

基线已有 `test_postgres_concurrency.py` 的成本同版本竞争、同采购单收货、收货与冲销竞争；上一轮 ISS-039 的 SQLite 测试已有真实预留下的审计失败回滚，但不证明 PostgreSQL 锁语义。上一轮集成的 [PostgreSQL 17 CI](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/41602567626/job/125804549988) 为基线的历史证据，不能证明本次新测试通过。

本次在现有 PostgreSQL 专项类增加五项：

1. 两个独立连接、两个认证用户以相同版本保存，已有收货和两个订单争用同一 SKU 的库存；检查一成功一冲突、两个订单预留、金额守恒和审计前后版本。
2. 保存与收货并行，检查两个请求成功及采购数量、已收数量、库存、预留、流水、费用和审计。
3. 保存与既有收货冲销并行，检查冲销记录、库存、预留、流水和审计。
4. 已有收货与预留下，在成本保存审计写入处注入失败，逐行比较成本归属与预留，检查版本、费用、流水及资金记录无意外变化。
5. 两张不同采购单关联同一 SKU，第一笔成本保存持有 SKU 行锁，第二笔成本保存必须等待该事务；检查真实收货支持的两个订单预留、两次审计及金额与流水。

并发工作线程使用独立 PostgreSQL 连接和不同 `pg_backend_pid()`；测试钩子在真实业务事务已取得采购单行锁或 SKU 行锁后暂缓第一个请求，并通过 `pg_blocking_pids()` 确认第二个连接实际被第一个连接阻塞，随后释放。数据库语句超时 20 秒。钩子只用于测试协调，不替代数据库锁；当前未在 PostgreSQL 实测，不能声称锁点已经通过。审计失败测试为单事务故障注入，并非并发故障注入，增加 CRM 全模型行级快照对照。

## 实际运行

Windows，指定 CPython **3.12.16** / Django **6.0.9**；`backend/requirements.lock` 的 16 个精确版本逐项核对一致，`pip check` 无冲突。没有安装新依赖。`APP_STAGE=development`、`DATABASE_URL=sqlite:///:memory:`，MEDIA_ROOT 为新生成临时路径。没有连接业务数据库。

命令（从 `backend` 执行）：

```powershell
python manage.py test crm.tests.test_postgres_concurrency crm.tests.test_iss039_shared_purchase_costs crm.tests.test_purchase_costs --verbosity 2
```

实际使用的解释器为 `C:\Users\Johnson\AppData\Local\Temp\sunjack-cpython312-verify-20261031-a37d\shared-venv\Scripts\python.exe`。首次结果：**37 项，18 通过、19 跳过、0 失败**；当时四项新增 PostgreSQL 场景均跳过。原始输出：[sqlite-test.raw.log](sqlite-test.raw.log)。

后续显式仅在本地进程解除类的 PostgreSQL 跳过，并将三个竞争场景及新增 SKU 场景的竞争辅助函数临时替换为顺序执行，验证夹具和结果断言：**4 项通过**，见 [三个场景](sqlite-sequential.raw.log) 和 [SKU 场景](sqlite-sku-sequential.raw.log)。另以 SQLite 运行未经顺序替换的审计失败回滚测试 **1 项通过**，见 [回滚日志](sqlite-rollback.raw.log)，其中异常堆栈是测试主动注入。该临时进程级覆盖未修改测试源码的 PostgreSQL 保护；这些结果不验证 PostgreSQL 锁或并发。

本机未发现 `postgres`、`pg_ctl`、`docker` 命令，localhost:5432 未监听；本次没有访问其他服务器。**真实 PostgreSQL 并发结果 BLOCKED，测试和预期未经 PostgreSQL 实测，不得视为已通过或无缺陷。** 请协调线程在受保护的 PostgreSQL 17 CI 测试库运行完整套件，保留测试名、结果及精确 SHA；若失败，先检查真实日志，不降低断言或绕过清理/审计触发器。前端与真实 Chrome 非本次测试代码改动范围，未运行。

当前尚未发现经复现的业务缺陷，因此没有修改业务实现。ISS-006 和 ISS-039 的全量验收及独立复审仍待完成。
