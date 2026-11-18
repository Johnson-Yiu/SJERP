# 财务交付遗漏复审（给协调任务整合）

## 基线与结论

- 固定审查基线：`3bb0970148ff98025d44d6c5ee42e17bfe180002`。
- 本轮实际源码：`/workspace/scratch/845e333a0b4f/candidate_review/source`。早期逐文件下载的不可变基线在 `finance_review/base`，原字节按 Git blob SHA 校验；没有用 e5ce 本地旧树冒充目标。
- 财务业务范围未确认新的功能遗漏。不能因来源分支不是祖先就恢复整分支：本轮检查的收款优化、退款归属、作废原子性、同账号恢复、原币实收与人民币银行事实分离均有后继实现。
- **确认且已接收的遗漏为 7 处财务展示文案**：财务概览 3 句、账户对账 4 句，来源 `a5869a50` / `01b6fe73`。仅恢复字符串，同步 2 条既有测试断言；业务服务、金额、权限、状态、模型和迁移不改。
- 本轮后端定向 84 项：71 通过、13 按环境条件跳过，0 失败。前端定向合计 46/46。不能据此宣布全站、PostgreSQL、真实 Chrome、ALEX 部署验收或所有历史需求完整。

## 已确认的遗漏与最小接收

| 文件/基线位置 | 实际遗漏 | 来源 | 已接收范围 |
| --- | --- | --- | --- |
| `frontend/src/views/FinanceDashboardPage.vue:65` | 仍为“构成明细加载失败” | `a5869a50` | 恢复“明细加载失败，请刷新后重试。” |
| 同文件 `:163` | 合同/账面/银行日期及当前余额说明仍为旧句 | `01b6fe73` | 按来源恢复等义自然文案，保留三个日期口径和当前余额不受期间影响的含义 |
| 同文件 `:197` | 银行/账户事实、凭证及毛流量说明仍为旧句 | `01b6fe73` | 按来源恢复等义自然文案，保留人工确认、自有归属、日期、凭证与排除启用基准/内部本金 |
| `frontend/src/views/FinanceLedgerPage.vue:82,130,161` | 保存、提交前核查、恢复失败仍用“请求身份”旧提示 | `01b6fe73` | 三句改“请求标识”，条件、阻断和会话存储不变 |
| 同文件 `:213` | 逐账户核对说明仍为旧句 | `01b6fe73` | 恢复差异归零与迟到记录/更正重新核对的说明 |
| `frontend/tests/finance-closeout.spec.js:31,49` | 两个既有用例断言旧提示 | `01b6fe73` | 仅同步预期文本 |

候选三文件精确 blob 在 `accepted_copy_files.json`；完整差异在 `accepted_copy.patch`。共有 7 处产品字符串和 2 处测试字符串，当前不会引入旧版页面结构。

## 按来源逐项复核

| 来源/主题 | 3bb 中实际证据 | 判断与接收决策 |
| --- | --- | --- |
| `75a6ff0843bc0b7c4a849fc3b61fd018486bdc84` 财务列表布局（分叉 1 提交） | `TransactionPage.vue:788,979,988` 有独立滚动容器、表格 `width:100%` / `min-width:850px`；`CashEventPage.vue:78,98` 有 `cash-table-wrap` 容器，table 保留正常表格显示并设全宽 | 主财务表的已知空表收缩修复已在 3bb，不能再次整文件覆盖。当前布局实测/Chrome由集成专项负责 |
| 同来源账户台账 grid→flex | 当前 `FinanceLedgerPage.vue:221` 为 `display:grid;min-width:0`；卡片使用 `repeat(auto-fit,minmax(min(100%,320px),1fr))` | CSS实现不同不等于需求丢失。未测得实际收缩，不为恢复关键字改布局 |
| `0f440a784130be326357cdf569ccb8959a560771` 汇总卡长数字（分叉 1 提交） | 当前 `SummaryCards.vue` 包含容器查询、`min-width:0`、`white-space:normal`、`overflow:visible`、`overflow-wrap:anywhere`、tabular-nums | 换行/不截断效果在后继实现中保留；响应断点与来源不同不作为遗漏 |
| `96ad680c7b0cd154914046bcbe63de23fb8e64e3` 作废审计、退款日期、同账号恢复（分叉 1 提交） | `views.py:3221–3249` 原子作废、`finance_void` 请求身份与重放；`:3302–3343` 验证实际退款日期、将日期纳入指纹及审计；`finance.py:1203,1260` 写入实际日期 | 来源修复实际保留；不能因 merge ancestry 缺失恢复旧 views.py |
| 同来源操作人/恢复防串账号 | `cash_events.py:444,458,475,519,521` 同操作人登记/确认重放；`finance.py:587–606` 操作人指纹及历史审计证明；`useFinanceAttempts.js` 账号分区与 ready 判定；收款、付款、结汇组件调用 | 源码保留；已跑当前收款、采购付款、应收应付、结汇组件定向回归 |
| `c978758f37db8b8acf5e751fc7aa836287163a6b` 收款优化（分叉 6 提交） | `finance.py:349–484,486–729` 明细凭证校验、已计入订单优惠不重复抵减、公司/客户承担手续费区分、客户实汇/实收/核销拆分、有效计划与额度锁定、原子写入/重放；当前 `test_finance_receipt_convergence.py` 为后继测试 | 旧 `test_finance_receipt_optimization.py` 文件不存在，不等于能力消失。后继服务和测试覆盖关键业务，不整包重放 |
| `52d924b05085e67bf97dc5a5cfac01b6ba48ed70` 统一财务流水入口（分叉 1 提交） | 共享 `CashEventEntryForm` 被 `TransactionPage.vue:849,956–959` 内联使用，详情及新收款两入口；`CashEventEntryForm.vue:176` 提交根收款 `source_receipt_id` | 共享内联结汇已保留。首发有意保留银行资金导航，不能回放来源中的隐藏导航 |
| 收款/费用与弹窗相关用户要求 | `TransactionPage.vue:93` 保留“其他期间费用（如水电费、物业费、软件订阅费等）”显示例子，存储 category 不改；已检财务弹窗无 `@click.self` 遮罩关闭 | 已有实现，不新增功能或改业务分类 |
| `60df1b045c06c7f2146b44e4a60866b1786024cc` 账面人民币参考标签（分叉 1 提交） | `0081_transaction_rmb_reference_label.py` 明确 `账面人民币折算参考`；当前 models / API / 测试区分账面参考和银行实际净额 | 元数据增量已保留，定向 4 个参考口径测试通过 |
| `a4b2ff4c53e117b2efffeb5af54813121887ce5f` 取消后退款/作废/更正/部分终止 | 以下 6 文件与来源 **逐 blob 一致**：finance.py、views.py、serializers.py、order_lifecycle.py、order_quantity_adjustments.py、OrderDetailModal.vue；详见下一节 | 财务核心源码无后续覆盖；`test_receipt_refund_attribution` 正常/拒绝/回滚用例本轮通过，2 PG竞争用例跳过 |
| `1cad93d0cb0297c33f764f6cb68d5c610512d9e4` actual-cash audit | 此分支唯一提交只有审计文档、日志与 probe_tests.py，未修改生产业务代码 | 不是待恢复业务分支；历史报告只作线索 |
| `phase-02c-finance-void-consistency` / `9150fcb31b1fc8aed86b4a131420b84d5bf3de50` | `test_finance.py:320,335,385` 递归作废/跨订单预收/子流水拒绝测试与 `finance.py:870` 当前作废服务仍在 | 末条跨订单作废测试未遗漏；本轮未逐条重放五个远古提交，不能将该抽查扩大为该分支所有历史差异接受 |
| `phase-02a-receipt-reversal` / `e0697eee363a57b4edf958b331b0557056549870` | 实为采购入库冲销，不是客户收款；当前 GoodsReceipt / reverse_receipt / 采购页有后继实现 | 已向核心代理交接，不将其列为财务收款缺失 |

## 取消退款来源逐 blob 保留证据

对比 `a4b2ff4c53e117b2efffeb5af54813121887ce5f` 和固定目标 `3bb09701`：

| 文件 | 两侧相同 Git blob |
| --- | --- |
| `backend/crm/services/finance.py` | `9c11133e56667db1749b371ddadd7f2a7f356990` |
| `backend/crm/views.py` | `8048543b10eee4addcedda34c57d1472b73ade65` |
| `backend/crm/serializers.py` | `be9daf7536fa183af75ff573ac1ff0b71352eb7e` |
| `backend/crm/services/order_lifecycle.py` | `66cf9ab3fc4ef3364f614a6c8c18d4ee3c1a45e4` |
| `backend/crm/services/order_quantity_adjustments.py` | `c7bea6acfe8d6faa1edddfb3dcd7f1d56549f8a5` |
| `frontend/src/components/OrderDetailModal.vue` | `16b95a983d13cc9c5b14026879a4f418cca97e81` |

`models.py` 后续有成本币种补修；`TransactionPage.vue` 后续有已知表格布局补修，不能要求整文件与更老来源相同。

## 不应恢复的旧实现

1. 不覆盖 `finance.py` 为 c978 版本：当前支持更强的真实现金/手续费信用拆分、凭证绑定、跨订单共享来源退款、取消后余额不复活、原始实际日期及账号身份重放。
2. 不恢复 c978 的旧迁移回填方式：目标 `0120_advanceallocation_cash_amount_and_more.py` 只在首次创建共享 cash_amount 列时回填；另一支 `0121_reconcile_legacy_fee_allocation_cash.py` 纠偏历史手续费现金拆分；`0123_merge_finance_receipt_histories.py` 保留双支历史并汇合。整体旧迁移回放会有覆盖已纠偏现金值风险。
3. 不将原 CashEventPage 文案补丁整页应用：当前表单已抽到 CashEventEntryForm。其账户名称选择、缺配置指引、“结汇信息已核对”“已找到原资金事件”等文案是后继等义实现；原 `请求键`/`后端预览` 技术性提示多数已消失。已核对位置 `:255,282,321,336,350–354,392,463–475,482,492`。
4. 不用回退旧代码来追求所有 branch head 成为祖先。当前业务结果和可追溯来源比“包含所有分支”更准确；这里不据局部审查证明全仓没有混入任何不需要的内容。

## 本轮实际验证

### 后端

Python：`/workspace/scratch/cfa5cd342276/audit/venv/bin/python`（父任务提供的锁定依赖环境）。在精确目标 backend 执行：

```sh
APP_STAGE=development DATABASE_URL=sqlite:////workspace/scratch/845e333a0b4f/finance_review/isolated.sqlite3 MEDIA_ROOT=/workspace/scratch/845e333a0b4f/finance_review/isolated-media /workspace/scratch/cfa5cd342276/audit/venv/bin/python manage.py test crm.tests.test_finance_receipt_convergence crm.tests.test_receipt_refund_attribution crm.tests.test_finance_reference_basis crm.tests.test_cash_events --noinput --verbosity 2
```

- Django 实际使用独立内存测试库 `file:memorydb_default?mode=memory&cache=shared`，测试清理成功；凭证夹具自行创建临时媒体目录并清理。
- 发现 84 项，71 通过、13 跳过、0 失败，退出码 0。
- 跳过的是 12 个 PostgreSQL 真实锁/并发用例和 1 个 PostgreSQL 历史升级用例；没有将 SQLite 说成并发证明。
- 测试日志包含 1 组原有表前后哈希一致的银行确认用例 `legacy_unchanged=true`；仅指该合成场景，非真实生产数据验证。
- 日志：`backend-targeted.log`。

### 前端

精确候选 frontend，Node 24.22.3（CI为22，环境不同需标注）：

```sh
node node_modules/vitest/vitest.mjs run tests/transaction-safety.spec.js tests/payment-plan-filters.spec.js src/components/PurchasePaymentModal.spec.js src/components/CashEventEntryForm.spec.js --environment jsdom
node node_modules/vitest/vitest.mjs run tests/finance-closeout.spec.js tests/finance-reference-basis.spec.js tests/finance-contract-navigation.spec.js --environment jsdom
```

- 第一组 4 文件 31/31；第二组 3 文件 15/15，均退出码 0。
- 第一组有 jsdom 的 `Window.scrollTo` 未实现提示，不影响测试断言通过，不能当作浏览器滚动实测。
- 日志：`frontend-targeted.log`、`frontend-copy-targeted.log`。
- 本轮未新增镜像实现的测试；同步既有行为断言并运行相关真实组件测试。

## 历史记录复核及验收边界

先检查目标代码及来源补丁，再读取以下目标版开发记录：

- `docs/uat-evidence/finance-completion-fixes-02/README.md`：原来源曾 PG94 与组件26通过、当时 Chrome待验。当前源码保留其要求，本轮只声明上述现测结果。
- `docs/uat-evidence/first-release-independent-review-02/README.md`：明确统一财务入口补丁已进 `0a3418d7`，后来迁移汇合、现金/手续费分离、凭证保护和原币退款强化；全站中文原未整包接收，不能把导航改名当中文完成。
- `docs/uat-evidence/cancel-refund-closeout-02/README.md`：取消后退款/作废/更正及终止履约来源验收，与6个当前相同blob相互印证；不把其历史Chrome/PG验收当本次新候选验收。
- 证据原文、blob与固定URL保存在 `historical_evidence.json`。

按AGENTS要求的真实Chrome视觉由UI/集成代理接续。UI代理已尝试本地浏览器：当前只有Chromium，且在创建页面前因 `socket() failed: Operation not permitted (1)` 退出，无截图；原始日志为 `/workspace/scratch/845e333a0b4f/ui_delivery_review/visual-tests.log`。不能标为Chrome或Chromium视觉通过，财务概览/Ledger视觉保留待验。全量CI、PostgreSQL并发与迁移、ALEX实际版本/资产校验由协调交付及Codex部署步骤完成。没有访问真实财务数据、执行生产写入、改变RBAC、合并master或推送。

## 最小交付建议

候选财务业务以 3bb 为底保留，加上上述 7 句已明确来源的展示恢复；将最终3文件新blob纳入发布源码清单。不要合并整条旧收款/布局分支。以最终候选SHA跑适用CI、真实Chrome与目标环境部署检查后再宣告可部署，不把本报告扩大为完整首发验收。
