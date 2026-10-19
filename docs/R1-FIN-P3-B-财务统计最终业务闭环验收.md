# R1-FIN-P3-B 财务统计最终业务闭环与兼容性验收

- 验收日期：2026-10-19
- 基线：`c27abcb2e95b833c3a4f4c59161c3fcc7c1d4f64`
- 范围：R1-FIN-P0 至 P3-A-FIX-01 的人民币实际资金统计、结汇后端、前端页面、旧账面参考报表兼容性验收。
- 数据安全：仅使用隔离 SQLite `p3b-isolated.sqlite3`、合成客户/订单/交易和合成银行凭证；没有连接或修改真实业务库。
- 业务规则：D01-D08 未修改；没有设置统计启用日期，没有实现银行账户余额或自动汇兑损益。

## 1. 前置核实

基线 `c27abcb` 的精确 CI 均已 SUCCESS：

- [Backend](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39248853218/job/118047375135)
- [Backend PostgreSQL](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39248853218/job/118047375494)
- [Frontend](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39248853218/job/118047374997)

ISS-122、ISS-123 的独立复审通过结论已同步为 `CLOSED`。ISS-105 仍为 `OPEN`，ISS-108、ISS-121 仍为 `BLOCKED`；本轮没有关闭这三项，也没有新增业务Issue。

## 2. 隔离业务数据

合成数据包括：

- `P3B-SO-500`：USD500、已完成履约；一笔 USD340 收款，PaymentPlan 仍为 USD160 open。
- USD340 结汇（CNY2400，含扣手续费 CNY5）；同一 USD100 来源分 60/40 两次结汇（CNY420/CNY280）。
- USD30 + USD70 合并结汇（CNY710）。
- CNY直接流入 CNY100、流出 CNY20；独立银行扣费 CNY5。
- JPY100 按零位原币精度结汇 CNY5；历史 USD12.3401 四位流水仅分配 USD12.3400，保留 USD0.0001 尾差。
- 一笔 pending 和一笔 cancelled 事件用于统计边界。

数据库快照：11 条 Transaction、1 条 PaymentPlan、1 条 Order、11 条资金事件、12 条来源分配。确认事件统计为流入 CNY4002.90、流出 CNY25.00、净流量 CNY3977.90、9 条确认事件。`P3B-REC-340` 的原始 `rmb_amount=2421.9750` 与银行净到账 CNY2400.00 同时保留，实际资金统计没有读取前者。

原始快照和哈希见 [`p3b-db-snapshot.json`](uat-evidence/r1-fin-p3-b/p3b-db-snapshot.json)、[`p3b-fixture-summary.json`](uat-evidence/r1-fin-p3-b/p3b-fixture-summary.json)。

## 3. 场景矩阵

| 场景 | 结果 | 证据与结论 |
|---|---|---|
| A 外币订单→收款→核销→结汇→实际人民币统计 | PASS | 隔离库、真实 `/api/actual-rmb-cash/`、财务概览截图；结汇没有第二笔客户收款。 |
| B 单笔来源分次结汇 | PASS | USD100 来源分配 60+40，两个确认事件合计 CNY700，来源额度只消耗一次。 |
| C 多笔同币种来源合并结汇 | PASS | USD30+70 合并事件，两个来源分配合计 USD100，统计仅计 CNY710。 |
| D 预收款及后续核销与结汇独立 | PASS | 既有 `AdvanceAllocation`/计划测试通过；资金事件不调用核销、不改变计划余额。 |
| E CNY直接收付款 | PASS | `P3B-CNY-IN/OUT` 进入已确认统计，分别 CNY100/CNY20。 |
| F 含扣手续费与独立银行扣费 | PASS | USD340 事件净额 CNY2400、含扣 CNY5；独立 CNY5 另列一次，未重复扣减。 |
| G 已确认、待确认、已放弃统计边界 | PASS | 9 条 confirmed 进入汇总；pending/cancelled 各一条不进入 totals。 |
| H 退款、作废、来源不明安全拒绝 | PASS | 真实隔离库调用作废/退款均拒绝，前后交易哈希相同；原始确认事件保留。见 [`p3b-rejection-check.json`](uat-evidence/r1-fin-p3-b/p3b-rejection-check.json)。 |
| I 跨月份、跨年度和银行日期 | PASS | 2026-09、2026-10、2027-01 分月返回 2400、1485、92.90；使用 `bank_date`。 |
| J 旧四位小数及新币种精度 | PASS | USD 历史四位值未舍入改写，JPY100 原币保持零位业务规则；SQLite/服务测试和迁移保护通过。 |
| K 账面折算参考与实际银行资金并存 | PASS | 旧财务概览仍显示账面参考 CNY217；实际资金独立显示 CNY775（10月1–19日），文案明确不是利润/销售收入/余额。 |
| L API、概览、报表中心、CSV一致 | PASS | 全期实际 API totals CNY3977.90；报表 JSON/CSV 同为 CNY3977.90；CSV 明确使用银行净额列。 |
| M 统计/导出权限与数据范围 | PASS | `test_actual_cash_reporting`、`test_functional_rbac` 及 403 回归通过；事件可见性先于聚合，不能用聚合推断不可见批次。 |
| N 历史报表、保存配置和旧 API | PASS | `cash` 旧来源和旧 `/api/finance-dashboard/` 保持原响应结构；`actual_cash` 作为独立来源，报表预设和旧 URL 未改写。 |
| O 接口失败、超时、重试、快速切换日期 | PASS/局部限制 | P3-A-FIX-01 容错与日期竞态自动回归、全量 Playwright 通过；本轮真实页面验证正常加载和真实 HTTP。未对隔离 API 施加真实网络超时，故该子分支保留为环境限制，不宣称已做破坏性网络注入。 |

## 4. 金额与资金一致性

- 实际资金只聚合 `RmbCashEvent.status=confirmed` 的 `bank_net_amount`，按 `bank_date` 计入；pending/cancelled 不计入。
- 流入正向、流出负向；含扣手续费已经体现在银行净额，独立扣费只统计一次。
- 结汇事件没有创建第二笔客户收款，没有重新核销 `PaymentPlan`/`AdvanceAllocation`，订单履约状态、库存和采购销售金额不变。
- `Transaction.rmb_amount` 仅作为旧账面参考；真实 API 的 CNY3977.90 来自 9 条已确认银行事件。
- 数据库快照与安全拒绝前后哈希一致：拒绝作废/退款没有修改交易、计划、订单或资金事件。
- `coverage_configured=false`、`coverage_since=null`；系统只称“已登记银行资金汇总”，不声称覆盖公司全部资金，不推测期初/期末余额，不称利润或银行账户余额。

## 5. 真实页面与 HTTP 证据

使用真实 Chromium 访问隔离 Vite `5195` 和 Django `8104`，完成 1440/1280/1024 财务概览及 1440 报表/银行资金列表截图。页面展示银行实际资金、账面人民币折算参考、确认状态、原币来源、银行日期和净额；报表中心实际资金预设显示 `银行实际人民币资金` 与 `金额（银行实际人民币净额）`。

- [财务概览 1440](uat-evidence/r1-fin-p3-b/p3b-finance-1440.png)
- [财务概览 1280](uat-evidence/r1-fin-p3-b/p3b-finance-1280.png)
- [财务概览 1024](uat-evidence/r1-fin-p3-b/p3b-finance-1024.png)
- [实际资金报表 1440](uat-evidence/r1-fin-p3-b/p3b-report-actual-1440.png)
- [银行资金列表 1440](uat-evidence/r1-fin-p3-b/p3b-rmb-cash-events-1440.png)
- [真实浏览器 HTTP/可见文本](uat-evidence/r1-fin-p3-b/p3b-real-browser-http.log)
- [报表中心真实浏览器记录](uat-evidence/r1-fin-p3-b/p3b-report-browser.log)

原始 API/CSV：[`p3b-actual-full.json`](uat-evidence/r1-fin-p3-b/p3b-actual-full.json)、[`p3b-actual-oct.json`](uat-evidence/r1-fin-p3-b/p3b-actual-oct.json)、[`p3b-report-actual.json`](uat-evidence/r1-fin-p3-b/p3b-report-actual.json)、[`p3b-report-actual.csv`](uat-evidence/r1-fin-p3-b/p3b-report-actual.csv)、[`p3b-legacy-dashboard.json`](uat-evidence/r1-fin-p3-b/p3b-legacy-dashboard.json)、[`p3b-events.json`](uat-evidence/r1-fin-p3-b/p3b-events.json)。

## 6. 自动化回归

| 检查 | 结果 |
|---|---|
| Backend SQLite 全量 | PASS：768 项，跳过 13 项 PostgreSQL 专属；使用隔离 SQLite 和可写临时媒体目录。 |
| Backend 定向资金/权限 | PASS：62 项，跳过 3 项 PostgreSQL 专属。 |
| Node | PASS：136 项。 |
| Vitest（项目配置的 `tests/`，排除 Node 风格 typography 文件） | PASS：63 个文件、635 项。 |
| Playwright 全量 | PASS：157 项。 |
| Frontend Build | PASS：Vite 隔离输出目录构建成功。 |
| PostgreSQL 本地并发 | BLOCKED：本机未安装/未监听 PostgreSQL（5432 不可用）；P2-A/P3-A 基线 PostgreSQL CI 已 SUCCESS，本次最终精确 HEAD 的 PostgreSQL CI 仍作为交付门槛复核。 |

原始日志：[`p3b-backend-full-final-2.log`](uat-evidence/r1-fin-p3-b/p3b-backend-full-final-2.log)、[`p3b-backend-targeted-3.log`](uat-evidence/r1-fin-p3-b/p3b-backend-targeted-3.log)、[`p3b-node.log`](uat-evidence/r1-fin-p3-b/p3b-node.log)、[`p3b-vitest-tests-final.log`](uat-evidence/r1-fin-p3-b/p3b-vitest-tests-final.log)、[`p3b-playwright-full-2.log`](uat-evidence/r1-fin-p3-b/p3b-playwright-full-2.log)、[`p3b-build-2.log`](uat-evidence/r1-fin-p3-b/p3b-build-2.log)。

## 7. 兼容性与遗留限制

- ISS-105、ISS-108、ISS-121 继续按现有状态保留；没有自行关闭或改变 D01-D08。
- 统计启用日期仍未配置；不能把登记汇总解释为全公司实际资金。
- 本轮没有新增前端/后端业务代码，验收未发现需要安全合并的产品缺陷；只新增验收报告、台账/阶段记录和原始证据。
- PostgreSQL 真实并发需要在 GitHub PostgreSQL job 或具备 PostgreSQL 的隔离环境中继续核验；本地 BLOCKED 不伪造 PASS。
- 未进行真实网络断开/超时注入；既有 P3-A-FIX-01 的接口失败隔离、独立重试和日期竞态回归保留。

## 8. 阶段性封版结论

在 D01-D08 不变、统计启用日期仍未确定、PostgreSQL 由精确 HEAD CI 复核通过的前提下，R1-FIN 财务统计与人民币实际资金模块具备阶段性封版条件。该结论只覆盖本报告列出的已登记银行事实、旧账面参考兼容性和安全拒绝边界，不等同于公司全量资金覆盖、完整银行账户总账、自动汇兑损益或 ISS-105/108/121 关闭。

本次验收提交和最终精确 HEAD 的三项 CI 链接在交付后补记；完成后停止等待 ChatGPT 独立代码、业务和视觉复审，不进入 P3-C、正式 RBAC、员工 UAT 或部署。
