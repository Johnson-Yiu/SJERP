# R1-PO-04 本地验收证据

日期：2026-10-20  
分支：`codex/r1-po-04`  
验收环境：独立 SQLite 数据库 `backend/po04-uat.sqlite3`，开发超级管理员，未启用正式 RBAC。

## 结论

当前实现已具备共享采购单的多订单成本归属、库存归属、数量守恒、分批到货和付款计划能力。本轮未发现需要修改业务代码的实际缺陷；本分支只提交本验收记录和真实浏览器截图。

状态：`LOCAL PASS / CI PENDING`

## 已具备能力审查

- `PurchaseOrder` 对应一个供应商真实采购单，可包含多条 `PurchaseOrderItem`。
- `PurchaseCostAllocation` 支持同一采购行拆分到多个销售订单、库存及其他合法用途。
- `validate_allocation_integrity` 要求每条采购行的成本归属数量与采购数量完全相等。
- `save_costs` 使用事务、行锁和版本号保存分配；订单成本由 `order_purchase_cost` 汇总，不会创建重复采购、付款或入库。
- `procurement_scope.py` 对可见销售订单和可写销售订单做后端校验，前端隐藏不是唯一保护。
- 到货流程通过 `GoodsReceipt` 与 `InventoryMovement` 保留多次到货记录；付款流程按应付计划结算。
- `PurchaseOrderItem` 保存供应商和 SKU 快照，历史单据不会随主档修改而改写。

## 实际浏览器验收

通过真实 Chrome 完成：

1. 创建采购草稿，选择 SKU A、SKU B，数量分别为 5、3，单价分别为 CNY 10、20。
2. 保存草稿并确认下单，采购单号为 `PO-2026-00001`。
3. 在成本分配中将 SKU A 分配为：库存 2、销售订单 A 2、销售订单 B 1；SKU B 分配为：库存 1、销售订单 B 2；保存为 V2。
4. 重新打开核对，页面显示每条明细“剩余 0.00”，且分配数量未超过采购数量。
5. SKU A 分两次登记合格到货 2 + 3，页面显示已到 5/5，并保留两条入库记录。
6. 登记供应商付款 CNY 110；页面显示已付 CNY 110、未付 CNY 0、两条应付计划均已结清。

截图：

- [采购概览、付款完成](01-overview-paid.png)
- [成本分配 V2 与多用途拆分](02-cost-allocation-v2.png)
- [SKU A 两次到货记录](03-receipts-two-records.png)
- [供应商付款及应付计划结清](04-payment-settled.png)

## 隔离数据库核对

实际命令：

```powershell
$env:DATABASE_URL='sqlite:///C:/Users/Johnson/.codex/worktrees/r1-po-04/backend/po04-uat.sqlite3'
python manage.py shell -c "...PurchaseOrder / PurchaseCostAllocation / GoodsReceipt / InventoryMovement / Transaction / PaymentPlan 核对..."
```

退出码：`0`。

关键结果：

- 采购单：1 张，状态 `partial`，合同金额 `110.00`。
- 采购行：SKU A `5.00`，已到 `5.00`；SKU B `3.00`，已到 `0.00`。
- 成本归属：SKU A `2 + 2 + 1 = 5`；SKU B `1 + 2 = 3`，均守恒。
- 销售订单采购成本：订单 A `20.00`；订单 B `50.00`。
- 收货：2 条，数量 `2.00` 和 `3.00`；采购来源库存流水：2 条，没有重复流水。
- 付款：按原有两条应付计划生成 `33.00 + 77.00 = 110.00` 两条确认支出流水；每条计划各结清一次，没有重复付款。
- 库存、预留和成本分配均由既有流程更新；库存辅助信息未修改采购数量或成本。

## 自动化测试

### 后端定向回归

命令：

```powershell
python manage.py test crm.tests.test_purchase_costs crm.tests.test_purchase_order_related_orders crm.tests.test_purchase_safety crm.tests.test_procurement_data_scope --verbosity 1
```

结果：`30 tests`，`OK`，退出码 `0`。

### SQLite 全量回归

第一次在受限沙箱直接执行退出码 `1`，唯一错误是附件测试无法在 worktree 的 `backend/media/follow-up-attachments` 创建目录，非业务断言失败。

随后在相同代码和隔离数据库下，以允许写入忽略媒体目录的测试环境重新执行同一命令：

```powershell
python manage.py test --verbosity 1
```

结果：`Ran 768 tests in 297.979s`，`OK (skipped=13)`，退出码 `0`；Django system check 无问题。测试输出同时确认历史数据库校验哈希不变、历史金额字段保持原值。

### 前端

- `npm run test:unit`：136 passed，0 failed，退出码 `0`。
- `npm run build`：Vite 构建成功，2005 modules transformed，退出码 `0`；只有既有 chunk size warning。

### PostgreSQL

本机没有 PostgreSQL 服务，`Test-NetConnection 127.0.0.1 -Port 5432` 为 `TcpTestSucceeded=False`，因此未伪造 PostgreSQL 通过结果。

## 权限与审计边界

当前开发环境显示“开发身份：Johnson 超级管理员”，并设置 `RBAC_ENFORCEMENT=false`，所以本轮真实 Chrome 流程验证的是开发超级管理员路径，不是正式采购员工/销售员工/无采购修改权限的真实 RBAC 组合。

代码审查确认成本分配 API 仍通过 `validate_cost_writes` 做后端范围校验；跨销售权限委托属于 ISS-039，本轮未扩大实施。

隔离服务未启用 `AUDIT_LOG_ENABLED`，因此本次数据库中的 `OperationLog` 数量为 0；不能将其报告为审计日志通过。正式验收前应在启用审计日志的认证环境补做历史操作记录验收。

## R1-SKU-01 / R1-MOQ-02 / R1-INV-03 兼容性

未修改、未合并任何关联分支。

- `codex/r1-moq-02` 与本分支的直接迁移差异是新增 `0078_purchase_moq_exceptions.py`，依赖 `0077_rmb_cash_events`。
- `codex/r1-moq-02` 与 `codex/r1-inv-03` 的临时三方差异检查发现共同修改 `backend/crm/views.py`、`frontend/src/views/PurchaseOrderPage.vue`、`frontend/src/views/PurchaseOrderPage.test.js` 以及项目记录文档，后续整合需人工解决，不能直接覆盖。
- R1-SKU-01 另有 `0078_sku_cost_verification.py`，同样依赖 `0077`。正式整合建议先使其中一条 0078 成为目标分支祖先，再新增只包含依赖关系的 0079 merge migration，同时依赖两个 0078；不得重写或删除已发布迁移。
- 本分支不包含上述功能，也没有将临时合并结果推送。

## ISS-039

ISS-039 的跨销售权限委托和公共费用局部重分摊仍是独立事项，本轮只复用现有可见/可写范围校验，不标记关闭。

