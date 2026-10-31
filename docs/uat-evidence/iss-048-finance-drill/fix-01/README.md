# ISS-048-FIX-01 最小权限一致性补修

## 基本信息

- 分支：`codex/iss-048-finance-drill`
- 修补基线：`f2a44dafabdd5cc7b4c5b95abed3865867fd9e7b`
- 范围：仅修复财务概览应付款指标下钻与概览权限矩阵不一致的问题。

## 修复结论

`payable_count` 和 `payable_rmb` 现在与财务概览的应付款卡片使用相同的最小权限边界：需要财务概览已有的 `transactions.view`，以及 `purchases.view`；不再额外要求 `orders.view`。采购成本、订单费用、预计订单利润仍保持 `orders.view + purchases.view`，销售/应收仍保持订单权限，其他指标未扩大访问范围。

应付款明细始终按付款计划的采购侧关联展示供应商和 `/purchase-orders?detail=...` 链接。后端仍复用 `scope_plan_queryset()`，因此没有放宽现有客户、部门或供应商数据范围；没有订单权限时不会通过应付款记录暴露销售订单关联。

## 权限与范围验收

后端真实 Django `APIClient` 测试覆盖：

- 有 `transactions.view`、`finance.view`、`purchases.view`，无 `orders.view`：应付款下钻返回 200，金额为 100，返回的计划 ID 与现有 `scope_plan_queryset()` 完全一致，供应商名称和采购单链接正确；概览卡片金额仍为 100。
- 去除 `purchases.view`：应付款下钻返回 403。
- 原有销售下钻在去除 `orders.view` 后仍返回 403，证明未把订单权限要求放宽到其他指标。
- 既有共享财务、客户范围、交易流水、计划和实际资金权限测试继续通过。

详细原始日志：`backend-finance-permission.log`。

## 前端与浏览器验收

- Node 单元回归：144 passed。
- 财务定向 Vitest：12 passed。
- 生产构建：通过。
- 真实 Chromium 财务回归：6 passed，覆盖财务参考口径、实际资金容错/日期竞态及财务下钻 1440px/700px。
- 本次浏览器测试使用现有 mock API；不将 mock 浏览器交互描述为真实 Django 跨账号集成。真实后端权限结论来自上面的 Django APIClient 测试。

日志：`frontend-node.log`、`frontend-finance-vitest.log`、`frontend-build.log`、`browser-finance-regression.log`。

截图：`finance-drill-1440.png`、`finance-drill-700.png`、`finance-bank-events-1440.png`、`finance-bank-events-700.png`。

## 剩余限制

- PostgreSQL、GitHub Actions 和真实 Django 跨账号浏览器集成仍按项目约定待外部环境验收；本轮未触发 CI。
- ISS-048 继续保持原有 `P3 / BLOCKED（延期）` 与 `FIXED_PENDING_REVIEW` 复审边界，未关闭任何 Issue。
