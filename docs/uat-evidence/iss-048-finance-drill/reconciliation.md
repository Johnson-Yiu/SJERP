# 汇总与明细对账

测试夹具固定查询期间为 `2026-09-01` 至 `2026-09-30`：

1. 正式订单 `FIN-DRILL-SO`：商品金额 USD 20，订单汇率 2，合同销售额人民币 40。
2. `FIN-DRILL-HISTORY` 为 `historical_only=True`，金额 999；不进入正式经营概览或销售下钻。
3. `FIN-DRILL-DRAFT` 为草稿，`FIN-DRILL-FUTURE` 在所选期间外；两者均不进入销售下钻。
4. 已确认账面收入 `FIN-DRILL-IN` 为 30，已确认账面支出 `FIN-DRILL-OUT` 为 4；未来流水 90 与 pending 流水 80 均排除，因此净收支为 26。
5. 两笔开放应收计划的当前未结本金为 USD 90 与 USD 25，订单汇率均为 2，当前待收合计为人民币 230，独立于所选日期。

| 查询 | Dashboard 汇总 | details 合计 | 记录数/结果 | 对账结论 |
|---|---:|---:|---:|---|
| `sales_rmb` | 40 | 40 | 1，`FIN-DRILL-SO` | 一致 |
| `income_rmb` | 30 | 30 | 1，`FIN-DRILL-IN` | 一致，未来/pending 排除 |
| `expense_rmb` | 4 | 4 | 1，`FIN-DRILL-OUT` | 一致 |
| `net_cash_rmb` | 26 | 26 | 2，收入与支出各 1 | 符号一致 |
| `receivable_rmb` | 230 | 230 | 2，分页每页 1 | 一致，当前余额口径 |

实际银行资金继续由既有 `test_actual_cash_reporting` 验证确认状态、`bank_date`、银行净额、手续费和 CSV；ISS-048 没有复制或改写这条事实链。
