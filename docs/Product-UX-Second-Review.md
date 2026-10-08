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

## Phase 2B — Core Detail Workbench Visual + Copy Pass

2026-10-08。起点为已接受的 `694c7a65e195bfde1584cfa9a53852b90793e1c5`，CI #168。保留第一轮架构，仅优化 Customer、Quote、Order、Purchase、SKU Inventory、Inventory Movement 六类详情的视觉层级及显示文案。

### 视觉与操作统一

- 六类头部沿用 #123C36，主标识 24px/700，辅助信息 12px；目标内边距 22px 26px。共用字体 token，不新增调色板或通用详情组件。
- Customer 根详情显示“客户详情”、实际客户名称、编号/国家、负责人和原阶段徽章。负责人从当前 context 的基础信息读取，缺失时不显示。保留新增跟进、新建报价、编辑客户；新增跟进视觉突出。业务区域、国家、阶段没有重新定义。
- Quote 将转为订单作为主操作，创建修订版/预览 PI 为次操作，导出 Excel 为工具操作；状态转换按钮独立分组并降低视觉权重。原状态条件、API、订单草稿与 PI 行为保持。版本标识/日期/状态及版本操作补齐间距。
- Order 保留客户、订单号、订单日期、预计交期、状态；确认/生产/完成与取消操作原条件保持，破坏性操作继续分开。卡片间距 16px，明显偏大的卡片内边距收至 16px。
- Purchase 补上工作台上下文和带文字的关闭按钮，保留供应商、采购号、日期、预计到货、状态和全部生命周期操作。页签改为 44px/13px 水平留白，与其他工作台的绿色底边、文字节奏一致。
- SKU Inventory 头部由五行定义收为一条紧凑说明；其余指标定义移至对应指标 title。六项指标值、筛选/排序/路由保持，主编号 24px，关闭按钮带文字，页签 44px。
- Inventory Movement 头部补上实际 SKU、来源和冲销状态。移除重复“返回库存流水”；保留唯一“关闭”，关闭保留流水筛选。所有 movement endpoint 的主档创建操作隐藏，包括泛型关联 SKU 的“新增SKU”；Product 的 SKU 创建行为保持。
- Customer/Movement 卡片边框 #E0E8E4、圆角 13px、内边距及卡片间距 16px，其他模块只归一明显差异。根关闭均一个；Customer 嵌套 Back 和 Quote 版本 Back 保留。
- Chrome 发现库存明细的多行流水编号点击中心可能落在行间空隙；编号链接改为 inline-block/nowrap，保留表格内横向滚动，实测鼠标点击和键盘 Enter 均能进入准确流水。

### Human Copy Pass

| 原显示 | 本轮显示 |
| --- | --- |
| 客户业务记录 / 点击记录查看详情 | 业务记录，去掉低价值操作说明 |
| 由最新跟进记录自动更新 | 随最新跟进自动更新 |
| 点击右上角新增记录并自动建立关联 | 客户各页签使用暂无跟进记录、暂无报价、暂无订单等专属空状态 |
| 该原始报价链已转出 X 张订单 | 已生成 X 张订单 |
| 展示当前原始报价及全部迭代版本转出的订单 | 查看该报价及修订版生成的订单 |
| 本页只展示当前版本的固定商品快照 | 当前版本的商品明细 |
| 树状关系记录每个版本实际从哪一版修改而来… | 查看各修订版之间的关系 |
| 存在待采购商品 / 存在待发货商品 / 存在待收款 | 待采购 / 待发货 / 待收款，保留实际 SKU 数及金额 |
| 当前无待处理业务 / 采购履约事项 | 当前没有待处理事项 |
| 采购商品成本及公共费用可分配到关联销售订单… | 将采购成本和公共费用分配到关联订单 |
| 存在待到货商品 | 待到货，还有 X 条明细未全部到货 |
| 五行常驻库存定义 | 库存均按 SKU 基础单位计算。可用库存 = 实际库存 - 已预留 |
| 查看采购单 / 查看销售订单 / 查看库存流水 | 采购单 / 销售订单 / 库存流水 |
| 支持按关键词筛选，点击列标题切换排序 | 去掉；保留搜索框和排序图标 |
| 这里只显示 SKU 本身的操作记录… | 仅记录 SKU 主档操作。库存增减请查看“库存流水” |

订单待办原逻辑按唯一 SKU 计数，因此显示“X 个 SKU”，没有改写成“X 条明细”。采购待到货沿用实际明细条数。商品快照、采购草稿尚未下单、预计装箱不会创建发货、冲销后果、验货不合格品处理、合同调整不自动退款等重要业务含义仍保留；只缩短说明。正式状态、持久化值、SKU/预留/冲销/交易单位/应收/应付/入库/出库术语保持。

### Chrome UAT 与截图

使用真实 Chrome Use，1440×900 视口、100% 缩放，DOM 实测 devicePixelRatio=1、visualViewport.scale=1。先采九张 BEFORE，再改代码，再采相同记录和页签的九张 AFTER；仅浏览与切换页签，没有业务数据修改。

| 视图 | 实际记录及观察 |
| --- | --- |
| Customer | 客户 12，UAT-R1 潜客 09；头部姓名/编号/国家/负责人/阶段清楚，三动作和业务页签完整 |
| Quote overview/orders | 报价 39，SJ20261002SG003；USD 1,560、1 项、关联 1 张订单保持，主动作与工具动作有区分 |
| Order overview/fulfillment | 订单 25，SO-2026-00025；100 pcs、USD 1,560、已收 1,560、待收 0；四段履约数量不变 |
| Purchase overview/receipt | 采购 13，PO-2026-00013；USD 650、100 pcs 到齐、已付 650、待付 0，验货入库/冲销仍显示 |
| Inventory | SKU 1；实际 0.01、预留 0、可用 0.01、在途 6.99、待采购 0、原状态保持 |
| Movement | 流水 82，REV-4198B418E1814CF1；日期、SKU、盘亏出库、-11 pcs、冲销生成/冲销流水保持，无多余返回或新增 SKU |

五条往返链路全部复核：Customer→Quote→Back 恢复 customer 12/quotes；Quote→Order→Back 恢复 quote 39/orders；Order→Purchase→Back 恢复 order 25/fulfillment；Purchase→Order→Back 恢复 purchase 13/orders；Inventory→Movement→Close→Back 保留 sku=1 并恢复 inventory detail=1/movements。Customer 嵌套报价 Back 仍回客户原页签。装箱空状态另行检查，生成按钮和重要提示保留。Quote 页签实测均为 44px。未发现新整页裁切，宽表格保留内部横向滚动。

截图根目录（非 Git）：`C:/Users/Johnson/.codex/visualizations/2026/10/08/01a11977-80e0-77b0-ad46-fafa2f93bdc7/erp-phase-2b/`。

`before/` 和 `after/` 各九张，全部逐图检查，编号对应：01 customer_detail、02 quote_overview、03 quote_orders、04 order_overview、05 order_fulfillment、06 purchase_overview、07 purchase_receipt、08 inventory_detail、09 movement_detail；文件分别为 `B2_BEFORE_01_customer_detail.png` 等及 `B2_AFTER_01_customer_detail.png` 等。

保留原始 JPEG，原尺寸转存 PNG，无裁剪、缩放或修图。页面视口统一 1440×900；接口库存输出为 1440×900，其他八个视图为 1425×891。截图未提交 Git。

### 自动回归、范围与 CI

- 前端回归包含六类根关闭、Movement 去重复返回/隐藏不适用创建、客户真实身份与三动作、Quote 主操作及五种状态下原转换请求、Order/Purchase 生命周期、全部 Foundation 页签与嵌套/跨模块 Back、原工作台/库存指标。
- 更新已改变的显示文案断言；保留 API 参数、事件对象、计数、金额、库存值、导航断言。
- 全量 Vitest 33 个文件、339/339；Node 单元测试 111/111，字体检查 1/1。生产构建通过，保留原有 bundle-size 提示。
- Backend：565 tests，OK，10 skipped，测试数据库已销毁；Django check 无问题；makemigrations --check --dry-run 无漂移。
- backend、models/migrations、权限与业务计算无修改。orderOverview/purchaseOverview 只改显示字符串，任务判定、统计与 action/target/key 保持。
- 正常提交并推送 master 后核验最终 HEAD 的 backend、backend-postgres、frontend 均 SUCCESS；实际 SHA、CI 运行链接及最终测试计数记录于交付回复。[master CI](https://github.com/Johnson-Yiu/SUNJACK-ERP/actions/workflows/ci.yml?query=branch%3Amaster)。此记录供独立视觉验收，不代替用户验收结论。

本轮未启动 Phase 2C 或 Finance UX。
