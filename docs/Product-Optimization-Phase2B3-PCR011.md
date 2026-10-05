# SUNJACK-ERP Product Optimization Phase 2B-3 — PCR-011

## 验收结论

**PCR-011：PASS。** 2026-10-05 在本地开发环境通过内置 Browser 完成 UAT-P2B3-001 至 009。应收、应付页面均使用同一 `PaymentPlanPage`；所有搜索和筛选都由后端处理，页面只请求 `/payment-plans/`。

本阶段没有改动结算/付款工作流、会计计算、模型字段或权限策略；没有新增迁移。

## 实现

### 服务端

- `PaymentPlanViewSet.search_fields` 使用项目已启用的 DRF `SearchFilter`：`order__order_no`、`order__customer__name`、`purchase_order__purchase_no`、`purchase_order__supplier__name`。没有增加重复的手写 `icontains` 搜索。
- `due_from=YYYY-MM-DD` 转为 `due_date__gte`；`due_to=YYYY-MM-DD` 转为 `due_date__lte`。可单独使用，也可组合；两端均包含边界。日期比较自然排除没有 `due_date` 的计划。
- 日期必须是规范的 `YYYY-MM-DD`。无效日期返回 HTTP 400 并指出字段及格式；`due_from > due_to` 返回 HTTP 400，提示开始日期不能晚于结束日期，不交换日期。
- `direction`、`order`、`purchase_order`、`status`、`overdue` 既有过滤仍先作用于查询集，再与 DRF 搜索和日期范围组合。`overdue=true` 语义保持 `status=open AND due_date < timezone.localdate()`；没有改变状态定义。

### 前端

- `/receivables` 与 `/payables` 共用紧凑筛选栏：方向专用搜索提示、状态、仅看逾期、到期日从/至和重置。
- 搜索防抖 300 ms；状态、逾期、搜索、日期范围都作为服务器参数发送。每次筛选只重载 `/payment-plans/`，不额外读取客户、供应商、订单或采购单，也不在 Vue 中二次过滤结果。
- 每次请求都从当前路由组件属性发送 `direction=receivable` 或 `direction=payable`。日期逆序时显示明确错误并阻止无效请求；后端也独立校验。
- 摘要卡片按当前服务器筛选结果计算，并显示相应提示。

## 真实 UI UAT

环境：`http://127.0.0.1:5192`，开发数据，日期 2026-10-05（Asia/Shanghai）。验收均在内置 Browser 中完成；没有用 API、数据库或 shell 修改 UAT 业务数据。

| 项目 | 结果 | 实际 UI 结果 |
| --- | --- | --- |
| UAT-P2B3-001 应收客户搜索 | PASS | 在 `/receivables` 搜索 `Alpha GmbH`，显示 8 条计划，往来方均为 `UAT-R1 客户 Alpha GmbH`；清空搜索恢复默认 8 条。 |
| UAT-P2B3-002 应收合同搜索 | PASS | 搜索 `SO-2026-00032` 显示两条该订单计划，日期分别为 2026-10-04、2026-10-05；清空恢复默认列表。 |
| UAT-P2B3-003 应付供应商搜索 | PASS | 在 `/payables` 搜索供应商名片段 `历史快照测试`，显示 10 条计划，每行往来方均为 `UAT 供应商 B-历史快照测试`。 |
| UAT-P2B3-004 应付合同搜索 | PASS | 搜索 `PO-2026-00015` 显示两条该采购单计划，日期为 2026-10-02 和 2026-10-09。 |
| UAT-P2B3-005 到期日范围 | PASS | 应付日期范围 2026-10-02 至 2026-10-03 显示 6 条，日期都含在两端边界内；将起始日期收紧至 2026-10-03 后显示 3 条，全部日期为 2026-10-03。 |
| UAT-P2B3-006 搜索 + 日期范围 | PASS | 搜索 `历史快照测试` 并设范围 2026-10-08 至 2026-10-09，交集显示 `PO-2026-00008`（10-08）与 `PO-2026-00015`（10-09）；每行供应商和日期均符合条件。 |
| UAT-P2B3-007 状态 / 逾期回归 | PASS | 应付“待结清”显示 21 条；“已结清”显示 14 条且均标为已结清；“全部状态”显示 35 条，包含当前存在的待结清、已逾期和已结清计划。仅看逾期显示 12 条，均为待结清且到期日在本地日期 2026-10-05 之前；与“已结清”组合时为空，符合后端逾期条件。 |
| UAT-P2B3-008 重置 | PASS | 同时设置搜索 `PO-2026-00015`、已结清、仅看逾期、日期 2026-10-01 至 2026-10-31 后点击重置；搜索为空、状态恢复待结清、逾期关闭、两端日期为空，并恢复当前应付方向的 21 条默认列表。 |
| UAT-P2B3-009 方向隔离 | PASS | 应收搜索 `SO-2026-00032` 显示两条应收计划；导航到 `/payables` 后没有销售订单应收行，页面载入应付数据。搜索 `PO-2026-00015` 显示两条应付计划；返回 `/receivables` 后载入 8 条应收数据，往来方均为 Alpha 客户。路由切换回到该方向的默认筛选。 |

浏览器截图保存在本次任务的本地视觉证据目录：`PCR011-UAT-receivable-order-search.jpg` 与 `PCR011-UAT-payable-search-date-range.jpg`。

## 自动化验证

- `crm.tests.test_payment_plan_filters`：9 项测试通过，覆盖客户/订单号/供应商/采购单号搜索，单端及双端日期过滤、边界包含、搜索和日期/状态组合、方向及订单关联 ID 隔离、逾期语义、非法日期和反向日期范围 400。
- `python manage.py test`：491 项通过，10 项跳过。
- `python manage.py check`：通过，无系统问题。
- `python manage.py makemigrations --check --dry-run`：通过，无迁移变更。
- `npm run test:unit`：109 项通过。
- `node --test tests/detail-drawer-typography.spec.js`：1 项通过。
- `npx --no-install vitest run tests --environment jsdom --exclude tests/detail-drawer-typography.spec.js`：13 个文件、82 项通过；其中 `payment-plan-filters.spec.js` 4 项通过，覆盖方向参数、300 ms 防抖、全部筛选参数组合、重置、方向变化、服务端结果保持和逆序范围前端校验。
- `npm run build`：通过。Vite 提示主 JS 包约 986.85 kB，超过既有 500 kB 提示阈值；不影响构建。
- 完整测试包含 PCR-001、PCR-002、PCR-003 相关既有套件，均通过；无迁移。

## CI 与限制

基线 CI #122（实现前）backend、backend-postgres、frontend 均为 SUCCESS。实现提交 CI #123 的 backend 与 frontend 通过；backend-postgres 暴露了测试供应商编码超过 `Supplier.code` 两字符字段长度的问题。提交 `95802a6` 将夹具编码修正为合法两字符后，CI #124（运行 ID `37300563221`）的 backend、backend-postgres、frontend 均为 SUCCESS。

没有未通过的 PCR-011 项，也没有已知功能限制。UAT 使用已有本地开发计划数据；没有增加库存、采购、应收应付、结算或财务流水记录。
