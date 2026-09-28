# Task C：订单采购草稿闭环

## 计算规则

- `to_procure_quantity` 保持既有语义：库存预留与正式采购覆盖后的真实缺口；草稿不改变它。
- `draft_procurement_quantity` 是当前订单归属的 Draft 采购单覆盖量。对相同 SKU 的多个订单行，按 OrderItem ID 顺序分配，避免重复覆盖。
- `draftable_quantity = max(0, to_procure_quantity - draft_procurement_quantity)`。

## 生成规则

- 仅 confirmed / production 销售订单可生成，且只能生成 Purchase Draft；用户仍须人工执行 place。
- 自动流程重新验证订单行 SupplierSKU：存在、启用、SKU 匹配，且订单快照币种不得与当前来源币种冲突。
- 每张草稿按 `Supplier + Currency` 分组。CNY 汇率固定 1；非 CNY 必须提交大于 0 的汇率。
- 参考价来自订单分配快照；本次单价与数量可在预览中调整，但数量不得超过实时 `draftable_quantity`，MOQ 仅警告。

## 并发与回滚

`create_purchase_drafts()` 在单一事务中锁定 Order、OrderItem 与当前 Draft PurchaseOrder，重算计划后才创建草稿。第二个并发请求会在取得 Order 锁后看到第一份 Draft，不能重复覆盖。批量分组创建与 PO 编号分配同属该事务，任一组失败会整体回滚。

## 状态安全

关联销售订单的采购 Draft 在 place 前重新检查订单状态；当订单不再是 confirmed / production 时拒绝下单。Draft 删除会自然恢复可生成数量；place 后 Draft 覆盖归零并由既有正式采购算法接管；取消正式采购后缺口按既有 fulfillment 逻辑恢复。

## 验证

- SQLite：采购计划、重复 SKU 分配、分组、汇率与数量校验、状态切换、批量回滚。
- PostgreSQL：两个独立 transaction 并发生成同一订单缺口，仅一个 Draft 成功。
- 前端：工作台缺口/草稿/关联采购展示与采购预览输入约束。

## 留待 Task D

1. 手工 Purchase 页面 SupplierSKU 参考价跨币种误复制。
2. Purchase create/update SupplierSKU source resolution 统一。
3. Supplier Allocation 与真实多供应商采购语义。
4. 同一 OrderItem 的多供应商正式拆分模型。

## 留待 Task E

- `cost_allocation_version`、legacy version-0 attribution、explicit Cost Allocation migration，以及 `PurchaseOrder.order` 的历史成本归属兼容均未改动。
