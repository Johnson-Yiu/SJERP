# ISS-048-FIX-01 权限矩阵核对

| 财务指标 | 概览显示条件 | 下钻条件 | 本轮处理 |
|---|---|---|---|
| `sales_rmb`、`receivable_count`、`receivable_rmb` | `orders.view` | `orders.view` | 保持不变 |
| `purchase_cost_rmb`、`order_expense_rmb`、`estimated_profit_rmb` | `orders.view` + `purchases.view` | `orders.view` + `purchases.view` | 保持不变 |
| `payable_count`、`payable_rmb` | `purchases.view` | `purchases.view` | 修复为一致 |
| `income_rmb`、`expense_rmb`、`net_cash_rmb` | `transactions.view` | `transactions.view` | 保持不变 |
| 预收/预付未核销指标 | `transactions.view` | `transactions.view` | 保持不变 |

所有指标仍首先要求财务概览的 `transactions.view`，并继续使用现有财务数据范围过滤。`purchases.view` 缺失时，应付款下钻由服务端拒绝；前端的入口可见性同步使用采购权限，不承担安全边界。
