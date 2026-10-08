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
