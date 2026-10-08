# Second Review — Global Foundation

本记录仅覆盖第二轮 UI/UX 的 P0/P1 全局交互基础修复，不代表整个 Second Review 完成。
起点：master `b3c98564bdd9998b63b9a49a5b0a0e2a45fb7edd`；验收日期：2026-10-08。

## 问题与结果

- Quote → Order 原来将订单 ID 放入 `/quotes?detail=<id>`。现有订单及报价创建订单后的入口统一进入 `/orders?detail=<id>`；浏览器 Back 恢复原报价及订单页签。报价内部切换版本同时更新 detail，避免返回错误的报价版本。
- Customer、Quote、Order、Purchase 原来在刷新或跨模块返回时丢失页签。现在根工作台使用 `detail + tab`，页签切换 replace 当前历史项，跨模块导航保留浏览器自然返回。先提交 URL，再显示新页签，避免快速点击关联入口取消尚未完成的路由切换。
- Customer/Quote 搜索原来与 URL 不一致。现在从 URL 初始化，300ms 防抖写回 search，刷新及 Back 可恢复。Quote 重置只删除 search/status/customer/ordering；其余上下文保留。
- Customer、Quote、Inventory Movement 的重复关闭按钮已移除，保留左侧“X 关闭”。嵌套详情的返回仍可使用；产品详情保留原有一个右侧关闭。
- Inventory Movement 显示“库存流水详情”，管理入口改为“返回库存流水”，导航 `/inventory-movements`，保留已有 sku。

客户实际 context keys 为 followups、quotes、orders、contacts、purchases（成交商品记录）、cash（财务流水），另有 operation_logs；没有虚构 transactions。

| 工作台 | URL tab 值 | 默认/非法值回退 |
| --- | --- | --- |
| Customer | 实际 context section keys + operation_logs | followups |
| Quote | overview/items/lineage/orders/notes/operation_logs | overview |
| Order | overview/items/fulfillment/payments/packing/inventory/operation_logs | overview |
| Purchase | overview/items/receipt/payment/orders | overview |

列表打开另一条记录时重置默认页签。关闭根详情仅删除 detail/tab，保留 search、status、todo、customer、ordering、sku、attention 等上下文。Customer 内嵌 Quote/Order 的局部页签不覆盖根 Customer 的 tab。未持久化内表搜索/排序。

## Chrome UAT

通过 Chrome Use 操作真实 Chrome 和本地 ERP `http://127.0.0.1:5191`。视口设置 1440×900，Ctrl+0 明确恢复 100%；DOM 实测 innerWidth=1440、innerHeight=900、devicePixelRatio=1、visualViewport.scale=1。仅浏览已有记录、切换页签及列表搜索，没有创建、编辑或删除业务数据。

| 用例 | 操作与实际 URL 证据 | 结果 |
| --- | --- | --- |
| UAT-SR-001 | Customer 12 报价记录 → 内嵌 Quote 39 → 打开报价工作台 → Back，返回 `/customers?detail=12&tab=quotes`，报价记录仍激活 | PASS |
| UAT-SR-002 | Order 25 采购与发货 → Purchase 13 → Back，返回 `/orders?detail=25&tab=fulfillment`，采购与发货仍激活 | PASS |
| UAT-SR-003 | Quote 39 订单 → 查看订单，到达 `/orders?detail=25`；Back 返回 `/quotes?detail=39&tab=orders` | PASS |
| UAT-SR-004 | Purchase 13 关联订单 → Order 25 → Back，返回 `/purchase-orders?detail=13&tab=orders`；另验证 receipt 刷新保持收货页签 | PASS |
| UAT-SR-005 | 客户搜索“新加坡”后刷新，URL `/customers?search=%E6%96%B0%E5%8A%A0%E5%9D%A1`，输入框和匹配记录恢复 | PASS |
| UAT-SR-006 | 报价 search=SJ20261002SG、status=accepted、customer=12、ordering=quote_date，刷新后 URL 与四项控件均恢复 | PASS |

## 截图

非 Git 临时目录：
`C:/Users/Johnson/.codex/visualizations/2026/10/08/01a11977-80e0-77b0-ad46-fafa2f93bdc7/erp-second-review/`

以下文件全部已保存，未加入提交。Chrome 接口提供 JPEG 原始截图，转换为 PNG 时未缩放、裁剪或修图。接口部分输出 1425×891，部分为 1440×900；页面实际视口均为 1440×900/100%，因此不能把所有输出文件的像素尺寸描述成完全一致。

| 文件 | 内容 | 状态 |
| --- | --- | --- |
| SR01_customer_detail_quotes.png | Customer 12 报价记录 | 已加载并补采 |
| SR02_quote_detail_overview.png | Quote 39 概览 | 已加载并补采 |
| SR03_order_detail_fulfillment.png | Order 25 采购与发货 | 已加载并补采 |
| SR04_purchase_detail_overview.png | Purchase 13 概览 | 已加载并补采 |
| SR05_inventory_movement_detail.png | Movement 90 单关闭、新标签和返回入口 | 已加载并补采 |
| SR06_order_purchase_back.png | 从 Purchase 返回 Order 的 fulfillment | 真实 Back 后补采 |
| SR07_customer_quote_back.png | 从 Quote 返回 Customer 的 quotes | 真实 Back 后补采 |
| SR08_quote_order_destination.png | 从 Quote 进入正确的 Order 25 | 实际点击后补采 |
| SR09_customer_list_loaded.png | 客户列表，13 行（含表头） | 完成加载后重采 |
| SR10_order_list_loaded.png | 订单列表，37 行（含表头） | 完成加载后重采 |

## 测试

新增 `frontend/tests/second-review-foundation.spec.js`，25 个集成用例以真实 Vue Router + 页面/工作台和 mock API 覆盖请求的 32 项行为（参数化用例及单用例的多断言）。

| 请求编号 | 覆盖 |
| --- | --- |
| 1–2、7–9 | Quote Orders → exact Order URL、Back exact Quote/tab、URL 初始化/点击/重新挂载 |
| 3–6 | Customer quotes URL、切换写回、非法回退、嵌套 Quote → 工作台 → Back |
| 10–15 | Order/Purchase URL 初始化/重新挂载/点击、Order→Purchase 与 Purchase→Order Back |
| 16–20 | 四种工作台新记录默认值及关闭仅移除 detail/tab，保留过滤上下文 |
| 21–27 | Customer/Quote URL 搜索初始化、299/300ms 防抖边界、保留 detail/tab/过滤器/重新挂载恢复 |
| 28 | Quote reset 仅移除指定四个搜索/过滤键 |
| 29–32 | 三种根详情只有一个 Close、嵌套 Back 功能保持 |
| 额外 | 三种文档非法/多值 tab 回退、Movement 返回保留 sku、报价创建订单后路由、报价版本切换后跨模块 Back |

本地验证：

- `npm run test:unit`：111/111 PASS。
- `npx --no-install vitest run tests --environment jsdom --exclude tests/detail-drawer-typography.spec.js`：32 个文件、307/307 PASS。
- `node --test tests/detail-drawer-typography.spec.js`：1/1 PASS。
- `npm run build`：PASS（沿用现有 bundle-size 提示）。
- `python manage.py test`：565 tests，OK，10 skipped；独立测试数据库已销毁。
- `python manage.py check`：无问题。
- `python manage.py makemigrations --check --dry-run`：No changes detected。
- 最终微调保留 Inventory Movement 原有搜索历史语义后，foundation 25 项再跑 PASS；完整回归由最终 HEAD CI 再验证。

## CI 与交付

工作流 `.github/workflows/ci.yml` 原样保留。正常提交并 push master 后，以最终 HEAD 的运行核验 backend、backend-postgres、frontend 三个 job 全部 SUCCESS；本地成功不能替代 PostgreSQL CI。最终提交 SHA、实际运行链接及三个 job 结果记录在本次任务最终交付回复。

[master CI 运行记录](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/workflows/ci.yml?query=branch%3Amaster)

## 文件范围

生产文件：`EntityDetailModal.vue`、`QuoteDetailModal.vue`、`OrderDetailModal.vue`、`PurchaseDetailModal.vue`、`DocumentPage.vue`、`ResourcePage.vue`、`utils/useDetailTab.js`（新增）、`utils/documentDetailRoute.js`、`utils/routePageState.js`。

测试文件：`src/views/DocumentPage.test.js`、`tests/second-review-foundation.spec.js`（新增）、`tests/customer-ux.spec.js`、`tests/entity-detail-quote-create.spec.js`、`tests/order-fulfillment-ux.spec.js`、`tests/order-overview-ux.spec.js`、`tests/purchase-editor-receipt.spec.js`、`tests/purchase-order-navigation.spec.js`、`tests/trade-finance.spec.js`。

未修改 backend 生产代码、models、migrations、权限设置或业务计算；未开展 Finance UX、sidebar/topbar 重设计、卡片布局、表格密度或 drawer 宽度调整。

## Phase 2A — Global List Visual + Copy Pass

实施基线：`634a322b925fd4ea1f37953c2aae8f2b44971f4e`（基线 CI #166）。本节是实施和验证记录，Phase 2A 最终 UI 验收由 ChatGPT 独立检查 diff、业务回归、CI、对比截图、文案及视觉一致性后决定，Codex 不宣告 Phase 2A PASS。未开始 Phase 2B 或 Finance UX。

### 布局与侧栏

- Customer、Quote、Order、Purchase、Inventory、Inventory Movement 删除内容区重复 H2；全局顶栏的英文 eyebrow 和中文 H1 保留。内容区改为说明/操作行，min-height 42px、下间距 18px、说明文字 13px/#71817B。
- 侧栏保持 248px，导航项实测 40px；组标题留白为上 14px、下 6px。保留原有权限判断、全部 25 个模块入口及路由。
- 分组：经营（经营概览/报表中心）、客户（客户管理/联系人/跟进记录）、销售（报价管理/订单管理）、采购与库存（供应商管理/采购管理/库存/库存流水）、产品资料（产品管理/SKU 管理/产品分类/产品参数/包装管理/交易单位/产品证书/HS 编码维护）、财务与工具（原次序）、组织与系统（组织与权限）。
- 列表表头统一为 42px、现有浅色背景、取消中文标题的 uppercase/额外字距，行内容居中。CSS 通过列表根容器及专用表格 class 限定，详情工作台和编辑器不做视觉重设计。

### Human copy pass

| 页面 | 新说明/辅助文案 |
| --- | --- |
| Customer | 管理客户资料、负责人和跟进计划。客户阶段会根据报价和订单自动更新。卡片提示：全部客户档案/已有正式订单/尚未成交/当前列表累计。主操作：新建客户 |
| Quote | 管理报价版本、状态和成交转单。指标提示：报价主单数/含所有修订版/草稿或已发送/客户已接受。主操作：新建报价 |
| Order | 管理订单、交付和收款进度。提示：已确认 / 生产中 / 已发货、尚未完成发货、仍有应收余额、已完成交付。主操作：新建订单 |
| Purchase | 管理采购、到货和供应商付款。提示：已下单 / 部分到货、尚未全部到货、仍有应付余额、已完成采购。主操作：新建采购单 |
| Inventory | 查看各 SKU 的实际库存、预留、可用量和采购缺口。提示缩短为当前列表/按基础单位汇总/已扣除预留/已下单未到货/采购缺口 / 数据异常；保留刷新及业务链接，无创建主操作 |
| Inventory Movement | 查看每次库存增减及其来源。辅助说明：数量按 SKU 基础单位显示；自动流水不可手工修改。保留类型/方向/来源。主操作：新建库存调整 |

各核心列表空状态使用“暂无…”与具体新建操作；过滤为空使用“没有匹配的…”和“请调整筛选条件。”库存无创建操作，引导进入 SKU 管理。Customer、Quote、Order、Purchase、Movement 指标数量与计算公式未改变。

已把永久质量规则写入项目 AGENTS.md：前端任务同时要求自动回归和真实 Chrome 检查；可见文案做人工语言检查。UI helper 可改写，正式字段只在含义不变时简化，实际状态值/数据不得改写。SKU、预留、冲销、采购草稿、应收、应付、交易单位、入库、出库等术语保留。

### 客户状态与表格

只在列表显示映射：lead → 线索、contact → 已联系、opportunity → 商机、customer → 正式客户、company → 返单客户。实际 company key 已在模型及当前生命周期文案中核对；完整“已有2张及以上正式订单”等说明保留在 title tooltip。现有字段、状态 class、后端语义、详情文案未改动，未知状态保留原显示。

客户名称最多两行并保留完整名称 tooltip；编号、状态、国家/地区、业务区域、负责人、日期、订单数、金额保持单行。仅客户列表收紧列内水平留白至 6px，保留 14px 正文字号。实测表格与可视容器均为 1107px，金额和操作列可完整显示。

Order 列设定最小宽度：订单号 125、客户 180、日期/交期各 100、状态 78、明细 60、金额 105、已收/待收 120、操作 80px；编号/日期/状态/数量/金额不换行，客户可换行。1440 桌面下表格与容器均为 1107px，无整页水平溢出。Purchase 编号/日期/状态/金额同样保持单行；金额列右对齐。较窄视口保留表格内部水平滚动。

### 库存

桌面库存卡片改为 `repeat(5, minmax(0, 1fr))`；1200px 以下使用 3 列，700px 以下 2 列，480px 以下 1 列。1440 桌面五卡同排，实测 y 坐标均为 171。

“待关注”卡片保留唯一过滤入口，使用原 toggleAttention/URL attention=1 和原缺口/异常判定；保留 active 样式及 aria-pressed。移除同功能的工具栏按钮。实际库存、预留、可用、在途、待采购计算未修改，混合基础单位分别汇总。

### Chrome 检查与截图

Chrome Use 操作真实 Chrome，本地 ERP `http://127.0.0.1:5191`；1440×900、Ctrl+0 恢复 100%，DOM 实测 devicePixelRatio=1、visualViewport.scale=1。改动前先采六页，改动后采相同数据列表及侧栏三段；仅浏览/切换筛选/展开树，没有业务数据修改。

| 页面/检查 | 观察结果 |
| --- | --- |
| Customer | 单一中文页面标题，新建客户；短状态单行并带完整说明；名称最多两行；全部列可见 |
| Quote | 单一标题、新建报价、四指标保持；真实树展开 42→44 行，收起恢复 42 行 |
| Order | 单一标题、新建订单；订单号/日期/已取消等状态单行；表格完整显示 |
| Purchase | 单一标题、新建采购单；日期/编号/状态/金额单行；列表筛选控件保留 |
| Inventory | 五卡同排；唯一待关注卡片点击写 attention=1/aria-pressed=true，再次点击删除过滤并恢复 3 条 SKU |
| Movement | 单一标题、新建库存调整；类型/方向/来源仍在，90 条流水数据保持，自动/冲销标记仍清晰 |
| 侧栏 | 七组、25 个模块入口；产品资料中部及组织与系统底部可滚动访问，当前项高亮；权限入口规则不变 |

截图根目录（非 Git）：
`C:/Users/Johnson/.codex/visualizations/2026/10/08/01a11977-80e0-77b0-ad46-fafa2f93bdc7/erp-phase-2a/`

BEFORE 文件在 `before/`，AFTER 文件在 `after/`；15 张全部加载完成且经逐图检查，未提交 Git：

- BEFORE_01_customer_list.png → AFTER_01_customer_list.png
- BEFORE_02_quote_list.png → AFTER_02_quote_list.png
- BEFORE_03_order_list.png → AFTER_03_order_list.png
- BEFORE_04_purchase_list.png → AFTER_04_purchase_list.png
- BEFORE_05_inventory_list.png → AFTER_05_inventory_list.png
- BEFORE_06_inventory_movement_list.png → AFTER_06_inventory_movement_list.png
- AFTER_07_sidebar_top.png、AFTER_08_sidebar_middle.png、AFTER_09_sidebar_bottom.png

截图接口原始文件为 JPEG，另存 PNG 时未裁剪/缩放/修图。页面视口均为 1440×900/100%；接口部分输出 1425×891，库存及侧栏中部为 1440×900。QA 联系表仅用于检查，独立验收应查看原尺寸 PNG。

### 自动验证与 CI

- 新增 `frontend/tests/phase2a-list-shell.spec.js`，19 项集成/样式检查：六页顶栏及无重复 H2、主操作文字、实际状态 key/tooltip、不换行/列宽、报价树及指标、Order/Purchase/Movement 筛选、按单位库存汇总、唯一 attention/URL/active 状态、全部模块路由和七组次序、初始/过滤空状态。
- 更新 ResourcePage、inventory-workbench、inventory-ledger、quote-list 旧测试中已改变的列表文字；既有工作台、导航、订单/采购业务回归保留。
- 全量 Vitest：33 个文件、326/326 通过。
- Node 单元测试：111/111 通过；字体检查：1/1 通过；生产构建通过（原有 bundle-size 提示）。
- Backend：565 tests，OK，10 skipped，独立测试数据库已销毁；Django check 无问题，makemigrations --check --dry-run 无漂移。
- 范围核对：backend、models/migrations、router、详情组件均无 diff；开发超级管理员权限规则保持原样。
- 正常 commit + push master 后核验最终 HEAD 的 backend、backend-postgres、frontend 全部成功；最终 SHA 和实际运行链接记录在本次最终交付回复。[master CI](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/workflows/ci.yml?query=branch%3Amaster)。这些验证记录供独立 UI 验收使用，不代替最终验收结论。

本轮实现文件：App.vue、styles.css、resourceConfigs.js、DocumentPage.vue、ResourcePage.vue、PurchaseOrderPage.vue、InventoryPage.vue、utils/customerListStatus.js（新增）、utils/inventoryLedger.js；另有 AGENTS.md、本文档、新增测试和四个更新的测试文件。

### Post-visual-review repair

2026-10-08，Phase 2A 独立视觉复核后的三项定点修复：

- 库存中文 SKU 名称与基础单位原先同排：增加专用 `inventory-name-cell`，名称和单位分别显示为 block；单位上留 3px 间距、12px caption 字号、#81908a。长名称自然换行，原名称、单位和库存值保持。
- 侧栏滚动条原先显示亮白条：仅 `.sidebar nav` 使用透明轨道、6px 圆角浅绿半透明滑块，hover 加深；Firefox 使用 thin/scrollbar-color。Chromium 在支持 WebKit 伪元素时恢复标准 scrollbar 属性为 auto，避免覆盖自定义滑块。主内容滚动条保持，侧栏仍可滚动到底部。
- 流水四卡原先重复“当前列表记录数”：按原顺序改为“当前筛选结果 / 库存增加 / 库存减少 / 冲销生成”；标签及计数表达式保持。

验证：全量 Vitest 33 个文件、329/329；Node 单元测试 111/111；字体检查 1/1；生产构建通过。新增库存原值与两块样式、侧栏 scrollbar 作用范围、流水原标签/计数/精确提示回归，既有 Phase 2A 测试全部通过。后端、业务逻辑、权限、详情布局无修改。

真实 Chrome Use：1440×900 视口、100% 缩放，未修改业务数据。库存三行名称/单位分开，长名称自然换行；流水实测计数仍为 90 / 41 / 49 / 12，四提示可读；侧栏滚动位置从顶部到 645px，底部组织入口可见，滑块细且无亮白轨道；未发现新裁切。

截图位于 Git 外目录 `C:/Users/Johnson/.codex/visualizations/2026/10/08/01a11977-80e0-77b0-ad46-fafa2f93bdc7/erp-phase-2a/focused-repair/`，三张均已逐图检查：

- `FIX_01_inventory_list.png`：已完成，1440×900。
- `FIX_02_inventory_movement_list.png`：已完成；页面视口 1440×900，截图接口原始输出 1425×891。
- `FIX_03_sidebar_scrollbar.png`：已完成，1440×900。

保留接口原始 JPEG，并按原尺寸转存 PNG，无裁剪、缩放或修图，截图未提交 Git。正常提交并推送 master 后，最终 HEAD 的三项 CI 结果及 SHA 记录于交付回复。本次未启动 Phase 2B 或 Finance UX。
