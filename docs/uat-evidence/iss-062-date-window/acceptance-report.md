# ISS-062 经营概览统计日期统一验收

## 基线与范围

- 分支：`codex/iss-062-date-window`
- 基线：`codex/r1-hist-01` / `b5e46be7863c9756f010df972870bfd0ec154a62`
- 冻结统计日：`2026-10-22`
- 本轮只调整经营概览 Dashboard 的日期边界、历史订单隔离、日期元数据和对应文案；未新增数据库迁移，未修改历史订单业务规则、ISS-121、实际银行人民币资金统计或自定义报表未来日期能力。

## API 证据

`dashboard-api.json` 的服务端日期元数据：

- `as_of`: `2026-10-22`
- `year_start` / `year_end`: `2026-01-01` — `2026-10-22`
- `trend_start` / `trend_end`: `2025-11-01` — `2026-10-22`

冻结数据返回结果：

- 本年销售额：`5000.00`；本年截至今日订单数：`2`。
- 2026-10-23 和 2026-11-01 的正式订单未进入本年销售额、订单数、客户排行或品类销售额。
- `historical_only=True` 的正式状态订单未进入经营概览。
- `monthly_sales` 恰好 12 个月，从 `2025-11` 到 `2026-10`；无订单月份返回 `0.0 / 0`。
- 已确认账面流水截至今日收入 `125.00`、支出 `40.00`；未来日期流水未进入统计，仍为 Transaction 的人民币折算参考。

`custom-report-future-api.json` 验证自定义销售报表仍可查询 `2026-11-01` — `2026-11-30`，返回未来期间订单金额 `99999.00`。

## 自动回归

- `backend-dashboard-import.log`：14/14 PASS，包含冻结日期、未来订单、历史订单、零月补齐、空趋势、账面流水和自定义未来报表验证。
- `backend-reporting.log`：20/20 PASS。
- `backend-actual-cash.log`：28/28 PASS（3 个既有 PostgreSQL 特定场景按项目现状跳过）；实际银行人民币资金仍按独立银行事件、银行日期和人民币净额统计。
- `frontend-unit.log`：142/142 PASS。
- `frontend-dashboard-vitest.log`：25/25 PASS。
- `frontend-build.log`：生产构建 PASS；仅有既有大 chunk 提示。
- `playwright-overview-reports-chrome.log`：13/13 PASS，使用真实 Chrome channel，覆盖 Dashboard/报表中心和 1440/1280/1024/700px。

## 真实 Chrome 视觉验收

- [1440px Dashboard 截图](dashboard-1440.png)：日期元数据、12 个月趋势、品类/重点客户范围、账面人民币折算参考均可见；无页面级横向溢出。
- [700px Dashboard 截图](dashboard-700.png)：卡片单列/双列响应式布局正常，趋势图保留内部横向滚动；无页面级横向溢出。

人工检查确认可见文案简短、面向办公任务，已移除“含未来日期订单”等过时说明，保留“正式订单”“人民币折算参考”等业务术语。

## 待独立代码审查

本报告不关闭 ISS-062，也不替代独立代码审查。CI 未触发，按要求保持 PENDING；本地临时 SQLite、合成视觉验收数据和运行服务仅用于本轮验收。
