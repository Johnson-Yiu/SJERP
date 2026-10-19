# SUNJACK-ERP R1-READINESS-01 全系统试用准备与业务阻断问题审查

- 审查日期：2026-10-19
- 审查基线：`199a21e0f407ba9ad772a5dec86e0b30dbd0c9b5`
- 范围：客户、联系人、跟进、产品/SKU/供应商、报价/销售订单、采购/收货、库存/发货、财务、权限、附件、导入导出及跨模块关联。
- 数据边界：本轮只读审查；未连接、读取或修改真实业务数据库；未修改业务代码、模型、迁移、权限执行策略或历史数据。
- 结论：当前不具备真实员工内部试用条件。具备开发超级管理员身份下的隔离环境演练条件；完成 A 类门槛后，才可进入受控的小范围员工试用准备。

## 1. 前置核实与财务阶段收尾

当前工作树为干净的 detached HEAD，精确指向 `199a21e0f407ba9ad772a5dec86e0b30dbd0c9b5`。该提交只增加 R1-FIN-P3-B 原始日志、API/CSV/数据库对比和测试证据；没有业务代码变更。

R1-FIN-P3-B 的独立复审结论按本轮授权记录为：已授权的人民币实际资金、银行结汇、实际资金统计和旧账面折算参考兼容范围通过阶段性验收。该结论只覆盖报告中声明的已登记银行事实、确认边界、旧报表兼容和安全拒绝路径，不等同于生产就绪、公司全部资金覆盖、银行账户总账或自动汇兑损益。

财务问题状态保持：

- ISS-105：OPEN，实际资金统计启用日期和历史覆盖边界尚未由财务负责人确认。
- ISS-108：BLOCKED，已确认银行事实的退款、作废、反向更正和来源额度解除规则未确定。
- ISS-121：BLOCKED，未登记资金是否纳入公司覆盖、期初/期末余额定义及启用日未确定。

P3-B 精确基线 `c27abcb2e95b833c3a4f4c59161c3fcc7c1d4f64` 的 CI 证据：

- [Backend](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39248853218/job/118047375135)
- [Backend PostgreSQL](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39248853218/job/118047375494)
- [Frontend](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/39248853218/job/118047374997)

当前 `199a21e` 是上述功能提交的文档证据后继提交；GitHub API 未返回一个新的独立运行记录，因此不把文档提交冒充为新的代码 CI。最近一次功能验证的结果为 Backend SQLite 768（跳过 13 个 PostgreSQL 专属项）、定向 Backend 62（跳过 3 个 PostgreSQL 专属项）、Node 136、Vitest 635、Playwright 157、Build PASS；本地 PostgreSQL 和真实网络超时注入在报告中保留为限制，没有伪造 PASS。证据见 [R1-FIN-P3-B 验收报告](R1-FIN-P3-B-财务统计最终业务闭环验收.md) 及 [P3-B 原始证据](uat-evidence/r1-fin-p3-b/)。

## 2. 代码、测试和部署证据

前端路由已经覆盖经营概览、客户、联系人、跟进、产品、SKU、报价、订单、导入、组织权限、库存、采购、财务概览、应收、应付、财务流水、人民币资金和报表中心，见 `frontend/src/router.js`。后端 `backend/crm/urls.py` 注册了相应客户、供应商、采购、报价、订单、交易、付款计划、库存、发货、报表和人民币资金 API。

核心流程存在针对性自动回归：

- 客户、跟进、附件：`test_customer_h1.py`、`test_customer_ux.py`、`test_followup_safety.py`、`follow-up-richtext-and-attachments.spec.js`。
- 产品、SKU、供应商和采购来源：`test_product_workspace.py`、`test_sku_*.py`、`test_supplier_*.py`、`test_procurement.py`、`purchase-workbench.spec.js`。
- 报价、订单、履约和应收：`test_quotes.py`、`test_sales_safety.py`、`test_fulfillment.py`、`test_fulfillment_receivables.py`、`fulfillment-receivables.spec.js`。
- 库存、收货和冲销：`test_inventory_movement_reversal.py`、`test_r1a_reliability.py`、`inventory-workbench.spec.js`。
- 财务和人民币实际资金：`test_finance.py`、`test_cash_events.py`、`test_actual_cash_reporting.py`、`test_finance_retry_safety.py`、`test_finance_reference_basis.py`、`CashEventPage.test.js`、`FinanceDashboardPage.test.js`。
- 权限、数据范围、导入导出：`test_functional_rbac.py`、`test_sales_data_scope.py`、`test_finance_data_scope.py`、`test_procurement_data_scope.py`、`test_safe_csv_import.py`、`functional-rbac.spec.js`。

开发配置仍明确是开发身份：`backend/config/settings.py` 默认 `APP_STAGE=development`、`DJANGO_DEBUG=true`、`DEVELOPMENT_SUPERADMIN=true`、`RBAC_ENFORCEMENT=false`，并且 `AUDIT_LOG_ENABLED=false`。服务端通过 `backend/crm/permissions.py` 的 `development_superadmin_enabled()` 统一放行。CI 的 PostgreSQL job 使用 `APP_STAGE=staging`、`DJANGO_DEBUG=false`、`DEVELOPMENT_SUPERADMIN=false`，但这只是 CI 隔离，不是员工试用环境。

仓库没有可供本轮证明的数据库与媒体联合备份/恢复演练脚本或运行记录。台账 ISS-018 已明确记录该缺口；因此不能把 Git 提交、SQLite 文件或 PostgreSQL CI 当作可恢复备份证明。对象存储/CDN/反向代理 ACL 也不在仓库内可证明，见 ISS-017、ISS-047。

## 3. 各模块试用准备状态

| 模块 | 当前结论 | 证据与限制 |
|---|---|---|
| 客户、联系人、跟进 | B：可在受控范围试用 | CRUD、客户工作台和跟进安全回归已有；附件真实上传、预览、下载、历史快照和直链授权仍由 ISS-007 跟踪，不能把自动测试当作文件权限验收。 |
| 产品、SKU、供应商 | B：可试用但需先准备主数据 | 产品/SKU/供应商和来源选择有回归；ISS-023 的 SKU 销售模型完整性、ISS-024 的 SKU 供应来源仍是开放的数据准备事项。 |
| 报价、销售订单 | B：可试用但保留边界 | 报价/订单导航、快照、订单履约与回款派生状态有证据；ISS-001、ISS-004、ISS-106 等仍是待独立复审，ISS-021 合同变更没有专用正常 UI 审批闭环。 |
| 采购、收货、应付 | B：可试用但排除未决政策 | 独立采购、交易单位、分批收货和付款有 R1-A/P3-B 证据；ISS-005 待复审，ISS-006/022/024 仍需边界或业务政策核实。不得把 MOQ 或委托采购规则自行解释为硬限制。 |
| 库存、发货、冲销 | B：可试用但需记录流水 | 库存、发货和冲销服务层及前端回归存在；ISS-006 仍有历史异常/并发覆盖缺口，ISS-014、068、069 等保留待复审。试用期间必须使用隔离数据并保留库存流水核对。 |
| 财务收付款、应收应付、统计 | B：可在明确范围内试用 | R1-FIN-P3-B 通过已授权阶段性验收；实际资金只统计 confirmed 的 `RmbCashEvent`，未设置公司统计启用日。ISS-105、108、121 仍不可用来宣称全公司实际资金或安全完成复杂更正/退款。 |
| 权限、附件、导入导出 | A/B：员工试用前先过权限门槛 | 开发身份拥有全部权限且正式 RBAC 未启用；ISS-003 是全站员工身份/模块/数据范围验收门槛，ISS-055 的客户范围 API 回归仍 OPEN。导入 ISS-052、文件直链 ISS-017/047 的正式身份和部署 ACL 证据不足。 |
| 跨模块关联 | B：可用合成数据试跑 | 客户—报价—订单—采购—库存—财务导航和历史快照有多组回归，但尚未用真实员工身份完成端到端试用；跨权限委托、合同变更和文件直链不能纳入默认范围。 |

## 4. 试用前必须解决的问题

A 类只有以下三项，均已有台账记录，未新建或关闭 Issue：

- **ISS-003：全站正式身份和数据范围验收。** 目前只证明开发超级管理员路径；真实员工需要经过 `self/department/department_tree/all`、缺模块权限、跨模块关联、导出和文件 URL 的 API/UI 矩阵。未完成前不能让员工接触客户、财务或附件数据。
- **ISS-018：数据库与媒体联合备份恢复演练。** 必须在隔离试用环境执行备份、恢复、行数/金额/图片完整性校验和回滚记录。没有这项证据，试用中的真实录入无法安全退出。
- **ISS-055：跨客户数据范围 API 回归。** 这是 OPEN 的服务端范围缺口，必须用受限身份验证越权返回 404/拒绝且不泄露对象是否存在；不能只看前端隐藏入口。

ISS-017（外部媒体 ACL）、ISS-047（媒体持久化与迁移）、ISS-051（生产 secret/DEBUG/开发身份）属于部署/外部访问门槛；若试用环境不提供外部文件直链并保持隔离，可列为 B 限制，但进入外部访问或生产前必须完成。ISS-002 的依赖审计也应在对外开放前完成，内部隔离试用可先限制网络暴露。

## 5. 可带警告开始的范围

在 A 类完成、并建立隔离 staging 数据库与媒体目录后，建议只开放：

- 客户、联系人、跟进基础流程；
- 已准备好销售模型和供应来源的产品/SKU；
- 报价、销售订单、履约、采购、收货、库存和应收应付的合成/试用数据；
- 财务流水和人民币实际资金的“已登记银行资金汇总”，不把它当作公司全部资金；
- CSV 导入导出仅限经过模板校验的数据，保留原文件和执行结果。

本阶段明确排除：真实银行账户接入、复杂退款/作废/反向更正、统计启用日和期初余额决策、跨客户委托采购、合同变更审批、外部文件直链、完整银行账户余额和自动汇兑损益。相关操作遇到安全拒绝应记录为 BLOCKED，不绕过服务层。

## 6. 全部 Issue 的 A–D 治理矩阵

以下按台账每个 ID 的最后一次记录逐项重算；没有改变任何 Issue 状态。当前唯一 ID 123 个，状态计数为 OPEN 5、BLOCKED 24、NEEDS_VERIFICATION 27、FIXED_PENDING_REVIEW 57、CLOSED 10。

- **A：阻止真实员工内部试用（3）**：ISS-003、ISS-018、ISS-055。
- **B：内部试用可开始但必须警告/限制（82）**：ISS-001–002、ISS-004–007、ISS-017、ISS-019–029、ISS-035–039、ISS-043–047、ISS-051–054、ISS-062–070、ISS-074–078、ISS-080–087、ISS-089–098、ISS-100、ISS-105–121。这里的连续区间只表示包含端点的 Issue ID 集合；ISS-003、ISS-018、ISS-055 已从区间中单独归入 A。
- **C：可等待实际使用反馈或独立复审（31）**：ISS-008–016、ISS-030–034、ISS-056–057、ISS-059–061、ISS-071–073、ISS-079、ISS-088、ISS-099、ISS-101–104、ISS-122–123。C 包含已按限定范围 CLOSED 的事项（122、123 也属于已授权财务阶段的已关闭修复），不表示重新打开。
- **D：长期增强/暂不开发（7）**：ISS-040–042、ISS-048–050、ISS-058。它们是 Packing List 输出、客户年度洞察、共享报表模板、指标下钻、列表筛选或批量维护等增强/观察项，不是当前试用闭环的必要条件。

分类依据是当前代码、测试和 Issue 的最新证据，而不是历史汇总数字。FIXED_PENDING_REVIEW、NEEDS_VERIFICATION 和 BLOCKED 不因本报告自动转 CLOSED；ISS-105、ISS-108、ISS-121 的原状态保持不变。

## 7. 最小内部试用方案（待 A 类完成后）

参与人员建议为 3–5 名真实员工：销售 1–2 名、采购/仓库 1–2 名、财务 1 名；先不开放全员。每人使用独立的正式身份和最小模块权限，开发超级管理员只做支持，不作为员工验收身份。

建议周期为 5 个工作日，使用独立 staging 数据库和媒体目录，先导入少量已脱敏客户、产品、SKU、供应商和期初试用数据，再按以下顺序每天执行：客户/跟进 → 报价/订单 → 采购/收货/库存 → 收付款/应收应付 → 导入导出和跨模块返回。每一笔异常都保留 HTTP 状态、页面截图、数据库前后快照和操作人。

退出条件：

- 核心链路无 P0/P1 数据破坏、越权或不可恢复错误；
- 订单、采购、库存、收付款和应收应付的前后余额可由流水解释；
- 备份恢复演练成功；
- 受限身份的查看、创建、修改、导出和文件 URL 边界通过；
- 未决业务规则按清单拒绝或人工升级，没有通过绕过 API 取得“成功”。

发生越权、历史记录被覆盖、库存/财务余额不守恒、备份无法恢复或无法说明操作人的情况，应立即退出试用并冻结写入。

## 8. 推荐下一批任务

1. 以 ISS-003 为中心完成 staging 身份、模块权限、数据范围、导出和文件 URL 矩阵；不改变当前开发超级管理员约定。
2. 以 ISS-018 执行数据库+媒体联合备份恢复演练，明确 RTO/RPO 和回滚记录。
3. 修复或验证 ISS-055 的跨客户 API 范围；随后再进行最小员工试用。
4. 准备 ISS-023/024 所需主数据并补 ISS-007、019、020、052 的真实文件/导出证据。
5. 在业务负责人明确 ISS-105、108、121 后，另行安排财务规则和统计覆盖验收；不要在本轮重开已封版财务功能。
6. 将 ISS-001/004/005/006 等 FIXED_PENDING_REVIEW 交独立审查，不把自动化 PASS 当作关闭依据。

## 9. 最终判断

当前可以继续做开发身份、隔离数据库、合成数据的受控演练；不具备真实员工内部试用或生产部署条件。原因不是财务 P3-B 阶段未通过，而是正式员工身份/数据范围、备份恢复和跨客户 API 范围仍没有足够证据。R1-FIN-P3-B 的阶段性封版结论保留，ISS-105 OPEN、ISS-108 BLOCKED、ISS-121 BLOCKED 保留。

本轮没有启动正式员工 UAT、没有启用正式 RBAC、没有部署，也没有修改业务代码。完成文档提交后停止，等待 ChatGPT 独立代码、业务和视觉审查。
