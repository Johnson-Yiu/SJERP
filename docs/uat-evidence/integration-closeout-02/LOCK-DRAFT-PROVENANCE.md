# 906 PostgreSQL 草稿运行来源说明

日期：2026-11-05

范围：只读核验旧 906 草稿 PostgreSQL 日志及其运行来源。未重跑测试；未修改原始日志字节。

主审当时报告的后续测试提交：`a8400fb8deb1bfeaaf99e0498d8b4aa34ef48f3f`。这是后续验收背景，不表示本说明独立复验了该提交或当前 HEAD。

原始日志归档：[lock-draft-original-logs.zip](lock-draft-original-logs.zip)；逐成员字节数与 SHA-256：[manifest](lock-draft-original-logs.manifest.json)。ZIP 含 11 个原始日志成员，未转换日志内容。

## 结论

906 草稿的实际 PostgreSQL 测试运行是五次 `r2`–`r6`。每次均运行 7 项：4 通过、3 失败、0 错误、0 跳过；每次 `POSTGRES_REGRESSION_EXIT=1`，wrapper 结果为 `FAILED` 且记录 `cleanup=complete`。五次合计为 35 次测试执行、20 通过、15 失败、0 错误、0 跳过；这是重复运行的累计数，不是 35 个不同测试。

失败均落在 3 个并发阻塞观察断言。`r2` 的断言要求 `pg_stat_activity.query` 包含账户表名，但采样到的是之前的资金事实查询；`r3`–`r6` 的等待观测返回空，worker 在主事务释放后完成，测试因此未确认主事务确实阻塞了 worker。`r5`、`r6` 记录到了 worker 发出的真实 `FinanceAccount ... FOR UPDATE` SQL，但未记录到被主 backend 阻塞的状态。这些日志不证明相应服务场景通过，也不作为当前提交的 PostgreSQL 结果。

## 实际测试命令与退出码

- 日志记录的测试选择：`crm.tests.test_finance_integration_lock_order`。
- wrapper 源码 [`run-postgres-regression.py`](../review-integration-batch-20261104/run-postgres-regression.py) 第 178–181 行显示，其内部测试进程命令为：`<venv-python> <checkout>/backend/manage.py test crm.tests.test_finance_integration_lock_order --verbosity 2`。这与各原始日志中的 `POSTGRES_TEST_SELECTION` 一致。
- 用户提供的 PostgreSQL 17 工具目录（wrapper 必需参数 `--postgres-bin`）：`C:\Users\Johnson\AppData\Local\Temp\sunjack-iss018-pg17-d26bfa744cf54322af03ea964e90089f\pgsql\bin`。该目录来自任务上下文；旧日志未保存外层参数字符串。
- 外层 PowerShell/Python shim 的完整命令行未保存：**UNKNOWN**。外层进程退出码未写入这些日志：**UNKNOWN**。可证实的测试子进程退出码是 `1`，wrapper JSON 为 `status=FAILED`。
- 这些运行的应用 HEAD 均由日志记为 `90683506f5d9447974302d83c89ba27351d5dfd4`。每次运行的未提交测试文件 SHA 不同，详见下表；不能把某一次的结果套用到之后修改过的测试文件。

## 五次实际测试运行

| 日志 | 测试文件 SHA-256 | 用时 | 通过/失败/错误/跳过 | 测试进程结果 | 原始日志 SHA-256 |
|---|---|---:|---:|---|---|
| [r2（归档成员）](lock-draft-original-logs.zip#member=logs%2Flock-order-90683506%2Flock-order-postgres-r2-90683506-uncommitted.log) `logs/lock-order-90683506/lock-order-postgres-r2-90683506-uncommitted.log` | `a093d9aa8ba735a41f905df05001cc59aab70a71534563581c1467b6b686d928` | 5.963s | 4 / 3 / 0 / 0 | exit 1；`pg_stat_activity.query` 断言未匹配到账户表 | `10e892f50bea91e0e1bc4a7ae031a40d318222d372cce5a9cd59ff03faadf15a` |
| [r3（归档成员）](lock-draft-original-logs.zip#member=logs%2Flock-order-90683506%2Flock-order-postgres-r3-90683506-uncommitted.log) `logs/lock-order-90683506/lock-order-postgres-r3-90683506-uncommitted.log` | `5e3a8446146b76f31f6f498c36421136dd1a64a4f0c4b7543ab01ca1d23be01e` | 65.786s | 4 / 3 / 0 / 0 | exit 1；3 项未确认 worker 被主事务行锁阻塞 | `853843eaf21bb43b480c9c2f827e5232d1bad3307451e46099aed8e695b59ea9` |
| [r4（归档成员）](lock-draft-original-logs.zip#member=logs%2Flock-order-90683506%2Flock-order-postgres-r4-90683506-uncommitted.log) `logs/lock-order-90683506/lock-order-postgres-r4-90683506-uncommitted.log` | `5d686997c84d34d93d25787b66b16b1ed09cfc77b728c1735c2165675694bca5` | 67.665s | 4 / 3 / 0 / 0 | exit 1；3 项未确认 worker 被主事务行锁阻塞 | `bdeaa125960a28f29c1f1bd8ce35bce447836dcf8a64ec1ceb8edbbd2cd3e686` |
| [r5（归档成员）](lock-draft-original-logs.zip#member=logs%2Flock-order-90683506%2Flock-order-postgres-r5-90683506-uncommitted.log) `logs/lock-order-90683506/lock-order-postgres-r5-90683506-uncommitted.log` | `61a77c60213fc22e299a09f47b07267430c7764a06f6297710958956e69aa517` | 72.535s | 4 / 3 / 0 / 0 | exit 1；观察到真实账户锁 SQL，但 3 项等待状态未确认 | `c8cbc7df126f3fc069bad0f13e403b0eed997e8ded747cd781a514ee93871da1` |
| [r6（归档成员）](lock-draft-original-logs.zip#member=logs%2Flock-order-90683506%2Flock-order-postgres-r6-90683506-uncommitted.log) `logs/lock-order-90683506/lock-order-postgres-r6-90683506-uncommitted.log` | `e67cb654b8ad808e85fccd20af2f2a0be702f8a936efbbbf66517f26e3ec94d6` | 66.042s | 4 / 3 / 0 / 0 | exit 1；观察到真实账户锁 SQL，但 3 项等待状态未确认 | `219662d2d753055ccf86be9b3bc9dd2ed399aa0da88cbddb34b24c73426309f5` |

每个 `r2`–`r6` 日志尾部均保留 `POSTGRES_REGRESSION_EXIT=1` 及 wrapper 的 `cleanup=complete`。表中链接指向 ZIP 和对应成员名；原始成员字节数、SHA-256 见 manifest。

## 当时 clean-check 例外的准确范围

`r2`–`r6` 日志头部逐次记录：

```text
PG_DRILL_APP_HEAD=90683506f5d9447974302d83c89ba27351d5dfd4
PG_DRILL_UNCOMMITTED_TEST=backend/crm/tests/test_finance_integration_lock_order.py sha256=<该次运行对应的哈希>
PG_DRILL_DIRTY_ALLOWLIST=exact test file only; all other backend/templates paths clean
```

当时通过进程内临时替换 `IsolatedPostgresDrill._assert_application`，容许上述**单一未提交测试文件**，并要求 HEAD 固定为 906、`backend/templates` 下其他路径干净。该例外没有写回源码，但确实绕过了该运行进程对这一个测试文件的 clean-check 拒绝；因此 `r2`–`r6` 是带例外的未提交草稿运行，不应列作原 guard 下的验收。

## 其余 906 草稿链路日志

以下日志用于解释测试前的启动/保护门槛，不含有效的 PostgreSQL 测试通过结果：

| 日志 | 可证实结果 | 原始日志 SHA-256 |
|---|---|---|
| [初次启动（归档成员）](lock-draft-original-logs.zip#member=logs%2Flock-order-90683506%2Flock-order-postgres-90683506-uncommitted.log) `logs/lock-order-90683506/lock-order-postgres-90683506-uncommitted.log` | `pg_ctl.exe` exit 1：Windows restricted token 错误；wrapper 同时记录 DLL 清理拒绝及临时 root。该日志本身不证明后续人工清理；0 项测试结果。 | `bc615686e837d944dbb8eee4c6863bc80d9e676e8aec814e2998464c32031b9c` |
| [r1 clean-check（归档成员）](lock-draft-original-logs.zip#member=logs%2Flock-order-90683506%2Flock-order-postgres-r1-90683506-uncommitted.log) `logs/lock-order-90683506/lock-order-postgres-r1-90683506-uncommitted.log` | 因 backend/templates checkout 不干净而拒绝；cleanup complete；未进入测试。 | `e738ba0f3b95dd959d1fc85c72e172d19f46ef7d51d06f3a6497a56e54e4dc94` |
| [r7 clean-check（归档成员）](lock-draft-original-logs.zip#member=logs%2Flock-order-90683506%2Flock-order-postgres-r7-90683506-uncommitted.log) `logs/lock-order-90683506/lock-order-postgres-r7-90683506-uncommitted.log` | 要求精确 HEAD 906 且仅有指定测试文件时失败；cleanup complete；未进入测试。 | `92311bef3eb82c3eb288d77a40706d7408f2ab86d6c823491824dd8eec294212` |
| [r8 clean-check（归档成员）](lock-draft-original-logs.zip#member=logs%2Flock-order-90683506%2Flock-order-postgres-r8-90683506-uncommitted.log) `logs/lock-order-90683506/lock-order-postgres-r8-90683506-uncommitted.log` | 拒绝“exact two untracked test files”条件；异常日志未含测试计数或 cleanup 结果。 | `25a99d6a226110727d449ab62f3e277a337859b83d20f67b7f0a8e40e6a7ef22` |
| [906 最后草稿标记（归档成员）](lock-draft-original-logs.zip#member=logs%2Flock-order-90683506%2Flock-order-postgres-final-90683506-uncommitted.log) `logs/lock-order-90683506/lock-order-postgres-final-90683506-uncommitted.log` | 仅记录进程内 allowlist 标记，未含 PostgreSQL 测试输出；测试数量及进程退出码 UNKNOWN。 | `e5bc6d4129450f3383057a714735750318b5d833dc2eed3ad56837add866314c` |

另有 9af 中止草稿 [归档成员](lock-draft-original-logs.zip#member=lock-order-pg%2Flogs%2Flock-order-postgres-9af2a32-draft.log) `lock-order-pg/logs/lock-order-postgres-9af2a32-draft.log`，378 bytes，SHA-256 `f97d3749525a9ae094e24b7d392e11a930c5a8f74de4c1889225ecffd67daf0a`。其内容只表明启动草稿 wrapper 的意图；按协调要求在测试结果产生前中止，不计作 PostgreSQL 测试。

## 当前后续结果的边界

主审报告称提交 `a8400fb8deb1bfeaaf99e0498d8b4aa34ef48f3f` 在原 clean guard 下真实 PostgreSQL 25/25 通过，并完成恢复验收。本说明只归档 906 旧草稿来源，没有重验或替代该提交的结果；以主审对应的原始日志和恢复产物为准。
