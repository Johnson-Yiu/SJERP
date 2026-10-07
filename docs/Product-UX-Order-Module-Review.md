# Order Module UX Review — Phase A

日期：2026-10-07。起点：`1e768dc159a90802d9297119dc216f407c0e143b`，master。

本阶段为列表结构与正式 OrderDetailModal 概览优化，待独立验收。**不标记整个 Order 模块 UX-FROZEN**。采购模块及订单采购与发货内部表格留待后续评审。

## 原始发现与实现

- 原订单列表的“创建时间”实际优先展示 updated_at，语义错误且缺少交期。现在列为订单号、客户、订单日期、预计交期、状态、明细、订单金额、已收 / 待收、操作；日期使用 order_date，交期使用 expected_ship_date，空交期灰色“未设置”。报价时间显示保持原行为。
- confirmed / production 按本地今天的 YYYY-MM-DD 显示还剩 X 天、今日到期、逾期 X 天。日历差值避免 DST 小时偏移；其他状态无紧急提示。仅前端展示，不影响生命周期。
- search 从 URL 初始化，300ms debounce 后 router.replace 保留最新 query/hash，route watcher 独占筛选加载；状态/待办改变保留搜索，包括 debounce 尚未完成时。刷新、直接 URL 和 Back 恢复。重置只移除 search/status/todo，保留 detail/sku/customer/quote 及其他上下文；离开组件清理定时器。
- SummaryCards 仍用既有视觉系统与尺寸，依次执行中（confirmed/production/shipped）、待出库（confirmed/production）、待收款（balance > 0 且非 draft/cancelled）、已完成；不聚合金额。
- 头部保留左侧唯一关闭，清楚展示客户、订单日期、订单号、预计交期与状态。确认/开始生产/完成为主动作，编辑草稿为次动作，取消使用 lifecycle-destructive 专用样式。production 无新增生命周期按钮。接口、确认流程保持原实现。
- 概览依次为全宽订单摘要、全宽当前待办、履约与回款、成本毛利与低权重来源报价。980px 以下单列；移动端摘要两列、任务按钮可换行。
- 摘要展示订单金额、商品项数、订单数量、交期，保留历史/草稿合同额语义。当前待办由已载入 order、fulfillment.items、payment_summary 派生，采购缺口和待发货按唯一 SKU 计数，多任务可并存；草稿确认、正式采购缺口、confirmed/production 待发货、正式待收款、shipped 完成提示分别适配。completed/cancelled 无活动任务，保留历史数据与现有回款入口。
- 回款卡只保留应收计划、已收、待收、既有回款百分比和现有应收 CTA。成本独立为人民币商品成本、附加费用、两者之和的总成本、毛利；仅负毛利标红，不持久化新值。
- 履约卡保留数量与百分比，CTA 只切换 fulfillment，不复制操作表单。来源报价仍 emit open-quote；应收仍 `/receivables?order=<id>`，普通历史支持返回同一工作台。
- 标签顺序：overview/items/fulfillment/payments/packing/inventory/operation_logs。日志卡限制到 operation_logs，避免 fulfillment 与无关日志混排。
- ContractAmountAdjustments、实际装箱、采购草稿、供应商分配、批量发货、冲销与支付内部功能不改。

## UAT

只通过内置浏览器操作现有 UAT 记录。未新增、保存、确认、完成、取消、删除或登记任何业务数据。

| 编号 | 结果 | 证据 |
| --- | --- | --- |
| UAT-ORDER-UX-001 | PASS（真实 UI） | /orders 九列准确；空交期未设置；已完成/取消无交期警示 |
| UAT-ORDER-UX-002 | PASS（真实 UI） | 搜索 SO-2026-00034 + shipped，刷新保持 `/orders?status=shipped&search=SO-2026-00034` |
| UAT-ORDER-UX-003 | PASS（自动化补证；真实 UI 部分验证） | 现有 36 单中 confirmed/production 均为 0，未制造正式数据。组件覆盖这两种状态，真实 shipped ID34 验证唯一关闭、客户、日期、交期、状态 |
| UAT-ORDER-UX-004 | PASS（真实 UI） | ID34 打开默认概览直接展示订单摘要、当前待办 |
| UAT-ORDER-UX-005 | PASS（自动化补证） | 无安全现有采购缺口订单；组件 confirmed/production 显示采购任务，任务按钮切到 fulfillment |
| UAT-ORDER-UX-006 | PASS（自动化补证） | 无安全现有待发货订单；组件验证 unshipped_quantity > 0 的发货任务与状态边界 |
| UAT-ORDER-UX-007 | PASS（真实 UI） | ID34 待收 USD9.90，待办点击到 `/receivables?order=34`；仅本单两计划；Back 回到 status/search/detail=34 原工作台 |
| UAT-ORDER-UX-008 | PASS（真实 UI） | ID34/30 回款仅支付信息，独立成本卡；ID30 总成本 ¥4752、负毛利 ¥-3672 |
| UAT-ORDER-UX-009 | PASS（真实 UI） | 七标签正确排序，履约 CTA 打开原采购与发货工作区 |
| UAT-ORDER-UX-010 | PASS（真实 UI） | ID30 订单已完成、当前无待处理业务；回款、出库、成本与报价历史保留 |

来源报价补充：ID30 SJ20261003FR002 点击打开 `/quotes?detail=44` 正式工作台。
截图：当前任务 visualizations 目录 `order-overview-uat.png`。

## 自动化与回归

新增 `frontend/tests/order-overview-ux.spec.js` 11 项组件/交互测试覆盖所列 22 条最低要求（生命周期状态参数化），另覆盖 debounce 未完成时改变状态、唯一 SKU 计数所用业务字段、已完成/取消健康状态、同一 URL Back，以及日志不混入 fulfillment。既有路由回归改为详情导航保留 route search。字体守卫明确允许本阶段用户指定的尺寸，保留其他抽屉守卫。

| 检查 | 结果 |
| --- | --- |
| frontend Node | 111 PASS |
| frontend Node typography | 1 PASS |
| frontend Vitest | 26 文件 / 201 PASS |
| frontend production build | PASS（既有大 chunk 提示） |
| backend full suite | 562 项 OK，本地跳过 10 项 PostgreSQL 专用测试 |
| Django check | 无问题 |
| migration drift | No changes detected |
| git diff --check | PASS |

后端代码与迁移未修改，既有生命周期、报价转订单、分配、采购、发货/冲销、实际装箱、应收、SKU、客户导航回归由完整测试覆盖。真实 UI 不做正式数据写入回归。

## Git、CI 与验收状态

采用普通 commit/push；不 force push/reset/rebase。非快进停止。最终提交 SHA 与该 SHA 对应 CI run、backend/backend-postgres/frontend 结论在最终交付报告记录；不提前声称 CI 通过。

Order UX Phase A：实现与本地回归完成，等待独立接受；整个订单模块尚未 UX-FROZEN。


## Phase A 验收阻塞修复：DRF 条件唯一校验

历史 [CI #157](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/37578392791) 对实现提交 `45ed9a5268570c1790f288aaafccab6d351b0dda`：frontend SUCCESS，backend/backend-postgres FAILURE，均为 `test_catalog_immutable_default_and_supplier_scope` 创建替代默认规格期望 201，实际返回 400。保留该失败记录，不将原 CI 改写为通过。

独立读取安装日志确认：[#156](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/37507773985) 使用 DRF 3.18.1 并通过；#157 使用 DRF 3.18.3。两次 CI 的 Django 均为 6.0.9。

修改前先检查本地 DRF 3.18.0：`SKUTradeUnitSerializer().get_validators()` 为 `[]`。在 `.venv/ci-drf-3183` 隔离安装 CI 解析版本，以 PYTHONPATH 加载（不降级依赖、不改 requirements），检查 DRF 3.18.3 实际输出：

```text
[<UniqueTogetherValidator(queryset=SKUTradeUnit.objects.all(), fields=('sku',), condition=<Q: (AND: ('is_default', True))>)>]
```

它对应模型唯一的 `trade_unit_one_default` 条件唯一约束。检查模型全部约束：正系数 CheckConstraint、条件 UniqueConstraint、默认必须启用 CheckConstraint；无其他自动对象级唯一校验器。未修复时，DRF 3.18.3 运行原失败测试准确复现 400/201 差异。

检查已安装 DRF 源码：旧版本只枚举 `len(constraint.fields) > 1` 的唯一约束；3.18.3 已枚举此单字段条件唯一约束并生成 UniqueTogetherValidator。这个请求是“切换默认”操作，校验时旧默认仍存在；默认切换原本在 create/update 的原子事务与 SKU 行锁内完成，自动校验先于它而错误拦截。

最终修复只在 `SKUTradeUnitSerializer.Meta` 明确设置 `validators = []`，并注释原因。没有依赖私有校验器属性过滤逻辑；检查确认该 serializer 当前唯一自动对象级校验器即冲突项，因此没有丢失其他自动对象级唯一规则。现有不可改写定义、factor > 0、停用时清除默认的显式校验保留；创建/更新的 SKU 锁、先清旧默认、再写新默认的事务保留；数据库三个约束不变。

新增 3 项 API/数据库回归：同 SKU 两个非默认规格创建成功；POST 新默认返回 201 并清除旧默认，数据库恰一条默认；非法系数拒绝；停用默认不保留默认标记；供应商范围规格创建成功；绕过 serializer 的非法写入仍被数据库拒绝；清旧默认后的写入失败回滚恢复旧默认。既有不可变字段与供应商范围、报价→订单→采购→到货→发货测试保持。

修复验证使用 DRF 3.18.3：交易单位专项 16 项 PASS；完整后端 565 项（SQLite 跳过 10 项 PostgreSQL 专用测试）；Django check 与 makemigrations drift 检查通过。前端 Node 111、字体 1、Vitest 201 项通过，生产构建通过。无模型/迁移/权限/Order Phase A 前端变更。

替代 [CI #158](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/runs/37580165250) 已完成，headSha 精确匹配修复提交 `2634bd6ccef7e8a0ddcafcfe80f90dc7bccf0bef`：backend SUCCESS、backend-postgres SUCCESS、frontend SUCCESS。包含此记录的最终文档提交仍须独立核对其 HEAD 的三个作业，最终 SHA、CI run 与结论在交付报告记录。Phase A 的 CI 阻塞已解决，仍等待独立接受，不开始 Phase B，也不宣布整个订单模块 UX-FROZEN。


## Order UX Phase B — Procurement & Shipment Workspace

日期：2026-10-07；已接受 Phase A 基线 `78ade4beea22deaabafe0e2adbba18958882a673`，CI #159 三作业成功。Phase B 仅改 OrderDetailModal 的采购与发货工作区，未开始采购管理 UX，也未更改后端、权限、模型或迁移。

### 层级与数据语义

原表将十类数量/操作摊为十列，用户须解码斜杠和自行判断当前任务。现在同一工作区依次展示履约状态摘要、SKU 履约明细、关联采购单、发货记录，无嵌套标签。

四张紧凑摘要：待采购 SKU、采购中 SKU 按 SKU 去重；待发货明细、已完成明细按 OrderItem 行计数。前两者分别依据 draftable_quantity > 0，以及 purchased_quantity > arrived_quantity 或 in_transit_quantity > 0；后两者分别依据 unshipped_quantity > 0 / <= 0。汇总不影响业务行，同 SKU 不同 OrderItem 和包装仍各一行，以 item.id 作 key。

七列为 SKU / 当前状态、采购来源、订单需求、采购进度、到货进度、发货进度、操作，最小宽度 940px，固定分配列宽避免长商品名挤压数量列。需求显示订单和已预留；采购保留待采购、可建草稿、采购草稿、已采购，非零次级数量按需显示，历史采购不会随缺口清零消失；到货明确标注已到/在途，无采购/到货时用 —；发货明确已发/待发，完成标为已全部发货。原十个 quantity 字段均直接使用 API 值，没有新计算或持久化。

`fulfillmentItemState(item)` 为只读前端展示：按 completed → needs_supplier → needs_procurement → purchasing → ready_to_ship → waiting_stock 优先级，严格采用要求中的字段条件，不赋予新操作权限。

批量发货是主按钮，生成采购草稿为次按钮，沿用 canBatchShip/canOpenProcurement。行确认发货仅在原许可状态且待发 > 0 时展示；采购来源为次级动作，原状态限制不改。行点击仍 ship(item) → openShipmentDialog([item.id])；来源弹窗接收完整精确 OrderItem。

### 采购与发货历史

采购卡按号码/供应商、状态/金额、预计到货、SKU 摘要分层，号码独占链接，仍 purchaseDetailLocation(purchase.id)，无额外查看按钮。ETA 只读本地 YYYY-MM-DD 日历差，placed/partial 显示未来/今日/逾期；实际接口把 placed 称为 ordered，因此一并兼容 ordered；completed/cancelled/draft 不显示警示。无后端状态转换。

发货卡保留发货单号、日期、状态、SKU 行及上下文动作；confirmed 仍整单冲销，cancelled 显示已冲销。冲销为低权重红色文字按钮。采购空状态区分无需采购与尚未建立关联采购；发货空状态说明库存就绪后可操作。成功提示继续留在当前页。

### PCR-006 与回归边界

本阶段没有编辑发货、冲销、采购草稿、供应商分配业务函数，也没有编辑弹窗内部、装箱、实际装箱、PurchaseOrderPage 或 detailNavigation。PCR-006 既有测试验证 OrderItem ID 独立选择、同 SKU 多行、单一 Shipment 请求、批量原子失败呈现、每行超发原因、整单冲销。仅将原“不可发货时显示禁用按钮”的断言改为本阶段要求的“隐藏无关发货按钮”；其余业务断言保留。

### 真实 UI UAT

只操作已有历史 UAT 订单，没有新建、保存、状态变更、采购生成、发货或冲销提交。

| UAT | 结果 | 实际证据 |
| --- | --- | --- |
| UAT-ORDER-B-001 | PASS（真实 UI） | SO-2026-00026 两条明细，七列取代十列 |
| UAT-ORDER-B-002 | PASS（真实 UI） | ID26 四张摘要 0 / 0 / 0 / 2 |
| UAT-ORDER-B-003 | PASS（真实 UI） | SKU-000001 订单100/采购100/已到100/已发100；CSV SKU 订单20/采购20/已到20/已发20，基础单位 pcs，各段带标签 |
| UAT-ORDER-B-004 | PASS（真实 UI） | 两行均已完成，与待发0和历史发货吻合；其他状态由六状态参数化测试补证 |
| UAT-ORDER-B-005 | PASS（自动化补证） | 两个同 SKU OrderItem 701/702 保留两行、不同精确动作；未为测试制造正式业务记录 |
| UAT-ORDER-B-006 | PASS（真实 UI） | PO-2026-00015 点击到 `/purchase-orders?detail=15` 并准确展开该采购详情；Back 返回 `/orders?status=completed&search=SO-2026-00026&detail=26`。当前 tab 非路由状态，返回默认概览，未引入新路由体系 |
| UAT-ORDER-B-007 | PASS（真实 UI） | ID26 采购卡 PO15/供应商B/USD70/完成/2026-10-09/CSV20 与 PO14/供应商A/USD650/完成/2026-10-17/SKU100 分层可见 |
| UAT-ORDER-B-008 | PASS（真实 UI） | 三笔发货号、2026-10-02 日期、已确认、数量60/20/40及冲销文字清晰，仅检查未提交 |
| UAT-ORDER-B-009 | PASS（自动化补证） | 当前安全历史订单无可发货操作；既有 PCR-006 及新组件测试验证批量按钮条件和精确行 ID，仅模拟 API |
| UAT-ORDER-B-010 | PASS（真实 UI） | 带 search/status 打开 ID26，概览 CTA → fulfillment → PO → Back → 同订单；关闭仅移除 detail，仍保留 search/status 与同一列表结果 |

截图：任务 visualizations 目录 `order-fulfillment-phase-b-uat.png`。

### 测试、CI 与接受状态

新增 `order-fulfillment-ux.spec.js` 15 项，覆盖摘要数量口径、同 SKU 独立行、七列/数量标签、六状态优先级、精确来源/发货行、采购链接/Back、三种活动采购 ETA、关闭状态无警示及空历史。完整前端继续覆盖 Phase A 搜索、筛选、应收与客户/SKU/采购导航、采购和装箱及 PCR-006。

| 检查 | 结果 |
| --- | --- |
| frontend Node | 111 PASS |
| typography | 1 PASS |
| frontend Vitest | 27 文件 / 216 PASS |
| frontend build | PASS（既有大 chunk 提示） |
| backend full suite，DRF 3.18.3 | 565 项 OK，本地 SQLite 跳过10项 PostgreSQL 专用测试 |
| Django check | 无问题 |
| migration drift | No changes detected |
| git diff --check | PASS |

普通 commit/push，不强推、不 reset、不远程历史 rebase。最终提交对应 CI 的 backend/backend-postgres/frontend 三作业及精确 SHA 另行核对并在交付报告记录；未完成前不标记成功。

Phase B 实现与本地 UAT 完成，等待 Phase A+B+跨模块导航的独立接受，**不自动标记 Order 模块 UX-FROZEN**。
