# 历史承接—财务 v1 跨包契约测试

日期：2026-11-04
集成分支：`codex/r1-prelaunch-consolidation-20261104`
测试时 HEAD：`673ae3724b5db8d69018acbcea3e26c904c3fea3`

## 来源与范围

- 财务稳定来源 `3a07e7ef1a9e63c98077d45492ba23b798c7fcdd` 和历史承接稳定来源 `a0729a0965850028fe52f5b6fcc3e825f23b1289` 均经 `git merge-base --is-ancestor` 核实为测试时 HEAD 的祖先。
- 契约依据：[CONTRACT-v1.md](../finance-closeout-batch-20261104/CONTRACT-v1.md)。历史流程复用 `backend/crm/tests/test_history_takeover.py::HistoryTakeoverFixtureMixin` 的合成工作簿、`application_and_group()` 上传申请路径，以及真实审核/执行 API。
- 本轮仅新增 `backend/crm/tests/test_review_history_finance_contract.py` 和本报告。没有改产品代码、迁移、台账或既有 fixture；没有提交。
- SQLite 单测使用内存测试库；另在隔离 PostgreSQL 全量回归中执行同一测试。两者均使用合成历史工作簿、受控临时媒体目录及合成 PDF；没有运行正式历史迁移执行器，也没有连接真实业务数据库。

## 已验证契约

1. **历史申请、审核和执行只建立 handoff。** 测试经实际上传申请、审核批准和执行 API 得到 finance handoff，其中保存两个历史收付款来源。执行结果仍为 `not_connected`，且在财务正式服务调用前没有新增 `FinanceFact`、旧 `Transaction`、`PaymentPlan`、库存流水或预留。
2. **资金事实通过财务官方服务显式建立。** 测试使用 `finance_closeout.create_account()` 建立合成自有人民币银行账户，通过 `finance_closeout.upload()` 上传并存储合成 PDF，再从 handoff 的 `TX-SO-1` 来源明确填写实际日期 `2024-09-03`、人民币金额 `287.43`、`source_system` 和唯一 `source_key`。来源原行为 USD；测试不从原币或汇率推算人民币金额。
3. **请求与来源幂等。** 同请求键、同内容重放返回同一指令；同请求键、改金额被拒绝；改用新请求键重复提交同一来源，在记账时被拒绝；已记账指令重放返回同一事实，唯一来源只保留一条 `FinanceFact`。
4. **真实性状态限制统计。** `needs_verification` 和 `simulated` 指令均保持待处理；审核和记账均被拒绝，且没有生成 `FinanceFact`。财务 `reporting_events()` 只返回已核实且实际记账的合成事实。
5. **审计身份及原始来源保持。** 财务发起人、复核人和记账人为三个不同的认证合成用户；测试核对 `FinanceInstruction`、`FinanceFact` 的持久操作人以及对应 `OperationLog.operator_id`。资金写入后，历史 group source rows、finance handoff payload 和 `HistoryTakeoverSourceRecord.source_snapshot` 均保持原值；旧 `Transaction` 与库存记录数量不变。

测试刻意不把 `not_connected` 改名或改状态。手工显式映射通过真实财务服务建立一条受控合成事实，证明 v1 契约可供受控调用；历史执行器本身仍未自动连接财务。

## 测试结果

命令：

```text
$env:DATABASE_URL='sqlite:///:memory:'
$env:APP_STAGE='development'
$env:PYTHONDONTWRITEBYTECODE='1'
python manage.py test crm.tests.test_review_history_finance_contract --verbosity 1
```

实际运行输出已保存在本报告中（本轮不重跑测试）：

```text
Creating test database for alias 'default'...
.
----------------------------------------------------------------------
Ran 1 test in 4.731s

OK
Destroying test database for alias 'default'...
Found 1 test(s).
System check identified no issues (0 silenced).
```

退出码：`0`。通过 1，失败 0，错误 0，跳过 0。该次测试时 HEAD 为 `673ae3724b5db8d69018acbcea3e26c904c3fea3`；测试文件之后已进入当前集成 HEAD。Django system check 报告无问题。
- 首次运行有 1 个测试错误：新建模型实例返回的 `actual_date` 仍为输入字符串，测试在调用 `.isoformat()` 时出错。测试改为从数据库刷新事实后再验证持久日期，并增加了事实与真实合成凭证关联及文件存在断言；重跑通过。未改业务服务。
- 两次测试只证明各自隔离数据库中的合成流程和已执行断言；不作为生产服务身份、真实历史资金或生产 handoff 验收证据。

### PostgreSQL 17 全量回归

- 当前集成 SHA：`1f189c3f74fda2908620dd3860230d860f1cbb43`；PostgreSQL 全量日志中的 `test_history_handoff_requires_explicit_finance_v1_mapping ... ok`（`logs/postgres-full-all-sources-1f189c3.log` 第 2071 行）证明本契约测试在该集成版本的 PG 全量中通过。
- 全量结果：`Ran 1312 tests in 1008.032s`，`OK (skipped=30)`；即 1282 通过、30 跳过、0 失败，`POSTGRES_REGRESSION_EXIT=0`。恢复演练记录的 PostgreSQL 版本为 17.11。
- 同一集成 SHA 的 SQLite 全量日志 `logs/backend-full-all-sources-1f189c3.log` 也记录本测试 `... ok`（第 2012 行）；该次全量为 1312 项、1251 通过、61 跳过、0 失败，816.678 秒。
- PG 与 SQLite 结果均为各自全量套件中的 1 项通过，不是另一次单测运行；此前专门 SQLite 单测仍单独记录为 1/1，通过时 SHA `673ae3724b5db8d69018acbcea3e26c904c3fea3`。
- 本结果验证的是合成历史申请/审核/执行与显式调用财务官方服务的契约。生产 handoff 仍为 `not_connected`，不证明生产导入自动创建财务事实，也不替代真实资料授权、生产账户或正式员工身份验收。

## 仍未接通与外部门槛

- **生产 handoff 仍未接通。** `HistoryTakeoverHandoff.status`、`HistoryTakeoverGroup.finance_handoff_status` 保持 `not_connected`；没有自动创建财务指令或事实。本测试的财务映射是测试代码显式调用服务，不代表生产导入已集成。
- **真实资料仍待授权和核实。** 投入真实历史资料前，需由业务/财务负责人授权提供并确认原始来源、原始凭证及其使用权限、实际人民币金额与银行入账日期、资金账户归属、唯一来源键映射和复核责任人。不得用历史外币金额、订单日期或参考汇率补造实际 CNY 事实。
- 正式历史资料迁移、生产账户建立、真实凭证上传及正式员工身份验收均不在本测试授权范围内；本报告不宣布历史资金正式接通或可导入。

## 交付前CI更新

代码1f189c3的CI41829100528最终为Backend/PG成功、Frontend失败（ISS039快照子进程2项）。已保留原始失败证据并最小补修有界输出缓冲/诊断；大快照2/2、受影响Chrome2/2和Node179/179通过，原全库/业务/权限断言保留。最终完整前端与精确SHA三CI见统一交付回执，本文各早期运行中/待验句仅保留当时状态，不是当前通过声明。后端全量1312项SQLite/PG均无失败，PG额外8命令专项8/8；未关闭Issue或替代ChatGPT独立复审。
