# 财务概览指标与下钻口径映射

| 概览指标 | 原始数据来源 | 金额/计数口径 | 日期依据 | 权限与范围 | 下钻结论 |
|---|---|---|---|---|---|
| 合同销售额 | 正式 `Order` | `Order.total_amount * exchange_rate`；包含已批准合同变更，变更不分配到商品行 | `order_date` | `transactions.view` + `orders.view`，复用客户相关数据范围；排除 `historical_only`、草稿、取消 | 支持，链接现有订单详情 |
| 预计订单利润 | `order_profit_summary(order)` | 合同销售额 − 采购归属成本 − 已确认订单费用；仅经营估算 | `order_date` | 订单和采购查看权限及既有范围；金额继续标注估算 | 支持，按订单展示构成说明 |
| 订单采购归属成本 | 既有采购成本归属服务 | `order_purchase_cost` 的采购归属成本 | `order_date` | 订单/采购查看权限及既有范围 | 支持；不把调整擅自分配到 SKU |
| 订单费用 | 既有订单利润服务 | 已确认订单费用，沿用原排除规则 | `order_date` | 订单/采购查看权限及既有范围 | 支持，按订单展示 |
| 账面收入（折算参考） | `Transaction` | `rmb_amount`，否则 `amount * exchange_rate`；仅 `status=confirmed` | `transaction_date` | `transactions.view`，复用流水数据范围；往来方名称按模块权限掩码 | 支持，链接现有财务流水 |
| 账面支出（折算参考） | `Transaction` | 与账面收入相同，支出行金额以正数展示 | `transaction_date` | 同上 | 支持，链接现有财务流水 |
| 账面净收支（折算参考） | `Transaction` | 已确认收入正数 − 已确认支出；不代表银行实际到账或余额 | `transaction_date` | 同上 | 支持，明细行保留收入/支出符号 |
| 待收笔数/待收款 | 开放 `PaymentPlan` | 开放应收计划计数；或 `remaining_amount * order.exchange_rate` | 当前余额，不受所选期间限制 | `orders.view` + 财务/交易查看，复用计划与客户范围 | 支持，明确标注当前余额 |
| 待付款笔数/待付款 | 开放 `PaymentPlan` | 开放应付计划计数；或 `remaining_amount * purchase_order.exchange_rate` | 当前余额，不受所选期间限制 | `purchases.view` + 财务/交易查看，复用计划范围 | 支持，明确标注当前余额 |
| 未核销预收款/预付款 | 已确认未核销 `Transaction` | `(amount - allocated_amount) * exchange_rate`；沿用当前余额口径 | 当前余额，不受所选期间限制 | `transactions.view`，复用流水范围 | 支持，链接现有财务流水 |
| 银行实际人民币资金 | `RmbCashEvent` | 已确认银行事件的 `bank_net_amount`；不含 pending/cancelled | `bank_date` | `/actual-rmb-cash/` 与现有 `cash.visible`/事件详情权限 | 已有可靠明细表和事件链接，本轮只增加卡片定位入口 |

没有可靠业务依据的银行账户余额、未确认银行凭证、会计利润等指标没有新增明细接口，避免把经营估算或账面参考冒充财务事实。
