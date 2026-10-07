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

替代 CI：修复提交普通推送后逐项核对 backend、backend-postgres、frontend；最终精确 SHA、CI run 与结论以交付报告记录，未完成前不标记成功。Phase A 仍等待独立接受，不开始 Phase B，也不宣布整个订单模块 UX-FROZEN。
