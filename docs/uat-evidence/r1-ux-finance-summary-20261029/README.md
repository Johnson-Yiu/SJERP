# R1-UX-FINANCE-SUMMARY-01

日期：2026-10-29

基线：`54e715bdc568b80ba624186fecd866550676cf38`

分支：`codex/fix-finance-summary-card-truncation-20261029`

## 验收结论

已修复 1024px 实际内容区过窄时汇总卡片仍按外部视口保持四列、导致金额被省略的问题。

- `SummaryCards` 新增无视觉占位的容器包装，并使用 container query 按实际可用内容宽度切换 4/3/2/1 列。
- 金额不再使用 `text-overflow: ellipsis`；金额允许自然换行，完整文本保持可读。
- 未修改金额计算、统计口径、权限、卡片图标、标签或提示。
- 仅修改前端呈现和测试；未修改共享台账、后端或数据库。

## 真实 Chrome 验收

使用真实 Chrome（`PLAYWRIGHT_CHANNEL=chrome`）和隔离模拟 API 数据，注入一笔 `¥ 20,000,000,000.00` 长金额，验证 DOM 文本完整、无水平文本溢出、无省略号，并保存实际截图。

| 页面 | 1440px | 1024px | 390px |
| --- | --- | --- | --- |
| 财务流水 | [截图](screenshots/transactions-1440.png) | [截图](screenshots/transactions-1024.png) | [截图](screenshots/transactions-390.png) |
| 应收计划 | [截图](screenshots/receivables-1440.png) | [截图](screenshots/receivables-1024.png) | [截图](screenshots/receivables-390.png) |
| 应付计划 | [截图](screenshots/payables-1440.png) | [截图](screenshots/payables-1024.png) | [截图](screenshots/payables-390.png) |

1024px 时实际主内容宽度约 708px，卡片使用两列；390px 时使用单列。其他共享 `SummaryCards` 页面也通过真实 Chrome 检查：客户管理、供应商管理、采购管理。

完整浏览器日志：[browser-finance-summary.log](logs/browser-finance-summary.log)

## 自动化结果

- 前端 Node 全量单元测试：`169` 通过，`0` 失败。
- 真实 Chrome：`12` 通过，`0` 失败；覆盖三处财务页面的 1440/1024/390px，以及三个其他共享卡片页面。
- 前端生产构建：通过，`2018 modules transformed`；保留既有大 chunk warning，不影响构建结果。
- 构建日志：[frontend-build.log](logs/frontend-build.log)
- 单元测试日志：[frontend-unit.log](logs/frontend-unit.log)

## 改动文件

- `frontend/src/components/SummaryCards.vue`
- `frontend/src/components/SummaryCards.test.js`
- `frontend/browser-tests/finance-summary-cards.spec.js`

本轮未触发 CI、未推送真实密钥、未修改财务统计口径或权限，也未修改 `PROJECT_ISSUES.md` / `PROJECT_PHASES.md`。
