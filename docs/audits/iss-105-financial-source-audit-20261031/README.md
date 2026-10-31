# ISS-105 财务资金统计来源审计

日期：2026-10-31  
分支：`codex/r1-iss105-financial-audit-20261031`  
固定基线：`bd324a8c3fb64af245c3afcabbd4301c84f7711c`  
审计方式：固定基线源码、迁移、自动化测试与已提交的财务验收报告静态核查。

## 结论摘要

现有实现已经把历史 `Transaction` 人民币折算参考与人工确认的人民币银行事件分开。新实际资金 API、报表与 CSV 仅聚合确认的 `RmbCashEvent.bank_net_amount`，按 `bank_date` 统计；未确认和已放弃事件排除。已登记结汇不新增客户收款或重新核销，含扣手续费不重复扣减，独立手续费按支出事件处理。

这不是完整的公司资金总账或余额系统。内部账户转账、跨银行字段级重复识别、现金资金账、期初基准及余额核算、银行对账与凭证化更正均未形成完整闭环。当前 API 明确返回 `coverage_configured=false`，页面也说明不代表全部资金、不推测余额。ISS-105 继续 `P1 / OPEN`；ISS-108（更正/退款资金来源政策）和 ISS-121（统计启用日/覆盖范围）继续按既有台账状态处理。

本轮未连接数据库、未运行会写数据库的测试、未修改业务代码、迁移或历史数据。报告中的测试覆盖判断来自源码测试及已提交的 P2/P3 验收记录，不代表本轮重新执行通过。

## 按确认规则逐项核对

| 规则 | 结论 | 依据/边界 |
|---|---|---|
| 1. 内部账户转账不计入公司整体流入/流出 | 未实现；存在误计风险 | `RmbCashEvent` 没有内部转账类型或成对账户转账关系；统计对每个确认事件按方向直接加总。没有跨账户抵销规则。 |
| 2. 已核实人民币银行资金按实际流水统计 | 已实现于登记且确认的子集 | `/api/actual-rmb-cash/` 及 `actual_cash` 报表使用事件净额、银行日期；范围并非公司全部资金。 |
| 3. 外币收款仅参考，结汇人民币只计一次 | 已实现于新实际资金报表 | 旧 `Transaction` 不进入实际资金聚合；实际 API 仅读确认的人民币事件。结汇不再次登记客户收款/核销。 |
| 4. 银行手续费独立处理 | 已实现 | 含扣费说明不二次扣减；独立 `bank_fee` 事件作为支出，既有定向测试覆盖。 |
| 5. 启用余额独立基准，不算新流入 | 未实现，且当前明确不推测 | 没有期初基准对象或入账流程；coverage 未配置。 |
| 6. 账面折算不得混入实际人民币资金统计 | 已实现来源隔离 | `cash` 来源使用 `Transaction` 并标为折算参考；`actual_cash` 来源独立使用 `RmbCashEvent`。旧参考金额的零值回退另见 FI-07。 |
| 7. 资金余额由基准余额及已确认变动核算 | 未实现 | 无账户级余额查询/账本，也无完整的账户变动集合，不能从当前统计计算可核实余额。 |
| 8. 重复流水识别考虑账户、日期、金额、币种、对手方、摘要 | 未实现；有重复统计风险 | 幂等只按 `request_key`，事件编号唯一；无银行流水候选比对或重复提示。模型未保存事件对手方/摘要字段。 |
| 9. 对账差异保留原始记录并凭证化更正 | 原记录保护已实现；更正闭环未实现 | 已确认事件禁止普通覆盖/删除；服务拒绝 `correction_of`，没有接受更正、差异单或纠正后的期间统计流程。 |
| 10. 现金与银行资金区分 | 部分实现 | 新统计专指银行事件；旧 `Transaction.payment_method` 是自由文本，没有现金/银行账户类型维度，未见独立实际现金统计。 |
| 11. 未确认资金不进正式统计 | 已实现于实际资金统计 | 两个统计消费路径均筛选 `status="confirmed"`；确认还要求人工确认标记、受控账户配置和凭证元数据。凭证内容校验限制见 FI-06。 |

## 问题清单（按严重程度）

### P1 — FI-01：内部账户转账没有独立建模或合并抵销，可进入总流入/流出

**类别：A / C / D（口径缺口、未实现、重复计数风险）**

`RmbCashEvent.kind` 仅支持结汇到账、人民币直接收付、独立银行扣费；事件只保存一组账户别名和方向。`actual_cash_api._summary()` 对所有可见确认事件按 `direction` 累加，报表也对每条事件直接取正负净额。未发现 paired transfer ID 或公司级统计排除内部转账的路径。因而若转账两腿以 `cny_direct` 作为收入/支出登记，系统没有能力识别并从公司整体流入/流出中同时排除；本轮未查业务库，不能断言已有错误记录。

- 代码：[`models.py`](../../../backend/crm/models.py#L1833)、[`cash_events.py`](../../../backend/crm/services/cash_events.py#L178)、[`actual_cash_api.py`](../../../backend/crm/actual_cash_api.py#L66)、[`reporting.py`](../../../backend/crm/reporting.py#L130)
- 当前测试：手续费/净额、CNY 直接收支和按事件聚合有覆盖；没有内部转账成对记录及公司总额不变测试。
- 最小建议：先确定账户与转账业务口径，再增加明确的成对内部转账事实（来源/目标账户、同一转账键、两腿/状态）；账户明细保留两腿，公司整体外部流入/流出排除它们。对旧记录不自动猜测或批量改类。

### P1 — FI-02：只有请求幂等，没有银行流水级重复识别

**类别：A / B / D（实际统计风险、测试缺口、重复计数风险）**

`event_no`、`request_key` 唯一只能阻止相同编号或相同请求键；`register_event()` 只按 `request_key` 查重。`bank_reference` 没有唯一/候选校验，且缺少明确的交易对手与银行摘要字段。因此改用新请求键、编号后，同账户、日期、金额、币种、对手方/摘要相同的重复输入不会被识别为候选重复，可能形成两条已确认统计事件。唯一约束也没有覆盖账户、银行日期、金额、币种和参考号组合。

- 代码：[`models.py`](../../../backend/crm/models.py#L1835)、[`cash_events.py`](../../../backend/crm/services/cash_events.py#L157)、[`cash_events.py`](../../../backend/crm/services/cash_events.py#L262)、[`0077_rmb_cash_events.py`](../../../backend/crm/migrations/0077_rmb_cash_events.py#L15)
- 当前测试：[`test_cash_events.py`](../../../backend/crm/tests/test_cash_events.py#L183)覆盖同请求键重放/冲突；[`test_cash_events.py`](../../../backend/crm/tests/test_cash_events.py#L132)证明相同金额可合法出现多次，但未覆盖多字段重复候选识别。不能简单将“同金额同日”设成拒绝条件，否则会误拒真实的重复金额交易。
- 最小建议：增加基于账户、银行日期、方向、金额、币种、对手方、摘要及银行参考号的规范化候选指纹/相似度检查；命中后先提示人工核实或要求显式确认，不静默去重。新增测试同时覆盖重复候选和字段相同但凭证证明为两笔的合法交易。

### P1 — FI-03：退款/对账差异没有可入账的银行更正闭环

**类别：C（未实现；当前安全拒绝是有意边界）**

事件类型没有银行退款/冲正种类；来源检查将退款、供应商退款和汇兑差额标为未明来源，退款与已有关联资金事件时服务拒绝自动退款；`normalize()` 对非空 `correction_of` 明确返回 400。已确认事件保留且禁止覆盖是正确的防污染措施，但因此并不能把退款或对账差异加入正式银行实际资金统计。ISS-108 文档已将更正日期、反向来源、银行撤回凭证、额度解除和审批规则列为 BLOCKED 决策。

- 代码：[`cash_events.py`](../../../backend/crm/services/cash_events.py#L133)、[`cash_events.py`](../../../backend/crm/services/cash_events.py#L163)、[`cash_events.py`](../../../backend/crm/services/cash_events.py#L349)、[`models.py`](../../../backend/crm/models.py#L1859)
- 当前测试：[`test_cash_events.py`](../../../backend/crm/tests/test_cash_events.py#L149)覆盖拒绝退款/作废/更正并断言原数据不变；没有合法凭证化更正的成功路径（当前也不应有，政策未决）。
- 最小建议：维持现有拒绝，不做覆盖、删除、自动释放或猜测性冲销。财务负责人明确更正日期/期间、银行凭证、反向来源、审批及额度处理后，另行实现追加式关联更正记录和原/更正事件并列追溯，再补双向迁移（如需）、事务、权限、报表期间和退款回归。

### P2 — FI-04：没有启用基准或可核算的账户余额

**类别：C（未实现；当前响应已正确披露限制）**

当前报表返回的是“已登记且已确认事件”流量；`coverage_since=null`、`coverage_configured=false`。没有账户期初余额/启用日数据模型、余额 API 或完整账户变动来源，故不能用已登记流量推出公司或逐账户余额，也不能把期初余额当新收入。历史 P3-B 验收明确记载不设启用日、不实现银行余额。

- 代码/证据：[`actual_cash_api.py`](../../../backend/crm/actual_cash_api.py#L109)、[`FinanceDashboardPage.vue`](../../../frontend/src/views/FinanceDashboardPage.vue#L189)、[P3-A验收](../../R1-FIN-P3-A-人民币实际资金统计与独立报表验收.md#L13)、[P3-B验收](../../R1-FIN-P3-B-财务统计最终业务闭环验收.md#L61)
- 当前测试：统计覆盖银行日期、确认状态及金额；没有余额基准/余额守恒测试。
- 最小建议：在财务负责人确认 cutover、逐账户启用余额、现金纳入范围及未登记资金处理前，继续不显示余额。批准后以独立期初基准和完整追加式账户变动建立余额，并测试“期初 + 已确认流入 − 已确认流出 = 期末”；未核实差异单列，不回写历史金额。

### P2 — FI-05：没有现金与银行的统一账户类型/独立现金资金统计

**类别：C / B（未实现、测试缺口）**

`Transaction` 只有自由文本 `payment_method`；无结构化账户及“现金/银行”类型。新 `RmbCashEvent` 明确是银行事实，但没有实际现金事件模型/统计源。因此银行统计本身没有混入旧账面流水，但现有模块不能按同一正式资金口径分别核算现金和银行，也不能完整汇总两者。

- 代码：[`models.py`](../../../backend/crm/models.py#L1786)、[`models.py`](../../../backend/crm/models.py#L1825)、[`models.py`](../../../backend/crm/models.py#L1833)、[`reporting.py`](../../../backend/crm/reporting.py#L31)
- 当前测试：覆盖银行事件权限/范围；未覆盖现金账户与银行账户分账、现金余额或两者合计。
- 最小建议：在业务确认现金登记范围后增加受控账户类型/账户标识和现金实际收支来源；保持 `book_rmb_reference` 与银行实际事实隔离，不按 `payment_method` 文本推断历史记录账户类型。

### P2 — FI-06：凭证哈希目前是人工填写格式值，不是系统核验过的文件哈希

**类别：B / D（证据真实性控制缺口）**

确认路径检查 `evidence_reference`、说明非空，且 `evidence_sha256` 为64位十六进制字符串；确认按钮参数是 `voucher_checked=true`。服务没有收到凭证文件或从受控凭证存储读取内容并计算哈希。因此该哈希证明的是操作者提交了一个格式正确的值，不证明对应文件存在、内容未变或来自银行。状态应理解为“人工声明核对”，不能作为系统已验证原始凭证的证据。

- 代码：[`cash_events.py`](../../../backend/crm/services/cash_events.py#L252)、[`cash_events.py`](../../../backend/crm/services/cash_events.py#L291)、[`CashEventPage.vue`](../../../frontend/src/views/CashEventPage.vue#L179)
- 当前测试：[`test_cash_events.py`](../../../backend/crm/tests/test_cash_events.py#L139)覆盖凭证元数据缺失及账户未配置拒绝；使用合成固定 SHA，不验证真实文件内容与哈希绑定。
- 最小建议：在确定凭证保存、隐私、权限和保留期限后，从受控附件对象计算并保存哈希，确认时校验文件/版本与引用；未提供该机制前保留“人工核实”措辞，不声称系统验证银行凭证真伪。

### P2 — FI-07：旧账面参考把 `rmb_amount=0` 当作缺值回退

**类别：A / B / D（参考统计金额语义风险，不是实际人民币资金混入）**

旧概览、旧报表和序列化均使用 `rmb_amount or amount * exchange_rate`。而 `rmb_amount` 是非空字段且默认0，零值也可能是有意义的已存值；当前测试 fixture 明确将其设为0并期待按汇率回退。该逻辑只用于标注为“账面人民币折算参考”的旧统计，未被新实际银行资金 API 使用，所以不构成已确认的实际资金与账面金额混算；但仍可能使旧参考统计无法区分“缺值”和“确认为零”。本轮未访问数据库，无法判断受影响历史行或金额。

- 代码：[`models.py`](../../../backend/crm/models.py#L1807)、[`views.py`](../../../backend/crm/views.py#L2371)、[`reporting.py`](../../../backend/crm/reporting.py#L128)、[`serializers.py`](../../../backend/crm/serializers.py#L2448)
- 当前测试：[`test_finance_reference_basis.py`](../../../backend/crm/tests/test_finance_reference_basis.py#L15)有零值回退预期；没有覆盖已确认零值与未计算值的独立表示。
- 最小建议：先只读盘点零值来源及历史兼容语义；未来在明确语义后用显式缺失状态/版本字段区分，不直接批量重算或覆盖历史 `rmb_amount`。

## 已有保护与测试覆盖

- 实际银行 API/报表/CSV共用确认事件和 `bank_net_amount`；`bank_date`作为日期，pending/cancelled 不进汇总：[`actual_cash_api.py`](../../../backend/crm/actual_cash_api.py#L66)、[`reporting.py`](../../../backend/crm/reporting.py#L93)。相关测试见 [`test_actual_cash_reporting.py`](../../../backend/crm/tests/test_actual_cash_reporting.py#L27)。
- 外币来源分配按具体 `Transaction` 行；核销不扣减结汇额度；分次/合并、超额拒绝、手续费、同键重试、旧记录不变、服务事务回滚和权限范围均有测试：[`test_cash_events.py`](../../../backend/crm/tests/test_cash_events.py#L86)。
- 已确认事件及来源快照的应用层覆盖/删除保护已测；退款、作废、更正的拒绝路径保持原值：[`test_cash_events.py`](../../../backend/crm/tests/test_cash_events.py#L149)。
- 迁移 `0077_rmb_cash_events` 是新增模型/约束，不批量改写 `Transaction`；迁移测试从0076旧状态逐条比较历史记录并验证旧金额精度：[`0077_rmb_cash_events.py`](../../../backend/crm/migrations/0077_rmb_cash_events.py#L15)、[`test_cash_events.py`](../../../backend/crm/tests/test_cash_events.py#L356)。
- 账面参考与实际银行资金的API、标签及CSV分开：[`finance_basis.py`](../../../backend/crm/finance_basis.py#L1)、[`views.py`](../../../backend/crm/views.py#L2439)、[`reporting.py`](../../../backend/crm/reporting.py#L649)。实际银行资金导出和报表中心 CSV 有回归：[`test_actual_cash_reporting.py`](../../../backend/crm/tests/test_actual_cash_reporting.py#L58)。

## 待补测试/决策顺序

1. 先确定并实现内部转账配对与公司汇总排除，再覆盖同日多笔、跨账户和一腿缺失/取消场景。
2. 设计银行重复候选字段和人工裁决行为；覆盖匹配重复、不同账户相同金额合法流水、相同参考号的业务含义。
3. 财务负责人先明确 ISS-108 的更正/退款规则，再测原记录不可变、凭证化更正、统计期间和额度关系；政策未定时继续拒绝。
4. 财务负责人确定 ISS-121 的启用日/覆盖范围与现金纳入范围后，另行设计期初基准、账户余额与现金/银行对账验收。
5. 明确凭证存储、哈希计算、可见范围及保留期；当前人工作业声明与系统内容验证要区分。
6. 只读盘点 `rmb_amount=0` 历史值来源后，决定旧参考口径如何表达未知；不得在此之前批量更新历史数据。

## 审计边界

本报告依据固定基线源码和仓库内验收记录，不含真实业务数据库抽样、银行凭证核验、PostgreSQL复跑、真实账户对账或本轮自动化重跑。P3-B历史回归结果不等于当前任务重跑。没有发现可以在不连库条件下证明的历史错误金额，也没有对任何既有流水作错误/重复定性。
