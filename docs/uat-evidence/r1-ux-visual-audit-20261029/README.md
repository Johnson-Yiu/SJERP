# R1-UX-VISUAL-AUDIT-01 — 真实浏览器视觉审查

## 结论

检查日期：2026-10-29。审查基线 `54e715bdc568b80ba624186fecd866550676cf38`，在真实 Chrome 和隔离合成数据下完成 1440、1024、390px 三视口检查。确认 2 项视觉缺陷：1 项 P2 财务汇总金额被截断，1 项 P3 报价编辑器底部按钮在窄屏被挤窄换行。没有确认 P0/P1，也没有关闭或修改任何 Issue。

本轮没有修改产品 UI/业务代码。仅增加本审查专用隔离数据种子、浏览器审查 spec，以及隔离启动器中的精确 allowlist 项；共享项目台账未改。

## 环境与安全边界

- 分支：`codex/audit-ux-visual-20261029`；基线 SHA：`54e715bdc568b80ba624186fecd866550676cf38`。
- 浏览器：本机 Google Chrome `156.0.8078.48`，通过 Playwright `PLAYWRIGHT_CHANNEL=chrome` 实际启动；截图来自实际页面，不是模拟页面或拼图。
- 视口：1440×1000、1024×1000、390×1000。三视口均检查了 13 个主要业务路由。
- 最终运行 runId：`b733c1fa-cecd-4817-ae0f-8109d0e06374`。API `127.0.0.1:8825`，Vite `127.0.0.1:8826`；实际 SQLite 与 MEDIA_ROOT 位于该 runId 的专属临时目录，API 直接身份和 Vite `/api` 代理身份均通过验证。迁移完整性通过。运行结束只清理了该运行自己带所有权标记的临时 DB/MEDIA_ROOT。
- 数据仅为隔离合成数据：30 客户、2 产品、4 SKU、1 销售订单、1 出货/装箱记录及合成财务数据。主要记录使用 `R1UXA-`，并复用已审核的隔离基础种子 `R0F7B` 数据；两者均为合成资料。没有连接或写入用户业务库；UI 表单只打开检查，未提交创建/编辑。
- 没有启用正式 RBAC 或修改权限。访问拒绝状态通过浏览器拦截合成响应展示，并非真实 RBAC 授权验收。操作审计日志在隔离运行中关闭；截图页脚出现的 Johnson 是开发身份标识，不代表真实登录或审计操作人。

## 复现缺陷（按严重程度）

### P2 — 财务汇总卡片截断金额

- 页面/视口：财务流水、应收计划、应付计划，1024px。
- 证据：[财务流水](screenshots/transactions-1024.png)、[应收计划](screenshots/receivables-1024.png)、[应付计划](screenshots/payables-1024.png)。
- 复现：打开对应页面并将浏览器视口设为 1024×1000。汇总区仍以四列显示；“账面收入”“待结金额”等卡片只显示 `¥20…`、`¥ 50…`、`¥25…`，完整金额无法从汇总卡片读取。页面明细行能显示金额，说明这是摘要视觉截断，不是 API 缺值。
- 依据：三张真实 Chrome 截图；共享 `SummaryCards.vue` 的金额样式使用 `overflow:hidden;text-overflow:ellipsis;white-space:nowrap`，1024px 视口下含侧栏的实际内容宽度不足以容纳数字、图标及预留边距。
- 建议最小修复：按主内容可用宽度而非 viewport 宽度切换摘要卡片列数，或为金额腾出图标空间/允许安全换行；添加 1024px 回归，断言完整金额可见。
- 重复 Issue 核对：ISS-057 记录财务筛选、统计语义和截图缺口；ISS-063 是经营概览；ISS-065 是报表图表；ISS-098 是列表列宽/筛选控件。未找到覆盖这三张财务页摘要卡片金额截断的同一缺陷，故本报告单独登记候选，不改共享台账。

### P3 — 390px 报价编辑器底部动作文字被挤成窄列

- 页面/视口：报价管理 → 新建报价，390px。
- 证据：[报价编辑器底部](screenshots/quote-form-390.png)。
- 复现：390×1000 打开 `/quotes`，点击“新建报价”，查看固定在底部的操作区。“取消”和“预览报价单”断成多行窄列，“保存并导出 Excel”也折行拥挤。按钮仍可见、可点，但动作文字难以快速扫描。
- 建议最小修复：在窄屏将次要动作收纳或独立换行，给主要保存动作保留可读的最小宽度；不改变保存/导出行为。
- 重复 Issue 核对：ISS-029 是收件人快照；ISS-033/034 是报价明细层级和 PI 预览标题；未找到已登记的报价编辑器窄屏底部按钮拥挤问题。

## 检查结果与范围说明

- 39 张主要路由截图覆盖产品、SKU、客户、报价、销售订单、采购订单、库存、库存流水、财务概览、财务流水、报表、应收、应付各 3 种视口；诊断中没有页面级横向溢出，窄屏表格可在自身容器内横向滚动。
- 实际操作覆盖客户搜索筛选（过滤到 1 条）、客户第 2 页、打开 7 类新建表单、产品编辑表单（未保存）、销售订单详情的实际装箱、Packing List 导出。导出响应成功，文件为 [PackingList-R1UXA-S001.xlsx](exports/PackingList-R1UXA-S001.xlsx)，65,113 bytes。
- 空列表、加载失败/重试、权限拒绝截图分别为浏览器注入的合成空响应、合成 503 及合成拒绝响应。重试后页面恢复显示合成产品。它们用于检查 UI 状态表达，不代表后端故障或真实权限结论。
- 未发现主要路由页面级水平溢出、导出失败或当前矩阵内的未捕获浏览器异常。订单详情日志中再次出现既有 `OrderDetailModal` Transition Vue 警告（ISS-103）；本轮未确认它造成可见功能失败，不重复报缺陷。预计装箱方案接口在未生成方案时返回 404，页面清楚显示“尚未生成预计装箱方案”，属于预期空状态。
- 限制：本轮未提交任何业务创建/编辑/收货/出货写入；未对真实 RBAC、真实权限拒绝或真实服务端 5xx 做验收；除产品编辑表单外未逐页提交现有资料编辑；收货详情的完整业务操作链未执行。不得将本轮结果解释为业务规则或数据写入验收通过。

## 自动化结果

- `npm run test:browser:isolated -- --business-test r1-ux-visual-audit-20261029.spec.js`：**4/4 passed**，2.2 分钟；真实 Chrome 运行。
- `npm run test:browser:isolated:verify`：**13/13 passed**，67.2 秒；包含端口占用安全失败、身份/代理错误拒绝、所有权清理及两个独立工作树并行运行。
- `git diff --check`：通过。
- 没有运行 GitHub Actions；没有执行构建（未改产品代码）；没有关闭 Issue。

浏览器诊断明细：[browser-diagnostics.json](browser-diagnostics.json)。

## 截图索引

### 主要页面矩阵（每个页面 1440 / 1024 / 390px）

| 页面 | 1440px | 1024px | 390px |
|---|---|---|---|
| 产品 | [图](screenshots/products-1440.png) | [图](screenshots/products-1024.png) | [图](screenshots/products-390.png) |
| SKU | [图](screenshots/skus-1440.png) | [图](screenshots/skus-1024.png) | [图](screenshots/skus-390.png) |
| 客户 | [图](screenshots/customers-1440.png) | [图](screenshots/customers-1024.png) | [图](screenshots/customers-390.png) |
| 报价 | [图](screenshots/quotes-1440.png) | [图](screenshots/quotes-1024.png) | [图](screenshots/quotes-390.png) |
| 销售订单 | [图](screenshots/orders-1440.png) | [图](screenshots/orders-1024.png) | [图](screenshots/orders-390.png) |
| 采购订单 | [图](screenshots/purchase-orders-1440.png) | [图](screenshots/purchase-orders-1024.png) | [图](screenshots/purchase-orders-390.png) |
| 库存 | [图](screenshots/inventory-1440.png) | [图](screenshots/inventory-1024.png) | [图](screenshots/inventory-390.png) |
| 库存流水 | [图](screenshots/inventory-movements-1440.png) | [图](screenshots/inventory-movements-1024.png) | [图](screenshots/inventory-movements-390.png) |
| 财务概览 | [图](screenshots/finance-1440.png) | [图](screenshots/finance-1024.png) | [图](screenshots/finance-390.png) |
| 财务流水 | [图](screenshots/transactions-1440.png) | [图](screenshots/transactions-1024.png) | [图](screenshots/transactions-390.png) |
| 报表 | [图](screenshots/reports-1440.png) | [图](screenshots/reports-1024.png) | [图](screenshots/reports-390.png) |
| 应收计划 | [图](screenshots/receivables-1440.png) | [图](screenshots/receivables-1024.png) | [图](screenshots/receivables-390.png) |
| 应付计划 | [图](screenshots/payables-1440.png) | [图](screenshots/payables-1024.png) | [图](screenshots/payables-390.png) |

### 表单和交互状态截图

7 类新建表单（各 3 种视口）：

- 产品：`product-form-1440.png`、`product-form-1024.png`、`product-form-390.png`。
- SKU：`sku-form-1440.png`、`sku-form-1024.png`、`sku-form-390.png`。
- 客户：`customer-form-1440.png`、`customer-form-1024.png`、`customer-form-390.png`。
- 报价：`quote-form-1440.png`、`quote-form-1024.png`、`quote-form-390.png`。
- 销售订单：`order-form-1440.png`、`order-form-1024.png`、`order-form-390.png`。
- 采购单：`purchase-form-1440.png`、`purchase-form-1024.png`、`purchase-form-390.png`。
- 财务流水：`transaction-form-1440.png`、`transaction-form-1024.png`、`transaction-form-390.png`。

其他场景：

- [产品编辑 1440px](screenshots/product-edit-1440.png) / [390px](screenshots/product-edit-390.png)（只打开未保存）。
- 客户筛选：[筛选结果 390px](screenshots/customers-search-filter-390.png)；[第 2 页 1440px](screenshots/customers-pagination-page-2-1440.png)。
- 客户空数据：[1440px](screenshots/customers-empty-1440.png)。
- 合成访问拒绝：[库存 390px](screenshots/inventory-access-denied-390.png)。
- 合成加载失败与恢复：[失败 1024px](screenshots/products-load-error-1024.png)、[重试成功 1024px](screenshots/products-retry-success-1024.png)。
- 窄屏表格横向滚动：[销售订单 390px](screenshots/orders-table-horizontal-scroll-390.png)。
- 实际装箱与 Packing List：[1440px](screenshots/packing-list-1440.png)、[1024px](screenshots/packing-list-1024.png)、[390px](screenshots/packing-list-390.png)；实际下载文件见上文链接。

截图总计 72 张，均由本轮真实 Chrome 浏览器操作保存。
