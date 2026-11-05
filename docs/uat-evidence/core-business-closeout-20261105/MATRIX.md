# 当前实现 / 已有证据 / 实际缺口矩阵

固定基线bcdcb57545f121b8a4102f352c74008b47372035。先行核对时间2026-11-05；下列疑点需失败复现，不能仅凭源码宣布缺陷。

| 子任务 | 当前实现 | 已有证据（本轮不冒充重新执行） | 本包验证/补修方向 |
|---|---|---|---|
| 销售闭环 | quote转SO、order_lifecycle确认/履约完成，finance.order_receivable_state独立欠款状态 | test_fulfillment_receivables、fulfillment-receivables浏览器及ISS001/004/109复审队列；完成仍欠款、收齐消失及退款恢复已有回归 | 新增独立API贯通，Chrome关键操作补验；检查原子性与取消/发货竞争，不重做财务账户服务或主体快照 |
| 采购闭环 | 独立/关联PO、cost_allocations跨SO、收货/冲销、PO父锁和应付计划 | test_contract_lifecycle、test_fulfillment、ISS005及ISS006库存Chrome原始证据 | 独立PO及共享PO分配改变后关联保留；部分/全部到货及冲销后应付不自动改写；取消竞争 |
| MOQ/单位 | SupplierSKU按PO合计基础数量，draft可保存、place例外原因/操作人/时间；normalize_trade与快照包装语义 | test_purchase_moq、test_trade_units、test_actual_packing、iss-022-procurement-moq及iss036-fix03 | 覆盖低/等/高、共享合计、可分数/不可拆分，旧冲突快照不擅自决定优先级；不重定义规则 |
| 库存/预留 | SKU全局锁、总量/预留、history基准、location_quantity、收发冲销 | test_history_operational_inventory、test_iss006_idempotency、test_inventory_reversal_audit_atomicity及库存Chrome证据 | **疑点C01**：位置库存强制校验只在有历史盘点基准时启用；普通多仓/批次可能借用别仓余额。先复现出库、入库冲销、手工冲销及手工出库，再最小服务修复 |
| 成本归属 | 金额比例、最大余数、零基数拒绝、version控制、PO行锁；采购update无需逐SO授权 | test_purchase_costs、test_iss039_shared_purchase_costs、20261103共享成本审查及后续比例补修，复审队列已说明旧数量法已修 | **疑点C02**：prepare_costs使用反序列化时的Order对象，取消后旧对象可被保存；先证明过时对象及真实API竞争，再补新鲜有序订单锁，不增加SO权限要求 |
| 异常/并发 | 持久Idempotency-Key、PO父锁、库存锁、API审计同事务、现有PG竞争 | test_postgres_concurrency、test_iss006_idempotency、fulfillment_audit_atomicity等 | 独立PG17连接覆盖响应丢失同键/异内容、超量、取消与履约、成本版本/取消竞争；核对完整业务快照，不用SQLite冒充锁验证 |

边界：不改主体快照/审批、权限框架、导出helper、财务账户资金、运维/运行器及共享台账。使用锁定依赖和合成资料、临时媒体/隔离DB。CI额度暂停，不执行Actions，所有本包提交[skip ci]。新发现跨边界问题记录复现和建议交集成协调，不顺手扩大修复。


## 复现后的补充核查

C01/C02 已失败复现并最小补修，保持上表先行判断不改写。补验全部收货后的应付及审计失败时新增 C03：采购付款服务完成后两条审计在事务外，第二条失败会留下付款/核销及第一条审计。先保留 before-payment-audit 失败与快照，再仅给 PurchaseOrderViewSet.pay 加统一事务；账户资金服务、付款及权限规则不改。最终状态和完整结果以 README 为准，均等待独立复审。
