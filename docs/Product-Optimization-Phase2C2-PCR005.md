# SUNJACK-ERP Product Optimization Phase 2C-2 — PCR-005

## 验收结论

**PCR-005：PASS。** 2026-10-05 在本地开发环境使用内置 Browser 完成 UAT-P2C2-001 至 008。应收、应付和流水列表中的合同号按显式关系 ID 导航；分配历史保留活动及撤回记录并可按关联 ID 打开合同详情。

本阶段只处理 PCR-005。没有改动财务核算、结算、分配或交易生命周期，没有数据库迁移，也没有改写财务概览现有的到期合同链接。

## 实现

### 财务计划与流水列表

- `/receivables` 的合同号用 `row.order` 生成 RouterLink，目标为 `/orders?detail=<order id>`。
- `/payables` 的合同号用 `row.purchase_order` 生成 RouterLink，目标为 `/purchase-orders?detail=<purchase order id>`。
- 缺少对应外键 ID 时，合同显示为纯文本；不使整行可点击。
- `/transactions` 只在 `row.order` 或 `row.purchase_order` 存在时，分别链接当前流水的 `order_no` 或 `purchase_no`。两个 ID 都缺失时显示“未关联合同”。
- 以上页面复用 PCR-004 的 `orderDetailLocation()` 与 `purchaseDetailLocation()`，使用 Vue Router 的正常历史行为，不产生整页刷新或附加 `create`、`edit`、`returnTo` 参数。

### 分配历史与序列化

- `TransactionSerializer.get_allocations()` 在原有分配 payload 中仅增加只读 `order`、`purchase_order` ID，来源分别为 `row.plan.order_id`、`row.plan.purchase_order_id`。`contract_no`、金额和 `is_active` 语义不变。
- 流水列表用 ViewSet 已配置的 `allocations__plan__order`、`allocations__plan__purchase_order` 预取；序列化器直接消费预取集合。没有预取的单对象序列化仍回退至一次关联查询。
- 分配历史中的合同号以分配自身的显式外键 ID 选择目标；ID 缺失时仍显示纯文本。已撤回分配不会隐藏，金额与“已核销/已撤回”显示保持不变。
- 不根据 `SO-` 或 `PO-` 前缀判定导航。合同号仅作显示文本，自定义或历史编号不会改变其 ID 对应的目标。

### 财务概览

`/finance` 的“到期与逾期计划”保持原有 RouterLink 逻辑，未作不必要改写。真实 UI 验证了应付合同跳转和 Back；前端测试验证应收与应付两种目标。

## 真实 UI UAT

环境：`http://127.0.0.1:5192`，日期 2026-10-05（Asia/Shanghai）。操作均经内置 Browser 和应用正常页面完成；本次没有通过 API、数据库或 shell 创建或修改 UAT 业务数据。

| 项目 | 结果 | 实际 UI 结果 |
| --- | --- | --- |
| UAT-P2C2-001 Receivable → Sales Order | PASS | 在 `/receivables` 点击 SO-2026-00032；到达 `/orders?detail=32`，订单工作台标题为 SO-2026-00032。 |
| UAT-P2C2-002 Payable → Purchase Order | PASS | 在 `/payables` 点击 PO-2026-00019；到达 `/purchase-orders?detail=19`，PO-2026-00019 详情展开。 |
| UAT-P2C2-003 Transaction → Sales Order | PASS | 点击流水 FIN-AA31EC535BAC4BE5 的 SO-2026-00030；到达 `/orders?detail=30`，SO-2026-00030 工作台打开。 |
| UAT-P2C2-004 Transaction → Purchase Order | PASS | 点击直接关联合同流水 FIN-4602FE2477E5469E 的 PO-2026-00013；到达 `/purchase-orders?detail=13`，PO-2026-00013 行展开。 |
| UAT-P2C2-005 Advance allocation link | PASS | 现有流水 ADV-5FDF696D6F67458B 的分配历史显示 SO-2026-00004 两笔已核销金额；点击其中合同号到达 `/orders?detail=4`，订单工作台标题匹配。UI 中未发现采购合同方向的已分配预付款样例；该方向由前后端自动化测试覆盖。 |
| UAT-P2C2-006 No contract | PASS | 实际流水 FIN-91174D296D6B414B（样品费用）显示“未关联合同”，该交易行无 RouterLink。 |
| UAT-P2C2-007 Browser Back | PASS | 从 `/finance` 点击 PO-2026-00003 到 `/purchase-orders?detail=3`；浏览器 Back 返回 `/finance`，财务概览恢复且没有弹窗。 |
| UAT-P2C2-008 Finance Dashboard regression | PASS | `/finance` 当前有应付到期样例，无应收到期样例。点击 PO-2026-00003 后 `/purchase-orders?detail=3` 中采购单展开；应收及应付两种 dashboard 链接均由前端自动化测试覆盖。 |

## 自动化验证

- 后端新增 5 项 focused tests：无分配交易仍返回空数组；应收分配含 `order` ID；应付分配含 `purchase_order` ID；撤回分配保留合同 ID；多笔分配保留各自合同 ID 与编号；列表序列化随流水/分配行增加不产生逐行查询增长。
- 前端新增 4 项 RouterLink 测试：应收与应付计划、直接关联销售和采购流水、无合同纯文本、销售与采购分配历史、撤回历史链接、无 ID 但编号带 `SO-` 前缀时不误链、自定义编号按 ID 导航，以及财务概览应收/应付链接。
- `manage.py check`：通过。
- `manage.py makemigrations --check --dry-run`：通过，无迁移变更。
- `manage.py test`：504 项通过，10 项跳过；包含本次 5 项分配序列化与查询行为测试。
- `npm run test:unit`：109 项通过。
- `node --test tests/detail-drawer-typography.spec.js`：1 项通过。
- Vitest：15 个文件、90 项通过。
- `npm run build`：通过。Vite 有既有的主 JS 包超过 500 kB 提示（本地构建约 989.38 kB）。
- `git diff --check`：通过。

## CI 与限制

PCR-005 提交后的 GitHub Actions CI 结果待补。

真实数据中没有可在 UI 验证的采购合同分配历史，也没有财务概览应收方向的到期样例；对应导航均由自动化测试覆盖。没有创建交易或改动财务记录。
