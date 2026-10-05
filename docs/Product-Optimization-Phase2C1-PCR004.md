# SUNJACK-ERP Product Optimization Phase 2C-1 — PCR-004

## 验收结论

**PCR-004：PASS。** 2026-10-05 在本地开发环境使用内置 Browser 完成 UAT-P2C1-001 至 007。采购来源订单与实际履约关联订单分别展示，订单、采购详情和收货成功后的订单导航均复用现有查询式详情路由。

本阶段只处理 PCR-004；没有改动采购成本分配语义、收货/库存业务逻辑、详情路由架构或权限，没有新增迁移。

## 实现

### 来源订单与履约关联订单

- `PurchaseOrder.order` 仍表示创建采购单时选择的**来源订单**；采购列表仍以“来源订单”展示，空值为 `—`。
- 新增只读 `related_orders` 序列化字段，形状为 `[{"id": <order id>, "order_no": <order number>}]`。它只从 `PurchaseOrderItem → cost_allocations → target_type="order" → order` 推导，按订单 ID 去重并稳定升序；包含已取消订单的历史分配，不从 `PurchaseOrder.order` 生成。
- 采购展开详情显示“履约关联订单”链接；空分配显示“暂无销售订单归属”。来源订单与履约关联订单是独立关系，可以分别指向不同订单。
- 收货成功保留提示“验货入库已完成，库存、预留及在途数量已同步。”，并按 `related_orders` 显示一个或多个订单链接。没有实际订单分配时不显示 CTA，不回退到来源订单，也不自动跳转。

### 导航与查询

- 订单详情“采购与发货”中的采购单号/“查看采购单”导航到 `/purchase-orders?detail=<purchase.id>`。
- 采购列表“来源订单”导航到 `/orders?detail=<PurchaseOrder.order id>`。
- 采购展开详情及收货成功 CTA 导航到 `/orders?detail=<PurchaseCostAllocation.order id>`。
- 导航使用 Vue Router；目标页现有查询式详情展开，浏览器 Back 可返回上一个详情，链接不携带 `create`、`edit` 或 `returnTo` 查询。
- `prefetch_purchase_related_orders()` 为采购列表、订单履约序列化、采购草稿生成响应和供应商采购上下文批量预取采购行及其成本分配，并 `select_related("order")`。序列化器处理已预取数据，不按每张采购单查询；未预取的单对象场景仍使用一条批量关系查询。后端查询数测试确认采购行数增加时成本分配查询数不增长。

## 真实 UI UAT

环境：`http://127.0.0.1:5192`，本地开发环境，日期 2026-10-05（Asia/Shanghai）。全部操作经内置 Browser 和应用正常页面完成；UAT 业务数据没有通过 API、数据库或 shell 创建/修改。

| 项目 | 结果 | 实际 UI 结果 |
| --- | --- | --- |
| UAT-P2C1-001 Order → Purchase | PASS | 打开 SO-2026-00028 的“采购与发货”，点击 PO-2026-00017 · 查看采购单；路由到 `/purchase-orders?detail=17`，PO-2026-00017 展开，供应商为 UAT 供应商 A、状态已完成。 |
| UAT-P2C1-002 Back to Order | PASS | 从采购详情浏览器 Back 返回 `/orders?detail=28`，SO-2026-00028 详情重开；没有 create/edit/returnTo 残留参数或编辑弹窗。 |
| UAT-P2C1-003 Purchase → Source Order | PASS | PO-2026-00017 的“来源订单”链接目标是 `/orders?detail=28`；点击后打开 SO-2026-00028 详情。 |
| UAT-P2C1-004 Actual related orders | PASS | PO-2026-00017 展示“履约关联订单”SO-2026-00028；点击链接打开 `/orders?detail=28`。此 UAT 记录中来源订单与分配订单相同；两者不同的情形由后端和前端自动化测试覆盖。 |
| UAT-P2C1-005 Receipt success CTA | PASS | 现有记录中无待收货且有销售订单分配的安全 UAT 采购单，因此通过应用新建并下单 PO-2026-00019，分配给 SO-2026-00033；在正常收货表单登记合格入库 0.01 pcs。成功提示原文保留，显示“查看关联订单 SO-2026-00033”；点击后打开 `/orders?detail=33`。PO 剩余 0.99 pcs，状态为部分到货。 |
| UAT-P2C1-006 No false related order | PASS | 对库存归属且无来源订单的 PO-2026-00005，通过正常收货表单登记 0.01 pcs。详情显示“暂无销售订单归属”；成功提示保留且没有关联订单 CTA。 |
| UAT-P2C1-007 Direct URLs / Refresh | PASS | 直接打开并刷新 `/orders?detail=33` 与 `/purchase-orders?detail=19`；刷新后订单 SO-2026-00033 和采购 PO-2026-00019 仍正确展开。 |

### 本次 UAT 数据变更

- 通过采购页面新增 PO-2026-00019：供应商 UAT 供应商 A，来源订单及实际订单分配均为既有 UAT 订单 SO-2026-00033，SKU-000001，基础单位 1.00 pcs，单价 USD 0.10，USD/CNY 汇率 7.2。下单后生成一条 USD 0.10 应付计划；已付 0、未付 USD 0.10。随后在正常 UI 收货 0.01 pcs，收货单价 USD 0.10。
- PO-2026-00019 草稿最初关联 SO-2026-00005；应用拒绝从草稿订单下单并提示订单状态不允许继续采购。草稿未产生应付计划；在应用中改选既有已确认订单 SO-2026-00033 后正常下单。没有确认或改动 SO-2026-00005。
- 修改既有 UAT 库存归属 PO-2026-00005：正常 UI 收货 0.01 pcs，收货单价 USD 7.10；剩余 1.99 pcs。该采购单没有来源订单，也没有销售订单成本分配。
- 没有创建销售订单、供应商、付款或其他财务记录；PO-2026-00019 下单生成的 USD 0.10 应付计划是开放收货流程所需的唯一新财务计划。

## 自动化验证

- 新增 `crm.tests.test_purchase_order_related_orders`：8 项测试，覆盖单一订单分配、多采购行同订单去重、多订单稳定排序、来源订单与实际分配订单不同、取消订单保留、仅库存/样品/其他分配返回空、原有序列化字段，以及采购列表和订单履约列表避免逐采购单增加分配查询。
- `python manage.py test`：499 项通过，10 项跳过；包含 PCR-001、PCR-002、PCR-003、PCR-011 既有回归测试。
- `python manage.py check`：通过。
- `python manage.py makemigrations --check --dry-run`：通过，无迁移变更。
- `npm run test:unit`：109 项通过。
- `node --test tests/detail-drawer-typography.spec.js`：1 项通过。
- `npx --no-install vitest run tests --environment jsdom --exclude tests/detail-drawer-typography.spec.js`：14 个文件、86 项通过。新增采购/订单导航测试覆盖 RouterLink 目标与 Back、查询清理、来源订单与履约订单 ID 不同、零/单/多关联订单的收货 CTA。
- `npm run build`：通过。Vite 保留既有主 JS 包超过 500 kB 的提示（当前约 988.58 kB）。
- `git diff --check`：通过。

## CI 与限制

实现与 UAT 文档已准备提交；远端 CI 将在提交推送后运行，具体工作流运行编号和 backend、backend-postgres、frontend 作业结论待完成后补记。

真实 UAT 数据没有来源订单与实际订单分配不同、也没有多订单分配的待收货例子；相关区别、多目标排序和多 CTA 已由自动化测试覆盖。构建仍显示既有的大包体提示，不影响构建和测试。
