# 财务服务协作契约（工作稿，尚未全链路验收）

基于 `codex/finance-inventory-consistency-01`。本稿供历史承接和库存界面工作包对接；不是批准迁移或发布的指令。

预收／预付款分配使用 `POST /api/transactions/{来源流水}/allocate/`，必须在 `Idempotency-Key` 请求头提供本次业务动作的稳定标识，正文为 `{"plan": 计划标识, "amount": "原币十进制金额"}`。首次成功及同内容重放均返回原有 HTTP 200 结果；重放附带 `Idempotent-Replay: true`。同一标识用于不同来源、计划、金额或操作身份返回 409。标识缺失返回 400。记录、计划、请求身份和审计在同一数据库事务内；失败回滚后可使用同一身份重试。

同一动作双击、超时或刷新后必须保持相同标识与内容；用户明确发起另一笔分配时创建新标识。收到结果不明的响应后不可生成新标识代替原操作。网页当前将待确认请求保留在同一标签页的 sessionStorage；关闭标签页及跨设备恢复尚未覆盖，需后续设计。

采购付款 `POST /api/purchase-orders/{采购单}/pay/` 和计划收付款 `POST /api/payment-plans/{计划}/settle/` 同样要求 `Idempotency-Key`；首次及重放返回原 HTTP 201 结果，重放附 `Idempotent-Replay: true`，同身份不同内容返回 409。计划路径保留用户选择的计划。网页仅在本标签页恢复结果不明的请求，真实浏览器验收尚未完成。

库存弹窗工作包 A：手工单笔 `POST /api/inventory-movements/` 和批量 `POST /api/inventory-movements/batch/` 使用同一 `Idempotency-Key` 请求头契约；相同内容重放返回原 201 及 `Idempotent-Replay: true`，同标识不同内容返回 409。请在发送前保存标识和完整提交意图，在结果不明或刷新后复用，确认新动作才创建新标识。库存流水、库存预留变化、全部审计及请求结果须整体提交或回滚。此接口在 A 的弹窗接入前不应视作最终集成完成。

客户收款结构化入口复用 `POST /api/transactions/` 和 `crm.services.finance.record_customer_receipt`：使用稳定的流水业务编号 `transaction_no`，同编号同指纹重放返回原记录，不同内容返回 409。收款原币实到、银行手续费和核销分配分开保存；折让等非现金抵减通过 `FinancePlanWriteoff` 和 `FinanceReceiptAdjustment` 保留凭证、审计及更正链，不应通过创建现金流水模拟。`allocation_capacity` 是可核销额度，`unallocated_amount` 是未分配的实际现金，`fx_available_amount` 以实际原币现金扣减已确认结汇为基础。

原始直接计划收款及历史承接仍有独立路径；不要在历史工作包复制旧财务实现。此工作稿不证明退款或跨模块银行确认已实现同一请求身份契约；库存弹窗与最终集成版本仍须验证。
