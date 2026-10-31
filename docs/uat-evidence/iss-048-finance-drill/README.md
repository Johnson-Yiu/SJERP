# ISS-048 财务概览指标下钻验收证据

## 范围

- 分支：`codex/iss-048-finance-drill`
- 基线：`codex/iss-042-shared-reports` / `fb859b91f68bb62c539d5439c65b52c06f13a58c`
- 本轮：财务概览卡片构成明细 API、分页/排序、权限范围复用、原始业务链接，以及桌面/窄屏界面入口。
- 未新增数据库迁移，未改变 ISS-062 日期规则、历史订单隔离、账面人民币折算参考或已确认银行人民币资金规则。

## 实施结论

`/api/finance-dashboard/details/` 按卡片指标返回服务端计算的总额、记录数、日期依据、口径说明和最多 100 条/页的明细；服务端复用财务概览的 `scope_customer_related_queryset`、`scope_plan_queryset`、`scope_transaction_queryset`、正式订单状态过滤和已确认流水过滤。前端在各可追溯卡片显示“查看构成明细”，支持表头日期/金额/记录排序、分页、空状态和现有订单/财务流水路由。

银行实际人民币资金没有复制一套下钻查询：卡片入口定位到现有“已确认银行资金明细”，其数据仍来自 `/api/actual-rmb-cash/` 的 `RmbCashEvent.status=confirmed`、`bank_date`、`bank_net_amount`，并链接现有人民币资金事件详情。

## 证据索引

- [指标及口径映射](metric-mapping.md)
- [汇总与明细对账](reconciliation.md)
- [测试结果](test-results.md)
- [销售明细 API 样例](api-sales-detail.json)
- [账面收支 API 样例](api-book-cash-detail.json)
- [权限/API 安全样例](api-permission-detail.json)
- 原始日志：`backend-focused.log`、`backend-full.log`、`frontend-finance-vitest.log`、`frontend-vitest-full.log`、`frontend-node.log`、`frontend-build.log`、`browser-finance-drill.log`、`browser-finance-regression.log`
- [1440px 下钻截图](finance-drill-1440.png)
- [700px 下钻截图](finance-drill-700.png)
- [1440px 银行事件截图](finance-bank-events-1440.png)
- [700px 银行事件截图](finance-bank-events-700.png)

## 验收边界与剩余事项

- Playwright 使用真实 Chromium，但 API 通过 route mock 提供，因此截图和交互属于“真实浏览器 + mock API”验收，不冒充 Django 集成验收。
- Django APIClient 的 SQLite 测试使用真实后端查询、权限和数据范围；当前环境没有可用于跨账号登录的长期浏览器测试服务账号，真实 Django 跨账号浏览器操作仍待集成环境补测。
- PostgreSQL 与 GitHub CI 仍按项目约定保持待执行/PENDING。
- 未为没有可靠业务依据的银行账户余额、会计利润或未确认银行凭证创建伪造下钻；这些不属于本轮新增可追溯指标。
- ISS-048 及其前置 ISS-041/ISS-042 不在本轮标记为 CLOSED，等待独立代码、权限、财务口径和视觉复审。
