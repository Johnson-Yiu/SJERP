# Phase 3C — Invariant Fault Injection 执行记录

**分支：** `phase-03c-invariant-fault-injection`  
**基线：** `master` `5f3d6d50bdb903a0f45269e2439657b0943c4c56`  
**执行原则：** 所有故障状态均由 Django `TestCase` 在 temporary test database 中构造；未使用 Phase 3B 开发数据库、未执行开发库 SQL/flush/seed/fixture，未修改业务代码、模型、serializer、view、service 或前端。

## 1. Coverage audit

| ID | 预期不变量 | 已有覆盖 | 覆盖判断 | 本轮动作 |
|---|---|---|---|---|
| E17 / I20 | Shipment 任一原 `sale_out` 缺失或 SKU、order、quantity、source_type 异常时整单拒绝 | 已有缺失 movement 测试 | 不充分 | 新增 SKU、order、quantity、source_type 四类异常，并统一 before/after 原子性断言 |
| E21 | cancelled Order 不得冲销 confirmed Shipment | 已有 completed Order 测试 | 不充分 | 新增 cancelled Order 场景与库存/预留/流水快照 |
| E25 | root 第二次 void 拒绝且历史不被覆盖 | API 重复作废已有覆盖 | 不充分 | 新增直接 service 二次调用与 root/child/plan 快照 |
| E26 / I37 | `allocated_amount` 与 active allocation 合计不一致时安全拒绝 | 已有 allocation mismatch 测试 | 充分但断言不足 | 补齐 transaction、allocation、advance、plan before/after 断言 |
| E27 | PaymentPlan rollback underflow 原子拒绝 | 已有单 root underflow 测试 | 不充分 | 新增 root + split child + plan underflow 快照 |
| E29 | settle/record_transaction 错误币种与非法 CNY 汇率拒绝 | 已有 API payload 校验 | 不充分 | 新增直接 service 币种/汇率测试 |
| E33 | 跨客户、供应商、方向、币种及非 open plan 的 allocate 拒绝 | 已有方向/取消计划测试 | 不充分 | 新增五类服务层场景并断言无 allocation/plan 变化 |
| E39 | SKU Code unique、创建后不可改、商业字段变化不替换稳定身份 | `test_sku_code_is_read_only_after_creation`、`test_model_rejects_direct_sku_code_change`、商业身份测试集 | 充分 | 不重复新增同义测试，直接复用现有测试 |
| E40 | receipt 二次 reversal 拒绝 | 已有二次调用测试 | 断言不足 | 新增 movement、库存、PO、received、reservation 快照 |
| E41 | shipment 二次 reversal 拒绝 | 已有二次调用测试 | 断言不足 | 新增 movement、库存、reservation、订单/Shipment 快照 |
| E42 / I49 | split child 不可单独 void | 已有 direct child 测试 | 充分但断言不足 | 补齐 Transaction/Allocation count 断言 |
| E43 / I53 | 失败 reversal/void 无部分副作用 | 分散在各测试 | 不充分 | 各新增/加强场景均使用 before/after snapshot |

说明：当前模型没有独立 `source_id` 字段，Shipment 原流水的可用来源字段为 `source_type`、`source_no`、`reference`；本轮按现有 `reverse_shipment()` 契约验证 `source_type` 及其 SKU/order/quantity 关联，不虚构不存在的字段。

## 2. Fault-injection results

| 场景 | 结果 | 原子性证据 |
|---|---|---|
| E17 / I20 | PASS — 缺失 movement、SKU 不一致、order 不一致、quantity 不一致、source_type 不一致均抛出 `ValidationError` | Shipment 仍 confirmed，`reversed_at`/reason/reversal movement 不变；InventoryMovement count、actual、reserved、reservation count、Order status 全部 before=after |
| E21 | PASS | cancelled Order + confirmed Shipment 被拒绝；Shipment、库存、Order、reservation、movement count 不变 |
| E25 | PASS | root 首次作废成功；第二次直接 service 调用拒绝；root/child cancelled 历史、voided_at/reason、PaymentPlan、Transaction/Allocation count 不变 |
| E26 / I37 | PASS | ledger mismatch 被拒绝；root/advance、active allocation、PaymentPlan、Transaction/Allocation count 无变化 |
| E27 | PASS | root + split child 下的 PaymentPlan rollback underflow 被拒绝；root/child、plan、Transaction/Allocation count 无变化 |
| E29 | PASS | USD plan 使用 EUR 被拒绝；CNY plan 使用非 1 汇率被拒绝；Transaction count、计划 settled/remaining 不变 |
| E33 | PASS | 跨客户、跨供应商、跨方向、跨币种、非 open plan 五类 `allocate_advance()` 均拒绝；无新 allocation，advance allocated_amount 与计划状态不变 |
| E39 | PASS — existing coverage | SKU Code unique/read-only 与 SKUVersion 商业身份稳定性由现有测试集覆盖，本轮未重复造测试 |
| E40 | PASS | 第一次 receipt reversal 后第二次 service 调用拒绝；无第二条 reversal movement，库存/received/PO/reservation 不变 |
| E41 | PASS | 第一次 shipment reversal 后第二次 service 调用拒绝；无第二条 adjust_in，库存/订单/Shipment/reservation 不变 |
| E42 / I49 | PASS | 直接 void split child 拒绝；root/child confirmed、PaymentPlan、Allocation/Transaction count 不变 |
| E43 / I53 | PASS | E17、E21、E26、E27、E29、E33、E40、E41、E42 均建立 before/after 快照并相等 |

## 3. Deferred invariants closure

| Invariant | 状态 | 依据 |
|---|---|---|
| I20 | PASS / CLOSED | `reverse_shipment()` 全单校验的五类内部异常测试 |
| I37 | PASS / CLOSED | allocation ledger mismatch 与 rollback underflow 均原子拒绝 |
| I49 | PASS / CLOSED | root 重复 void、split child direct void 均拒绝 |
| I53 | PASS / CLOSED | reversal/void 失败场景的 before/after 快照全部一致 |

## 4. Scope and issue classification

- `REAL BUSINESS BUG-P3C`：0。
- 本轮没有修改生产逻辑；新增/加强内容仅在 `backend/crm/tests/` 与本执行记录。
- 未开始 Phase 4；Phase 3B UAT 数据和执行记录保持封存。

## 5. Regression

后端：`python manage.py check` PASS；`makemigrations --check --dry-run` PASS（No changes detected）；完整测试 `308/308 PASS`。

前端：unit `61/61 PASS`；node-only `1/1 PASS`；Vitest `31/31 PASS`；`npm run build` PASS（仅有既有 chunk-size warning）。

定向 finance/fulfillment 测试：`70/70 PASS`。本轮未修改前端代码。
