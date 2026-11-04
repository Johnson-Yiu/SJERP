# 财务来源静态预审

## 审查边界

- 固定来源：`codex/finance-closeout-batch-20261104`，SHA `3a07e7ef1a9e63c98077d45492ba23b798c7fcdd`。
- 来源父提交：`e6e841f10e758ec1d589cd674b6c20beaaebaa85`；与集成基线 `4388947d70d26bca66ca0bfc76b2383a2fc0d404` 的改动按该固定 SHA 检查。检查时本地分支和 `origin/` 跟踪引用均指向固定 SHA。
- 本文是 Codex 开发侧静态预审，不是独立 ChatGPT 复审。未修改业务代码、台账或来源分支；未运行测试、CI、真实 HTTP 或 PostgreSQL。初审时 CI `41815451746` 尚未独立查询；后续主审已确认远端该运行三项成功。该结果作为主审交接证据记录，不表示本预审自行重跑或独立查询 CI。
- 重点检查事实真实性及统计、完整更正、转账本金与手续费、不可覆盖、双人审批、审计原子性和幂等。

## 主审合入与证据核对补记

以下为主审后续提供的集成核对结果，不改变上文针对固定财务来源 SHA 的静态语义结论：

- 主审确认固定 SHA `3a07e7ef1a9e63c98077d45492ba23b798c7fcdd` 已完整合入，11 个来源提交均在集成结果中；远端 CI `41815451746` 的三项检查均成功。
- 唯一提及的路径冲突是 `cash-duplicate` 浏览器测试证据目录标识。主审保留了财务来源受控 voucher helper，并采用本包 `fixtureRoot` 隔离路径处理；没有因此删去财务证据。
- 集成证据文件 [`finance-evidence-verification.json`](finance-evidence-verification.json) 记录 `accepted_source=3a07e7ef1a9e63c98077d45492ba23b798c7fcdd`、`manifest_source_head=e6e841f10e758ec1d589cd674b6c20beaaebaa85`，112 条路径、112 个唯一路径，112/112 的清单摘要与 Git 索引字节摘要匹配。此处采用核对文件中的 **112** 计数，修正此前交付消息的 **109**；本预审没有重新计算每项 SHA。
- 上述合入、CI 与证据完整性结果不自动解决本报告第 1 节的真实性读端/持久层防护缺口，也不改变双人审批范围需要确认的结论。主审负责的综合回归仍以集成版本自身证据为准。

## 结论摘要

正常服务写入路径对待核实/模拟指令有明确拒绝；更正、显式转账匹配、银行净额与独立手续费的实现及相应测试大体符合约定。已记资金事实禁止普通覆盖，关键服务将写入与审计放在同一数据库事务，重复请求有稳定重放处理。

有一项具体的代码级防护缺口：`FinanceFact.truth` 未受模型/数据库约束，多个余额和报表读取路径也不筛选 `truth`。固定 SHA 中唯一搜索到的正常事实写入点 `post()` 会拦截非 `verified` 值，因此没有发现经支持 HTTP 操作可绕过该检查的路径；但任何内部 ORM 写入者若误建待核实/模拟事实，它会被当前正式统计读取端接受。该差异需要主审决定是否在集成前以持久层约束和/或统计读取条件封闭，不能把目前的服务层校验描述为全路径不变量。

双人复核的范围是指定敏感操作，不覆盖每一种实际收支。若验收口径要求每笔实际资金都经另一名真实认证员工审批，需要业务负责人明确后再判定当前范围是否足够。

## 按业务约定核查

### 1. 待核实或模拟事实不进入正式统计

**支持的服务/API路径有拒绝保护。** `normalize()` 默认 `truth=needs_verification` 并仅接受三种枚举值；`approve()` 和 `post()` 都要求 `verified`，`post()` 在创建 `FinanceFact` 前再次检查真实性。待核实及模拟测试提交指令后调用 `post()` 会被拒绝（`backend/crm/services/finance_closeout.py:214-233,298-310,349-364`；`backend/crm/tests/test_finance_closeout.py:78-89`）。未发现另一个业务服务或迁移代码在固定 SHA 中创建 `FinanceFact`；唯一 ORM 创建点是 `post()`（同文件 `:449-452`）。

**确定的条件性防护缺口。** `FinanceFact.truth` 是普通 `CharField`，`Meta.constraints` 没有真实性枚举约束，`save()` 只保护已存在对象不被更新（`backend/crm/models.py:2048-2078`）。读端也不检查真实性：账户余额从 `account_rows()` 读取该账户全部事实（`backend/crm/services/finance_closeout.py:514-539`）；`reporting_events()` 按日期取事实并只排除基准、已匹配/被更正记录及零更正，没有 `truth` 条件（同文件 `:553-577`）；`fact_data()` 会对未排除的普通事实设置 `company_flow_included`，`flow_rows()` 也读取日期范围内全部事实（`backend/crm/finance_closeout_api.py:40-70`）。后两者被实际资金 API 和 `actual_cash` 报表使用（`backend/crm/actual_cash_api.py:71-75`；`backend/crm/reporting.py:77-81`）。

**最小复现（静态推演，未执行）：** 建立一个 `truth="simulated"` 的待处理指令后，直接用 `FinanceFact.objects.create(instruction=..., account=..., voucher=..., truth="simulated", amount=..., direction=..., kind="cash", ...)` 建立一行；当前模型未拒绝该新增。随后 `reporting_events()` 会返回它，财务明细会把它标为纳入公司流量；若账户已有基准，`balance()` 也会将其计入。此复现需要内部 ORM 写入权限，**不是已发现的 HTTP/用户端绕过**。

**关闭所缺：** 在固定来源或集成代码中证明所有事实创建均被不可绕过地限制为已核实，或在模型/数据库层拒绝非 `verified` 的事实并让余额、明细、CSV、实际资金及经营报表对真实性状态采用一致条件；补一条模拟/待核实事实不能进入这些读端的回归测试。主审应记录选用的约束边界和测试结果。

### 2. 更正是完整替代事实，不是新增支出

更正要求关联同账户原事实；已有后续依赖、退款或本金关联时拒绝直接分叉。过账创建新的完整版本，不改原记录；统计排除被替代原事实并纳入有效更正，零金额更正不制造现金流。余额也按更正关系排除旧版本。相应测试验证原金额保持不变、旧期间流量移除、新期间只呈现替代金额、余额和对账指纹变化（`backend/crm/services/finance_closeout.py:403-425,523-539,542-550,569-578`；`backend/crm/tests/test_finance_closeout.py:109-124`）。`FinanceFact.save/delete` 及自定义 queryset 阻止通常 ORM 更新、删除；测试覆盖 `.update()` 和 `.delete()` 拒绝（`backend/crm/models.py:2077-2084`；测试 `:239-252`）。

### 3. 内部转账本金排除，手续费不重复扣

转账只有在两端为不同账户、方向相反、金额相等且性质明确为 `internal_principal` 时才能匹配；差额不会被推断为手续费。匹配前本金仍可见，匹配后公司流量排除两端，账户明细仍保留原两笔事实；独立手续费仍作为另一笔费用保留（`backend/crm/services/finance_closeout.py:471-494,553-577`；测试 `backend/crm/tests/test_finance_closeout.py:125-140`）。

旧银行流水以 `bank_net_amount` 计入统计，`fee_mode=included` 的费用只作为说明字段，不会从净额再减一次。独立费用必须是独立 CNY `bank_fee` 事件；`fee_for` 仅允许关联 `fee_mode=none` 的已确认结汇，阻止同一笔已含手续费的结汇再挂独立费。汇总逐行直接使用净额（`backend/crm/services/cash_events.py:217-228,269-272`；`backend/crm/actual_cash_api.py:78-98`）。测试包含“含费结汇净额 710、独立手续费 5、净流量 705”及禁止重复关联（`backend/crm/tests/test_cash_events.py:148-157`），新账户转账测试也确认独立费保留（`test_finance_closeout.py:125-134`）。

### 4. 原事实不可覆盖

新账户事实保存后不能再次 `save()` 或删除，普通 queryset 更新/删除受保护；新旧银行流水更正都以关联原事实和新增更正事实表达，不覆写原流水。修正限制包含已有退款、匹配或后续事实等依赖，避免更正后释放来源或改变历史核实基础（`backend/crm/models.py:2048-2084`；`backend/crm/services/finance_closeout.py:403-425`；`backend/crm/services/cash_events.py:169-177`）。该结论针对应用模型/服务路径；数据库管理员直接改表不在应用级保护范围内。

### 5. 真实认证双人审批、审计原子性、幂等

- `APPROVAL_KINDS` 明确为 `opening`、`correction`、`refund_approval`、`refund_payment`。审批要求当前审批者是认证用户、指令创建者记录为认证用户且两者 user id 不同；开发身份不能作为审批人。敏感类型过账要求状态已批准（`backend/crm/services/finance_closeout.py:24,298-315,367-368`）。身份写入复用 `cash.actor()`，认证用户落真实 user id，开发身份保持独立标记（`backend/crm/services/cash_events.py:59-66`）。分权测试覆盖创建者自批、匿名审批拒绝（`backend/crm/tests/test_finance_closeout.py:165-179`）。
- 双人审批**不是所有流水的统一要求**：`cash`、`bank_return`、`refund_return` 不在上述集合；由有相应权限的已认证操作人提交且声明 `verified` 后可单人过账。当前测试夹具也按此方式创建普通现金事实（`test_finance_closeout.py:30-47`）。若业务口径要求每笔实际资金或转账匹配都必须另一人批准，这是需要明确的流程缺项；现有代码和合同体现的是敏感类型双人审批。
- `submit/approve/cancel/fail/post/match_transfer` 使用事务；资金事实、指令状态及 `OperationLog` 在同一事务内写入。审计失败测试验证过账事实与状态回滚；银行事件测试验证登记、确认审计失败时事件/分配/状态回滚（`backend/crm/services/finance_closeout.py:270-294,297-315,348-455,470-494`；`backend/crm/tests/test_finance_closeout.py:194-201`；`backend/crm/tests/test_cash_operation_audit.py:17-47`）。生产阶段设置要求 `AUDIT_LOG_ENABLED=true`（`backend/config/settings.py:75-77`）。
- 相同 `request_key` 与规范化内容重放原指令；同键不同内容冲突。`source_system/source_key` 唯一，避免同源重复过账；重复过账返回现有事实。PostgreSQL 并发测试覆盖同键创建、重复过账、累计退回/退款上限及并发更正（`backend/crm/services/finance_closeout.py:271-294,349-356,449-452`；`backend/crm/models.py:2070-2073`；`backend/crm/tests/test_finance_closeout.py:53-66`；`test_finance_closeout_concurrency.py:15-120`）。并发测试有 `skipUnless(connection.vendor == "postgresql")`，因此仅在真实 PostgreSQL job 执行时才构成该项证据；本预审未重跑，也未独立核实 CI job 的数据库及通过状态。

## 复审交接

1. 优先处理或接受第 1 节真实性持久层/读端缺口；在补强前，结论应限定为“受支持的过账入口拒绝非 verified”，不能扩大为“所有可能写入的事实均不会进入统计”。
2. 由业务负责人确认双人复核是否只适用于 `APPROVAL_KINDS`，还是覆盖普通现金、退回及转账匹配。
3. 综合验收需在实际 PostgreSQL job 中确认并发测试没有被跳过，并用部署认证身份核对两人审批权限、审计开关及失败回滚。来源给出的 CI 成功声明不替代上述精确证据。

除上述真实性防护缺口及双人审批的策略范围确认外，本次限定静态检查没有提出其他确定的财务语义缺陷；这不等价于独立复审或综合验收通过。

## 服务入口负路径 SQLite 复验

按后续要求新增隔离回归 `backend/crm/tests/test_finance_source_semantics.py`，只经 `finance_closeout.submit/approve/post` 和正式统计读取入口操作；没有直接写入待核实或模拟 `FinanceFact`，没有修改产品模块或模型。

- 执行命令：`manage.py test crm.tests.test_finance_source_semantics --verbosity 2`。
- 环境：项目 Python 3.12 venv；`APP_STAGE=development`、`AUDIT_LOG_ENABLED=true`、`DATABASE_URL=sqlite:///:memory:`。Django 建立并销毁内存 SQLite 测试库；不连接 PostgreSQL 或共享业务库。测试凭证媒体文件使用 fixture 的临时 MEDIA_ROOT。
- 结果：**2 项通过、0 项失败、0 项跳过**，运行 0.259 秒，退出码 0；Django system check 无问题，完整迁移至财务 0102 成功。
- `test_pending_and_simulated_commands_cannot_change_financial_statistics` 先通过服务流程建立期初与已核实基线，再分别提交 `needs_verification`、`simulated` 指令；审批和过账均被拒绝，指令仍为 pending，资金事实数量、余额、实际资金 API、资金明细总额和 `actual_cash` 报表总额与操作前完全相同。
- `test_effective_correction_transfer_principal_and_independent_fee_accounting` 验证原事实保留、完整更正成为有效版本；等额内部转账匹配后两端仍在账户明细但不计入公司流量，独立手续费仍计支出。期末余额为 `1047.00`，实际资金流入 `90.00`、流出 `3.00`、净额 `87.00`。
- 原始终端输出：[finance-source-negative-paths-sqlite.txt](finance-source-negative-paths-sqlite.txt)。

这组负路径结果证明受支持服务入口当前拒绝待核实/模拟指令且不改变相关统计；它**没有**消除前述内部 ORM 写入的静态条件风险，因为测试刻意没有绕开状态机创建正式事实。SQLite 结果也不替代主审的 PostgreSQL 集成回归。
