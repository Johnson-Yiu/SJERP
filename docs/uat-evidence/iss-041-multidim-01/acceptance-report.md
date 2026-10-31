# ISS-041-A 报表中心两级交叉分组验收

## 范围

- 基线：`codex/iss-062-date-window` / `9edbb6488a66a0801ecc1e5bc842df7866c6c7dc`
- 实施分支：`codex/iss-041-multidim-01`
- 数据环境：独立 SQLite、合成订单/客户/分类/SKU/Transaction 数据；服务器日期冻结为 2026-10-22。
- 未新增数据库迁移；未修改实际银行人民币资金事件口径、权限体系或自定义报表未来日期能力。

## API 与计算核对

1. 国家 + 客户交叉查询返回 3 个分组，金额合计 `33,200`，去重单据数 `3`，数量 `200 pcs / 10 box`。每行包含独立的 `groups` 数组，组合 key 使用 JSON 数组编码，避免分隔符碰撞。
2. 产品分类 + SKU 查询返回 3 个分组，合计与底层订单一致；不同单位保持分开，不把 `pcs` 与 `box` 相加。
3. 时间 + 客户查询按月份与客户分别归组；未来月份不会被伪造为零值实体组合。单维度时间查询仍补齐完整月份。
4. `historical_only=True`、取消、草稿等无效订单未进入正式报表；国家/客户权限分别校验。
5. CSV 两级表头为 `国家/地区,客户,金额（人民币）,去重单据/档案数,数量（按单位）`，合计行保持单据去重和分单位数量；单维度 CSV 表头未改变。
6. 自定义未来期间 `2026-11-01 — 2026-11-30` 查询仍可返回 1 笔、`9,801` 元，证明本轮未给报表中心增加全局未来日期限制。
7. 最近 12 个月时间查询 `2025-11-01 — 2026-10-22` 返回恰好 12 个自然月标签，详见 `api-time-12-months.json`。

原始响应和 CSV：

- `api-country-customer.json`
- `api-category-sku.json`
- `api-country-customer.csv`
- `api-future-custom.json`
- `api-time-12-months.json`

## 前端与下钻

- 查询配置新增“第二统计维度（可选）”；切换数据来源会清除不适用的第二维度。
- 两级结果表格分别显示两个分组字段，图表使用条形图并只截取展示前 12 项，表格与 CSV 保留完整结果。
- 点击第一分组切换为第二维度，点击第二分组切换为第一维度；下钻清除第二维度，时间值不会生成实体筛选请求。
- “返回上次分析”恢复原日期、来源、筛选、第一/第二维度及 URL 条件。
- 旧单维度 URL、localStorage 配置和预设继续兼容；无权限来源或维度不能通过旧配置恢复。

## 自动化与视觉结果

- Backend：`crm.tests.test_reporting crm.tests.test_finance_data_scope crm.tests.test_actual_cash_reporting`，49 项通过，见 `backend-regression.log`。
- Frontend Node：142 项通过，见 `frontend-unit.log`。
- 报表 Vitest：14 项通过，见 `frontend-report-unit.log`。
- Frontend production build：通过；仅有既有大 chunk 警告，见 `frontend-build.log`。
- 真实 Chrome 报表中心 Playwright：14 项通过，覆盖 1440/1280/1024/700、URL/保存恢复、权限、两级表格及双向下钻，见 `playwright-overview.log`。
- 真实截图：
  - `screenshots/reports-multidim-1440.png`
  - `screenshots/reports-multidim-700.png`
  - `screenshots/reports-drill-1440.png`
  - `screenshots/reports-return-1440.png`

## 未完成与限制

本轮只完成 ISS-041-A 两级交叉分组基础能力。原始销售订单/商品明细独立详情列表，以及客户、产品、SKU 详情页的“查看经营分析”入口，按用户授权保留为后续 ISS-041 子任务。当前等待独立代码审查；本报告不代表 ISS-041 整体关闭。
